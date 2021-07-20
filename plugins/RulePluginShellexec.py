import sys, os
import subprocess
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.CoreRule):
    _PluginRuleFields = {
        "ShellCommand": (
            '插件执行的命令行，可使用占位符',
            str,
            ''
        )
    }
    
    def RuleHit(self, InputData, InputRule, HitItem):
        '数据分析方法接口，只有当数据满足规则的时候才执行插件功能'
        try:
            cmd = self._AnalyseBase.FlagGenerator(InputData, InputRule.get('ShellCommand', ''))
            subprocess.Popen(cmd) # 调用subprocess.Popen()函数执行命令
        except Exception as e:
            print(e)
        finally:
            return super().RuleHit(InputData, InputRule, HitItem) 

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "外部命令执行插件，使用subprocess.Popen()方法"

    @property
    def AliasName(self):
        return 'shellexec'