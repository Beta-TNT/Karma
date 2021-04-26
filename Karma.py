'Karma is a status-based and plugin-extensible rule engine with callback mechanism.'

__author__ = 'Beta-TNT'
__version__= '3.0.0'

# Project Karma
# 3.0版本应增加RuleFeeder功能
# 功能设计：应用类似Lifetime和Expire的生存周期管理机制对动态规则进行管理
# 设计两个规则池：静态和动态。
# 静态规则池和原版规则列表一样，是固化的
# 动态规则池来自接口，由内部对象负责生命周期管理
# 使用的时候，两个规则池的有效规则合并成一个规则列表
# 静态规则池可以为空，完全依赖输入的动态规则

import re, os, base64
from enum import IntEnum
from abc import ABCMeta, abstractmethod

class AnalyseBase(object):
    'Project Karma'

    '''规则字段结构（字典）：
    Operator    ：字段匹配运算代码，见OperatorCode
    PrevFlag    ：时序分析算法历史匹配Flag构造模板，可以为空，为空则是入口点规则
    PrevFlagContent：规则命中后自动生成，内容是生成的PrevFlag内容，以供插件或者后续其他逻辑调用
    ExcludeFlag ：反向Flag模板。当该Flag命中时规则被认为失配，可以为空
    RemoveFlag  ：字段匹配规则和历史匹配Flag命中之后，需要删除的Flag。可以为空
    RemoveFlagContent：规则命中后自动生成，内容是生成的RemoveFlag内容，以供插件或者后续其他逻辑调用
    CurrentFlag ：时序分析算法本级规则命中后构造Flag的模板，可以为空
    CurrentFlagContent：规则命中后自动生成，内容是生成的CurrentFlag内容，以供插件或者后续其他逻辑调用
    PluginNames ：需要调用的插件名列表，请将插件名列表以分号分隔写入这个字段，引擎将按列表顺序以串行执行运行插件函数。原PluginName字段废除
    FieldCheckList[]    ：字段匹配项列表
        字段匹配项结构（字典）：
            FieldName   ：要进行匹配的字段名
            MatchContent：匹配内容，当MatchCode的值是7或者-7且FieldName对应字段值也是字典的时候，MatchContent内容是子字段匹配规则集，结构相同
            MatchCode   ：匹配方式代码
            Operator    ：如果是多层数据和多层字段匹配规则，MatchCode=7或-7时有效，对下一级规则列表使用的字段匹配运算代码，定义同OperatorCode
            PluginNames ：MatchCode=7或-7时，对子规则使用的插件列表。注意，子规则仅调用插件的数据预处理函数DataPreProcess()
    ''' # Lifetime/Threshold和Delay/Expire功能拆分成两个单独的插件，基础算法中不再实现

    SampleRule = {                                  # A simple sample rule dict
        'RuleName': 'SampleRule',                   # Optional, actually not even used.
        'Operator': 1,                              # Required
        'PrevFlag': '',                             # Optional, default value: None
        'ExcludeFlag': None,                        # Optional, default value: None
        'RemoveFlag': None,                         # Optional, default value: None
        'CurrentFlag': 'RuleHit:{Timestamp}',       # Optional, default value: None
        'PluginNames': 'AnalyzerPluginSlicer',      # Optional, if plugin is not needed
        'FieldCheckList': [                         # Optional, if field check is not necessary
            {
                'FieldName': 'SampleField1',        # Required
                'MatchCode': 1,                     # Required
                'MatchContent': '.ocx',             # Required
                'SliceFrom': -4,                    # AnalyzerPluginSlicer Plugin rule field
                'SliceTo': None,                    # AnalyzerPluginSlicer Plugin rule field
                'Step': None                        # AnalyzerPluginSlicer Plugin rule field
            },
            {
                'FieldName': 'SampleField2',        # Required
                'MatchCode': -7,                    # Required
                'Operator': -2,                     # Required for MatchCode = 7 or -7
                'MatchContent': [                   # Required
                    {
                        'FieldName': 'SubSampleField1',
                        'MatchCode': 2,
                        'MatchContent': '.exe'
                    },
                    {
                        'FieldName': 'SubSampleField2',
                        'MatchCode': 2,
                        'MatchContent': '.dll'
                    }
                ]
            }
        ]
    }

    class OperatorCode(IntEnum):
        Preserved   = 0 # 预留，使用该代码的字段匹配结果永远为真
        OpAnd       = 1
        OpOr        = 2
        # 逻辑代码对应的负数代表结果取反，例如-1代表NotAnd，不再显式声明
        # Negative code means flip the result, i.e., -1 means OpNotAnd.

    class FieldMatchMode(IntEnum):
        Preserved           = 0 # 为带字段比较功能插件预留，使用该代码的字段匹配结果永真，用于将插件处理结果传递给下一个插件
        Equal               = 1 # 值等匹配。数字相等或者字符串完全一样，支持二进制串比较
        SequenceContain     = 2 # 序列匹配，包括文本匹配（忽略大小写）和二进制串匹配，包含即命中。如果需要具体命中位置，请用AnalyzerPluginSeqFind插件
        RegexTest           = 3 # 正则匹配，正则表达式有匹配即命中。如需判断匹配命中的内容，请用AnalyzerPluginRegex插件
        GreaterThan         = 4 # 大于（数字）
        LengthEqual         = 5 # 元数据比较：数据长度等于（忽略数字类型数据）
        LengthGreaterThan   = 6 # 元数据比较：数据长度大于（忽略数字类型数据）
        SubFieldRuleList    = 7 # 应对多层数据的子规则集匹配，FieldName对应的字段必须是dict
        # 匹配代码对应的负数代表结果取反，例如-1代表不等于（NotEqual），不再显式声明
        # Negative code means flip the result, i.e., -1 means NotEqual, -4 means LessThanOrEqual
        # 目前仅支持插件应用在规则第一层逻辑
        
    class PluginBase(object):
        '分析插件基类'
        _ExtraRuleFields = {}
        _ExtraFieldMatchingRuleFields = {}
        _AnalyseBase = None # 插件实例化时需要分析算法对象实例

        def __init__(self, AnalyseBaseObj):
            if not AnalyseBaseObj or AnalyseBase not in {type(AnalyseBaseObj), type(AnalyseBaseObj).__base__}:
                raise TypeError("invalid AnalyseBaseObj Type, expecting AnalyseBase.")
            else:
                self._AnalyseBase = AnalyseBaseObj # 构造函数需要传入分析算法对象实例

        def DataPreProcess(self, InputData, InputRule):
            '数据预处理函数，如果插件依托默认规则判断逻辑，仅需要在判断之前对数据进行预处理，可将业务代码放在这个函数'
            pass

        def AnalyseSingleData(self, InputData, InputRule):
            '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同DefaultSingleRuleTest()函数'
            # 如果无需操作对分析引擎内部对象，可无需改动该函数
            self.DataPreProcess(InputData, InputRule)
            hitResult, hitItem = self._AnalyseBase.DefaultSingleRuleTest(InputData, InputRule)
            if hitResult:
                return self.DataPostProcess(InputData, InputRule, hitItem)
            else:
                return hitResult, hitItem
        
        def DataPostProcess(self, InputData, InputRule, HitItem):
            '数据后处理函数，仅当数据命中插件规则后执行，返回值结构同DefaultSingleRuleTest()函数'
            return True, HitItem

        def DefaultExtraRuleFieldValue(self, RuleFieldName):
            try:
                return self._ExtraRuleFields.get(RuleFieldName, [2])
            except:
                return None

        def DefaultFieldMatchingRuleFieldValue(self, RuleFieldName):
            try:
                return self._ExtraFieldMatchingRuleFields.get(RuleFieldName[2])
            except:
                return None


        @property
        def PluginInstructions(self):
            '插件介绍文字'
            pass

        @property
        def ExtraRuleFields(self):
            '插件独有的扩展规则字段，应返回一个dict()，其中key是字段名称，value是说明文字。无扩展字段可返回{}'
            rtn = self._ExtraRuleFields.copy()
            if self._ExtraFieldMatchingRuleFields:
                rtn['FieldCheckList'] = self._ExtraFieldMatchingRuleFields.copy()
            return rtn

    _flags = dict() # Flag-缓存对象字典
    _plugins = dict() # 插件名-插件对象实例字典
    _pluginExtraRuleFields = dict() # 插件专属规则字段名-插件对象字典，暂无实际应用

    PluginDir = os.path.abspath(os.path.dirname(__file__)) + '/plugins/' # 插件存放路径
    DefaultEncoding = 'utf-8'

    def __init__(self):
        self.__LoadPlugins('AnalysePlugin')

    def __LoadPlugins(self, PluginInterfaceName):
        '加载插件，返回包含所有有效插件实例的插件名-插件实例字典'
        if os.path.isdir(self.PluginDir):
            self._plugins.clear()
            print("Loading plugin(s)...")
            for plugin in filter(
                lambda str:(True, False)[str[-4:] == '.pyc' or str.find('__init__.py') != -1],
                os.listdir(self.PluginDir)
            ):
                try:
                    pluginName = os.path.splitext(plugin)[0]
                    self._plugins[pluginName] = getattr(
                        __import__(
                            "plugins.{0}".format(pluginName),
                            fromlist = [pluginName]
                        ),
                        PluginInterfaceName
                    )(self)
                    print(pluginName)
                except Exception:
                    continue
            print("{0} plugin(s) loaded.".format(len(self._plugins)))

    def FieldCheck(self, TargetData, InputFieldCheckRule):
        '默认的字段检查函数，输入字段的内容以及单条字段检查规则，返回True/False'
        'Default field check func, input target data and single field check rule, returns True/False indicating whether the rule hits.'
        # 为应对多层级输入数据结构，字段检查规则也应具备多层结构，采用递归形式进行匹配测试
        if type(InputFieldCheckRule) != dict:
            raise TypeError("Invalid InputFieldCheckRule type, expecting dict")
        fieldCheckResult = False
        matchContent = InputFieldCheckRule["MatchContent"]
        matchCode = InputFieldCheckRule["MatchCode"]
        if matchCode == AnalyseBase.FieldMatchMode.Preserved:
            fieldCheckResult = True
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.Equal:
            # 相等匹配 equal test
            try:
                if type(TargetData) in {bytes, bytearray} and type(matchContent)==str:
                    # 如果原数据类型是二进制，并且比较内容是字符串，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                    # for binary input data, try to decode it into BASE64 string before check
                    matchContent = base64.b64decode(matchContent)
                    # 特别注明。如果需要比较二进制的原数据是否是某个字符串的二进制编码，需要先将比较内容字符串按这种编码解码成bytes，再编码成BASE64
                    # InputFieldCheckRule["MatchContent"] = base64.b64encode(matchContentStr.encode('utf-8')))
                if type(matchContent) == type(TargetData) or {type(TargetData), type(matchContent)} in {bytes, bytearray}:
                    # 同数据类型，直接判断
                    # same data type, test them directly
                    fieldCheckResult = (matchContent == TargetData)
                else:
                    # 不同数据类型，都转换成字符串判断
                    # different data type, convert'em all into string before test
                    fieldCheckResult = (str(matchContent) == str(TargetData))
            except:
                pass
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.SequenceContain:
            # 文本匹配，支持字符串比对和二进制比对。字符串比对忽略大小写。
            # 如果需要进行二进制匹配，或者大小写敏感匹配，请将输入数据和比较内容都转换成bytes，并将比较内容编码成BASE64串再使用。
            # Text match test, supporting text match (ignore case) and binary match.
            # In case you need case-sensitive check,
            # encode test data and match content into bytes, and encode match content into base64 string before using.
            try:
                if type(matchContent) not in {bytes, bytearray, str}:
                    # pre-proccess for matchContent: convert it into string if it's not bytes, bytearray or str.
                    matchContent = str(matchContent)
                if type(TargetData) not in (bytes, bytearray, str, list):
                    # same pre-process for target data.
                    TargetData = str(TargetData)
        
                if {type(TargetData), type(matchContent)} in {bytes, bytearray} or type(TargetData) == type(matchContent) or type(TargetData) == list:
                    # 如果都是二进制、相同数据类型或者目标数据是列表，无需预处理
                    # no additional pre-process for them if they are all binary or all string
                    pass
                elif type(TargetData) in {bytes, bytearray} and type(matchContent)==str:
                    # 如果输入数据类型是二进制，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                    # for binary input data, try to decode it into BASE64 string before check
                    matchContent = base64.b64decode(matchContent)
                else:
                    pass
                fieldCheckResult = (matchContent in TargetData)
            except:
                pass
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.RegexTest:
            # 正则匹配（字符串） regex match
            if type(matchContent) != str:
                matchContent = str(matchContent)
            if type(TargetData) != str:
                TargetData = str(TargetData)
            fieldCheckResult = bool(re.match(matchContent, TargetData))
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.GreaterThan:
            # 大小比较（数字，字符串尝试转换成数字，转换不成功略过该字段匹配）
            if type(matchContent) in (int, float) and type(TargetData) in (int, float):
                fieldCheckResult = (matchContent > TargetData)
            else:
                try:
                    fieldCheckResult = (int(matchContent) > int(TargetData))
                except:
                    pass
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.LengthEqual:
            # 元数据比较：数据长度相等。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float, bool, complex):
                try:
                    fieldCheckResult = (len(matchContent) == int(TargetData))
                except:
                    pass
            else:
                pass
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.LengthGreaterThan:
            # 元数据比较：数据长度大于。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float, bool, complex):
                try:
                    fieldCheckResult = (len(matchContent) > int(TargetData))
                except:
                    pass
            else:
                pass
        elif abs(matchCode) == AnalyseBase.FieldMatchMode.SubFieldRuleList:
            # 子规则字段匹配，采用递归调用
            # TODO: 目前已经将插件功能函数拆分成三部分：
            # 数据预处理、规则判断和数据后处理
            # 如果在子规则中指定了调用插件，应先按顺序执行所有指定插件的数据预处理函数DataPreProcess()
            # 子规则需要包括插件调用所必须的所有字段
            pluginNameList = list(
                filter(
                    None, 
                    map(
                        lambda str:str.strip(), 
                        InputFieldCheckRule.get('PluginNames','').split(';')
                    )
                )
            )
            if pluginNameList:
                for pluginName in pluginNameList:
                    pluginObj = self._plugins.get(pluginName)
                    if pluginObj:
                        # 调用插件的数据预处理函数
                        pluginObj.DataPreProcess(TargetData, InputFieldCheckRule)

            fieldCheckResult = self.FieldCheckList(
                InputData=TargetData,
                InputFieldCheckRule={
                    'Operator':InputFieldCheckRule['Operator'],
                    'FieldCheckList': matchContent
                }
            )
        else:
            pass
        fieldCheckResult = ((matchCode < 0) ^ fieldCheckResult) # 负数代码，结果取反
        return fieldCheckResult

    @staticmethod
    def FlagGenerator(InputData, InputTemplate, BytesDecoding='utf-16'):
        '默认的Flag生成函数，根据输入的数据和模板构造Flag。将模板里用大括号包起来的字段名替换为InputData对应字段的内容，如果包含bytes字段，需要指定解码方法'
        if not InputTemplate:
            return None

        if type(InputTemplate) != str:
            raise TypeError("Invalid Template type, expecting str")
        if type(InputData) != dict:
            raise TypeError("Invalid InputData type, expecting dict")
            
        for inputDataKey in InputData:
            inputDataItem = InputData[inputDataKey]
            if type(inputDataItem) in (bytes, bytearray):
                try:
                    InputData[inputDataKey] = inputDataItem.decode(BytesDecoding)
                except Exception:
                    InputData[inputDataKey] = ""

        rtn = InputTemplate.format(**InputData)
        return rtn

    def FieldCheckList(self, InputData, InputFieldCheckRule):
        rtn = False
        if type(InputFieldCheckRule.get("FieldCheckList")) in (dict, list) and InputFieldCheckRule["FieldCheckList"]:
            fieldCheckResults = list(
                map(
                    lambda y:self.FieldCheck(InputData[y['FieldName']], y),
                    filter(
                        lambda x:x.get('FieldName') in InputData,
                        InputFieldCheckRule["FieldCheckList"]
                    )
                )
            )
            if abs(InputFieldCheckRule["Operator"]) == AnalyseBase.OperatorCode.OpOr:
                rtn = any(fieldCheckResults)
            elif abs(InputFieldCheckRule["Operator"]) == AnalyseBase.OperatorCode.OpAnd:
                rtn = all(fieldCheckResults)
            rtn = bool(fieldCheckResults) and ((InputFieldCheckRule["Operator"] < 0) ^ rtn) 
        else:
            rtn = True
        return rtn

    def DefaultSingleRuleTest(self, InputData, InputRule):
        '用数据匹配单条规则，如果数据匹配当前规则，返回Flag命中的应用层数据对象'
        if InputRule.get("Operator", 0) == AnalyseBase.OperatorCode.Preserved:
            # Magicode!
            return (True, None)

        if type(InputData) != dict or type(InputRule) != dict:
            raise TypeError("Invalid InputData or InputRule type, expecting dict")

        fieldCheckResult = self.FieldCheckList(InputData=InputData, InputFieldCheckRule=InputRule)

        if not fieldCheckResult or self.FlagGenerator(InputData, InputRule.get("ExcludeFlag")) in self._flags:
            return (False, None)

        if InputRule["PrevFlag"]:  # 判断前序flag是否为空
            prevFlag = self.FlagGenerator(InputData, InputRule.get("PrevFlag"))
            rtn, hitItem = prevFlag in self._flags, self._flags.get(prevFlag)
            # 将构造好的PrevFlag内容写入规则备用
            InputRule['PrevFlagContent'] = prevFlag
            return rtn, hitItem
        else:
            return (True, None)
            
    def SingleRuleTest(self, InputData, InputRule):
        '单规则匹配函数，可根据需要在派生类里重写。本函数也是插件的入口位置'
        pluginNameList = list(
            filter(
                None, 
                map(
                    lambda str:str.strip(), 
                    InputRule.get('PluginNames','').split(';')
                )
            )
        )
        if pluginNameList:
            pluginResults = set()
            for pluginName in pluginNameList:
                pluginObj = self._plugins.get(pluginName)
                if pluginObj:
                    pluginResult = pluginObj.AnalyseSingleData(InputData, InputRule)
                    pluginResults.add(pluginResult)
                    if not pluginResult[0]:
                        break
            return (False, None) if len(pluginResults) != 1 else pluginResults.pop()
        else:
            return self.DefaultSingleRuleTest(InputData, InputRule)

    def PluginExec(self, PluginName, InputData, InputRule):
        '单独的插件执行函数，如果传入的插件名无效，返回失配结果(False, None)'
        PluginObj = self._plugins.get(PluginName)
        if PluginObj:
            return PluginObj.AnalyseSingleData(InputData, InputRule)
        else:
            return (False, None)
    
    def _DummyCallbackFunc(self, InputData, HitRule, HitItem, CurrentFlag):
        import uuid
        return str(uuid.uuid1())

    def SingleRuleAnalyse(self, InputData, InputRule, RuleHitCallbackFunc):
        '单规则分析函数，完成Flag匹配和管理'
        rtn = None
        if not InputRule:
            return rtn
            
        currentFlag = self.FlagGenerator(InputData, InputRule.get("CurrentFlag"))
        removeFlag = self.FlagGenerator(InputData, InputRule.get("RemoveFlag"))
        # 进行插件逻辑之前，将构造好的CurrentFlag和RemoveFlag内容写入规则备用
        InputRule['CurrentFlagContent'] = currentFlag
        InputData['RemoveFlagContent'] = removeFlag

        ruleCheckResult, hitItem = self.SingleRuleTest(InputData, InputRule)
        if ruleCheckResult:
            newDataItem = RuleHitCallbackFunc(
                InputData=InputData,
                HitRule=InputRule,
                HitItem=hitItem, 
                CurrentFlag=currentFlag
            )
            if currentFlag and currentFlag not in self._flags:
                self._flags.pop(removeFlag, None)
                if newDataItem:
                    self._flags[currentFlag] = newDataItem
                    rtn = newDataItem
            else: # Flag冲突, 忽略
                pass
        return rtn

    def MultiRuleAnalyse(self, InputData, InputRules, RuleHitCallbackFunc):
        '''默认的分析算法主函数。根据已经加载的规则和输入数据。'''
        if not RuleHitCallbackFunc:
            RuleHitCallbackFunc = self._DummyCallbackFunc
            
        if not InputRules:
            return None

        rtn = set()  # 该条数据命中的缓存对象集合

        for rule in InputRules:
            result = self.SingleRuleAnalyse(InputData, rule, RuleHitCallbackFunc)
            if result:
                rtn.add(result)
        return rtn