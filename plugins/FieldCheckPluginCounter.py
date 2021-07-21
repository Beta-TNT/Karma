import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma
from time import monotonic

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '计数器插件'
    _PluginRuleFields = {
        "CounterName": (
            "计数器名称，支持占位符", 
            str,
            ''
        ),
        "Step": (
            "累加数，不指定时默认为1，可以是负数",
            int,
            1
        ),
        "CounterOperation": (
            "操作，只能是以下值之一：count, peek, remove，字段为空或不存在时按count处理",
            str,
            'count',
            lambda x:x in {'peek', 'count', 'remove', None},
            'invalid operation: %s, expecting "peek", "count" or "remove".'
        )
    }
    # 计数器操作：
    # count     将Step累加到指定计数器上，并返回累加后的值。计数器不存在时建立计时器并将Step作为初始值
    # peek      返回指定计数器的值但不改变它（忽略Step字段），不存在时返回None
    # remove    返回指定计数器的值并将其删除。不存在时返回None

    # 返回值是指定计时器的值，单位是秒，需要使用MatchCode=4/-4（GreaterThan/LessOrEqual）判断值的范围

    _counter = dict()
    def DataPreProcess(self, InputData, InputRule):
        counterName = self._AnalyseBase.FlagGenerator(InputData, InputRule.get('CounterName'))
        counterOperation = InputRule.get('CounterOperation', 'count')
        counterValue = self._counter.get(counterName)
        rtn = None
        if counterOperation == 'count':
            rtn = counterValue if counterValue else 0  + InputRule.get('Step', 1)
            self._counter[counterName] = rtn
        elif counterOperation == 'peek':
            rtn = counterValue
        elif counterOperation == 'remove':
            rtn = self._counter.pop(counterName, None)
        else:
            pass
        return rtn
            
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "计数器插件。"

    @property
    def AliasName(self):
        return 'counter'