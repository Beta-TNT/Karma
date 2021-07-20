import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma
from time import monotonic

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '秒表/计时器插件'
    _PluginRuleFields = {
        "TimerName": (
            "计时器名称，支持占位符", 
            str,
            ''
        ),
        "TimerOperation": (
            "操作，只能是以下值之一：start, stop, reset, peek，字段为空或不存在时按peek处理",
            str,
            'start',
            lambda x:x in {'create', 'start', 'stop', 'reset', 'peek', 'remove', None},
            'invalid operation: %s, expecting "create", "start", "stop", "reset", "peek" or "remove".'
        )
    }
    # 计时器操作：
    # create    建立计时器并设置为停止状态，如果计时器已经存在则等同peek
    # start     建立计时器并开始计时，将计时器状态设置为运行；如果计时器名已存在而且是停止状态，则以当前时间为基础继续计时；不影响已存在且正常运行的计时器
    # stop      计时器停止计时，并将状态设置为停止；不影响已存在且状态是停止的计时器
    # reset     将运行和停止状态的计时器归零并重新开始计时，将状态设置为运行；计时器不存在时相当于start
    # peek      查看计时器当前值，不改变计时器状态
    # remove    删除指定的计时器。如果指定计时器不存在，则返回None

    # 返回值是指定计时器的值，单位是秒，需要使用MatchCode=4/-4（GreaterThan/LessOrEqual）判断值的范围

    _timers = dict()
    __timerInfo = {
        'UpdatedTime': 0.0,
        'StoppedTime': 0.0
    }
    def DataPreProcess(self, InputData, InputRule):
        timerName = self._AnalyseBase.FlagGenerator(InputData, InputRule.get('TimerName'))
        timerOperation = InputRule.get('TimerOperation')
        timerObj = self._timers.get(timerName)
        rtn = None
        if timerOperation == 'create':
            if not timerObj:
                self._timers[timerName] = {
                    'UpdatedTime': monotonic(),
                    'StoppedTime': monotonic()
                }
                rtn = 0.0
            else:
                if timerObj['StoppedTime']:
                    rtn = timerObj['StoppedTime'] - timerObj['UpdatedTime']
                else:
                    rtn = monotonic() - timerObj['UpdatedTime']

        elif timerOperation == 'start':
            if not timerObj:
                self._timers[timerName] = {
                    'UpdatedTime': monotonic(),
                    'StoppedTime': 0
                }
                rtn = 0.0
            else:
                if timerObj['StoppedTime']:
                    timerObj['UpdatedTime'] += monotonic() - timerObj['StoppedTime']
                    timerObj['StoppedTime'] = 0
                rtn = monotonic() - timerObj['UpdatedTime']

        elif timerOperation == 'stop':
            if timerObj:
                rtn = monotonic() - timerObj['UpdatedTime']
                timerObj['StoppedTime'] = monotonic()

        elif timerOperation == 'reset':
            if not timerObj:
                self._timers[timerName] = {
                    'UpdatedTime': monotonic(),
                    'StoppedTime': 0
                }
                rtn = 0.0
            else:
                rtn = monotonic() - timerObj['UpdatedTime']
                timerObj['UpdatedTime'] = monotonic()
                timerObj['StoppedTime'] = 0

        elif timerOperation in ('peek', 'remove'):
            if timerObj['StoppedTime']:
                rtn = timerObj['StoppedTime'] - timerObj['UpdatedTime']
            else:
                rtn = monotonic() - timerObj['UpdatedTime']

        else:
            pass
        
        if timerOperation == 'remove':
            self._timers.pop(timerName, None)

        return rtn
            
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "计时器插件。"

    @property
    def AliasName(self):
        return 'stopwatch'