#!/usr/bin/env python

import os, sys
import time
import datetime as dt
import importlib
import ColorLogger

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("Device:          ")
    return clogger.log(log_type,text)

class Device:
    def __init__(self,args):
        ###########################
        #Class handling all devices
        ###########################
        self.delim = '\n'
        now = dt.datetime.now()
        self.year = str(now.year)
        self.month = str(now.month)
        self.day = str(now.day)
        self.hr = str(now.hour)
        self.min = str(now.minute)
        self.sec = str(now.second)
        self.args = args
        self.devs = {}
        self.coms = {}

    def __getResponse__(self, com):
        #######################################################
        #Get response from selected device based on given 
        #device ID. If there is no response, user is asked
        #to turn on connected machine. If response does not
        #correspond to given ID, user is urged to select 
        #ports manually or to change configuration.
        #######################################################

        _devs = {}
        try:
            _mod = importlib.import_module(com['id'])
            _class = getattr(_mod,com['id']) 
            _devs[com['id']] = _class()
        except ImportError:
            log("e",com['id']+".py class not found! Please provide dedicated class for this device.")
            sys.exit(0)
        except AttributeError:
            log("e",com['id']+" class not specified. Name of the module must match the class name and start with capital letter.")
            sys.exit(0)
        except FileNotFoundError:
            log("e",com['id']+".py class tried to load non-existing binaries.")
            sys.exit(0)
        except Exception as e:
            log("f",com['id']+".py class raised an unknown exception! Check for syntax errors.")
            log("f",str(type(e)))
            sys.exit(0)

        if _devs[com['id']].test() == com['id']:
            log("i","Loading command library and sub-routines for "+com['id']+".")
        else:
            log("e","This class do not match "+com['id']+" device!")
            sys.exit(0)

        self.devs[com['id']] = _devs[com['id']]                      #Enable access to device routines
        self.__write__(self.__cmd__(com,"CMDINIT"))                  #Some devices require initial sequence to enable sending commands
        real_id = self.__read__(self.__cmd__(com,"ID?",vital=True))  #Real ID may contain more strings than predefined keyword
        #clean real ID from invisible symbols
        if "\r" in real_id:
            real_id = "".join([c for c in real_id.split("\r") if c != ""])
        if "\n" in real_id:
            real_id = "".join([c for c in real_id.split("\n") if c != ""])
        if real_id is not "":
            if real_id == "REFUSED":
                log("e","Socket connection refused for DEV="+com['id']+".")
                log("e","Server is switched OFF.")
                sys.exit(0)
            if com['model'] not in real_id and com['model'][1:] not in real_id: 
                if self.args.selectPort:
                    log("w","Outdated or not matching class for DEV="+com['id']+" was provided.")
                    log("w","MODEL found    = "+str(real_id)) 
                    log("w","MODEL required = "+com['model'])
                    log("e","Please use --selectPort again to select ports manually in case your class is not outdated.")
                    sys.exit(0)
                else:
                    log("w","Device ID="+com['id']+" not matched. Retry...")
                    real_id = "FAILED"
            else:
                log("i","Response received from DEV_NAME="+str(real_id))
        else:
            if self.args.selectPort:
                log("w","Please turn on device ID="+com['id']+".")
                sys.exit(0)
            else:
                log("w","Device ID="+com['id']+" not matched. Retry...")
                real_id = "FAILED"

        return real_id,com

    def __write__(self,cmd):
        #####################################
        #Write command in device-specific way
        #unless command is not vital and 
        #string is empty or unknown.
        #####################################

        if cmd['cmd'] == "" or cmd['cmd'] == "UNKNOWN":
            return False
        if self.args.verbosity > 2:
            log("i",cmd['id']+" : WRITECMD : \""+str(cmd['cmd'])+"\".")

        write_status = self.devs[cmd['id']].write(cmd['com'],cmd['cmd'])
        return write_status

    def __read__(self,cmd):
        #################################################
        #Read command return value in device-specific way
        #unless command is not vital and string is empty
        #or unknown.
        #################################################

        if cmd['cmd'] == "" or cmd['cmd'] == "UNKNOWN":
            return False   
        if self.args.verbosity > 2:
            log("i",cmd['id']+" : READCMD : \""+str(cmd['cmd'])+"\".")

        read_value = self.devs[cmd['id']].read(cmd['com'],cmd['cmd'])
        return read_value

    def __cmd__(self,com,cmd_type,arg="",vital=False,check=""):
        ##########################################
        #Return device specific command to be used 
        #in read/write routines.
        ##########################################

        #Define command category and redefine command type if needed
        cat = ""
        _cmd_type = ""
        if cmd_type[-1] == "?":
            cat = "get"
            _cmd_type = cmd_type[:-1]
        elif arg=="ON" or arg=="OFF":
            cat = "switch"
            _cmd_type = cmd_type
        elif len(str(arg))!=0:
            cat = "set"
            _cmd_type = cmd_type
        else:
            cat = "do"
            _cmd_type = cmd_type

        #Vital commands must be defined in corresponding class
        (raw_cmd,isOK,isNOT) = self.devs[com['id']].cmd(_cmd_type, arg = arg, cat = cat)
        if (vital and len(raw_cmd)==0) or (vital and raw_cmd=="UNKNOWN"):
            log("e","Command: "+_cmd_type+" not defined in "+com['id']+" class.")
            self.__terminate__("EXIT") #TODO: crosscheck for abort commands in device class must be done when importing
        if len(check) != 0:
            isBit = False
            for ok in isOK:
                if ":" in ok: isBit = True
            for ok in isNOT:
                if ":" in ok: isBit = True
            if not isBit:    
                if str(check) in isOK or (len(isOK) == 0 and str(check) not in isNOT):
                    return True
                else:
                    return False
            else:
                bitcheck = "{0:08b}".format(int(check))
                isOK_value = [ok.split(":")[0] for ok in isOK]
                isOK_bit   = [ok.split(":")[1] for ok in isOK]
                isNOT_value = [ok.split(":")[0] for ok in isNOT]
                isNOT_bit   = [ok.split(":")[1] for ok in isNOT]
                if (bitcheck[-int(isOK_bit[0])-1] == isOK_value[0]) or (len(isOK) == 0 and bitcheck[-int(isNOT_bit[0])-1] != isNOT_value[0]):
                    return True
                else:
                    return False

        #construct final command
        _cmd = {'id' : com['id'], 'com' : com['com'], 'cmd' : raw_cmd}
        
        return _cmd

    def __par__(self,com,par_type,vital=False):
        #######################################
        #Return device-specific parameter value
        #######################################

        #Vital parameters must be defined in corresponding class
        raw_par = self.devs[com['id']].par(par_type)
        if (vital and len(str(raw_par))==0) or (vital and str(raw_par)=="UNKNOWN"):
            log("e","Parameter: "+str(par_type)+" not defined in "+com['id']+" class.")
            self.__terminate__("EXIT")

        return raw_par

    def __checkInterlock__(self,dev_type="ALL", safeMode=False):
        #######################
        #Check interlock status
        #######################

        if dev_type == "ALL":
            for _dev_type in self.coms.keys():
                self.__checkInterlock__(_dev_type)
        else:
            dev_info = dev_type
            if dev_type == "meas":
                dev_info = "the main measurement device"
            elif dev_type == "source":
                dev_info = "the external high voltage source"
            elif dev_type == "zstation":
                dev_info = "z-station"
            else:
                dev_info = dev_type
            #Check if interlock is checkable
            if self.__par__(self.coms[dev_type],"interlockCheckable",vital=True):
                #Update interlock status 
                self.interlock[dev_type] = self.__read__(self.__cmd__(self.coms[dev_type],"INTERLOCK?",vital=True))
                if "\n" in self.interlock[dev_type]: self.interlock[dev_type] = self.interlock[dev_type].strip(",")[-1]
                if " "  in self.interlock[dev_type]: self.interlock[dev_type] = self.interlock[dev_type].strip(" ")[0]
                if ","  in self.interlock[dev_type]: self.interlock[dev_type] = self.interlock[dev_type].strip(",")[0]
                isOK = self.__cmd__(self.coms[dev_type],"INTERLOCK?",vital=True, check=self.interlock[dev_type]) 

                if len(self.interlock[dev_type])!=0:
                    if isOK:
                        log("i","Interlock exists for "+dev_info+".")
                    else:
                        log("h","Interlock cable for "+dev_info+" was found but it is not connected or fixture is open!!!")
                        if safeMode: 
                            self.__terminate__("EXIT")
                else:
                    log("h","Interlock for "+dev_info+" does not exist!!!")
                    if safeMode: 
                        self.__terminate__("EXIT")
            else:
                log("i","Interlock for "+dev_info+" is not defined or implicitely checked.")

    def __checkBias__(self,com,bias):
        #######################################################
        #Check if voltage to be set is inside of allowed range.
        #Return corrected value.
        #######################################################

        if float(bias) > self.maxBias:
            log("w","Selected bias overflow! Setting maximum bias: "+str(self.maxBias)+"V.")
            return str(self.maxBias)
        elif float(bias) < self.minBias:
            log("w","Selected bias underflow! Setting minimum bias: "+str(self.minBias)+"V.")
            return str(self.minBias)
        else:
            if self.__par__(com,"decimalVolt",vital=True):
                if len(str(bias).split(".")[-1]) > 2:
                    log("i","Maximum 2 decimal places are allowed. Pre-Setting bias to: "+"{:.2f}".format(bias)+"V.")
                else:
                    log("i","Pre-Setting bias to: "+"{:.2f}".format(bias)+"V.")
                return "{:.2f}".format(bias)
            else:
                log("i","Decimals not allowed. Pre-Setting bias to: "+str(int(bias))+"V.")
                return str(int(bias))

    def __checkBiasRange__(self,com,biasRange):
        ##################################################################
        #Check if values inside of bias range lie inside of allowed range.
        #Check if values inside of range are ordered properly.
        #Return corrected range.
        ##################################################################

        #Sort
        isNegative = True
        isPositive = True
        for bias in biasRange:
            if float(bias) > 0:
                isNegative = False
            if float(bias) < 0:
                isPositive = False
        if isNegative and not isPositive:
            biasRange.sort(reverse=True)
        else:
            biasRange.sort()
            
        #Check value    
        _biasRange = []
        for bias in biasRange:
            correct_bias = self.__checkBias__(com,bias)
            if len(_biasRange) > 0:
                if str(correct_bias) == str(_biasRange[-1]):
                    continue
                else:
                    _biasRange.append(correct_bias)
            else:    
                _biasRange.append(correct_bias)
        
        return _biasRange        

    def __setRemote__(self,dev_type="ALL"):
        ##########################################
        #Set device remote and disable front panel
        ##########################################

        if dev_type == "ALL":
            for _dev_type in self.coms.keys():
                self.__setRemote__(_dev_type)
        else:
            _vital = False
            if dev_type in ["meas","source"]:
                if self.__par__(self.coms[dev_type],"remoteCheckable",vital=True):
                    _vital = True
            self.__write__(self.__cmd__(self.coms[dev_type],"REMOTE",vital=_vital))

    def __setLocal__(self,dev_type="ALL"):
        ##########################################
        #Set device local and enable front panel
        ##########################################

        if dev_type == "ALL":
            for _dev_type in self.coms.keys():
                self.__setRemote__(_dev_type)
        else:
            _vital = False
            if self.__par__(self.coms[dev_type],"remoteCheckable",vital=True):
                _vital = True    
            self.__write__(self.__cmd__(self.coms[dev_type],"LOCAL",vital=_vital))

    def __getCurrentRange__(self,bias_point):
        ##################################################
        #Calculates predicted current range based on 
        #order of resistence under consideration
        ##################################################

        if int(bias_point) < 0: bias_point *= -1
        res = self.args.expOhm[0] #def=1e-9
        curr_range = 2e-3
        if int(bias_point) in range(200,1000):
            curr_range = 2e3/res #2muA
        elif int(bias_point) in range(20,200):   
            curr_range = 2e2/res #200nA
        elif int(bias_point) in range(2,20): 
            curr_range = 2e1/res #20nA   
        elif int(bias_point) in range(0,2):
            curr_range = 2e0/res #2nA
        return curr_range

    def __chargingTime__(self,initBias,targetBias):
        #######################################################
        #Calculate charging time to be used in sleep function. 
        #######################################################
 
        delta = abs(targetBias-initBias)
        biasStep = 10
        timeStep = 0.25
        isRes = delta%biasStep > 0
        nSteps = 0
        if isRes:
            nSteps = int((delta//biasStep)+1.0)
        else:
            nSteps = int(delta//biasStep)
        return nSteps*timeStep     

    def __detectMalfunction__(self,motionIsDone,dev_type="zstation"):
        ###########################################################
        #Aux function to detect malfunction of given station device
        ###########################################################

        if "station" not in dev_type:
            return False
        else:
            if "x" in dev_type: dev_type_info = "x-station"
            if "y" in dev_type: dev_type_info = "y-station"
            if "z" in dev_type: dev_type_info = "z-station"
        realVelo = self.__read__(self.__cmd__(self.coms[dev_type],"VELOCITY?"))
        if not motionIsDone:
            if self.args.verbosity > 2:
                log("i","Real velocity for "+str(dev_type_info).capitalize()+" is "+str(realVelo)+".")
            if realVelo and abs(float(realVelo)) > 0.:
                log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info).capitalize())
                self.__abort__(dev_type)
                self.__terminate__("EXIT")
            else:
                if self.args.verbosity > 1:
                    log("i","All movement stopped for "+str(dev_type_info).capitalize()+".")
        else:
            return False

    def __initDevice__(self,coms,EMG):
        #############################################
        #Run sequence of commands initializing device
        #############################################

        log("i","Initializing starting sequence.")

        #Minimum initialization in case of emergency
        if EMG:
            self.sleep_time = {}
            for dev_type in coms:
                #Sleep time constants
                self.sleep_time[dev_type] = {'short'  : self.__par__(coms[dev_type],"tShort"),
                                             'medium' : self.__par__(coms[dev_type],"tMedium"),
                                             'long'   : self.__par__(coms[dev_type],"tLong")
                                            }
            return False    

        #Bias boundaries for the source device
        if self.args.extVSource:
            self.minBias = self.__par__(coms['source'],"minBias")
            self.maxBias = self.__par__(coms['source'],"maxBias")
        else:
            self.minBias = self.__par__(coms['meas'],"minBias")
            self.maxBias = self.__par__(coms['meas'],"maxBias")    

        self.sleep_time = {}
        self.interlock =  {}
        self.stations = 0
        dev_type_info = ""
        for dev_type in coms:

            #Setup measurement device and HVSource
            if dev_type in ['meas','source']:
                if not self.args.extVSource and dev_type == 'source': continue

                #Reset device and Reset power-on default settings
                self.__write__(self.__cmd__(coms[dev_type],"RESET",vital=True))
                self.__write__(self.__cmd__(coms[dev_type],"POSETUP"))

                #Setting up system date and time
                self.__write__(self.__cmd__(coms[dev_type],"STIME",arg=self.hr+", "+self.min+", "+self.sec))
                self.__write__(self.__cmd__(coms[dev_type],"SDATE",arg=self.year+", "+self.month+", "+self.day))

            #General
            #Sleep time constants
            self.sleep_time[dev_type] = {'short'  : self.__par__(coms[dev_type],"tShort"),
                                         'medium' : self.__par__(coms[dev_type],"tMedium"),
                                         'long'   : self.__par__(coms[dev_type],"tLong")
                                        }

            #Disable time consuming redundant functions
            self.__write__(self.__cmd__(coms[dev_type],"MATH",arg="OFF"))

            #Zero Check Interlock (safeMode=False)
            self.__checkInterlock__(dev_type)

            #Setup xyz station(s)
            if "station" in dev_type:
                self.stations += 1
                if "x" in dev_type: dev_type_info = "x-station"
                if "y" in dev_type: dev_type_info = "y-station"
                if "z" in dev_type: dev_type_info = "z-station"

                #set velocity    
                self.__write__(self.__cmd__(coms[dev_type],"SVELOCITY",arg=self.__par__(coms[dev_type],"safeVelo")))
                if self.args.verbosity > 0:
                    setVelo = self.__read__(self.__cmd__(coms[dev_type],"SETVELO?"))
                    log("i",dev_type_info.capitalize()+" control velocity set to "+str(setVelo))

                #turn ON motor    
                self.__write__(self.__cmd__(coms[dev_type],"MOTOR",arg="ON",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(coms[dev_type],"MOTOR?",vital=True))))
                if not isMotorOn:
                    log("e",str(dev_type_info).capitalize()+" motor is turned OFF while expected working!")
                    self.__terminate__("EXIT")
                else:
                    if self.args.verbosity > 0:
                        log("i",str(dev_type_info).capitalize()+" motor is ON.")    
                
                #goto home position
                self.__write__(self.__cmd__(coms[dev_type],"GOHOME",vital=True))
                motionIsDone = False
                runTime = 0.
                runTimeError = 15.
                while not motionIsDone and runTime < runTimeError:
                    time.sleep(self.sleep_time[dev_type]['long'])
                    returnValue = str(self.__read__(self.__cmd__(coms[dev_type],"MOVE?",vital=True)))
                    if len(returnValue) != 0:
                        motionIsDone = bool(int(returnValue))
                    runTime += self.sleep_time[dev_type]['long']
                self.__detectMalfunction__(motionIsDone,dev_type)

                #goto top position with z-station only
                if "z" in dev_type:
                    self.__write__(self.__cmd__(coms[dev_type],"SGOTO",arg=self.__par__(coms[dev_type],"topPosition"),vital=True))
                    motionIsDone = False
                    runTime = 0.
                    runTimeError = 15.
                    while not motionIsDone and runTime < runTimeError:
                        time.sleep(self.sleep_time[dev_type]['long'])
                        returnValue = str(self.__read__(self.__cmd__(coms[dev_type],"MOVE?",vital=True)))
                        if len(returnValue) != 0:
                            motionIsDone = bool(int(returnValue))
                        runTime += self.sleep_time[dev_type]['long']
                    self.__detectMalfunction__(motionIsDone,dev_type)

        #notify user to position probe manually           
        if self.stations == 0:
            log("w","No station device is used. User is expected to ensure bias ring connection manually.")

    def __prepMeasurement__(self):
        ################################################################
        #Run sequence of commands in order to prepare measurement device 
        #(and external source) for particular measurement. In case of
        #very particular sub-routines required by device, these are
        #invoked from here.
        ################################################################

        #Inform about power-on settings
        powerOnSetup = ""
        if self.args.extVSource:
            powerOnSetup = self.__read__(self.__cmd__(self.coms['source'],"POSETUP?"))
        else:
            powerOnSetup = self.__read__(self.__cmd__(self.coms['meas'],"POSETUP?"))
        if not powerOnSetup or len(powerOnSetup) == 0: powerOnSetup = "UNKNOWN"    
        log("i","PowerOn setup: "+str(powerOnSetup))    

        #Clear buffer of measurement device and set buffer memory size
        self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True)) 

        #Zero check ON for measurement device + sleep time until done
        self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="ON"))
        time.sleep(self.sleep_time['meas']['medium'])

        #Run device specific pre-routine if specified by device-specific class (for all)
        for dev_type in self.coms:
            status, message = self.devs[self.coms[dev_type]['id']].pre(self.coms[dev_type]['com'])
            log(status, message)
            if status in ["e","f"]:
                self.__terminate__("EXIT")

        #Setting voltage limits in addition to crosschecked voltage bias
        if self.args.extVSource:
            self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['source'],"vlimitCheckable",vital=True):
                self.__write__(self.__cmd__(self.coms['source'],"SVOLTLIM",arg=str(max(abs(self.minBias),abs(self.maxBias))),vital=True)) #Set absolute voltage limit
            if self.args.verbosity > 0:
                limVSet = self.__read__(self.__cmd__(self.coms['source'],"VOLTLIM?"))
                limVDef = self.__par__(self.coms['source'],"defBias")
                if limVSet:
                    log("i","External Source Voltage limit was specified (manufacturer) to "+str(limVDef)+".")    
                    log("i","External Source Voltage limit was set (user) to "+str(limVSet)+".")
        else:
            self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['meas'],"vlimitCheckable",vital=True):
                self.__write__(self.__cmd__(self.coms['meas'],"SVOLTLIM",arg=str(max(abs(self.minBias),abs(self.maxBias))),vital=True)) #Set absolute voltage limit
            if self.args.verbosity > 0:
                limVSet = self.__read__(self.__cmd__(self.coms['meas'],"VOLTLIM?"))
                limVDef = self.__par__(self.coms['meas'],"defBias")
                if limVSet:
                    log("i","Measurement device Source Voltage limit was specified (manufacturer) to "+str(limVDef)+".")
                    log("i","Measurement device Source Voltage limit was set (user) to "+str(limVSet)+".")

        #re-enable safe connection by controling z-station only
        if 'zstation' in self.coms:
            if not self.__write__(self.__cmd__(self.coms['zstation'],"SGOTOREL",arg=self.__par__(self.coms['zstation'],"touchPosition"),vital=False)):
                self.__write__(self.__cmd__(self.coms['zstation'],"SGOTO",arg=self.__par__(self.coms['zstation'],"touchPosition"),vital=True))
            motionIsDone = False
            runTime = 0.
            runTimeError = 15.
            while not motionIsDone and runTime < runTimeError:
                time.sleep(self.sleep_time['zstation']['long'])
                returnValue = str(self.__read__(self.__cmd__(self.coms['zstation'],"MOVE?",vital=True)))
                if len(returnValue) != 0:
                    motionIsDone = bool(int(returnValue))
                runTime += self.sleep_time['zstation']['long']
            self.__detectMalfunction__(motionIsDone,"zstation")
        else:     
            log("w","If not done manually, probe is not touching sensor.")

    def __abort__(self,dev_type="ALL"):
        ####################################################################
        #Run sequence of abort commands to shut down critical systems.
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #Use in case of emergency only
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #dev_type = 
        #    "ALL": abort all devices
        #    "<dev_type>" : abort device under <dev_type>
        #    "EXIT" : abort program itself
        #         (WARNING: not safe if called without thinking!) 
        ####################################################################
        if dev_type != "EXIT":
            log("i","Abort requested for "+dev_type+".")
        else:
            log("i","Abort requested for ALL followed by EXIT.")

        if dev_type == "ALL":
            first_dev = ""
            if "source" in self.coms.keys():
                #LIFE HAZARD FIRST
                self.__abort__("source")
                first_dev = "source"
            elif "meas" in self.coms.keys():
                #MATERIAL DMG HAZARD SECOND
                self.__abort__("meas")
                first_dev = "meas"
            for _dev_type in self.coms.keys():
                #THEN THE REST
                if _dev_type != first_dev:
                    self.__abort__(_dev_type)
        elif dev_type != "EXIT":
            _vital = False
            if (dev_type == "meas" and not self.args.extVSource) or (dev_type == "source" and self.args.extVSource):
                _vital = True
            if dev_type in ["meas","source"]:
                #TURN OFF BIAS (LIFE HAZARD)
                self.__write__(self.__cmd__(self.coms[dev_type],"SVOLT",arg="0",vital=_vital))
                self.__write__(self.__cmd__(self.coms[dev_type],"SOURCE",arg="OFF",vital=_vital))
            elif "station" in dev_type:    
                #STOP ALL MOTION (MATERIAL DMG HAZARD)
                self.__write__(self.__cmd__(self.coms[dev_type],"STOP",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))
                if isMotorOn:
                    self.__write__(self.__cmd__(self.coms[dev_type],"MOTOR",arg="OFF",vital=True))
                    time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))    
                runTime = 0.
                runTimeError = 15.
                while isMotorOn and runTime < runTimeError:
                    time.sleep(self.sleep_time[dev_type]['medium'])
                    isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))
                    runTime += float(self.sleep_time[dev_type]['medium'])
        else:
            self.__abort__("ALL")
            sys.exit(0)

    def __terminate__(self,dev_type="ALL"):
        ####################################################################
        #Run sequence of commands to safely terminate any measurement
        #and to return device(s) to initial state. 
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #In case of life HAZARD / material damage HAZARD call __abort__()  
        #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        #dev_type = 
        #    "ALL": terminate all devices
        #    "<dev_type>" : terminate device under <dev_type>
        #    "EXIT" : terminates program itself
        #         (WARNING: not safe if called without thinking!) 
        ####################################################################
        if dev_type != "EXIT":
            log("i","Terminate requested for "+dev_type+".")
        else:
            log("i","Terminate requested for ALL followed by EXIT.")

        if dev_type == "ALL": 
            for _dev_type in self.coms.keys():
                self.__terminate__(_dev_type)
        elif dev_type != "EXIT":
            dev_type_info = ""
            if dev_type == "meas":
                dev_type_info = "main measurement device"
            elif dev_type == "source":
                dev_type_info = "external voltage source"
            elif dev_type == "zstation":
                dev_type_info = "z-station"
            else:
                dev_type_info = dev_type
            log("i","Finalizing measurement.")

            #FIRST SEQUENCE
            _vital = False
            if (dev_type == "meas" and not self.args.extVSource) or (dev_type == "source" and self.args.extVSource):
                _vital = True
            if dev_type in ["meas","source"]:    
                self.__write__(self.__cmd__(self.coms[dev_type],"SVOLT",arg="0",vital=_vital))
                source_stat = self.__read__(self.__cmd__(self.coms[dev_type],"SOURCE?",vital=_vital))
                if not self.__cmd__(self.coms[dev_type],"SOURCE?",vital=_vital,check=source_stat):
                    log("i","Turning OFF high-voltage source for "+dev_type_info+".")
                    self.__write__(self.__cmd__(self.coms[dev_type],"SOURCE",arg="OFF",vital=_vital))
                setVolt = self.__read__(self.__cmd__(self.coms[dev_type],"VOLT?",vital=_vital))
                if self.args.verbosity > 1:
                    log("i","Voltage re-set to zero for "+dev_type_info+": "+str(setVolt))    
            elif "station" in dev_type:    
                #stop motor movement if needed
                self.__write__(self.__cmd__(self.coms[dev_type],"STOP",vital=True))
                motionIsDone = False
                runTime = 0.
                runTimeError = 15.
                while not motionIsDone and runTime < runTimeError:
                    time.sleep(self.sleep_time[dev_type]['long'])
                    returnValue = str(self.__read__(self.__cmd__(self.coms[dev_type],"MOVE?",vital=True)))
                    if len(returnValue) != 0:
                        motionIsDone = bool(int(returnValue))
                    runTime += self.sleep_time[dev_type]['long']
                if not motionIsDone:
                    log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info))
                    self.__abort__(dev_type)
                else:
                    #cross check for real velocity
                    realVelo = self.__read__(self.__cmd__(self.coms[dev_type],"VELOCITY?",vital=True))
                    if realVelo and float(realVelo) > 0.:
                        log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info))
                        self.__abort__(dev_type)
                    else:
                        if self.args.verbosity > 1:
                            log("i","All movement stopped for "+str(dev_type_info)+".")
         
            #SECOND SEQUENCE        
            self.__write__(self.__cmd__(self.coms[dev_type],"ZCHECK",arg="ON"))
            self.__write__(self.__cmd__(self.coms[dev_type],"ZCOR",arg="OFF"))
            if "station" in dev_type:
                #turn OFF motor        
                self.__write__(self.__cmd__(self.coms[dev_type],"MOTOR",arg="OFF",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))
                if isMotorOn:
                    log("h",str(dev_type_info).capitalize()+" motor is turned ON while expected OFF!")
                    self.__abort__(dev_type)
                else:
                    if self.args.verbosity > 1:
                        log("i","Motor for "+str(dev_type_info)+" was turned OFF.")
            #set local
            self.__setLocal__(dev_type)

        elif dev_type == "EXIT":
            self.__terminate__("ALL")
            sys.exit(0)

    def load(self,COMS,SOCKETS,EMG):
        ########################################################
        #Global function called from mkMeasure to get response
        #from all devices in use and loading their sub-routines
        #from library.
        #COMS    = serial connections
        #SOCKETS = socket connections 
        ########################################################
        DEV_MEAS_NAME,self.coms['meas'] = self.__getResponse__(COMS['meas']) 
        if self.args.extVSource:
            DEV_SOURCE_NAME,self.coms['source'] = self.__getResponse__(COMS['source'])
        OTHER_DEV_NAMES = {}
        for dev_type in self.args.addPort:
            OTHER_DEV_NAMES[dev_type],self.coms[dev_type] = self.__getResponse__(COMS[dev_type])
        for dev_type in self.args.addSocket:    
            DEV_PROBE_NAME,self.coms[dev_type] = self.__getResponse__(SOCKETS[dev_type])
      
        loadStatus = {}
        if "FAILED" in DEV_MEAS_NAME:
            loadStatus['meas'] = (self.coms['meas']['port'],0)
        else:
            loadStatus['meas'] = (self.coms['meas']['port'],1)            
        if self.args.extVSource and "FAILED" in DEV_SOURCE_NAME:
            loadStatus['source'] = (self.coms['source']['port'],0)
        elif self.args.extVSource and "FAILED" not in DEV_SOURCE_NAME:
            loadStatus['source'] = (self.coms['source']['port'],1)
        for dev_type in self.args.addPort:
            if "FAILED" in OTHER_DEV_NAMES[dev_type]:
                loadStatus[dev_type] = (self.coms[dev_type]['port'],0)
            else:
                loadStatus[dev_type] = (self.coms[dev_type]['port'],1)
        allOK = True        
        for key in loadStatus.keys():
            port,valid = loadStatus[key]
            if valid == 0:
                allOK = False 
        if not allOK: return loadStatus

        #-----------------------------------------------------------------------------------------------
        #From now on one can write/read commands in Device under 
        #corresponding COM using general commands: 
        #    self.__read__(self.__cmd__(COM,"command",arg="arguments",vital="if command is neccessary"))
        #Evaluating more complicated sub-routines than read/write 
        #is also possible:
        #    self.devs[COM['id']].subroutine()
        #-----------------------------------------------------------------------------------------------

        #Initialize sequence 
        self.__initDevice__(self.coms,EMG)

        #Return success if all is OK
        return { 'success' : 1 }

    def sense(self,connectTimeError=0, fullManual=False):
        #############################################################
        #Global function called from mkMeasure providing real time
        #sensing for a presence of current. When connection is found,
        #table is moved to safe position.
        #############################################################
        #Sensitivity settings
        nSamples = 1            #samples per measurement
        sampleTime = 0.25       #time per sample
        residualCurrent = 2e-13 #minimum current
        currentStability = 2    #meaning at least 3 positive measurements in semi-automatic mode

        #Set remote control
        self.__setRemote__("meas")

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr"))
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))

        #Adjusting current range for measurement device
        self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg="OFF"))
        isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
        if not isAuto:
            log("i","IV measurement: Current AUTO range disabled.")
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(0.))))
            if self.args.verbosity > 0:
                setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                if setCurrRange:
                    log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
        else:
            log("i","IV measurement: Current AUTO range enabled.")

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?"))
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=self.__par__(self.coms['meas'],"triggerType"),vital=True))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            log("e","Trigger is not supported by this measurement device (or commands are not specified).")
       
        if connectTimeError == 0:
            #Wait until user confirms connection
            log("i","##################################################")
            log("i","#Please establish connection with measured sensor.")
            log("i","#To cancel manual sensing mode press \"n\".")
            log("i","##################################################")

            userInput = ""
            isConnected = False
            while not isConnected:
                userInput = log("tt","Press \"y\" to test connection: ")
                if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["y","f"]:
                    if fullManual or userInput.lower().split(" ")[0] == "f":
                        isConnected = True
                    else: #Check for residual current
                        #Sleep
                        time.sleep(self.sleep_time['meas']['short'])

                        #Read out measurement data
                        readout = ""
                        self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
                        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
                        time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                        self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                        readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?",vital=True))                                         #Read data from full buffer
                        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=True))                                     #Stop trigger
                        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

                        #Process read out
                        if len(readout) == 0:
                            log("w","Readout is empty!")
                            continue

                        current_readings = []
                        readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim",vital=True))
                        for iread,reading in enumerate(readout_list):
                            if self.__par__(self.coms['meas'],"readoutIdentifier",vital=True) in reading:
                                curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier",vital=True),''))
                                current_readings.append(curr)
                                if self.args.verbosity > 0:
                                    log("i","Current reading: "+str(curr))

                        current = 0.0
                        if len(current_readings) == nSamples:
                            current = sum(current_readings)/float(nSamples)
                        else:
                            if len(current_readings) == 0:
                                log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                                continue
                            else:
                                current = sum(current_readings)/float(len(current_readings))
                        
                        #Check for current residuals
                        if abs(current) > residualCurrent:
                            isConnected = True
                elif len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] == "n":
                    log("w","Bias ring connection not established. Measurement interrupted by user.")
                    self.__terminate__()
                    return False

        else:
            #Loop until runTimeError or connection established
            log("i","#################################################")
            log("i","Please establish connection with measured sensor.")
            log("i","#################################################")
            isConnected = False
            stableCurrent = []
            runTime = 0.
            runTimeError = connectTimeError
            while not isConnected and runTime < runTimeError:
                #Sleep
                time.sleep(self.sleep_time['meas']['short'])

                #Read out measurement data
                readout = ""
                self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
                self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
                time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?",vital=True))                                         #Read data from full buffer
                self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=True))                                     #Stop trigger
                self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

                #Process read out
                if len(readout) == 0:
                    log("w","Readout is empty!")
                    continue

                current_readings = []
                readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim",vital=True))
                for iread,reading in enumerate(readout_list):
                    if self.__par__(self.coms['meas'],"readoutIdentifier",vital=True) in reading:
                        curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier",vital=True),''))
                        current_readings.append(curr)
                        if self.args.verbosity > 0:
                            log("i","Current reading: "+str(curr))

                current = 0.0
                if len(current_readings) == nSamples:
                    current = sum(current_readings)/float(nSamples)
                else:
                    if len(current_readings) == 0:
                        log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                        continue
                    else:
                        current = sum(current_readings)/float(len(current_readings))

                #Check for current residuals
                if abs(current) > residualCurrent:
                    stableCurrent.append(current)
                else:
                    stableCurrent = []

                print(len(stableCurrent))
                if len(stableCurrent) > currentStability:
                    isConnected = True   

                #Raise run time
                runTime += self.sleep_time['meas']['short'] + (nSamples+1)*sampleTime

        #In case of connection, move table to ready to connect relative position before closing box
        if not isConnected:
            log("w","Failed to establish bias connection. Repeat sensing.")
            self.__terminate__()
            return False
        else:
            log("i","Bias connection established.")
        time.sleep(self.sleep_time['meas']['long'])
        if 'zstation' in self.coms:
            if not self.__write__(self.__cmd__(self.coms['zstation'],"SGOTOREL",arg=self.__par__(self.coms['zstation'],"detouchPosition"),vital=False)):
                self.__write__(self.__cmd__(self.coms['zstation'],"SGOTO",arg=self.__par__(self.coms['zstation'],"detouchPosition"),vital=True))
            motionIsDone = False
            runTime = 0.
            runTimeError = 15.
            while not motionIsDone and runTime < runTimeError:
                time.sleep(self.sleep_time['zstation']['long'])
                returnValue = str(self.__read__(self.__cmd__(self.coms['zstation'],"MOVE?",vital=True)))
                if len(returnValue) != 0:
                    motionIsDone = bool(int(returnValue))
                runTime += self.sleep_time['zstation']['long']
            self.__detectMalfunction__(motionIsDone,"zstation")
        else:
            log("w","If not removed manually, probe is now touching sensor.")

        return True   

    def box(self,mode="MEAS"):
        ###################################################################
        #Test environmental conditions and HV inhibitor after box is closed
        ###################################################################
        
        if mode == "DEBUG": #ignore
            log("h","Ignoring initial environmental conditions and TestBox check.")
            return True
         
        log("i","#################################################")
        log("i","Please close the TestBox.")
        log("i","Press \"n\" for terminate.")
        log("i","#################################################")
        if not self.args.extVSource:
            source_dev = 'meas'
        else:
            source_dev = 'source'
        userInput = ""
        isClosed = False
        isReady  = False
        while not isClosed or not isReady:
            userInput = log("tt","Press \"y\" to test environmental conditions.")
            if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["y","f"]:
                if userInput.lower().split(" ")[0] == "f":
                    isClosed = True
                    isReady  = True
                else: 
                    #check environmental conditions
                    if 'probe' not in self.args.addSocket:
                        log("e","Device providing environmental measurements is required.")
                        self.__terminate__()
                        return False
                    initTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                    initHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                    initLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
                    reqTemp = self.__par__(self.coms['probe'],"reqTemp")
                    reqHumi = self.__par__(self.coms['probe'],"reqHumi")
                    reqLumi = self.__par__(self.coms['probe'],"reqLumi")
                    isReady = True
                    if float(initTemp0) < float(reqTemp['min']) or float(initTemp0) > float(reqTemp['max']):
                        log("w","Measured temperature is: "+str(initTemp0)+".")
                        isReady = False
                    if float(initHumi) < float(reqHumi['min']) or float(initHumi) > float(reqHumi['max']):
                        log("w","Measured humidity is: "+str(initHumi)+".")
                        isReady = False
                    if float(initLumi) < float(reqLumi['min']) or float(initLumi) > float(reqLumi['max']):
                        log("w","Measured luminescence is: "+str(initLumi)+".")
                        isReady = False  
                    
                    #check if box and dry air ventil are closed
                    if not isReady:
                        log("w","Wrong environmental conditions!")
                    else:
                        log("i","Good environmental conditions confirmed.")
                        log("i","Please check if box and dry air ventil are closed.")
                        userSecondaryInput = log("tt","Press \"y\" to continue measurement: ")
                        if len(userSecondaryInput.lower().split(" ")) >=1 and userSecondaryInput.lower().split(" ")[0] == "y":
                            if self.__par__(self.coms[source_dev],"inhibitorCheckable",vital=True):
                                inh_status = self.__read__(self.__cmd__(self.coms[source_dev],"INHIBITOR?",vital=False))
                                if self.__cmd__(self.coms[source_dev],"INHIBITOR?",vital=False, check=str(inh_status)):
                                    isClosed = True
                                else:
                                    isClosed = False
                        elif len(userSecondaryInput.lower().split(" ")) >=1 and userSecondaryInput.lower().split(" ")[0] == "n":
                            log("w","Box is not closed. Measurement interrupted by user.")
                            self.__terminate__()
                            return False
                        if not isClosed:
                            log("w","Active inhibitor detected! Box is not closed.")
            elif len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] == "n":
                log("w","Environmental conditions not checked. Measurement interrupted by user.")
                self.__terminate__()
                return False

        log("i","Initial environmental conditions, HV inhibitor and TestBox checked.")    
        return True

    def single(self, mtype="IV", mpoint=0, sampleTime=0.50, nSamples=5):
        #######################################
        #Alias for all single type measurements
        #######################################

        if "IV" in mtype:
            return self.singleIV(biasPoint=mpoint, sampleTime=sampleTime, nSamples=nSamples)
        else:
            log("f","Unknown single measurement type.")
            sys.exit(0)
        
    def singleIV(self, biasPoint=0, sampleTime=0.50, nSamples=5):
        #############################################################
        #Global function called from mkMeasure defining basic single
        #bias measurement. Particular device commands are read from
        #corresponding device library class, however general routines 
        #are defined here.
        #############################################################

        #Define real high voltage source dev_type
        source_dev = ''
        source_dev_info = ""
        if not self.args.extVSource:
            source_dev = 'meas'
            source_dev_info = "main measurement device"
        else:
            source_dev = 'source'
            source_dev_info = "external source"

        #Set remote control
        self.__setRemote__()

        #Crosscheck interlock
        self.__checkInterlock__(safeMode=True)

        #Check settings
        if sampleTime < float(self.__par__(self.coms['meas'],"minSampleTime")):
            log("w","Minimum sample time per IV measurement exceeded. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        biasPoint = self.__checkBias__(self.coms[source_dev],biasPoint)  

        #Prepare device before each measurement
        self.__prepMeasurement__()

        #Adjusting voltage range
        _range = "1"
        if abs(float(biasPoint)) > 100.:
            if int(self.__par__(self.coms[source_dev],"defBias")) <= 1000:
                _range = str(int(self.__par__(self.coms[source_dev],"defBias")))
            else:
                _range = "1000"
            self.__write__(self.__cmd__(self.coms[source_dev],"SVRANGE",arg=_range))
        else:
            if int(self.__par__(self.coms[source_dev],"defBias")) <= 100:
                _range = str(int(self.__par__(self.coms[source_dev],"defBias")))
            else:
                _range = "100"
            self.__write__(self.__cmd__(self.coms[source_dev],"SVRANGE",arg=_range))

        #Set Bias
        self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg=str(biasPoint),vital=True))
        if self.args.verbosity > 0:
            setBias = self.__read__(self.__cmd__(self.coms[source_dev],"VOLT?"))
            if setBias:
                log("i","Voltage set: "+str(setBias)+".")

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr")) 
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))

        #Adjusting current range for measurement device
        self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg="OFF"))
        isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
        if not isAuto:
            log("i","IV measurement: Current AUTO range disabled.")
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(float(biasPoint)))))
            if self.args.verbosity > 0:
                setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                if setCurrRange:
                    log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
        else:
            log("i","IV measurement: Current AUTO range enabled.")

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?")) 
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])        

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=self.__par__(self.coms['meas'],"triggerType"),vital=True))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            log("e","Trigger is not supported by this measurement device (or commands are not specified).")

        #Turn on bias!!!
        log("i","Turning ON high-voltage source for "+source_dev_info+".")
        self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="ON",vital=True))

        #Accomodating for charging time
        log("i","Charging time...")
        time.sleep(self.__chargingTime__(0.,float(biasPoint)))
        log("i","Released.") 

        #Read out enviro data
        enviro = {}
        preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
        if 'probe' in self.args.addSocket:
            preTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
            preTemp1 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
            preTemp2 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
            preHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
            preLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
        enviro['temp1'] = preTemp0
        enviro['temp2'] = preTemp1
        enviro['temp3'] = preTemp2
        enviro['humi'] = preHumi
        enviro['lumi'] = preLumi
        log("i","Temperature CH0 before measurement: "+str(preTemp0))
        log("i","Temperature CH1 before measurement: "+str(preTemp1))
        log("i","Temperature CH2 before measurement: "+str(preTemp2))
        log("i","Humidity before measurement: "+str(preHumi))
        log("i","Lumi before measurement: "+str(preLumi))

        #Read out measurement data
        readout = ""
        self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
        self.__write__(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=True))                                  #Initialize trigger on source if needed
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
        time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
        self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
        readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?",vital=True))                                         #Read data from full buffer
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=True))                                     #Stop trigger
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

        #Return z-station to bottom position before finalizing measurement
        if 'zstation' in self.coms:
            self.__write__(self.__cmd__(self.coms['zstation'],"SGOTO",arg=self.__par__(self.coms['zstation'],"bottomPosition"),vital=True))
            motionIsDone = False
            runTime = 0.
            runTimeError = 21.
            while not motionIsDone and runTime < runTimeError:
                time.sleep(self.sleep_time['zstation']['long'])
                returnValue = str(self.__read__(self.__cmd__(self.coms['zstation'],"MOVE?",vital=True)))
                if len(returnValue) != 0:
                    motionIsDone = bool(int(returnValue))
                runTime += self.sleep_time['zstation']['long']
            self.__detectMalfunction__(motionIsDone,"zstation")
        else:
            log("h","Probe is still touching sensor!")

        #Process and return results
        if len(readout) == 0:
            log("w","Readout is empty!")
            self.__terminate__("EXIT")
        else:
            if self.args.verbosity > 1:
                log("i",str(readout))

        current_readings = []
        readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim",vital=True))
        for iread,reading in enumerate(readout_list):
            if self.__par__(self.coms['meas'],"readoutIdentifier",vital=True) in reading:
                curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier",vital=True),''))
                current_readings.append(curr)
                if self.args.verbosity > 0:
                    log("i","Current reading: "+str(curr))

        current = 0.0
        if len(current_readings) == nSamples:
            current = sum(current_readings)/float(nSamples)
        else:
            if len(current_readings) == 0:
                log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                self.__terminate__("EXIT")
            else:    
                current = sum(current_readings)/float(len(current_readings))

        #Run post routine if there is one specified

        #Finalize measurement
        self.__terminate__()

        #Return to mkMeasure
        return current, biasPoint, enviro

    def continuous(self, mtype="IV", mrange=[], sampleTime=0.50, nSamples=5): 
        ##########################################
        #Alias for all continuos type measurements
        ##########################################

        if "IV" in mtype:
            return self.continuousIV(biasRange=mrange, sampleTime=sampleTime, nSamples=nSamples)
        else:
            log("f","Unknown continuous measurement type.")
            sys.exit(0)

    def continuousIV(self, biasRange, sampleTime, nSamples):
        ###############################################################
        #Global function called from mkMeasure performs the multi-point
        #bias measurement. Particular device commands are read from the
        #corresponding device library class, however logic behind such
        #a measurement is defined here and is general to every device. 
        #VSource remains switched ON during the entire measurement.
        #############################################################
        #HACK FIXME
        sampleTime = sampleTime[0]
        nSamples   = nSamples[0]

        #Define real high voltage source dev_type
        source_dev = ''
        source_dev_info = ""
        if not self.args.extVSource:
            source_dev = 'meas'
            source_dev_info = "main measurement device"
        else:
            source_dev = 'source'
            source_dev_info = "external source"

        #Set remote control
        self.__setRemote__()

        #Crosscheck interlock
        self.__checkInterlock__(safeMode=True)

        #Check settings
        if sampleTime < float(self.__par__(self.coms['meas'],"minSampleTime")):
            log("w","Minimum sample time per IV measurement underflow. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        biasRange = self.__checkBiasRange__(self.coms[source_dev],biasRange)

        #Prepare device before each measurement
        self.__prepMeasurement__()

        #Adjusting voltage range
        _range = "1"
        maxBiasPoint = max(abs(float(min(biasRange))),abs(float(max(biasRange))))
        if maxBiasPoint > 100.:
            if int(self.__par__(self.coms[source_dev],"defBias")) <= 1000:
                _range = str(int(self.__par__(self.coms[source_dev],"defBias")))
            else:
                _range = "1000"
            self.__write__(self.__cmd__(self.coms[source_dev],"SVRANGE",arg=_range))
        else:
            if int(self.__par__(self.coms[source_dev],"defBias")) <= 100:
                _range = str(int(self.__par__(self.coms[source_dev],"defBias")))
            else:
                _range = "100"
            self.__write__(self.__cmd__(self.coms[source_dev],"SVRANGE",arg=_range))

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr"))
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))   

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?"))
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=self.__par__(self.coms['meas'],"triggerType"),vital=True))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            log("e","Trigger is not supported by this measurement device (or commands are not specified).")    

        #Turn on bias!!!
        log("i","Turning ON high-voltage source for "+source_dev_info+".")
        self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="ON",vital=True))    

        #Loop over bias values
        results = { 'data' : [], 'enviro' : [] }
        for ibias,biasPoint in enumerate(biasRange):
            #Set Bias
            self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg=str(biasPoint),vital=True))
            if self.args.verbosity > 0:
                setBias = self.__read__(self.__cmd__(self.coms[source_dev],"VOLT?"))
                if setBias:
                    log("i","Voltage set: "+str(setBias)+".")

            #Accomodating for charging time
            log("i","Charging time...")
            if ibias == 0:
                time.sleep(self.__chargingTime__(0.,float(biasPoint)))
            else:
                time.sleep(self.__chargingTime__(float(biasRange[ibias-1]),float(biasPoint)))
            log("i","Released.")

            #Adjusting current range for a measurement device
            self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg="OFF"))
            isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
            if not isAuto:
                log("i","IV measurement: Current AUTO range disabled.")
                self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(float(biasPoint)))))
                if self.args.verbosity > 0:
                    setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                    if setCurrRange:
                        log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
            else:
                log("i","IV measurement: Current AUTO range enabled.")  

            #Read out enviro data
            enviro = {}
            preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
            if 'probe' in self.args.addSocket:
                preTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                preTemp1 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                preTemp2 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                preHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                preLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
            enviro['temp1'] = preTemp0
            enviro['temp2'] = preTemp1
            enviro['temp3'] = preTemp2
            enviro['humi']  = preHumi
            enviro['lumi']  = preLumi
            if self.args.verbosity > 1:
                log("i","Temperature CH0 before measurement: "+str(preTemp0))
                log("i","Temperature CH1 before measurement: "+str(preTemp1))
                log("i","Temperature CH2 before measurement: "+str(preTemp2))
                log("i","Humidity before measurement: "+str(preHumi))
                log("i","Lumi before measurement: "+str(preLumi))    

            #Read out measurement data
            readout = ""
            self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
            self.__write__(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=False))                                 #Initialize trigger on source if needed
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
            time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
            self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
            readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?",vital=True))                                         #Read data from full buffer
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=True))                                     #Stop trigger
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state
        
            #Process and store results
            if len(readout) == 0:
                log("w","Readout is empty!")
                self.__terminate__()
            else:
                if self.args.verbosity > 1:
                    log("i",str(readout))

            current_readings = []
            readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim",vital=True))
            for iread,reading in enumerate(readout_list):
                if self.__par__(self.coms['meas'],"readoutIdentifier",vital=True) in reading:
                    curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier",vital=True),''))
                    current_readings.append(curr)
                    if self.args.verbosity > 0:
                        log("i","Current reading: "+str(curr))

            current = 0.0
            if len(current_readings) == nSamples:
                current = sum(current_readings)/float(nSamples)
            else:
                if len(current_readings) == 0:
                    log("w","BiasPoint: "+str(biasPoint)+": Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                    current = "N/A"
                    #self.__terminate__("EXIT")
                else:
                    current = sum(current_readings)/float(len(current_readings))
            results['data'].append((current,biasPoint))    
            results['enviro'].append(enviro)

        #Return z-station to bottom position before finalizing measurement
        if 'zstation' in self.coms:
            self.__write__(self.__cmd__(self.coms['zstation'],"SGOTO",arg=self.__par__(self.coms['zstation'],"bottomPosition"),vital=True))
            motionIsDone = False
            runTime = 0.
            runTimeError = 21.
            while not motionIsDone and runTime < runTimeError:
                time.sleep(self.sleep_time['zstation']['long'])
                returnValue = str(self.__read__(self.__cmd__(self.coms['zstation'],"MOVE?",vital=True)))
                if len(returnValue) != 0:
                    motionIsDone = bool(int(returnValue))
                runTime += self.sleep_time['zstation']['long']
            self.__detectMalfunction__(motionIsDone,"zstation")
        else:
            log("h","Probe is still touching sensor!")

        #Finalize measurement
        self.__terminate__()

        #Return to mkMeasure
        return results

    def multiIV(self, biasRange, sampleTime, nSamples):
        ################################################################
        #Global function called from mkMeasure performs the multi-point
        #bias measurement. Particular device commands are read from the
        #corresponding device library class, however logic behind such
        #a measurement is defined here and is general to every device. 
        #For each bias point the full initialization including switching
        #HV source is performed.
        ################################################################
        #HACK FIXME
        sampleTime=sampleTime[0]
        nSamples=nSamples[0]

        #Define real high voltage source dev_type
        source_dev = ''
        source_dev_info = ""
        if not self.args.extVSource:
            source_dev = 'meas'
            source_dev_info = "main measurement device"
        else:
            source_dev = 'source'
            source_dev_info = "external source"

        #Check settings
        if sampleTime < float(self.__par__(self.coms['meas'],"minSampleTime")):
            log("w","Minimum sample time per IV measurement underflow. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        biasRange = self.__checkBiasRange__(self.coms[source_dev],biasRange)

        #Loop over bias points
        results = { 'data' : [], 'enviro' : [] }    
        for biasPoint in biasRange:
            current, bias, enviro = self.singleIV(biasPoint, sampleTime, nSamples)
            results['data'].append((current,bias))
            results['enviro'].append({ 'temp1' : enviro[0],
                                       'temp2' : enviro[1],
                                       'temp3' : enviro[2],
                                       'humi'  : enviro[3],
                                       'lumi'  : enviro[4]
                                     })

        return results    
           
    def finalize(self):
        ################################
        # Terminate I2C servers
        ################################

        for dev_type in self.coms.keys():
            if "probe" in dev_type:
                self.__write__(self.__cmd__(self.coms[dev_type],"STOP",vital=True))
        log("i","All done.")        

    #----------------------------------------
    #Quick global functions for parallel use:
    #----------------------------------------

    def terminate(self):
        ############################################################
        #Terminate all devices + return z-station to bottom position
        ############################################################
        log("h","EMERGENCY TERMINATE SELECTED")

        #Return z-station to bottom position before finalizing measurement
        if 'zstation' in self.coms:
            self.__write__(self.__cmd__(self.coms['zstation'],"SGOTO",arg=self.__par__(self.coms['zstation'],"bottomPosition"),vital=True))
            motionIsDone = False
            runTime = 0.
            runTimeError = 21.
            while not motionIsDone and runTime < runTimeError:
                time.sleep(self.sleep_time['zstation']['long'])
                returnValue = str(self.__read__(self.__cmd__(self.coms['zstation'],"MOVE?",vital=True)))
                if len(returnValue) != 0:
                    motionIsDone = bool(int(returnValue))
                runTime += self.sleep_time['zstation']['long']
            self.__detectMalfunction__(motionIsDone,"zstation")
        else:
            log("h","Probe is still touching sensor!")

        self.__terminate__("EXIT")

    def abort(self):
        #############################################################
        #Abort all devices: TURN OFF HV and STOP MOVEMENT
        #############################################################
        log("h","EMERGENCY ABORT SELECTED")

        #Emergency stop of moving parts
        if 'zstation' in self.coms:
            self.__write__(self.__cmd__(self.coms['zstation'],"ABORT",vital=True)) 

        #Abort all
        self.__abort__("ALL")

        

