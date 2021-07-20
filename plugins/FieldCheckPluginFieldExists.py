import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '字段是否匹配判断插件'
    _PluginRuleFields = {
        "FieldName": (
            "要判断的字段名或者字段名列表", 
            list,
            []
        ),
        "FieldExistsMatchCode": (
            "多个判断结果逻辑。1=All, 2=Any，负数取反", 
            int,
            0,
            lambda x:x in (-2, -1, 1, 2),
            'invalid value range: %s, expecting -2, -1, 1, 2'
        )
    }

    def DataPreProcess(self, InputData, InputRule):
        checkList = InputRule.get('FieldName', [])
        pluginResult = False
        if type(checkList) == str:
            checkList = [checkList]
        if checkList:
            if abs(InputRule['FieldExistsMatchCode']) == 1:
                pluginResult = all(map(lambda x:x in InputData, checkList))
            elif abs(InputRule['FieldExistsMatchCode']) == 2:
                pluginResult = any(map(lambda x:x in InputData, checkList))
            else:
                pass
            pluginResult = ((InputRule['FieldExistsMatchCode'] < 0) ^ pluginResult)
        return pluginResult

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "字段存在判断插件"

    @property
    def AliasName(self):
        return 'existscheck'