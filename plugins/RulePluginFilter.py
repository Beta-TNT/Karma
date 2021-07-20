import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.CoreRulePlugin):
    '过滤器插件，按简单单层规则过滤数据'
    # 对于功能扩展类插件，如无特殊需要，建议直接调用默认的单规则匹配函数作为用户函数，扩展功能加在匹配函数之后
    # 对于数据分析型插件，可自由选择先调用默认匹配函数还是后调用，或者直接将其代替
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