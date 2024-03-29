import os, sys
import datetime
import json
import importlib
import ColorLogger

#def log(log_type="i",text=""):
#    clogger = ColorLogger.ColorLogger("InputParser:     ")
#    return clogger.log(log_type,text)

class InputParser:
    def __init__(self,args):
        self.args = args
        self.config = []
        self.clogger = ColorLogger.ColorLogger("InputParser:     ",self.args.logname)

    def log(self,log_type="i",text=""):
        return self.clogger.log(log_type,text)

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
                self.log("i","Reading input config file: "+altDir+"/"+str(configFile))
            else:
                self.log("e","Configuration file not found.")
                sys.exit(0)
        else:
            os.system("cp "+configFile+" "+exeDir)
            isCopy = True
            self.log("i","Reading input config file: "+str(configFile))
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
                                standByMode = False
                                if 'waitingTime' in seq.keys(): standByMode = True     
                                for irep in range(0,int(seq['repeat'])):
                                    _oneSeq = {
                                                'type'       : seq['type'],
                                                'bias'       : seq['bias'],
                                                'sampleTime' : seq['sampleTime'],
                                                'nSamples'   : seq['nSamples']
                                              }
                                    if standByMode:
                                        _oneSeq['waitingTime'] = seq['waitingTime']  
                                    self.config.append(_oneSeq) 
                            else:
                                self.log("e","IV-type of measurement requires: \'bias\',\'sampleTime\' and \'nSamples\' parameters.")
                                sys.exit(0)
                        elif 'standbyZ' in seq['type']:
                            hasAllAttr = True
                            for att in ['waitingTime']:
                                if att not in seq:
                                    hasAllAttr = False
                                else:
                                    if not isinstance(seq[att], int):
                                        if isinstance(seq[att], list) and len(seq[att]) >= 1:
                                            _val = seq[att][0]
                                            seq[att] = _val
                            if hasAllAttr:
                                _oneSeq = {
                                           'type'        : seq['type'],
                                           'waitingTime' : seq['waitingTime']
                                          }
                                self.config.append(_oneSeq)
                            else:
                                self.log("e","StandByZ-type of measurement requires: \'waitingTime\' parameter.")
                                sys.exit(0) 
                        else:
                            self.log("e","Unknown measurement type: "+str(seq['type']))
                            sys.exit(0)
                    else:
                        self.log("e","Measurement type not specified.")
                        sys.exit(0)
            else:
                self.log("e","Key word: \"sequence\" required and not found. Measurement sequence is unknown.")
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
                                standByMode = False
                                if 'waitingTime' in seq.keys(): standByMode = True
                                for irep in range(0,int(seq['repeat'])):
                                    _oneSeq = {
                                                'type'       : seq['type'],
                                                'bias'       : seq['bias'],
                                                'sampleTime' : seq['sampleTime'],
                                                'nSamples'   : seq['nSamples']
                                              }
                                    if standByMode:
                                        _oneSeq['waitingTime'] = seq['waitingTime']
                                    self.config.append(_oneSeq) 
                            else:
                                self.log("e","IV-type of measurement requires: \'bias\',\'sampleTime\' and \'nSamples\' parameters.")
                                sys.exit(0)
                        elif 'standbyZ' in seq['type']:
                            hasAllAttr = True
                            for att in ['waitingTime']:
                                if att not in seq:
                                    hasAllAttr = False
                                else:
                                    if not isinstance(seq[att], int):
                                        if isinstance(seq[att], list) and len(seq[att]) >= 1:
                                            _val = seq[att][0]
                                            seq[att] = _val
                            if hasAllAttr:
                                _oneSeq = {
                                           'type'        : seq['type'],
                                           'waitingTime' : seq['waitingTime']
                                          }
                                self.config.append(_oneSeq)
                            else:
                                self.log("e","StandByZ-type of measurement requires: \'waitingTime\' parameter.")
                                sys.exit(0)
                        else:
                            self.log("e","Unknown measurement type: "+str(seq['type']))
                            sys.exit(0)
                    else:
                        self.log("e","Measurement type not specified.")
                        sys.exit(0) 
        else:
            self.log("e","Unknown format for input configuration file.")
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
            self.log("w","No measurement sequence defined.")
        else:
            for seq in self.config:
                if "IV" in seq['type']:
                    self.log("i","    TYPE: "+seq['type'])
                    self.log("i","        BIAS: "+str(seq['bias']))
                    if "waitingTime" in seq.keys():
                        self.log("i","        STANDBY: "+str(seq['waitingTime'])) 
        return self.config

