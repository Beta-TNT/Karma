import sys, os, hashlib, zlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib
from enum import IntEnum

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '哈希比较插件'

    class HashMatchCode(IntEnum):
        '哈希算法代号，负数结果取反'
        MD5 = 101
        SHA1 = 102
        SHA224 = 103
        SHA256 = 104
        SHA384 = 105
        SHA512 = 106

    _ExtraFieldMatchingRuleFields = {
        'Encoding': (
            '字符串编码。如无指定则默认为utf-8', 
            str,
            'utf-8'
        )
    }

    def DataPreProcess(self, InputData, InputRule):
        '哈希比较插件'
        fieldCheckList = InputRule.get('FieldCheckList')
        if fieldCheckList:
            i = 0
            for fieldCheckRule in filter(lambda x:101<= abs(x.get('MatchCode', 0)) <= 106 and type(InputData.get(x['FieldName'])) in (str, bytes, bytearray), fieldCheckList):
                try:
                    targetData = InputData[fieldCheckRule['FieldName']].encode(fieldCheckRule.get("Encoding", 'utf-8')) if type(InputData[fieldCheckRule['FieldName']]) == str else InputData[fieldCheckRule['FieldName']]
                    targetDataFieldName = '%s_Content_%s' % (self._CurrentPluginName, i)
                    m = None
                    if abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.MD5:
                        m = hashlib.md5(targetData)
                    elif abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.SHA1:
                        m = hashlib.sha1(targetData)
                    elif abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.SHA224:
                        m = hashlib.sha224(targetData)
                    elif abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.SHA256:
                        m = hashlib.sha256(targetData)
                    elif abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.SHA384:
                        m = hashlib.sha384(targetData)
                    elif abs(fieldCheckRule['MatchCode']) == self.HashMatchCode.SHA512:
                        m = hashlib.sha512(targetData)
                    InputData[targetDataFieldName] = m.hexdigest()
                    fieldCheckRule['FieldName'] = targetDataFieldName
                    fieldCheckRule['MatchContent'] = fieldCheckRule['MatchContent'].lower()
                    fieldCheckRule['MatchCode'] = 1 if fieldCheckRule['MatchCode'] >= 0 else -1
                    i += 1
                except:
                    continue

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "哈希比较，支持MD5和SHA1等，目标字段必须是二进制或者字符串，可通过字段匹配规则的Encoding字段值来指定字符串编码，默认不指定使用utf-8。"