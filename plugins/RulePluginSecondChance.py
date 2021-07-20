import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.CoreRulePlugin):
    '失败条件插件，当主规则未能命中时测试指定的其他规则'
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