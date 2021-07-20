'Karma is a status-based and plugin-extensible rule engine with callback mechanism.'

__author__ = 'Beta-TNT'
__version__= '3.1.0'

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
coreFieldCheckPluginName = 'core'
coreRulePluginName = 'core'

class AnalyseBase(object):

    'Project Karma'

    '''规则字段结构（字典）：
    Operator    ：字段匹配运算代码，见OperatorCode
    PrevFlag    ：时序分析算法历史匹配Flag构造模板，可以为空，为空则是入口点规则
    PrevFlagContent：仅在运行时生成，规则命中后自动生成，内容是生成的PrevFlag内容，以供插件或者后续其他逻辑调用
    ExcludeFlag ：反向Flag模板。当该Flag命中时规则被认为失配，可以为空
    RemoveFlag  ：字段匹配规则和历史匹配Flag命中之后，需要删除的Flag。可以为空
    RemoveFlagContent：仅在运行时生成，规则命中后自动生成，内容是生成的RemoveFlag内容，以供插件或者后续其他逻辑调用
    CurrentFlag ：时序分析算法本级规则命中后构造Flag的模板，可以为空
    CurrentFlagContent：仅在运行时生成，规则命中后自动生成，内容是生成的CurrentFlag内容，以供插件或者后续其他逻辑调用
    PluginName ：需要调用的插件名，
    FieldCheckList[]    ：字段匹配项列表
        字段匹配项结构（字典）：
            FieldName   ：要进行匹配的字段名
            MatchContent：匹配内容，当MatchCode的值是7或者-7且FieldName对应字段值也是字典的时候，MatchContent内容是子字段匹配规则集，结构相同
            MatchCode   ：匹配方式代码
            Operator    ：如果是多层数据和多层字段匹配规则，MatchCode=7或-7时有效，对下一级规则列表使用的字段匹配运算代码，定义同OperatorCode
            PluginName  ：这条规则需要调用的插件名
     ''' 
    # Lifetime/Threshold和Delay/Expire功能拆分成两个单独的插件，基础算法中不再实现

    # 3.0.0 版插件工作原理：
    # 规则如果需要调用插件，则先用插件的数据预处理函数DataPreProcess(InputData, InputRule)扫描整个数据和子规则
    # 如果遇到符合插件要求的子规则，则插件根据数据和子规则生成新的数据项，以%plugin_name%_#index#作为Key写入原数据
    # 例如下面这条示例规则的切片插件，如果输入数据里'SampleField1'字段的内容是'c:\windows\system32\sol.exe'，
    # 插件会在输入数据中增加名为'AnalyzerPluginSlicer_0'的字段，内容是'.exe'（r'c:\windows\system32\sol.exe'[-4:]）
    # 插件生成数据之后不会立即根据规则内容进行判定，而是将这条规则的FieldName修改为'AnalyzerPluginSlicer_0'
    # 插件执行流程结束之后，进入常规规则判定时，规则会使用'AnalyzerPluginSlicer_0'作为字段名，
    # 从结果中获取插件添加的字段的值，再根据基础的判定逻辑规则是否命中。
    # 相当于在插件判定流程结束之后，将一条需要调用插件的规则转换为常规规则
    # 这种机制问题在于不够灵活，而且在原数据中插入新字段的方式有重名的风险
    # 如果有两种插件要求的字段签名一致（或者其中一个是另一个的子集），会造成不可预料的结果

    # 拟修改方案
    # 废除规则中的 PluginNames 字段，改为在每条字段判定规则中增加 PluginName 字段
    # 废除插件预扫描机制和插入插件结果机制，改为在字段判定阶段执行插件功能和结果判断逻辑
    # 同一条字段判定规则只能执行一个插件
    # 如需使用插件的数据预处理功能，请将调用预处理插件的规则的MatchMode设为0（Preserved）
    # 引擎会按列表顺序扫描规则列表，使用map-reduce方式运行MatchMode为0的规则调用的插件处理输入数据
    # 并将这些规则从后续的判定流程中剔除
    # 引擎本身并不限制插件对输入数据甚至输入规则的修改，插件开发人员和用户应谨慎使用这一机制
    # 在调用插件的字段判定规则中，插件对该规则的所有字段有绝对的控制权，插件可以在运行时临时给规则添加或修改字段
    # 比如，对于分析引擎默认需要具备的MatchCode和MatchContent字段，其值的含义在插件规则中也可能被插件重定义
    # 实际上就是最初.net版分析引擎时的插件机制

    # 以上修改已经进行完毕，相当于将目前插件机制的范围缩小到字段匹配功能上
    # 版本号更新至3.1.0
    # 拟增加规则级插件，可接管单条规则匹配逻辑，实现数据预处理、过滤以及功能扩展等特性

    # 已增加规则级插件，接口名RulePlugin，原字段匹配插件接口名改为FieldCheckPlugin

    # 2021-07-19
    # 核心的默认字段匹配逻辑和规则匹配逻辑已拆分成单独的插件类，在引擎代码文件里实现
    # 两个核心插件强制加载，可通过名称'core'调用
    # 如果规则没有通过"PluginName"字段指定插件名，则默认调用core插件

    class PluginBase(object):
        '字段匹配插件基类'
        _PluginRuleFields = {}
        _AnalyseBase = None # 插件实例化时需要分析算法对象实例

        def __init__(self, AnalyseBaseObj):
            if not AnalyseBaseObj or AnalyseBase not in {type(AnalyseBaseObj), type(AnalyseBaseObj).__base__}:
                raise TypeError("invalid AnalyseBaseObj Type, expecting AnalyseBase.")
            else:
                self._AnalyseBase = AnalyseBaseObj # 构造函数需要传入分析算法对象实例

        def DefaultPluginRuleFields(self, RuleFieldName):
            try:
                return self._PluginRuleFields.get(RuleFieldName, [2])
            except:
                return None

        @property
        def PluginInstructions(self):
            '插件介绍文字'
            pass

        @property
        def PluginRuleFields(self):
            '插件独有的扩展规则字段，应返回一个dict()，其中key是字段名称，value是说明文字。无扩展字段可返回{}'
            return self._PluginRuleFields.copy()

        @property
        def AliasName(self):
            # 插件别名
            return ''

    class FieldCheckPluginBase(PluginBase):
        def DataPreProcess(self, InputData, InputFieldCheckRule):
            '字段匹配插件'
            # 默认情况下等价于原字段匹配逻辑
            if not InputFieldCheckRule.get('FieldName'):
                # 不指定字段名的时候，返回全部当前数据
                return InputData
            else:
                # 指定字段名，则返回字段值，如果字段不存在返回None
                return InputData.get(InputFieldCheckRule['FieldName'])
        
        def FieldCheck(self, TargetData, InputFieldCheckRule):
            return self._AnalyseBase._coreFieldCheckPlugin.FieldCheck(TargetData, InputFieldCheckRule)

        def AnalyseSingleField(self, InputData, InputFieldCheckRule):
            '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同DefaultSingleRuleTest()函数'
            # 如果无需操作对分析引擎内部对象，可无需改动该函数
            # 如无特殊处理，会调用默认的字段检查函数检查规则生成的数据
            # 如有需要，可重写本函数，返回布尔型数据
            if self.FieldCheck(
                self.DataPreProcess(
                    InputData,
                    InputFieldCheckRule
                ),
                InputFieldCheckRule
            ):
                return self.DataPostProcess(InputData, InputFieldCheckRule)
            else:
                return False
        
        def DataPostProcess(self, InputData, InputFieldCheckRule):
            return True

    class RulePluginBase(PluginBase):
        '规则插件基类'
        def DataPreProcess(self, InputData, InputRule):
            '数据预处理函数/数据业务函数，默认需要根据输入的数据和字段匹配规则返回一个结果，并代入后续的字段匹配流程'
            return InputData

        def AnalyseSingleData(self, InputData, InputRule):
            # 规则级插件逻辑，默认调用核心规则插件
            result, hitItem = self._AnalyseBase._coreRulePlugin.AnalyseSingleData(
                self.DataPreProcess(InputData, InputRule),
                InputRule
            )
            if result:
                # 条件执行
                return self.RuleHit(InputData, InputRule, hitItem)
            else:
                return False, hitItem
        
        def RuleHit(self, InputData, InputRule, HitItem):
            # 规则命中之后执行的代码，默认等同于默认的分析逻辑
            return True, HitItem

    _flags = dict() # Flag-缓存对象字典
    _plugins={
        'FieldCheckPlugins': dict(), # 字段匹配插件名-插件对象实例字典
        'RulePlugins': dict()       # 规则匹配插件-插件对象实例字典
    }
    _coreFieldCheckPlugin = None
    _coreRulePlugin = None

    PluginDir = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'plugins') # 插件存放路径
    DefaultEncoding = 'utf-8'

    def __init__(self):
        self._coreFieldCheckPlugin = CoreFieldCheck(self)
        self._coreRulePlugin = CoreRule(self)
        self._plugins['FieldCheckPlugins'] = self.__LoadPlugins('FieldCheckPlugin')
        self._plugins['RulePlugins'] = self.__LoadPlugins('RulePlugin')
        self._plugins['FieldCheckPlugins'][coreFieldCheckPluginName] = self._coreFieldCheckPlugin
        self._plugins['RulePlugins'][coreRulePluginName] = self._coreRulePlugin
        self.FieldCheckList = self._coreRulePlugin.FieldCheckList

    def __LoadPlugins(self, PluginInterfaceName):
        '加载插件，返回包含所有有效插件实例的插件名-插件实例字典'
        rtn = dict()
        if os.path.isdir(self.PluginDir):
            print("Loading plugin(s)...")
            rtn = dict(
                zip(
                    map(lambda x:os.path.splitext(x)[0],os.listdir(self.PluginDir)),
                    map(
                        lambda x:self.__LoadPlugin(PluginInterfaceName, x),
                        map(lambda x:os.path.splitext(x)[0],os.listdir(self.PluginDir))
                    )
                )
            )
            rtn = {k:v for k,v in rtn.items() if v is not None}
            alias = {}
            for i in rtn:
                if rtn[i]:
                    print(i)
                    if rtn[i].AliasName and rtn[i].AliasName not in rtn:
                        print('alias as %s' % rtn[i].AliasName)
                        alias[rtn[i].AliasName] = rtn[i]
                    else:
                        if rtn[i].AliasName:
                            print('alias name %s duplicated.'% rtn[i].AliasName)

        print('%s plugin(s) loaded.' % len(set(rtn.values())))
        rtn.update(alias)
        return rtn 
    
    def __LoadPlugin(self, PluginInterfaceName, PluginName):
        try:                 
            return getattr(
                __import__(
                    "plugins.{0}".format(PluginName),
                    fromlist = [PluginName]
                ),
                PluginInterfaceName
            )(self)
        except Exception as e:
            return None

    def FieldCheck(self, TargetData, InputFieldCheckRule):
        '默认的字段检查函数，输入字段的内容以及单条字段检查规则，返回True/False'
        'Default field check func, input target data and single field check rule, returns True/False indicating whether the rule hits.'
        # 为应对多层级输入数据结构，字段检查规则也应具备多层结构，采用递归形式进行匹配测试
        try:
            pluginObj = self._plugins['FieldCheckPlugins'].get(
                InputFieldCheckRule.get(
                    'PluginName'
                ),
                self._coreFieldCheckPlugin
            )
            return pluginObj.FieldCheck(TargetData, InputFieldCheckRule)
        except Exception as e:
            raise e

    @staticmethod
    def FlagGenerator(InputData, InputTemplate, BytesDecoding='utf-8'):
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

    def AnalyseSingleField(self, InputData, InputFieldCheckRule):
        '单独的插件执行函数，如果传入的插件名无效，返回失配结果False'
        pluginObj = self._plugins['FieldCheckPlugins'].get(InputFieldCheckRule.get('PluginName'), self._coreFieldCheckPlugin)
        if pluginObj:
            return pluginObj.AnalyseSingleField(InputData, InputFieldCheckRule)
        else:
            return False

    def AnalyseSingleData(self, InputData, InputRule):
        pluginObj = self._plugins['RulePlugins'].get(InputRule.get('PluginName'), self._coreRulePlugin)
        if pluginObj:
            return pluginObj.AnalyseSingleData(InputData, InputRule)
        else:
            return False
   
    def _DummyCallbackFunc(self, InputData, HitRule, HitItem, RemovedItem):
        import uuid
        return str(uuid.uuid1())

    def SingleRuleAnalyse(self, InputData, InputRule, RuleHitCallbackFunc):
        '单规则分析函数，完成Flag匹配和管理'
        rtn = None
        if not InputRule:
            return rtn
        # 第一步，构造PrevFlag, CurrentFlag和RemoveFlag
        prevFlag = self.FlagGenerator(InputData, InputRule.get("PrevFlag"))
        currentFlag = self.FlagGenerator(InputData, InputRule.get("CurrentFlag"))
        removeFlag = self.FlagGenerator(InputData, InputRule.get("RemoveFlag"))
        # 进行插件逻辑之前，将构造好的CurrentFlag和RemoveFlag内容写入规则备用
        InputRule['PrevFlagContent'] = prevFlag
        InputRule['CurrentFlagContent'] = currentFlag
        InputRule['RemoveFlagContent'] = removeFlag
        # 第二步，字段检查和插件调用，以及PrevFlag检查
        ruleCheckResult, hitItem = self.AnalyseSingleData(InputData, InputRule)
        if ruleCheckResult:
            # 第三步，如果规则命中，调用用户回调函数
            newDataItem = RuleHitCallbackFunc(
                InputData=InputData,
                HitRule=InputRule,
                HitItem=hitItem,
                RemovedItem=self._flags.pop(removeFlag, None) # 删除被RemoveFlag标记的Flag
            )
            rtn = newDataItem
            if currentFlag and currentFlag not in self._flags:
                if newDataItem:
                    # 构造CurrentFlag到用户返回对象的关联
                    self._flags[currentFlag] = newDataItem
            else: # Flag冲突或者为空, 忽略
                pass
        else:
            rtn = hitItem
        return rtn

    def MultiRuleAnalyse(self, InputData, InputRules, RuleHitCallbackFunc):
        '''默认的分析算法主函数。根据已经加载的规则和输入数据。'''
        if not RuleHitCallbackFunc:
            RuleHitCallbackFunc = self._DummyCallbackFunc
            
        if type(InputRules) in (list, set, tuple):
            # 输入规则是列表时，返回值是列表
            return list(
                map(
                    lambda x:self.SingleRuleAnalyse(
                        InputData=InputData,
                        InputRule=x,
                        RuleHitCallbackFunc=RuleHitCallbackFunc
                    ),
                    InputRules
                )
            )
        elif type(InputRules) == dict:
            # 输入规则是字典时，返回值也是字典，规则的Key对应规则命中的对象
            return dict(
                zip(
                    InputRules.keys(),
                    map(
                        lambda x:self.SingleRuleAnalyse(
                            InputData=InputData,
                            InputRule=x,
                            RuleHitCallbackFunc=RuleHitCallbackFunc
                        ),
                        InputRules.values()
                    )
                )
            )
        else:
            return None

class CoreFieldCheck(AnalyseBase.FieldCheckPluginBase):

    class FieldMatchMode(IntEnum):
        Preserved           = 0 # 为带字段比较功能插件预留，使用该代码的字段匹配结果永真，用于将插件处理结果传递给下一个插件
        Equal               = 1 # 值等匹配。数字相等或者字符串完全一样，支持二进制串比较，布尔型数据用0/1判断False和True
        SequenceContain     = 2 # 序列匹配，包括文本匹配（忽略大小写）和二进制串匹配，包含即命中。如果需要具体命中位置，请用AnalyzerPluginSeqFind插件
        RegexTest           = 3 # 正则匹配，正则表达式有匹配即命中。如需判断匹配命中的内容，请用AnalyzerPluginRegex插件
        GreaterThan         = 4 # 大于（数字）
        LengthEqual         = 5 # 元数据比较：数据长度等于（忽略数字类型数据）
        LengthGreaterThan   = 6 # 元数据比较：数据长度大于（忽略数字类型数据）
        SubFieldRuleList    = 7 # 应对多层数据的子规则集匹配，FieldName对应的字段必须是dict。如果不指定FieldName，则判断当前层级数据
 
        # 匹配代码对应的负数代表结果取反，例如-1代表不等于（NotEqual），不再显式声明
        # Negative code means flip the result, i.e., -1 means NotEqual, -4 means LessThanOrEqual
        # 目前仅支持插件应用在规则第一层逻辑
        # 不设立字段存在匹配（exists），如果字段匹配规则请求的字段名在数据中不存在，该字段规则匹配将被忽略
        # 如需判断字段匹配，请使用插件AnalyzerPluginFieldExists.py
    _PluginRuleFields = {
        "FieldName": (
            "要匹配的字段名", 
            str,
            ''
        ),
        "MatchContent": (
            "匹配内容", 
            str,
            None
        ),
        "MatchCode": (
            "匹配代码，对应负值代表结果取反", 
            int,
            1
        ),
        "Operator": (
            "多层匹配时深层数据规则集逻辑，负值代表结果取反", 
            int,
            1
        ),
        "PluginName": (
            "调用的插件名", 
            str,
            ''
        )
    }
    def FieldCheck(self, TargetData, InputFieldCheckRule):
        '默认的字段检查函数，输入字段的内容以及单条字段检查规则，返回True/False'
        'Default field check func, input target data and single field check rule, returns True/False indicating whether the rule hits.'
        # 为应对多层级输入数据结构，字段检查规则也应具备多层结构，采用递归形式进行匹配测试
        if not InputFieldCheckRule:
            return False
        fieldCheckResult = False
        matchContent = InputFieldCheckRule["MatchContent"]
        matchCode = InputFieldCheckRule["MatchCode"]
        if matchCode == self.FieldMatchMode.Preserved:
            fieldCheckResult = True
        elif abs(matchCode) == self.FieldMatchMode.Equal:
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
        elif abs(matchCode) == self.FieldMatchMode.SequenceContain:
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
        elif abs(matchCode) == self.FieldMatchMode.RegexTest:
            # 正则匹配（字符串） regex match
            if type(matchContent) != str:
                matchContent = str(matchContent)
            if type(TargetData) != str:
                TargetData = str(TargetData)
            fieldCheckResult = bool(re.search(matchContent, TargetData))
        elif abs(matchCode) == self.FieldMatchMode.GreaterThan:
            # 大小比较（数字，字符串尝试转换成数字，转换不成功略过该字段匹配）
            if type(matchContent) in (int, float) and type(TargetData) in (int, float):
                fieldCheckResult = (matchContent > TargetData)
            else:
                try:
                    fieldCheckResult = (int(matchContent) > int(TargetData))
                except:
                    pass
        elif abs(matchCode) == self.FieldMatchMode.LengthEqual:
            # 元数据比较：数据长度相等。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float, bool, complex):
                try:
                    fieldCheckResult = (len(matchContent) == int(TargetData))
                except:
                    pass
            else:
                pass
        elif abs(matchCode) == self.FieldMatchMode.LengthGreaterThan:
            # 元数据比较：数据长度大于。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float, bool, complex):
                try:
                    fieldCheckResult = (len(matchContent) > int(TargetData))
                except:
                    pass
            else:
                pass
        elif abs(matchCode) == self.FieldMatchMode.SubFieldRuleList:
            fieldCheckResult = self._AnalyseBase.FieldCheckList(
                InputData=TargetData,
                InputFieldCheckRuleList=matchContent,
                InputOperator=InputFieldCheckRule['Operator']
            )
        else:
            pass
        fieldCheckResult = ((matchCode < 0) ^ fieldCheckResult) # 负数代码，结果取反
        return fieldCheckResult

    def AnalyseSingleField(self, InputData, InputFieldCheckRule):
        '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同DefaultSingleRuleTest()函数'
        # 如果无需操作对分析引擎内部对象，可无需改动该函数
        # 如无特殊处理，会调用默认的字段检查函数检查规则生成的数据
        # 如有需要，可重写本函数，返回布尔型数据
        if self.FieldCheck(
            self.DataPreProcess(
                InputData,
                InputFieldCheckRule
            ),
            InputFieldCheckRule
        ):
            return self.DataPostProcess(InputData, InputFieldCheckRule)
        else:
            return False

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Core Single Field Check Plugin, same as the original."

    @property
    def AliasName(self):
        return coreFieldCheckPluginName

class CoreRule(AnalyseBase.RulePluginBase):
    _PluginRuleFields = {
        "PrevFlag": (
            "时序分析算法历史匹配Flag构造模板，可以为空，为空则是入口点规则", 
            str,
            ''
        ),
        "ExcludeFlag": (
            "反向Flag模板。当该Flag命中时规则被认为失配，可以为空", 
            str,
            ''
        ),
        "RemoveFlag": (
            "字段匹配规则和历史匹配Flag命中之后，需要删除的Flag。可以为空", 
            str,
            ''
        ),
        "CurrentFlag": (
            "时序分析算法本级规则命中后构造Flag的模板，可以为空", 
            str,
            ''
        ),
        "MatchCode": (
            "匹配代码，对应负值代表结果取反", 
            int,
            1
        ),
        "Operator": (
            "字段匹配运算代码，见OperatorCode", 
            int,
            1
        ),
        "PluginName": (
            "调用的插件名", 
            str,
            ''
        ),
        'FieldCheckList':(
            "字段检查规则列表", 
            list,
            []
        )
    }

    class OperatorCode(IntEnum):
        Preserved   = 0 # 预留，使用该代码的字段匹配结果永远为真
        OpAnd       = 1
        OpOr        = 2
        # 逻辑代码对应的负数代表结果取反，例如-1代表NotAnd，不再显式声明
 
        # 匹配代码对应的负数代表结果取反，例如-1代表不等于（NotEqual），不再显式声明
        # Negative code means flip the result, i.e., -1 means NotEqual, -4 means LessThanOrEqual
        # 目前仅支持插件应用在规则第一层逻辑
        # 不设立字段存在匹配（exists），如果字段匹配规则请求的字段名在数据中不存在，该字段规则匹配将被忽略
        # 如需判断字段匹配，请使用插件AnalyzerPluginFieldExists.py
    
    def FieldCheckList(self, InputData, InputFieldCheckRuleList, InputOperator=1):
        rtn = False
        if InputFieldCheckRuleList and type(InputFieldCheckRuleList) == list:
            fieldCheckResults = list(
                map(
                    lambda x:self._AnalyseBase.AnalyseSingleField(
                        InputData=InputData,
                        InputFieldCheckRule=x
                    ),
                    InputFieldCheckRuleList
                )
            )
            if abs(InputOperator) == self.OperatorCode.OpOr:
                rtn = any(fieldCheckResults)
            elif abs(InputOperator) == self.OperatorCode.OpAnd:
                rtn = all(fieldCheckResults)
            # 负数匹配代码，结果取反
            rtn = bool(fieldCheckResults) and ((InputOperator < 0) ^ rtn)
        else:
            rtn = True
        return rtn

    def SingleRuleTest(self, InputData, InputRule):
        '用数据匹配单条规则，如果数据匹配当前规则，返回Flag命中的应用层数据对象'
        if InputRule.get("Operator", 0) == self.OperatorCode.Preserved:
            # Magicode!
            return (True, None)

        if type(InputData) != dict or type(InputRule) != dict:
            raise TypeError("Invalid InputData or InputRule type, expecting dict")

        # 2021-07-14
        # 修改前序PrevFlag检查和字段匹配检查顺序
        # 修改为先进行PrevFlag检查，再进行字段匹配检查
        # 并且规则会预先生成PrevFlag并写入规则（PrevFlagContent）
        hitItem = None
        rtn= False 
        if InputRule.get("PrevFlag", ""):  # 判断前序flag是否为空
            prevFlag = InputRule["PrevFlagContent"]
            rtn, hitItem = prevFlag in self._AnalyseBase._flags, self._AnalyseBase._flags.get(prevFlag)
        else:
            rtn = True
        
        fieldCheckResult = self.FieldCheckList(
            InputData=InputData, 
            InputFieldCheckRuleList=InputRule.get('FieldCheckList', []),
            InputOperator=InputRule.get('Operator', 1)
        )
        excludeItem = self._AnalyseBase._flags.get(self._AnalyseBase.FlagGenerator(InputData, InputRule.get("ExcludeFlag")), None)
        if not fieldCheckResult or excludeItem:
            return False, excludeItem
        else:
            return rtn, hitItem
    
    def AnalyseSingleData(self, InputData, InputRule):
        # 规则级插件逻辑
        result, hitItem = self.SingleRuleTest(self.DataPreProcess(InputData, InputRule), InputRule)
        if result:
            # 条件执行
            return self.RuleHit(InputData, InputRule, hitItem)
        else:
            return False, hitItem

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Core Rule Plugin, same as the original."

    @property
    def AliasName(self):
        return coreRulePluginName
