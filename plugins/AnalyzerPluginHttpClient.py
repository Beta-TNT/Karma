import os, sys, json, copy
from urllib import request, error, parse
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import NeoHoney_Analyse

class AnalysePlugin(NeoHoney_Analyse.NeoHoneyAsyncPlugin):
    'HTTP客户端插件，从异步调用插件基类继承，只需实现WorkFunc()函数，基类即可采用多线程的方式执行。需要DefaultReturnValue配置项'
    _SettingItemProperties = {
        'Timeout':(
            '超时长度，单位是秒',
            float,
            10
        ),
        'DefaultMethod': (
            '默认的HTTP方法，值只能是POST或者GET，当该值内容无效时，实际生效的是GET', 
            str,
            'GET',
            lambda x:x in ('GET', 'POST'),
            'invalid value: %s, expecting "GET" or "POST"'
        ),
        'DefaultUrl':(
            '默认的目的URL，不支持占位符',
            str,
            'http://localhost'
        ),
        'DefaultHeaders':(
            '默认使用的HTTP HEADERS，JSON格式，不支持占位符',
            str,
            ''
        )
    }

    _ExtraRuleFields = {
        'Method': (
            'HTTP方法，值只能是POST或者GET，该项有效时将覆盖默认Method配置', 
            str,
            'GET',
            lambda x:x in ('GET', 'POST'),
            'invalid value: %s, expecting "GET" or "POST"'
        ),
        'Url': (
            '目的URL，可包含占位符，会对插入URL的占位符内容进行URL ENCODING。该项有效时将覆盖默认的目的URL', 
            str,
            ''
        ),
        'Headers': (
            'JSON格式的HTTP HEADERS，不支持占位符。该项参数有效时将覆盖默认使用的HTTP HEADERS',
            str,
            ''
        ),
        'Body': (
            'HTTP请求体，可包含占位符，该数据项仅在Method为POST时有效',
            str,
            ''
        ),
        "RepostOption": (
            "全文转发选项，将传入插件的原始数据全文作为Body以指定格式发送到目的URL，该选项有效时将覆盖Method和Body字段（Method字段强制为POST）。0或其他值=不转发；1=JSON格式全文转发，2=XML格式全文转发", 
            int,
            0
        )
    }
    
    __DefaultHeaders = None
    _PluginFilePath = os.path.abspath(__file__)

    def __init__(self, AnalyseObj):
        super().__init__(AnalyseObj)
        self.PluginInit()
        # 读取默认配置里的HTTP HEADERS
        try:
            self.__DefaultHeaders = json.loads(self._SettingItems.get('DefaultHeaders', None))
        except Exception:
            self.__DefaultHeaders = dict()

        # 读取默认配置里的HTTP METHOD
        self._SettingItems['DefaultMethod'] = self._SettingItems['DefaultMethod'].upper()
        if self._SettingItems['DefaultMethod'] not in ['POST', 'GET']:
            self._SettingItems['DefaultMethod'] = 'GET'

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "Http客户端插件"

    def _WorkerFunc(self, InputData, InputRule):
        '请求发送函数'
        # 构造URL
        targetUrl = ''
        if InputRule.get("Url", '') != '':
            targetUrl = InputRule['Url']
            if targetUrl.find("{") >= 0:
                #可能包含占位符，因为需要深拷贝比较花时间，先判断用不用进行URL编码以及占位符替换
                urlInputData = copy.deepcopy(InputData)
                for k in urlInputData:
                    urlInputData[k] = parse.quote(str(urlInputData[k]),encoding='utf-8')
                targetUrl = self.ReplaceSpaceHolder(urlInputData, targetUrl)
        else:
            targetUrl = self._SettingItems['DefaultUrl']

        #构造HEADERS
        usingHeaders = None
        if self.__DefaultHeaders != None:
            usingHeaders = self.__DefaultHeaders
        else:
            try:
                usingHeaders = json.loads(InputRule.get('Headers', ''))
            except Exception:
                # 没有有效的headers，用个空的默认headers
                usingHeaders = dict()
        
        #构造request
        req = request.Request(url=targetUrl, headers=usingHeaders)

        if InputRule.get('RepostOption', 0) == 1:
            # JSON全文转发
            req.method = 'POST'
            req.data = json.dumps(InputData).encode(encoding='utf-8')
            pass
        elif InputRule.get('RepostOption', 0) == 2:
            # XML全文转发
            req.method = 'POST'
            def dict2xml(InputData, RootName):
                from xml.dom.minidom import Document
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
            req.data = str(dict2xml(InputData, InputData.get('DataType','Data'))).encode(encoding='utf-8')
        else:
            # 其他
            usingMethod = InputRule.get('Method', '').upper()
            if usingMethod not in ['POST', 'GET']:
                usingMethod = self._SettingItems['DefaultMethod']
            req.method = usingMethod
            if req.method == 'POST' and InputRule.get('Body', '') != '':
                req.data = InputRule['Body'].encode(encoding='utf-8')

        self._PluginLogger.info('{method} {url}'.format(method=usingMethod, url=targetUrl))
        
        #发送请求
        try:
            resp = request.urlopen(req, timeout=self._SettingItems['Timeout'])
            self._PluginLogger.info(resp.read().decode('utf-8'))
        except error.HTTPError as e:
            #HTTP错误处理
            print(e.reason, e.code, sep='\n')
            self._PluginLogger.error('{code} {reason}'.format(code=e.code, reason=e.reason))
        except error.URLError as e:
            #URL错误
            self._PluginLogger.error(e.reason)
            print(e.reason)
