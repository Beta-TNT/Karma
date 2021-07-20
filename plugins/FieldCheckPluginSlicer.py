import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.CoreFieldCheck):
    '切片比较插件'
    _PluginRuleFields = {
        "SliceFrom": (
            "切片起始", 
            int,
            0
        ),
        "SliceTo": (
            "切片截止，可以为空", 
            int,
            None
        ),
        "Step": (
            "切片步长，无此项默认为1", 
            int,
            1
        )
    }

    def DataPreProcess(self, InputData, InputFieldCheckRule):
        '数据预处理'
        return super().DataPreProcess(InputData, InputFieldCheckRule)[InputFieldCheckRule.get('SliceFrom', 0):InputFieldCheckRule.get('SliceTo'):InputFieldCheckRule.get('Step', 1)]
    
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "切片比较，支持原字段匹配全部的匹配操作代码，包括二进制支持。"
    @property
    def AliasName(self):
        return 'slicer'