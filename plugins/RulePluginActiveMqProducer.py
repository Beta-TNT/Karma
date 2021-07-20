# stomp package acquired.
# install cmd: pip install stompy
import stomp
import sys, os, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.AnalyseBase.RulePluginBase):
    _PluginRuleFields = {
        "ContentBody": (
            "发送到ActiveMQ的内容，支持占位符", 
            str,
            ''
        ),
        "JsonEscape": (
            '是否对ContentBody中占位符替换的内容进行JSON字符转义',
            bool,
            False
        ),
        'ActiveMqServer': (
            "目的ActiveMQ服务器IP，指定该项将覆盖默认配置",
            str,
            'localhost'
        ),
        'StompPort': (
            "Stomp服务端口号，一般是61613，指定该项将覆盖默认配置",
            int,
            61613,
            lambda x:0<x<65536,
            'invalid port number: %s, expecting 1-65535'
        ),
        'ActiveMqLogin': (
            "ActiveMQ服务登录名，指定该项将覆盖默认配置",
            str
        ),
        'ActiveMqPassword': (
            "ActiveMQ服务密码，指定该项将覆盖默认配置",
            str,
            ''
        ),
        'TopicOrQueue': (
            "指定Topic还是Queue方式，值必须是'topic'或者'queue'，指定该项将覆盖默认配置",
            str,
            'topic',
            lambda x:x in ('queue', 'topic'),
            'invalid value: %s, expecting "topic" or "queue"'
        ),
        'Destination': (
            "接收路径，以点号分隔，比如'NeoHoney.Test'，指定该项将覆盖默认配置",
            str,
            ''
        ),
        "RepostOption": (
            "全文转发选项，将传入插件的原始数据全文转发到的目的MQ，该选项有效时将覆盖ContentBody和JsonEscape字段。0或其他值=不转发；1=JSON格式全文转发，2=XML格式全文转发", 
            int,
            0,
            lambda x:0<=x<=2,
            'invalid value range: %s, expecting 0, 1 or 2'
        )
    }

    _SettingItemProperties = {
        'DefaultActiveMqServer': (
            '默认使用的ActiveMQ服务器地址',
            str,
            'localhost'
        ),
        'DefaultActiveMqLogin': (
            '默认使用的ActiveMQ服务器登录名',
            str,
            'admin'
        ),
        'DefaultActiveMqPassword': (
            '默认使用的ActiveMQ服务器登录密码',
            str,
            'admin'
        ),
        'DefaultTopicOrQueue': (
            "指定Topic还是Queue方式，值必须是'topic'或者'queue'",
            str,
            'topic',
            lambda x:x in ('queue', 'topic'),
            'invalid value: %s, expecting "topic" or "queue"'
        ),
        'DefaultStompPort': (
            'ActiveMQ服务器Stomp服务端口，一般是61613',
            int,
            61613,
            lambda x:0<x<65536,
            'invalid port number: %s, expecting 1-65535'
        ),
        'DefaultDestination': (
            '默认的数据接收路径，以点号分隔，比如"NeoHoney.Test"',
            str,
            'NeoHoney.Test'
        )
    }

    conn = None
    _PluginFilePath = os.path.abspath(__file__)

    def __init__(self, AnalyseBaseObj):
        super().__init__(AnalyseBaseObj)
        self.PluginInit()

    def RuleHit(self, InputData, InputRule, HitItem):
        try:
            if self.conn == None:
                self.conn = stomp.Connection([(self._SettingItems['DefaultActiveMqServer'], self._SettingItems['DefaultStompPort'])])
                self.conn.begin()
                self.conn.connect(login=self._SettingItems['DefaultActiveMqLogin'], password=self._SettingItems['DefaultActiveMqPassword'])

            sendContent = ''
            repostOpt = InputRule.get("RepostOption", 0)

            if repostOpt == 1:
                #JSON全文转发
                sendContent = json.dumps(InputData, ensure_ascii=False)

            elif repostOpt == 2:
                #XML全文转发
                def dict2xml(InputData, RootName):
                    from xml.dom.minidom import Document
                    import copy
                    if type(InputData) != dict:
                        raise TypeError("Invalid InputData type, expecting dict")
                    def build(father, structure):
                        if type(structure) == dict:
                            for k in structure:
                                tag = doc.createElement(str(k))
                                father.appendChild(tag)
                                build(tag, structure[k])

                        elif type(structure) == list:
                            grandFather = father.parentNode
                            tagName = father.tagName
                            grandFather.removeChild(father)
                            for l in structure:
                                tag = doc.createElement(tagName)
                                build(tag, l)
                                grandFather.appendChild(tag)

                        else:
                            father.appendChild(doc.createTextNode(str(structure)))
                    doc = Document()
                    root = doc.createElement(RootName)
                    doc.appendChild(root)
                    build(root, InputData)

                    return doc.toprettyxml(indent="    ")
                sendContent = dict2xml(InputData,InputData['DataType'])

            else:
                if InputRule.get('JsonEscape', False):
                    for itm in InputData:
                        if type(InputData[itm]) in {str, bytes}:
                            InputData[itm] = json.encoder.py_encode_basestring(InputData[itm])[1:-1]
                sendContent = self.ReplaceSpaceHolder(InputData, InputRule.get('ContentBody', ''))
            
            sendDestination = '/{0}/{1}'.format(
                self._SettingItems.get(
                    'DefaultTopicOrQueue',
                    ""
                ), 
                self._SettingItems.get(
                    'DefaultDestination', 
                    ""
                )
            )
            self.conn.send(body=sendContent, destination=sendDestination)
        except Exception as e:
            self._PluginLogger.exception(str(e))
        finally:
            return super().RuleHit(InputData, InputRule, HitItem)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return("ActiveMQ队列消息发送插件")

    @property
    def AliasName(self):
        return 'activemq'