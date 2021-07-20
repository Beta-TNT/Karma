import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.CoreFieldCheck):
    '条件分支判断插件'
    _PluginRuleFields = {
        "SuccessBranch": (
            "字段判定为真时执行的字段匹配规则。如需执行多条规则，请使将子规则的MatchCode字段设置为7/-7", 
            dict,
            {}
        ),
        "FailureBranch":(
            "字段判定为假时执行的字段匹配规则。如需执行多条规则，请使将子规则的MatchCode字段设置为7/-7", 
            dict,
            {}
        )
    }

    def DataPostProcess(self, InputData, InputFieldCheckRule):
        return self._AnalyseBase.AnalyseSingleField(
            InputData,
            InputFieldCheckRule.get('SuccessBranch', {})
        )

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
            return self._AnalyseBase.AnalyseSingleField(
                InputData,
                InputFieldCheckRule.get('FailureBranch', {})
            )

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "条件分支判断插件"

    @property
    def AliasName(self):
        return 'condition'
