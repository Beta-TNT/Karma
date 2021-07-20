import sys, os, threading
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.AnalyseBase.RulePluginBase):
    '延迟生效和过期销毁FLAG插件，'

    _PluginRuleFields = {
        "Delay": (
            "Flag延迟生效时间，当前规则生效之后生成的CurrentFlag经过延迟时间后才生效，单位是秒，浮点数", 
            float,
            0.0
        ),
        "Expire": (
            "Flag有效时间，过期删除，单位是秒，浮点数", 
            float,
            0.0
        )
    }

    _delayTimers = dict()
    _expireTimers = dict()
    _liveFlags = set() # 存活/有效的Flag

    def __delayFunc(self, InputFlag, ExpireSec):
        # 延迟生效计时器函数，将Flag设置为生效并启动过期计时器
        self._liveFlags.add(InputFlag)
        if ExpireSec:
            threading.Timer(
                interval=ExpireSec,
                function=self.__expireFunc,
                args=[InputFlag]
            ).start()

    def __expireFunc(self, InputFlag):
        # 过期计时器函数，将Flag从插件缓存以及分析器对象缓存中删除
        if InputFlag in self._liveFlags:
            self._liveFlags.remove(InputFlag)
        self._AnalyseBase._flags.pop(InputFlag, None)

    def RuleHit(self, InputData, InputRule, HitItem):
        prevFlag = InputRule.get('PrevFlagContent')
        if prevFlag in self._liveFlags or not prevFlag:
            # 获取本级规则Flag
            currentFlag = InputRule.get('CurrentFlagContent')
            delaySec = InputRule.get("Delay", 0)
            expireSec = InputRule.get("Expire", 0)
            if {type(delaySec),type(expireSec)}.issubset({int, float}) and currentFlag not in self._liveFlags:
                #字段类型判断，以及忽略已存在的Flag防止重复
                if delaySec: # 延迟生效秒数字段有效，设置延迟计时器
                    threading.Timer(
                        interval=delaySec,
                        function=self.__delayFunc,
                        args=[currentFlag, expireSec]
                    ).start()
                if expireSec: # 延过期时间秒数有效，设置过期计时器
                    self.__delayFunc(currentFlag, expireSec)
            return True, HitItem
        else:
            return False, None

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "timed flag."

    @property
    def AliasName(self):
        return 'timed'