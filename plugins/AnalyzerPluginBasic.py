import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

# 插件形式提供的分析引擎原版单规则匹配逻辑
# 直接调用基础算法的规则匹配函数实现

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    _ExtraRuleFields = {}
    _SettingItems = {}
    _SettingItemProperties = {}
    
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Basic Single Rule Test Plugin, same as the original."

    def __init__(self, AnalyseBaseObj):
        super().__init__(AnalyseBaseObj)