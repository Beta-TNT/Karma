import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma
from re import compile

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '正则截取插件'
    # 单独设立的正则截取插件，可以比配并比较正则表达式在输入数据里的匹配值
    # 类似切片插件，将会在数据中产生名为AnayzerPluginRegex_Content_#的新字段，#为下标序号，从0开始，内容是匹配结果。适配结果也将占据序号，内容是None
    _PluginRuleFields = {
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
        "ResultIndex": (
            "RegexFunc取值为findall时，取结果的索引号，为空或不存在时使用默认值0，负值代表从后往前取", 
            int,
            0
        ),
        "RegexFunc": (
            "使用的正则表达式函数：search, match, findall。使用findall时需要指定ResultIndex", 
            str,
            'search',
            lambda x:x in ('search', 'match', 'findall'),
            'invalid value %s: expecting "search", "match" or "findall"'
        )
    }
    _regularExpressionCache = {} # 正则表达式-正则flag-正则对象缓存

    def DataPreProcess(self, InputData, InputFieldCheckRule):
        try:
            targetData = super().DataPreProcess(InputData, InputFieldCheckRule)
            regexPattern = InputFieldCheckRule['RegexPattern']
            regexFlag = InputFieldCheckRule.get('RegexFlag', 0)
            regexFunc = InputFieldCheckRule.get('RegexFunc', 'search')
            resultIndex = InputFieldCheckRule.get('ResultIndex', 0)
            if regexPattern not in self._regularExpressionCache:
                self._regularExpressionCache[regexPattern] = dict()
            if regexFlag not in self._regularExpressionCache[regexPattern] :
                self._regularExpressionCache[regexPattern][regexFlag] = compile(regexPattern, regexFlag)
            regexObj = self._regularExpressionCache[regexPattern][regexFlag]
            if regexFunc == 'findall':
                return regexObj.findall(targetData)[resultIndex]
            elif regexFunc == 'search':
                return regexObj.search(targetData).group() 
            elif regexFunc == 'match':
                return regexObj.match(targetData).group()
            else:
                return None
        except:
            return None

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "正则提取插件"

    @property
    def AliasName(self):
        return 'regex'
