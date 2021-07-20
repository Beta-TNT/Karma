import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.CoreRulePlugin):
    '过滤器插件，按简单单层规则过滤数据'
    _PluginRuleFields = {
        'FilterRules': (
            '过滤器规则列表，基本等同于字段匹配规则列表',
            list,
            []
        ),
        'FilterOperator': (
            '过滤器规则逻辑，同默认字段匹配规则Operator字段定义，默认为1（OpAnd）',
            int,
            1,
            lambda x: x in (-2, -1, 1, 2),
            'Invalid FilterOperator: %s, expecting -2, -1, 1, 2.'
        ),
    }    

    def AnalyseSingleData(self, InputData, InputRule):
        # 规则级插件逻辑
        if self._AnalyseBase.FieldCheckList(InputData, InputRule.get('FilterRules'), InputRule.get('FilterOperator', 1)):
            return super().AnalyseSingleData(InputData, InputRule)
        else:
            return False, None

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Filter plugin"

    @property
    def AliasName(self):
        return 'filter'