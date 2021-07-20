import sys, os, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

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
            lambda x:x in {'create', 'start', 'stop', 'reset', 'peek', '', None},
            'invalid operation: %s, expecting "create", "start", "stop", "reset" or "peek".'
        )
    }
    # 计时器操作：
    # create    建立计时器并将状态设置为停止；如果计时器已存在，则相当于peek操作；
    # start     建立计时器并开始计时，将计时器状态设置为运行；如果计时器名已存在而且是停止状态，则以当前时间为基础继续计时；不影响已存在且正常运行的计时器
    # stop      计时器停止计时，并将状态设置为停止；不影响已存在且状态是停止的计时器
    # reset     将运行和停止状态的计时器归零并重新开始计时，将状态设置为运行；计时器不存在时相当于start
    # peek      查看计时器当前值，不改变计时器状态

    # peek 操作之外所有其他操作都默认包含peek操作，如果TimerName指向一个有效的计时器名称，
    # 会在数据里加入"AnalyzerPluginStopWatch_#TimerName#"字段，值为指定计时器当前值。start操作返回数值0
    # 如果计时器名无效，除了start操作之外，其他操作都不会在数据里加入"AnalyzerPluginStopWatch_#TimerName#"字段

    def DataPreProcess(self, InputData, InputRule):
        '插件数据分析方法用户函数，接收被分析的dict()类型数据和规则作为参考数据，由用户函数判定是否满足规则。返回值定义同SingleRuleTest()函数'
        # TODO 完成功能代码
        pass        
                
    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "计时器插件。"
    @property
    def AliasName(self):
        return 'stopwatch'