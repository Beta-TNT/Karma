import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import AnalyseLib

class AnalysePlugin(AnalyseLib.AnalyseBase.PluginBase):
    '正则截取插件'
    # 单独设立的正则截取插件，可以比配并比较正则表达式在输入数据里的匹配值
    # 类似切片插件，将会在数据中产生名为AnayzerPluginRegex_Content_#的新字段，#为下标序号，从0开始，内容是匹配结果。适配结果也将占据序号，内容是None
    _ExtraRuleFields = {}
    _ExtraFieldMatchingRuleFields = {
        "RegexPattern": (
            "正则表达式", 
            str,
            ''
        ),
        "RegexFlag": (
            "正则表达式Flag，为空或不存在时使用默认值0", 
            int,
            0
        ),
        "RegexFunc": (
            "使用的正则表达式函数，0=search(), 1=match(), 2=findall()。使用findall()时，匹配结果后缀序号将改为#,#，为空或不存在时使用默认值0", 
            int,
            0
        )
    }

    def DataPreProcess(self, InputData, InputRule):
        fieldCheckList = InputRule.get('FieldCheckList')
        if fieldCheckList:
            i = 0
            for fieldCheckRule in filter(
                lambda x:'RegexPattern'in x and type(
                    InputData.get(
                        x['FieldName']
                    )
                ) == str, 
                fieldCheckList
            ):
                try:
                    targetData = InputData[fieldCheckRule['FieldName']]
                    regexPattern = fieldCheckRule['RegexPattern']
                    regexFlag = fieldCheckRule.get('RegexFlag', 0)
                    regexFunc = fieldCheckRule.get('RegexFunc', 0) % 3
                    if regexFunc == 2:
                        j = 0
                        for findAllResult in re.findall(regexPattern, targetData, regexFlag):
                            targetDataFieldName = '%s_Content_%s,%s' % (self._CurrentPluginName, i, j)
                            fieldCheckRule['FieldName'] = targetDataFieldName
                            InputData[targetDataFieldName] = findAllResult
                            j += 1
                        InputData['%s_Content_%s_Count' % (self._CurrentPluginName, i)] = j
                    else:
                        targetDataFieldName = '%s_Content_%s' % (self._CurrentPluginName, i)
                        fieldCheckRule['FieldName'] = targetDataFieldName
                        regexMatchResult = re.search(regexPattern, targetData, regexFlag) if regexFunc == 0 else re.match(regexPattern, targetData, regexFlag)
                        if regexMatchResult:
                            InputData[targetDataFieldName] = regexMatchResult.group()
                        else:
                            InputData[targetDataFieldName] = None
                    i += 1
                except:
                    continue

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "正则提取插件"