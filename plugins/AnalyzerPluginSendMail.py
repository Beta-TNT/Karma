import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os, sys, json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from NeoHoney_Analyse import NeoHoneyAsyncPlugin

class AnalysePlugin(NeoHoneyAsyncPlugin):
    '邮件发送插件，从异步调用插件基类继承，只需实现WorkFunc()函数，基类即可采用多线程的方式执行。需要DefaultReturnValue配置项'
    _SettingFilePath = os.path.dirname(os.path.realpath(__file__)) + '/settings/' + '.'.join(os.path.basename(__file__).split('.')[:-1]) + '.json'
    _ExtraRuleFields = {
        "MailSubject": (
            "邮件标题，支持占位符", 
            str,
            ''
        ),
        "MailContent": (
            "邮件正文，支持占位符", 
            str,
            ''
        ),
        "To": (
            "接收邮箱列表，多个邮箱用英文分号';'分隔", 
            str,
            ''
        ),
        "RepostOption": (
            "全文转发选项，将传入插件的原始数据全文作为MailContent以指定格式发送到目的邮箱，该选项有效时将覆盖MailContent字段。0或其他值=不转发；1=JSON格式全文转发，2=XML格式全文转发", 
            int,
            0
        )
    }

    _SettingItemProperties = {
        'SmtpServer': (
            'SMTP邮件服务器IP地址', 
            str,
            'localhost'
        ),
        'SmtpPort': (
            'SMTP服务端口，通常是25', 
            int,
            25,
            lambda x:0<x<65536,
            'invalid port number: %s, expecting 1-65535'
        ),
        'UserName': (
            '登录邮箱',
            str,
            'username'
        ),
        'Password': (
            '邮件服务密码',
            str,
            'password'
        ),
        'DefaultReturnValue': (
            '默认返回值',
            bool,
            False
        )
    }

    _PluginFilePath = os.path.abspath(__file__)

    def __init__(self, AnalyseBaseObj):
        super().__init__(AnalyseBaseObj)
        self.PluginInit()

    @property
    def PluginInstructions(self):
        '插件介绍文字'
        return "邮件发送插件"

    def _WorkerFunc(self, InputData, InputRule, AnalyseObj):
        '邮件发送函数'
        receivers = InputRule.get('To', '').split(';')
        repostOpt = InputRule.get("RepostOption", 0)

        mailCtn = ''

        if repostOpt == 1:
            #JSON全文转发
            mailCtn = json.dumps(InputData)

        elif repostOpt == 2:
            #XML全文转发
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

            mailCtn = dict2xml(InputData, InputData['DataType'])

        else:
            mailCtn = self.ReplaceSpaceHolder(InputData, InputRule.get('MailContent', ''))
        try:
            message = MIMEText(mailCtn, 'plain', 'utf-8')
            message['From'] = Header(self._SettingItems['UserName'], 'utf-8')
            message['To'] =  Header(receivers[0], 'utf-8')
            message['Subject'] = Header(self.ReplaceSpaceHolder(InputData, InputRule.get('MailSubject','')), 'utf-8')
            self._PluginLogger.info('From: %s' % message['From'])
            self._PluginLogger.info('To: %s' % message['To'])
            self._PluginLogger.info('Subject: %s' % message['Subject'])
            with smtplib.SMTP() as smtpObj:
                smtpObj.connect(self._SettingItems['SmtpServer'], self._SettingItems['SmtpPort'])
                smtpObj.login(self._SettingItems['UserName'], self._SettingItems['Password'])
                smtpObj.sendmail(self._SettingItems['UserName'], receivers, message.as_string())
                smtpObj.quit()
                self._PluginLogger.info('Mail sent successful.')
        except Exception as e:
            self._PluginLogger.exception(e)