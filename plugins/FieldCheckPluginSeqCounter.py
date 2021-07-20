import sys, os, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '序列查找插件，查找子串在目标数据里出现的次数'
    # 单独设立序列查找插件，是因为find()函数的时间复杂度比in查找操作高，不应直接用find()代替in
    # 查找结果为-1（失配）或者大于等于0（第一个命中原序列的位置）
    # 支持字符串和二进制序列（bytes/bytearray）
    # 当输入数据是字符串时，查找忽略大小写；
    # 输入数据是二进制时，会尝试将目标序列值按BASE64解码为bytes。如需进行大小写敏感查找，请使用二进制
    _PluginRuleFields = {
        "SubSeq": (
            "要查找的序列。如果FieldName指向字段类型是bytes或bytearray，则试着将本字段内容按BASE64解码为bytes再比较", 
            str,
            ''
        )
    }

    @staticmethod
    def findall(pattern, seq, overlapping):
        i = seq.find(pattern)
        while i != -1:
            yield i
            i = seq.find(pattern, i + (1 if overlapping else len(pattern)))

    def DataPreProcess(self, InputData, InputFieldCheckRule):
        targetData = InputData.get(InputFieldCheckRule.get('FieldName'))
        subSeq = InputFieldCheckRule.get('SubSeq', '')
        if type(targetData) in (bytes, bytearray):
            subSeq = base64.b64decode(subSeq)
        elif type(targetData) == str:
            return targetData.count(subSeq)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "序列计数插件"
    @property
    def AliasName(self):
        return 'seqcounter'