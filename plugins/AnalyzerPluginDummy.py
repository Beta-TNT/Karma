import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '插件基类'
    # 对于功能扩展类插件，如无特殊需要，建议直接调用默认的单规则匹配函数作为用户函数，扩展功能加在匹配函数之后
    # 对于数据分析型插件，可自由选择先调用默认匹配函数还是后调用，或者直接将其代替

    _ExtraRuleFields = {}
    _ExtraFieldMatchingRuleFields = {}

    def __init__(self, AnalyseBaseObj):
        # 重写原构造函数，加载配置
        super().__init__(AnalyseBaseObj)

    def DataPreProcess(self, InputData, InputRule):
        # add your own data preprocess code here
        super().DataPreProcess(InputData, InputRule)

    def AnalyseSingleData(self, InputData, InputRule):
        '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同_DefaultSingleRuleTest()函数'
        return super().AnalyseSingleData(InputData, InputRule)

    def DataPostProcess(self, InputData, InputRule, HitItem):
        # add your own postprocess/function extension code here

        # you can even call other plugin func here like this:

        # try:
        #     self._AnalyseBase.PluginExec('OtherPluginName', InputData, InputRule)
        # except Exception:
        #     pass # "Sorry, the plugin you've called does not exist."
        return super().DataPostProcess(InputData, InputRule, HitItem)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Dummy plugin for test and sample."