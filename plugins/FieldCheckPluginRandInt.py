import sys, os
from random import Random
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '使用Random().randint()函数生成随机整数'
    _PluginRuleFields = {
        "RangeFrom": (
            "随机数范围起始",
            int,
            0
        ),
        "RangeTo": (
            "随机数范围截止",
            int,
            0
        ),
        "Seed": (
            "随机数种子，如不指定则采用系统时间",
            int,
            None
        )
    }
    _myRand = Random() # 实例化插件自己的非共享的随机数对象
    def DataPreProcess(self, InputData, InputRule):
        self._myRand.seed(InputRule.get('Seed'))
        return self._myRand.randint(
            min(InputRule.get('RangeFrom', 0), InputRule.get('RangeTo', 0)),
            max(InputRule.get('RangeFrom', 0), InputRule.get('RangeTo', 0))
        )

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "随机数生成插件，其值与输入数据无关。请使用大于、小于或者等于判定生成的值，实现概率事件"

    @property
    def AliasName(self):
        return 'randint'