# pysyslogclient package acquired.
# install cmd: pip install pysyslogclient
import pysyslogclient
import sys, os, urllib, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import Karma

class RulePlugin(Karma.AnalyseBase.RulePluginBase):
    _PluginRuleFields = {
        "LogContent": (
            "日志内容，支持占位符。注意SYSLOG日志最长1000字节，内容可能被截断", 
            str,
            ''
        ),
        "LogPriority": (
            "日志等级，取值范围从0-7,。7为最低级（debug），0为最高级（emerg）", 
            int,
            0
        ),
        'SyslogServerUrl':(
            'Syslog服务器URL，如该参数存在且有效，将代替默认配置，发送日志到该URL指定的Syslog服务。格式范例："udp://192.168.0.1:514"',
            str,
            ''
        ),
        'Repost':(
            '全文转发选项，0/None/不存在=不转发；1=JSON格式转发；2=XML格式转发，该选项有效时会覆盖LogContent字段，注意SYSLOG日志最长1000字节，内容可能被截断',
            int,
            0
        )
    }

    _SettingItemProperties = {
        'DefaultSyslogServerUrl': (
            '如果不在规则中指定SyslogServerUrl，默认发送的目的Syslog服务器URL。格式范例："udp://127.0.0.1:514"', 
            str,
            'udp://localhost:514'
        ),
        'Facility': (
            '日志以何种设备代码发送，范围从0~23',
            int,
            0,
            lambda x:0<=x<=23,
            'invalid port number: %s, expecting 0-23'
        ),
        'LocalLog': (
            '是否将日志内容写入本地文件',
            bool,
            False
        )
    }

    __SyslogClient = None
    _PluginFilePath = os.path.abspath(__file__)

    def __init__(self, AnalyseBaseObj):
        super().__init__(AnalyseBaseObj)
        self.PluginInit()

        try:
            TargetUrl = urllib.parse.urlparse(self._SettingItems.get('DefaultSyslogServerUrl', ""))
            TargetProtocol = TargetUrl.scheme
            TargetHost, TargetPort = urllib.parse.splitnport(TargetUrl.netloc, 0)
            TargetProtocol = 'udp' if TargetProtocol not in {'tcp', 'udp'} else TargetProtocol
            self.__SyslogClient = pysyslogclient.SyslogClientRFC5424(TargetHost, TargetPort, proto=TargetProtocol)
            if self._SettingItems.get('LocalLog', False):
                self._PluginLogger.info("Syslog sender started.")
        except Exception as e:
            raise e

    def RuleHit(self, InputData, InputRule, HitItem):
        '数据分析方法接口，接收被分析的dict()类型数据和命中的规则作为参考数据，返回值定义同SingleRuleTest()函数'
        # 该方法是唯一一个由分析引擎直接调用的方法。
        repostOption = InputRule.get("Repost", 0)
        if repostOption == 1: # JSON全文转发
            LogContent = json.dumps(InputData)
        elif repostOption == 2: # XML全文转发
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

                return doc.toprettyxml()

            LogContent = dict2xml(InputData, InputData['DataType'])
        else:
            LogContent =self.ReplaceSpaceHolder(InputData, InputRule.get('LogContent', ""))

        Facility =int(self._SettingItems.get("Facility", 23))
        LogPriority = int(InputRule.get("LogPriority", self._SettingItems.get("LogPriority", 7)))
        SyslogServerUrl = InputRule.get('SyslogServerUrl', self._SettingItems.get("DefaultSyslogServerUrl", ""))
        if SyslogServerUrl:
            TargetUrl = urllib.parse.urlparse(SyslogServerUrl)
            TargetProtocol = TargetUrl.scheme
            TargetHost, TargetPort = urllib.parse.splitnport(TargetUrl.netloc, 0)
            if TargetProtocol and TargetHost and TargetPort:
                TargetProtocol = TargetProtocol.lower()
                if TargetProtocol not in {'tcp', 'udp'}:
                    TargetProtocol = 'udp'
                pysyslogclient.SyslogClientRFC5424(
                    server=TargetHost,
                    port=TargetPort,
                    proto=TargetProtocol
                ).log(
                    message=LogContent, 
                    facility=Facility,
                    severity=LogPriority
                )
            else:
                self.__SyslogClient.log(LogContent, Facility, LogPriority)
        else:
            self.__SyslogClient.log(LogContent, Facility, LogPriority)
        
        if self._SettingItems.get('LocalLog'):
            self._PluginLogger.info(LogContent)

        return super().DataPreProcess(InputData, InputRule, HitItem)

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Syslog 客户端插件，可向指定的syslog服务器发送日志。请确保分析引擎到syslog服务器之间网络可达"
    @property
    def AliasName(self):
        return 'syslog'
