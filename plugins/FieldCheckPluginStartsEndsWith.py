import sys, os, base64
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.CoreFieldCheck):
    '检查字符串/二进制串是否以指定序列开始/结束'
    _PluginRuleFields = {
        "Func": (
            "startswith/endswith", 
            str,
            lambda x:x in ('startswith', 'endswith'),
            'invalid func: %s, expecting "startswith" or "endswith".'
        ),
        "Begin": (
            "起始位置，默认值为0", 
            int,
            0
        ),
        "End": (
            "结束位置，默认值为None（字符串末尾）", 
            int,
            None
        )
    }

    def FieldCheck(self, TargetData, InputFieldCheckRule):
        matchContent = InputFieldCheckRule.get('MatchContent')
        beginPos = InputFieldCheckRule.get('Begin')
        endPos = InputFieldCheckRule.get('End')
        if type(matchContent) != str or not matchContent:
            return False
        try:
            func = None
            if InputFieldCheckRule.get('Func') == 'startswith':
                func = TargetData.startswith
            elif InputFieldCheckRule.get('Func') == 'endswith':
                func = TargetData.endswith
            else:
                return False
            if type(TargetData) in (bytes, bytearray):
                # 二进制，将比较数据按base64解码为二进制
                return func(base64.b64decode(matchContent), beginPos, endPos)
            elif type(TargetData) == str:
                # 字符串
                return func(matchContent, beginPos, endPos)
            else:
                return False
        except:
            return False

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "检查字符串/二进制串是否以指定序列开始/结束"

    @property
    def AliasName(self):
        return 'startsendswith'