import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.AnalyseBase.RulePluginBase):
    '原基础算法中实现的Threshold功能，出于精简代码和数据结构考虑，单独拆分成插件'
    # 本插件只负责检查Flag是否有效，不提供Flag到应用层数据的映射关系
    # 通过规则的PrevFlag构造Flag-CacheItem映射
    # 以及规则的CurrentFlag去检查Flag-CacheItem映射是否满足条件
    # 如果不满足条件，返回False, None，否则返回True, hitItem
    # 2021-07-14
    # 拟修改为只有Threshold功能，并且只返回True/False
    # 通过外层规则的1/-1来控制，即“命中多少次之后生效”/“命中多少次之后失效”
    # 需要同时具备Threshold和Lifetime功能时通过规则AND逻辑以及RemoveFlag字段配合实现
    # 不再返回命中对象
    # 修改引擎，单条规则进入字段判定流程之前会预先生成PrevFlag，

    class CacheItem(object):
        '实现Flag生命周期管理，业务层里作为Flag到用户数据对象之间的映射'
        # 注意，本插件生成的Threshold和Lifetime只有调用本插件的规则才有效，
        # 已经通过本插件生成的带有Threshold和Lifetime的Flag在原算法里仍然还是普通Flag，可以被直接操作或访问
        '''缓存对象CacheItem（命中后存储的Flag对应的数据）：
        Threshold   ：  门槛消耗剩余，来自触发这条规则的FlagThreshold字段。
                        Flag生成之后每次命中Threshold消耗1，直到Threshold变为0时这个Flag才能正式生效。
                        Flag判定时应判断Threshold是否为0，Threshold为0的Flag才是生效的Flag，否则将Flag的Threshold减1，并返回Flag未命中
        Lifetime    ：  生存期剩余，来自触发这条规则的FlagLifetime字段。
                        Flag生效之后（Threshold消耗完）每次命中Lifetime消耗1。
                        当最后一次命中之后Lifetime减0时这个Flag将被销毁。
                        Lifetime如果初始就是0，则为永久有效，跳过Lifetime判定和消耗流程。
        FlagContent ：  对应Flag的内容'''
        _Threshold = 0  # 门槛剩余
        _LifeTime = 0  # 生存期剩余
        _FlagContent = ''  # Flag内容
        _Valid = True  # 指示当前Flag是否应还有效，当生存期消耗完毕或者超过有效时间时为False，其他情况包括门槛未消耗完毕时仍然为True。
        # 检查缓存对象是否可用应使用Check()函数，而不是直接使用_Valid属性

        @property
        def ThresholdRemain(self):
            return self._Threshold

        @property
        def LifetimeRemain(self):
            return self._LifeTime

        @property
        def FlagContent(self):
            return self._FlagContent

        @property
        def Valid(self):
            return self._Valid

        def __init__(self, FlagContent, Threshold, LifeTime):
            self._Threshold = Threshold
            self._LifeTime = LifeTime
            self._FlagContent = FlagContent
            # self._ExtraData = ExtraData

        def _ConsumeThreshold(self):
            '消耗门槛操作，如果门槛已经消耗完毕，返回True。在门槛消耗完毕之前，Valid属性仍然是True'
            # 注意，如果设置了Threshold为N，Flag在第N+1次重复命中时才会生效
            # 例：如果设置Threshold为1，则Flag在第二次重复命中的时候才会生效
            # 之所以这么设计，是考虑到当Threshold设置为0的时候，等价于即刻生效，下一次Flag命中即生效
            if self._Valid:
                if self._Threshold <= 0:
                    return True
                else:
                    self._Threshold -= 1
                    return False
            else:
                return False

        def _ConsumeLifetime(self):
            '消耗生存期操作。如果还在生存期内或者生存期无限（值为0）返回True，否则返回False并将Valid属性设为False'
            # Lifetime由1变成0的时候才会使得_Valid变为False，初始就是0时表示无限
            if self._Valid:
                if self._LifeTime > 0:
                    self._LifeTime -= 1
                    # 生存期失效之前最后一次调用，返回True并将_Valid设为False
                    self._Valid = not (self._LifeTime == 0)
                    # 特别注意，当规则设置Lifetime为1的时候，Flag仅在生效的那一个周期有效，过后即被销毁
                return True
            else:
                return False

        def Check(self):  # 检查是否有效
            if not self._Valid:
                return False
            else:
                if self._ConsumeThreshold():
                    return self._ConsumeLifetime()
                else:
                    return False

    _PluginRuleFields = {
        "Threshold": (
            "Flag触发门槛，相同的Flag每次触发之后消耗1，消耗到0之后Flag才正式生效。默认值0即无门槛", 
            int,
            0
        ),
        "Lifetime": (
            "Flag生存期，Flag生效之后相同的Flag再命中多少次之后即失效。默认值0即生存期无限", 
            int,
            0
        )
    }

    # 原分析算法基类中的Flag生命周期管理缓存对象，现拆分成单独的插件实现Threshold和Lifetime功能
    _cache = dict() # Flag-CacheItem映射

    def FlagPeek(self, InputFlag):
        if not InputFlag: #hitResult为True且前序Flag为空，为入口点规则
            return True, None
        else:
            rtn = False
            hitItem = self._cache.get(InputFlag)
            if hitItem:
                rtn = hitItem.Valid
            return rtn, hitItem

    def FlagCheck(self, InputFlag):
        rtn, hitItem = self.FlagPeek(InputFlag)
        if not rtn:
            if hitItem:
                self.RemoveFlag(InputFlag)
        else:
            if hitItem:
                rtn = hitItem.Check()
                if not hitItem.Valid:  
                    self.RemoveFlag(InputFlag)
            else: # hitResult为True且前序Flag为空，为入口点规则
                rtn = True
        return rtn

    def RemoveFlag(self, InputFlag):
        # 删除过期/无效的Flag，包括Flag-CacheItem映射和算法对象中的Flag
        self._cache.pop(InputFlag)
        self._AnalyseBase.RemoveFlag(InputFlag)

    def RuleHit(self, InputData, InputRule, HitItem):
        if self.FlagCheck(InputRule.get('PrevFlagContent')):
            # 在插件内构造Flag-CacheItem映射
            if InputRule.get("Threshold", 0) or InputRule.get("Lifetime", 0):
                # Threshold和Lifetime至少有一个不为0才进行Flag映射和管理
                currentFlag = InputRule.get('CurrentFlagContent')
                if currentFlag and currentFlag not in self._cache: # 判断生成的currentFlag是否已经存在
                    newCacheItem = self.CacheItem( # 防止覆盖
                        currentFlag,
                        InputRule.get("Threshold", 0),
                        InputRule.get("Lifetime", 0),
                    )
                    self._cache[currentFlag] = newCacheItem
            return True, HitItem
        else:
            return False, None

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Dummy plugin for test and sample."

    @property
    def AliasName(self):
        return 't&l'