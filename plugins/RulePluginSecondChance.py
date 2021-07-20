import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.CoreRulePlugin):
    '失败条件插件，当主规则未能命中时测试指定的其他规则'
    # 对于功能扩展类插件，如无特殊需要，建议直接调用默认的单规则匹配函数作为用户函数，扩展功能加在匹配函数之后
    # 对于数据分析型插件，可自由选择先调用默认匹配函数还是后调用，或者直接将其代替
    _PluginRuleFields = {
        'FailureBranch': (
            '当前规则未能命中时执行的规则',
            dict,
            {}
        )
    }    

    def AnalyseSingleData(self, InputData, InputRule):
        # 规则级插件逻辑
        result, hitItem = super().AnalyseSingleData(InputData, InputRule)
        if result:
            return True, hitItem
        else:
            return super().AnalyseSingleData(InputData, InputRule.get('FailureBranch', {}))

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Second Chance plugin"

    @property
    def AliasName(self):
        return '2ndchance'