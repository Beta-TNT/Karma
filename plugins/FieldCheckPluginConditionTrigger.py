import sys, os
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