import sys, os, hashlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma
from enum import IntEnum

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '哈希比较插件'

    class HashMatchCode(IntEnum):
        '哈希算法代号，负数结果取反'
        MD5 = 101
        SHA1 = 102
        SHA224 = 103
        SHA256 = 104
        SHA384 = 105
        SHA512 = 106

    _PluginRuleFields = {
        'Encoding': (
            '字符串编码。如无指定则默认为utf-8', 
            str,
            'utf-8'
        )
    }

    def DataPreProcess(self, InputData, InputFieldCheckRule):
        '哈希比较插件'
        targetData = InputData[InputFieldCheckRule['FieldName']].encode(InputFieldCheckRule.get("Encoding", 'utf-8')) if type(InputData[InputFieldCheckRule['FieldName']]) == str else InputData[InputFieldCheckRule['FieldName']]
        m = None
        if abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.MD5:
            m = hashlib.md5(targetData)
        elif abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.SHA1:
            m = hashlib.sha1(targetData)
        elif abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.SHA224:
            m = hashlib.sha224(targetData)
        elif abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.SHA256:
            m = hashlib.sha256(targetData)
        elif abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.SHA384:
            m = hashlib.sha384(targetData)
        elif abs(InputFieldCheckRule['MatchCode']) == self.HashMatchCode.SHA512:
            m = hashlib.sha512(targetData)
        else:
            return None
        return m.hexdigest().lower()

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "哈希比较，支持MD5和SHA1等，目标字段必须是二进制或者字符串，可通过字段匹配规则的Encoding字段值来指定字符串编码，默认不指定使用utf-8。"
        
    @property
    def AliasName(self):
        return 'hash'