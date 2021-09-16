import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class FieldCheckPlugin(Karma.AnalyseBase.FieldCheckPluginBase):
    '根据指定规则提取其他插件产生值（DataPreProcess()函数返回值），以指定的名称写入数据并使用当前规则进行测试'
    # 该插件的一个使用技巧是将FieldMatchCode设置为0（Preserved）
    _selfName = os.path.splitext(os.path.basename(__file__))[0]
    _selfAlias = 'extractor'

    _PluginRuleFields = {
        "CallPluginName": (
            "要调用的插件名",
            str,
            '',
            lambda x:x not in (_selfName, _selfAlias),
            'invalid plugin name: %s: you can not call itself.' # 禁止套娃
        ),
        "CallPluginRule": (
            "附加的插件规则。如果指定了一个有效值，则将该规则传入调用插件，否则将传入当前规则",
            dict,
            {}
        ),
        "OutputFieldName": (
            "输出数据的字段名。如果不指定，则以CallPluginName字段内容命名",
            str,
            ''
        )
    }
    def DataPreProcess(self, InputData, InputFieldCheckRule):
        pluginName = InputFieldCheckRule.get('CallPluginName', '')
        if pluginName in (self._selfAlias, self._selfName):
            # 禁止套娃
            return None
        pluginRule = InputFieldCheckRule.get('CallPluginRule', InputFieldCheckRule)
        outputFieldName = InputFieldCheckRule.get('OutputFieldName', pluginName)
        pluginObj = self._AnalyseBase._plugins['FieldCheckPlugins'].get(pluginName)
        if pluginObj:
            pluginRtn = pluginObj.DataPreProcess(InputData, pluginRule)
            InputData[outputFieldName] = pluginRtn
            return pluginRtn
        else:
            return None

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "插件返回值提取"

    @property
    def AliasName(self):
        return self._selfAlias