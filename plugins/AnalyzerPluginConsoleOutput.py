import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '屏幕输出插件'
    _ExtraRuleFields = {
        "PrintContent": (
            "输出内容，支持占位符，可使用Python规范字体颜色前后缀", 
            str,
            None
        ),
        "PrintContentLines": (
            "输出内容列表，如果指定了PrintContent的值，则PrintContent的值将插入PrintContentLines的第一条", 
            list,
            []
        ),
        "sep": (
            "print()函数可选参数sep，不指定则采用默认值", 
            str,
            None
        ),
        "end": (
            "print()函数可选参数end，不指定则采用默认值", 
            str,
            None
        ),
        "AdditionalOutput": (
            "附加输出内容，0=不附加，1=打印触发数据；2=打印命中规则；3=打印前两者，为空或者不存在则默认为0", 
            int,
            0,
            lambda x:0<=x<=3,
            'invalid value range: %s, expecting 0-3'
        )
    }

    def DataPostProcess(self, InputData, InputRule, HitItem):
        try:
            printContents = map(
                lambda x:self._AnalyseBase.FlagGenerator(InputData, x),
                filter(
                    None,
                    [InputRule.get('PrintContent')] + InputRule.get('PrintContentLines')
                )
            )
            if printContents:
                print(*printContents, end=InputRule.get('end'), sep=InputRule.get('sep'))

            additionalOutput = InputRule.get('AdditionalOutput', self.DefaultExtraRuleFieldValue('AdditionalOutput'))
            if additionalOutput & 1:
                print("Hit data:\r\n%s" % InputData)
            if additionalOutput & 2:
                print("Hit rule:\r\n%s" % InputRule)
        except Exception as e:
            print(e)
        return super().DataPostProcess(InputData, InputRule, HitItem)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "正则提取插件"