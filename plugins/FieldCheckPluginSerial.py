
import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '正则截取插件'
    # 串行插件匹配。可依次执行多个插件
    # 待执行插件队列（list, tuple）的每一项是 插件名，或者 (插件名, 附加规则) 二元组
    # 不带有附加规则的插件名传入当前规则
    # 依次执行的时候，任意一个插件判定结果为False时，跳出循环返回，否则一直将插件列表执行完
    _PluginRuleFields = {
        "PluginList": (
            "要调用的插件名/(插件名，附加规则)二元组列表", 
            list,
            []
        )
    }

    def AnalyseSingleField(self, InputData, InputFieldCheckRule):
        pluginList = InputFieldCheckRule.pop('PluginList', []) # 打破套娃，直接pop
        for plugin in pluginList: 
            pluginObj = None
            additionalPluginRule = InputFieldCheckRule
            if type(plugin) == str:
                pluginObj = self._AnalyseBase._plugins['FieldCheckPlugins'].get(plugin, 'core')
            elif type(plugin) in (list, tuple):
                pluginObj = self._AnalyseBase._plugins['FieldCheckPlugins'].get(plugin[0], 'core')
                additionalPluginRule = additionalPluginRule if len(plugin) < 2 else  plugin[1]
            if pluginObj:
                if not pluginObj.AnalyseSingleField(InputData, additionalPluginRule):
                    return False
            else:
                continue
        return bool(pluginList)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "插件列表调用"

    @property
    def AliasName(self):
        return 'serial'