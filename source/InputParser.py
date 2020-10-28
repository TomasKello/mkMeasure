import os, sys
import datetime
import json
import importlib

def log(log_type="i",text=""):
    source = "InputParser:     "
    if "i" in log_type:
        print(source,"[INFO]     ",text)
    elif "n" in log_type:
        print("                  ",text)
    elif "w" in log_type:
        print(source,"[WARNING]  ",text)
    elif "e" in log_type:
        print(source,"[ERROR]    ",text)
    elif "f" in log_type:
        print(source,"[FATAL]    ",text)
    elif "t" in log_type and "tt" not in log_type:
        print("<<     ",text)
    elif "tt" in log_type:
        return input(text+"  >>")

class InputParser:
    def __init__(self,args):
        self.args = args
        self.config = []

    def _date(self):
        _date = datetime.datetime.now()
        month = str(_date.month)
        day = str(_date.day)
        if len(str(_date.month)) == 1: month = "0"+str(_date.month)
        if len(str(_date.day)) == 1: day = "0"+str(_date.day)
        return str(_date.year)+month+day

    def load(self,configFile):
        #--------------
        #FIND CFG
        #--------------
        exe = sys.executable
        exeDir = exe[:exe.rfind("/")]
        altDir = exeDir[:exeDir.rfind("/")]+"/configuration"
        isCopy = False
        if not os.path.exists(configFile):
            if configFile.startswith("./"): configFile = configFile.replace("./","")
            if os.path.exists(altDir+"/"+configFile):
                os.system("cp "+altDir+"/"+configFile+" "+exeDir)
                isCopy = True
                log("i","Reading input config file: "+altDir+"/"+str(configFile))
            else:
                log("e","Configuration file not found.")
                sys.exit(0)
        else:
            os.system("cp "+configFile+" "+exeDir)
            isCopy = True
            log("i","Reading input config file: "+str(configFile))
            configFile = configFile[configFile.rfind("/")+1:]

        #--------------
        #PYTHON
        #--------------
        if configFile.endswith(".py"):
            _cfg = importlib.import_module(configFile.replace(".py",""))
            if hasattr(_cfg,"sequence"):
                for key,seq in _cfg.sequence.items():
                    if 'type' in seq:
                        #Add repeat attribute if missing
                        if 'repeat' not in seq:
                            seq['repeat'] = 1

                        #Check for attributes needed for IV measurement
                        if 'IV' in seq['type']:
                            hasAllAttr = True
                            for att in ['bias','sampleTime','nSamples']:
                                if att not in seq: 
                                    hasAllAttr = False
                                else:
                                    if not isinstance(seq[att], list):
                                        _list = []
                                        _list.append(seq[att])
                                        seq[att] = _list
                            if hasAllAttr:    
                                for irep in range(0,int(seq['repeat'])):
                                    self.config.append({ 
                                                          'type'       : seq['type'],
                                                          'bias'       : seq['bias'],
                                                          'sampleTime' : seq['sampleTime'],
                                                          'nSamples'   : seq['nSamples']
                                                       })
                            else:
                                log("e","IV-type of measurement requires: \'bias\',\'sampleTime\' and \'nSamples\' parameters.")
                                sys.exit(0)
                        else:
                            log("e","Unknown measurement type: "+str(seq['type']))
                            sys.exit(0)
                    else:
                        log("e","Measurement type not specified.")
                        sys.exit(0)
            else:
                log("e","Key word: \"sequence\" required and not found. Measurement sequence is unknown.")
                sys.exit(0)

        #--------------
        #JSON
        #--------------
        elif configFile.endswith(".json"):
            with open(configFile, 'r') as _cfgFile: 
                _cfg=json.load(_cfgFile)
                for seq in _cfg:
                    if 'type' in seq:
                        #Add repeat attribute if missing
                        if 'repeat' not in seq:
                            seq['repeat'] = 1

                        #Check for attributes needed for IV measurement
                        if 'IV' in seq['type']:
                            hasAllAttr = True
                            for att in ['bias','sampleTime','nSamples']:
                                if att not in seq:
                                    hasAllAttr = False
                                else:
                                    if not isinstance(seq[att], list):
                                        _list = []
                                        _list.append(seq[att])
                                        seq[att] = _list
                            if hasAllAttr:
                                for irep in range(0,int(seq['repeat'])):
                                    self.config.append({
                                                          'type'       : seq['type'],
                                                          'bias'       : seq['bias'],
                                                          'sampleTime' : seq['sampleTime'],
                                                          'nSamples'   : seq['nSamples']
                                                       })
                            else:
                                log("e","IV-type of measurement requires: \'bias\',\'sampleTime\' and \'nSamples\' parameters.")
                                sys.exit(0)
                        else:
                            log("e","Unknown measurement type: "+str(seq['type']))
                            sys.exit(0)
                    else:
                        log("e","Measurement type not specified.")
                        sys.exit(0) 
        else:
            log("e","Unknown format for input configuration file.")
            sys.exit(0)

        #--------------
        #CLEAN
        #--------------
        if isCopy:
            os.system("rm "+exeDir+"/"+configFile)

        #--------------
        #Return config
        #--------------
        if len(self.config) == 0:
            log("w","No measurement sequence defined.")
        else:
            for seq in self.config:
                if "IV" in seq['type']:
                    log("i","    TYPE: "+seq['type'])
                    log("i","        BIAS: "+str(seq['bias']))
        return self.config

