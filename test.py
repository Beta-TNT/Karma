from Karma import AnalyseBase
import uuid

SampleData1={
    'SampleField1': 'setup.exe',
    'SampleField2':{
        'SubSampleField1': 'eula.txt',
        'SubSampleField2': 'install.dll'
    }
}

SampleData2={
    'SampleField1': 'install.exe',
    'SampleField2': 'setup.exe'
}

SampleRule1 = {                                  # A simple sample rule dict
    'RuleName': 'SampleRule',                   # Optional, actually not even used.
    'Operator': 1,                              # OpAnd
    'PrevFlag': '',                             # 
    'ExcludeFlag': None,                        # 
    'RemoveFlag': None,                         # 
    'CurrentFlag': 'RuleHit:{SampleField1}',    # 
    'PluginName': 'shellexec',                  # try the plugin alias name, you can call a plugin via its filename or alias
    'ShellCommand': 'notepad.exe',              # if this rule hit, note pad will be show up
    'FieldCheckList': [                         # Optional, if field check is not necessary
        {
            'PluginName': 'condition',          # condition plugin
            'MatchCode': 7,                     # without "FieldName", MatchCode=7/-7 will try current level data on sub field check rules
            'Operator': 1,
            'MatchContent': [
                {
                    'PluginName': 'slicer',         # try another plugin, the slicer
                    'FieldName': 'SampleField1',        # slicer on "SampleField1" field
                    'SliceFrom': -4,                    # let's see if the last 4 char of SampleField1 field makes ".exe"
                    'MatchContent': '.exe',
                    'MatchCode': 1
                },
                {
                    'PluginName': 'FieldCheckPluginSlicer',
                    'FieldName': 'SampleField1',        # Required
                    'SliceTo': 4,                    # AnalyzerPluginSlicer Plugin rule field
                    'MatchContent': 'setu',
                    'MatchCode': 1
                }
            ],
            'SuccessBranch':{
                'FieldName': 'SampleField2',        # "FieldName" assigned
                'MatchCode': 7,                     # with valid FieldName assigned, MatchCode=7/-7 will tread field SampleField2 as another dict and try the field check rules on it
                'Operator': 1,                      # OpAnd
                'MatchContent': [                   # field check list
                    {
                        'MatchCode': 7,
                        'Operator': 1,
                        'MatchContent':[
                            {
                                'FieldName': 'SubSampleField1',
                                'MatchContent': '\.txt',
                                'MatchCode': 3,                     # Required
                            },
                            {
                                'FieldName': 'SubSampleField2',
                                'PluginName': 'regex',              # regular expression test
                                'RegexFunc': 'findall',
                                'RegexPattern': '\.DLL',
                                'ResultIndex': 0,                   # extract result index zero
                                'RegexFlag': 2,                     # re.IGNORECASE
                                'MatchCode': 1,
                                'MatchContent': '.dll'
                            }
                        ]
                    }
                ]
            }
        }
    ]
}

SampleRule2 = {                                  # A simple sample rule dict
    'RuleName': 'SampleRule',                   # Optional, actually not even used.
    'Operator': 1,                              # OpAnd
    'PrevFlag': 'RuleHit:{SampleField2}',       # Optional, default value: None
    'ExcludeFlag': None,                        # Optional, default value: None
    'RemoveFlag': None,                         # Optional, default value: None
    'CurrentFlag': 'time to stop this',       # Optional, default value: None
    'PluginName': 'RulePluginShellexec',
    'ShellCommand': 'calc.exe',
    'FieldCheckList': [                         # Optional, if field check is not necessary
        {
            'FieldName': 'SampleField2',
            'MatchContent': 'setup.exe',
            'MatchCode': 1,                     # Equal test
        }
    ]
}


def DummyCallbackFunc1(InputData, HitRule, HitItem, RemovedItem):
    print('rule hit!')
    #print(HitRule)
    rtn = str(uuid.uuid1())
    print(rtn)
    return rtn

def DummyCallbackFunc2(InputData, HitRule, HitItem, RemovedItem):
    print('another rule hit!')
    #print(HitRule)
    print(HitItem)
    return str(uuid.uuid1())

if __name__=='__main__':
    k = AnalyseBase()
    rules = {
        'rule1':SampleRule1,
        'rule2':SampleRule2
    }
    k.SingleRuleAnalyse(SampleData1, SampleRule1, DummyCallbackFunc1)
    hitItems2=k.MultiRuleAnalyse(SampleData2, rules, DummyCallbackFunc2)

    pass