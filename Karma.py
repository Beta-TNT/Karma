'Karma is a status-based and plugin-extensible rule engine with callback mechanism.'

__author__ = 'Beta-TNT'
__version__= '3.2.0'

import os
from enum import IntEnum
from fnmatch import fnmatchcase, fnmatch
from re import search
from base64 import b64decode, b64encode

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
                # 不指定字段名（为空或者值不存在）的时候，返回全部当前数据
                return InputData
            else:
                # 指定字段名，则返回字段值，如果字段不存在返回None
                return InputData.get(InputFieldCheckRule['FieldName'])
        
        def FieldCheck(self, TargetData, InputFieldCheckRule):
            return self._AnalyseBase._coreFieldCheckPlugin.FieldCheck(TargetData, InputFieldCheckRule)

        def AnalyseSingleField(self, InputData, InputFieldCheckRule):
            '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。'
            # 如果无需操作对分析引擎内部对象，可无需改动该函数
            # 如无特殊处理，会调用默认的字段检查函数检查规则生成的数据
            # 如有需要，可重写本函数，返回布尔型数据
            # 已支持MatchContent字段内容是列表/元组/集合
            # 会使用当前规则的其他字段和MatchContent的每个元素进行对数据进行测试
            # 测试结果按Operator字段指定的逻辑进行组合

            fieldCheckResult = False
            matchContent = InputFieldCheckRule.get('MatchContent')
            operatorLogic = InputFieldCheckRule.get('Operator', 2)

            # 当MatchContent是复数（list, tuple, set）时，
            # 保持当前其他规则字段不变，使用当前规则和数据对每个MatchContent进行测试，
            # 多个结果默认使用OpAny逻辑运算符进行判断
            # 如果MatchContent不是复数，则将其包装成一元list，

            matchResults = map(
                lambda ruleItem:self.FieldCheck(
                    self.DataPreProcess(
                        InputData,
                        ruleItem
                    ),
                    ruleItem
                ),
                map(
                    lambda x:dict(InputFieldCheckRule, **{"MatchContent" : x}),
                    matchContent if type(matchContent) in (list, tuple, set) else [matchContent]
                )
            )

            matchResult = False
            if abs(operatorLogic) == 1:
                # OpAll
                matchResult = all(matchResults)
            elif abs(operatorLogic) == 2:
                # OpAny
                matchResult = any(matchResults)
            fieldCheckResult = (operatorLogic < 0) ^ matchResult

            if fieldCheckResult:
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
        self._plugins['FieldCheckPlugins'][self._coreFieldCheckPlugin.AliasName] = self._coreFieldCheckPlugin
        self._plugins['RulePlugins'][self._coreRulePlugin.AliasName] = self._coreRulePlugin
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

        # 元标签构造：Flag元数据化

        # 实现方案：
        # Flag构造时用户可选择命中的数据中指定字段和值作为Flag的一部分
        # 而且还可以指定加入新的键值对，新的键值对名称和内容都支持占位符
        # 也允许用户构造一个新的映射，将数据中的key以新的名字写入flag
        # 由于dict是可变数据类型，无法直接当做key，因此需要将其转化为元组（tuple）
        # 而且元素内容相同但顺序不同的元祖被认为是不同的元祖
        # 因此FLAG构造完毕转换成元组的时候按Key排序以去除特序性
        # 构造完毕的Flag（dict类型）按key进行排序，然后转化成tuple，形如：
        # ((key1, val1),(key2, val2)...(key_n, val_n))
        # 原核心规则将变成该核心规则的一个特例，即Flag元组只包含两个元素："Flag"和"{构造的Flag}"

        # 元数据化Flag的InputTemplate将是一个二元的有序序列（list或者tuple）
        # 每个元素都是字典（dict）
        # 第一个字典存储Flag字段映射。如果需要将引用数据中的字段改名之后写入flag，需要在写在这个字典里
        # 该字典的Key是引用数据中的字段名，Value是映射后在Flag里的新字段名。
        # 如果希望继续使用原数据字段名称无需修改，则将Value设置为和Key相同、None或者''
        # 尤其注意，如果引用的字段在原数据中不存在，写入的键值对是("FieldName", None)

        # 第二个字典存储附加字段，Key对应的值将经过占位符替换之后，和Key一起作为键值对写入Flag
        # 例：
        # 输入InputTemplate模板：
        # template = (
        #     {
        #         'Name': None,
        #         'Sex': 'Gender'
        #     },
        #     {
        #         'Info': '{Name}, {Age}, {Sex}'
        #     }
        # )
        # 输入数据：
        # data = {
        #     'Name': 'Alice',
        #     'Sex': 'Female',
        #     'Age': 26
        # }
        # 构造的Flag字典：
        # f = {
        #     'Name': 'Alice',
        #     'Gender': 'Female',
        #     'Info': 'Alice, 26, Female'
        # }
        # 经过排序后构造的元祖类型Flag：
        # ft = (
        #     ('Gender', 'Female'),
        #     ('Info', 'Alice, 26, Female'),
        #     ('Name', 'Alice')
        # )
    MetaFlagGenerator = staticmethod(
        lambda InputData, InputTemplate, IgnoreInvalidKey=True, BytesDecoding='utf-8': None if not (
            InputTemplate 
            and type(InputTemplate) in (tuple, list) 
            and all(map(lambda x:type(x) == dict, InputTemplate))
        ) else tuple(
            sorted(
                dict(
                    {
                        InputTemplate[0][k] if InputTemplate[0][k] 
                        else k:InputData[k] for k in InputTemplate[0] if k in InputData
                    } if IgnoreInvalidKey 
                    else {
                        InputTemplate[0][k] if InputTemplate[0][k] 
                        else k: InputData.get(k) for k in InputTemplate[0]
                    },
                    **dict(
                        {} if len(InputTemplate) < 2 else {
                            AnalyseBase.PlaceHolderReplace(
                                InputData,
                                k,
                                BytesDecoding
                            ):AnalyseBase.PlaceHolderReplace(
                                InputData,
                                InputTemplate[1][k],
                                BytesDecoding
                            ) for k in InputTemplate[1]
                        }
                    )
                ).items()
            )
        )
    )

    FlagGenerator = staticmethod(lambda InputData, InputTemplate, BytesDecoding='utf-8':
        AnalyseBase.MetaFlagGenerator(InputData, ({}, {'Flag': InputTemplate}), True, BytesDecoding)
        if type(InputTemplate) == str else
        AnalyseBase.MetaFlagGenerator(InputData, InputTemplate, BytesDecoding)
        if type(InputTemplate) in (tuple, list) and InputTemplate else
        None
    )

    # @staticmethod
    # def PlaceHolderReplace(InputData, InputTemplateString, BytesDecoding='utf-8'):
    #     '默认的Flag生成函数，根据输入的数据和模板构造Flag。将模板里用大括号包起来的字段名替换为InputData对应字段的内容，如果包含bytes字段，需要指定解码方法'
    #     if not (InputTemplateString and type(InputTemplateString) == str and type(InputData) == dict):
    #         return None
        
    #     for inputDataKey in InputData:
    #         inputDataItem = InputData[inputDataKey]
    #         if type(inputDataItem) in (bytes, bytearray):
    #             if BytesDecoding == 'base64':
    #                 InputData[inputDataKey] = base64.b64decode(inputDataItem)
    #             else:
    #                 try:
    #                     InputData[inputDataKey] = inputDataItem.decode(BytesDecoding)
    #                 except Exception:
    #                     InputData[inputDataKey] = ""
    #     rtn = InputTemplateString.format(**InputData)
    #     return rtn
    
    PlaceHolderReplace = staticmethod(
        lambda InputData, InputTemplateString, BytesDecoding='utf-8':
        None if not (InputTemplateString and type(InputTemplateString) == str and type(InputData) == dict) 
        else InputTemplateString.format(
            **{
                k:(
                    b64encode(InputData[k]).decode('ascii') if BytesDecoding == 'base64'
                    else InputData[k].decode(BytesDecoding)
                ) if type(InputData[k]) in (bytes, bytearray) 
                else InputData[k]
                for k in InputData
            }
        )
    )

    def AnalyseSingleField(self, InputData, InputFieldCheckRule):
        '单独的插件执行函数，如果包含的插件名无效，返回失配结果False'
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
        return ruleCheckResult, rtn

    def MultiRuleAnalyse(self, InputData, InputRules, RuleHitCallbackFunc, RecycleData=False):
        '''默认的分析算法主函数。根据已经加载的规则和输入数据。'''
        # RecycleData: 是否循环利用输入数据，如果为True，先前规则和插件对输入数据的修改将被保留下来作为下一条规则的输入数据
        # 对于输入规则集为dict这类无法预测规则执行顺序情况，建议将其设置为False
        if not RuleHitCallbackFunc:
            RuleHitCallbackFunc = self._DummyCallbackFunc
            
        if type(InputRules) in (list, set, tuple):
            # 输入规则是列表时，返回值是列表，剔除未命中的结果
            return {i[1] for i in
                map(
                    lambda x:self.SingleRuleAnalyse(
                        InputData=InputData if RecycleData else InputData.copy(),
                        InputRule=x,
                        RuleHitCallbackFunc=RuleHitCallbackFunc
                    ),
                    InputRules
                ) if i[0]
            }
        elif type(InputRules) == dict:
            # 输入规则是字典时，返回值也是字典，规则的Key对应规则命中的对象
            # 如果对应的规则未能命中(False, None)，则会从返回值中剔除
            return {k:v[1] for k,v in
                zip(
                    InputRules.keys(),
                    map(
                        lambda x:self.SingleRuleAnalyse(
                            InputData=InputData if RecycleData else InputData.copy(),
                            InputRule=x,
                            RuleHitCallbackFunc=RuleHitCallbackFunc
                        ),
                        InputRules.values()
                    )
                ) if v[0]
            }
        else:
            return None

class CoreFieldCheck(AnalyseBase.FieldCheckPluginBase):

    class FieldMatchMode(IntEnum):
        Preserved           = 0 # 为带字段比较功能插件预留，使用该代码的字段匹配结果永真，用于将插件处理结果传递给下一个插件
        Equal               = 1 # 值等匹配。数字相等或者字符串完全一样（大小写敏感），支持二进制串比较，布尔型数据用0/1判断False和True
        SequenceContain     = 2 # 序列匹配，包括文本匹配（大小写敏感）和二进制串匹配，包含即命中。如果需要具体命中位置，请用AnalyzerPluginSeqFind插件
        RegexTest           = 3 # 正则匹配，正则表达式有匹配即命中。如需判断匹配命中的内容，请用AnalyzerPluginRegex插件
        GreaterThan         = 4 # 大于（数字）
        LengthEqual         = 5 # 元数据比较：数据长度等于（忽略数字类型数据）
        LengthGreaterThan   = 6 # 元数据比较：数据长度大于（忽略数字类型数据）
        SubFieldRuleList    = 7 # 应对多层数据的子规则集匹配，FieldName对应的字段必须是dict。如果不指定FieldName，则判断当前层级数据
        WildcardMatch       = 8 # 大小写敏感的通配符字符串匹配，支持?和*。可以用 '?*' 或者 '*?' 判断字符串是否为空
        IcWildcardMatch     = 9 # 大小写不敏感的通配符字符串匹配，字符串不敏感相等匹配也可以使用这个

        # 如果有其他二元（数据-判定内容）运算判定，后续还可以更新到这里
        # 匹配代码对应的负数代表结果取反，例如-1代表不等于（NotEqual），不再显式声明
        # Negative code means flip the result, i.e., -1 means NotEqual, -4 means LessThanOrEqual

    _PluginRuleFields = {
        "FieldName": (
            "要匹配的字段名", 
            str,
            ''
        ),
        "MatchContent": (
            "匹配内容，当字段内容是list、tuple和set时会使用当前规则对每个匹配内容元素进行测试，然后根据Operator字段进行逻辑运算", 
            str,
            None
        ),
        "MatchCode": (
            "匹配代码，对应负值代表结果取反", 
            int,
            1
        ),
        "Operator": (
            "产生复数匹配结果时匹配结果之间的逻辑，负值代表结果取反", 
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
        matchContent = InputFieldCheckRule.get("MatchContent")
        matchCode = InputFieldCheckRule.get("MatchCode", 2)
        if matchCode == self.FieldMatchMode.Preserved:
            fieldCheckResult = True
        elif abs(matchCode) == self.FieldMatchMode.Equal:
            # 相等匹配 equal test
            try:
                if type(TargetData) in {bytes, bytearray} and type(matchContent)==str:
                    # 如果原数据类型是二进制，并且比较内容是字符串，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                    # for binary input data, try to decode it into BASE64 string before check
                    matchContent = b64decode(matchContent)
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
            # 文本匹配，支持字符串比对和二进制比对。当输入数据是二进制时，会尝试将字符串类型的比较内容按base64解码成bytes
            # Text match test, supporting text match and binary match.
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
                else:
                    if type(TargetData) in {bytes, bytearray} and type(matchContent)==str:
                        # 如果输入数据类型是二进制，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                        # for binary input data, try to decode it into BASE64 string before check
                        matchContent = b64decode(matchContent)
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
            fieldCheckResult = bool(search(matchContent, TargetData))
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
        elif abs(matchCode) == self.FieldMatchMode.WildcardMatch:
            fieldCheckResult = fnmatchcase(TargetData, matchContent)
        elif abs(matchCode) == self.FieldMatchMode.IcWildcardMatch:
            fieldCheckResult = fnmatch(TargetData, matchContent)
        else:
            pass
        fieldCheckResult = ((matchCode < 0) ^ fieldCheckResult) # 负数代码，结果取反
        return fieldCheckResult

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Core Single Field Check Plugin, same as the original."

    @property
    def AliasName(self):
        return "core"

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
        OpAll       = 1
        OpAny       = 2
        # 逻辑代码对应的负数代表结果取反，例如-1代表NotAnd，不再显式声明
    
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
            if abs(InputOperator) == self.OperatorCode.OpAny:
                rtn = any(fieldCheckResults)
            elif abs(InputOperator) == self.OperatorCode.OpAll:
                rtn = all(fieldCheckResults)
            # 负数匹配代码，结果取反
            rtn = bool(fieldCheckResults) and ((InputOperator < 0) ^ rtn)
        else:
            rtn = True
        return rtn

    def SingleRuleTest(self, InputData, InputRule):
        '用数据匹配单条规则，如果数据匹配当前规则，返回Flag命中的应用层数据对象'
        if type(InputData) != dict or type(InputRule) != dict:
            raise TypeError("Invalid InputData or InputRule type, expecting dict")

        # 2021-07-14
        # 修改前序PrevFlag检查和字段匹配检查顺序
        # 修改为先进行PrevFlag检查，再进行字段匹配检查
        # 并且规则会预先生成PrevFlag并写入规则（PrevFlagContent）
        hitItem = None
        rtn= False 
        if InputRule.get("PrevFlag", "") and not InputRule.get("Operator", 0) == self.OperatorCode.Preserved:  # 判断前序flag是否为空
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
        return "core"
