import sys, os, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '切片比较插件'
    _ExtraFieldMatchingRuleFields = {
        "SliceFrom": (
            "切片起始", 
            int,
            0
        ),
        "SliceTo": (
            "切片截止，可以为空", 
            int,
            None
        ),
        "Step": (
            "切片步长，无此项默认为1", 
            int,
            1
        )
    }

    def DataPreProcess(self, InputData, InputRule):
        '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同SingleRuleTest()函数'
        # 切片比较插件，实现数据部分对比和偏移量截取功能
        # 在字段比较子规则里加入SliceFrom和SliceTo两个字段，整数，前者可为负，后者可以为None，实际上就是Python切片操作的前后两个参数
        # 由于内容性质，仅支持Equal/NotEqual和TextMatching/NotTextMatching两种比较运算
        # 运算结果会动态修改已输入的规则和数据。例如：
        # 输入字段切片比较规则（判断name字段内容最后3个字符是不是‘Doe’）：
        # {
        #    'FieldName': 'name',
        #    'MatchContent': 'Doe',
        #    'MatchCode': 1,
        #    'SliceFrom': -3,
        #    'SliceTo': None,
        #    'Step': None
        # }
        # 输入数据：
        # {'name': 'John Doe'}
        # 实际匹配运算内容：(InputData['name'][-3,] == 'Doe')
        # 在本例中，匹配结果是命中，于是在原数据中追加字段保存匹配结果：
        # {'name': 'John Doe', 'AnalyzerPluginSlicer_Result_0': True}
        # 最后改写当前切片匹配规则，使其变成原分析引擎可处理的普通规则：
        # {
        #    'FieldName': 'AnalyzerPluginSlicer_Result_0',
        #    'MatchContent': True,
        #    'MatchCode': 1
        # }
        # 这个机制可以推广到其他字段匹配插件
        # 当然也有不增加原数据字段的办法，在原数据里随便取一个字段，改写当前规则内容判断是否相等即可

        # 20201231更新
        # 修改匹配方法。按指定的切片操作将匹配目标内容从目标字段中提取出来
        # 在原数据中新建字段，名为“AnalyzerPluginSlice_Content_#”，内容是切片内容
        # 修改规则，将匹配字段改名为“AnalyzerPluginSlice_Content_#”
        # 规则匹配方式和匹配内容都不用修改，用当前匹配方式支持相等、文本、正则等匹配，
        # 最后让基础算法完成实际的匹配操作，而不是本插件。SliceFrom和SliceTo参数会被忽略

        fieldCheckList = InputRule.get('FieldCheckList')
        if fieldCheckList:
            i = 0
            for fieldCheckRule in filter(
                lambda x:'SliceFrom'in x and type(
                    InputData.get(
                        x['FieldName']
                    )
                ) in (str, bytes, bytearray), 
                fieldCheckList
            ):
                try:
                    targetData = InputData[fieldCheckRule['FieldName']][fieldCheckRule['SliceFrom']:fieldCheckRule.get('SliceTo'):fieldCheckRule.get('Step', 1)]
                    targetDataFieldName = '%s_Content_%s' % (self._CurrentPluginName, i)
                    InputData[targetDataFieldName] = targetData
                    fieldCheckRule['FieldName'] = targetDataFieldName
                    i += 1
                except:
                    continue
                
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "切片比较，支持原字段匹配全部的匹配操作代码，包括二进制支持。"