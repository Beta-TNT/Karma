import sys, os, re, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '翻转字段比较左值和右值，相等比较和元数据比较除外'
    # 虽然不知道有什么用，但还是弄一个吧

    def AnalyseSingleData(self, InputData, InputRule):
        '数据分析方法接口，接收被分析的dict()类型数据和规则作为参考数据，应返回True/False'
        # 暂时将分析器的字段比较函数替换成翻转版的，完事再换回去
        # 是否线程安全未知
        funcTemp = self._AnalyseBase.FieldCheck # 先将原版本函数保存起来
        self._AnalyseBase.FieldCheck = Karma.ReversedFieldCheck
        rtn = super()._DefaultAnalyseSingleData(InputData, InputRule)
        self._AnalyseBase.FieldCheck = funcTemp
        return rtn

    @staticmethod
    def ReversedFieldCheck(TargetData, InputFieldCheckRule):
        if type(InputFieldCheckRule) != dict:
            raise TypeError("Invalid InputFieldCheckRule type, expecting dict")
        fieldCheckResult = False
        matchContent = InputFieldCheckRule["MatchContent"]
        matchCode = InputFieldCheckRule["MatchCode"]
        if matchCode == Karma.AnalyseBase.MatchMode.Preserve:
            pass
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.Equal:
            # 相等匹配 equal test
            if type(TargetData) in {bytes, bytearray}:
                # 如果原数据类型是二进制，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                matchContent = base64.b64decode(matchContent)
            if type(matchContent) == type(TargetData):  # 同数据类型，直接判断
                fieldCheckResult = (matchContent == TargetData)
            else:  # 不同数据类型，都转换成字符串判断
                fieldCheckResult = (str(matchContent) == str(TargetData))
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.TextMatching:
            # 文本匹配（字符串） text matching (ignore case)
            try:
                if type(TargetData) in {bytes, bytearray}:
                    # 如果原数据类型是二进制，则试着将比较内容字符串按BASE64转换成bytes后再进行比较
                    matchContent = base64.b64decode(matchContent)
                else:
                    matchContent = str(matchContent) if type(matchContent) != str else matchContent
                    TargetData = str(TargetData) if type(TargetData) != str else TargetData
                fieldCheckResult = (TargetData in matchContent)
            except:
                pass
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.RegexMatching:
            # 正则匹配（字符串） regex match
            if type(matchContent) != str:
                matchContent = str(matchContent)
            if type(TargetData) != str:
                TargetData = str(TargetData)
            fieldCheckResult = bool(re.match(TargetData ,matchContent))
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.GreaterThan:
            # 大小比较（数字，字符串尝试转换成数字，转换不成功略过该字段匹配）
            if type(matchContent) in (int, float) and type(TargetData) in (int, float):
                fieldCheckResult = (TargetData > matchContent)
            else:
                try:
                    fieldCheckResult = (int(TargetData) > int(matchContent) )
                except:
                    pass
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.LengthEqual:
            # 元数据比较：数据长度相等。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float):
                try:
                    fieldCheckResult = (len(matchContent) == int(TargetData))
                except:
                    pass
            else:
                pass
        elif abs(matchCode) == Karma.AnalyseBase.MatchMode.LengthGreaterThan:
            # 元数据比较：数据长度大于。忽略无法比较长度的数字类型
            if type(matchContent) not in (int, float):
                try:
                    fieldCheckResult = (len(matchContent) > int(TargetData))
                except:
                    pass
            else:
                pass
        else:
            pass
        fieldCheckResult = ((matchCode < 0) ^ fieldCheckResult) # 负数代码，结果取反
        return fieldCheckResult

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "逆转匹配"
        
    @property
    def AliasName(self):
        return 'rev'