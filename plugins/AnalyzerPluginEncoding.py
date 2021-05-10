import sys, copy, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import NeoHoney_Analyse
import urllib.parse, base64, cgi, html
from enum import IntEnum

class AnalysePlugin(NeoHoney_Analyse.NeoHoneyAnalyserPluginInterface):
    '插件基类'

    class Codec(str):
        OpUrlEncoding = 'U'
        OpUrlDecoding = 'u'

        OpHtmlEncoding = 'X'
        OpHtmlDecoding = 'x'

        OpBase64Encoding = 'Q'
        OpBase64Decoding = 'q'

        OpBytesToBase64 = 'B'
        OpBase64ToBytes = 'b'
    
    _ExtraRuleFields = {
        'CodecFields': (
            '待转换的字段，字典类型，Key是要转换的字段名，Value是转换代码，可按顺序组合多次转换，比如"uq"',
            dict,
            {}
        )
    }
    _SettingItemProperties = {'Encoding': ('编码代码',str, 'utf-8')}

    _encoding = 'utf-8' # 涉及到字符串编码/解码时使用的字符集
    _PluginFilePath = os.path.abspath(__file__)

    def __init__(self, AnalyseBaseObj):
        super().__init__(AnalyseBaseObj)
        self.PluginInit()

    def DataPreProcess(self, InputData, InputRule):
        '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同_DefaultSingleRuleTest()函数'
        # add your own data preprocess code here
        modifiedData = copy.copy(InputData)
        CodecFields = InputData.get('CodecFields',{})
        for CodecField in CodecFields:
            if CodecField in modifiedData:
                for flagChar in list(CodecFields[CodecField]):
                    if flagChar == 'U':
                        modifiedData[CodecField] = urllib.parse.quote(modifiedData[CodecField])
                    elif flagChar == 'u':
                        modifiedData[CodecField] = urllib.parse.unquote(modifiedData[CodecField])
                    elif flagChar == "Q":
                        modifiedData[CodecField] = base64.b64encode(str(modifiedData[CodecField]).encode(self._SettingItems['Encoding']))
                    elif flagChar == 'q':
                        modifiedData[CodecField] = base64.b64decode(modifiedData[CodecField]).decode(self._SettingItems['Encoding'])
                    elif flagChar == 'X':
                        modifiedData[CodecField] = html.escape(modifiedData[CodecField])
                    elif flagChar == 'x':
                        modifiedData[CodecField] = html.unescape(modifiedData[CodecField])
                    elif flagChar == 'B':
                        if type(modifiedData[CodecField]) in (bytes, bytearray):
                            modifiedData[CodecField] = base64.b64encode(modifiedData[CodecField])
                    elif flagChar == 'b':
                        modifiedData[CodecField] = base64.b64decode(modifiedData[CodecField])
        return super().AnalyseSingleData(modifiedData, InputRule)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Encoding/Decoding Plugin"