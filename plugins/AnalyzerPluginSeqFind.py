import sys, os, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '序列查找插件，查找子串在目标数据里出现的次数和位置'
    # 单独设立序列查找插件，是因为find()函数的时间复杂度比in查找操作高，不应直接用find()代替in
    # 类似切片插件，将会在数据中产生名为AnayzerPluginSeqFind_Content_#的新字段，#为下标序号，从0开始，内容是匹配结果
    # 查找结果为-1（失配）或者大于等于0（第一个命中原序列的位置）
    # 支持字符串和二进制序列（bytes/bytearray）
    # 当输入数据是字符串时，查找忽略大小写；
    # 输入数据是二进制时，会尝试将目标序列值按BASE64解码为bytes。如需进行大小写敏感查找，请使用二进制
    _ExtraFieldMatchingRuleFields = {
        "SubSeq": (
            "要查找的序列。如果输入数据类型是bytes或bytearray，则试着将本字段内容按BASE64解码为bytes再比较", 
            str,
            ''
        ),
        "Overlapping": (
            "是否查找交叠，例如在ababab中查找abab，非交叠查找结果为[0]，交叠查找结果为[0,2]。无此项默认为非交叠", 
            bool,
            False
        )
    }

    @staticmethod
    def findall(pattern, seq, overlapping):
        i = seq.find(pattern)
        while i != -1:
            yield i
            i = seq.find(pattern, i + (1 if overlapping else len(pattern)))

    def DataPreProcess(self, InputData, InputRule):
        # 序列查找插件
        fieldCheckList = InputRule.get('FieldCheckList')
        if fieldCheckList:
            i = 0
            for fieldCheckRule in filter(
                lambda x:'SubSeq'in x and type(
                    InputData.get(
                        x['FieldName']
                    )
                ) in (str, bytes, bytearray), 
                fieldCheckList
            ):
                try:
                    targetData = InputData[fieldCheckRule['FieldName']]
                    subSeq = fieldCheckRule['SubSeq']
                    if type(targetData) in {bytes, bytearray}:
                        # 输入数据是二进制，将匹配内容按BASE64解码成二进制
                        subSeq = base64.b64decode(subSeq)
                    elif type(targetData) == str:
                        # 输入数据是字符串，两者都改为小写，忽略大小写
                        targetData = targetData.lower()
                        subSeq = subSeq.lower()
                    else:
                        # 忽略其他类型
                        continue
                    j = 0
                    for pos in self.findall(subSeq, targetData, fieldCheckRule.get('Overlapping')):
                        InputData['%s_Content_%s,%s' % (self._CurrentPluginName, i, j)] = pos
                        j += 1
                    InputData['%s_Content_%s_Count' % (self._CurrentPluginName, i)] = j
                    i += 1
                except:
                    continue

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "序列匹配插件"