#!/usr/bin/env python

import os, sys
import time
import datetime as dt
import importlib
import ColorLogger
import DelayedKeyboardInterrupt as warden

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
        self.clogger = ColorLogger.ColorLogger("Device:          ",self.args.logname)

    def log(self,log_type="i",text=""):
        return self.clogger.log(log_type,text)

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
            self.log("e",com['id']+".py class not found! Please provide dedicated class for this device.")
            sys.exit(0)
        except AttributeError:
            self.log("e",com['id']+" class not specified. Name of the module must match the class name and start with capital letter.")
            sys.exit(0)
        except FileNotFoundError:
            self.log("e",com['id']+".py class tried to load non-existing binaries.")
            sys.exit(0)
        except Exception as e:
            self.log("f",com['id']+".py class raised an unknown exception! Check for syntax errors.")
            self.log("f",str(type(e)))
            sys.exit(0)

        if _devs[com['id']].test() == com['id']:
            self.log("i","Loading command library and sub-routines for "+com['id']+".")
        else:
            self.log("e","This class do not match "+com['id']+" device!")
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
                self.log("e","Socket connection refused for DEV="+com['id']+".")
                self.log("e","Server is switched OFF.")
                sys.exit(0)
            if com['model'] not in real_id and com['model'][1:] not in real_id: 
                if self.args.selectPort:
                    self.log("w","Outdated or not matching class for DEV="+com['id']+" was provided.")
                    self.log("w","MODEL found    = "+str(real_id)) 
                    self.log("w","MODEL required = "+com['model'])
                    self.log("e","Please use --selectPort again to select ports manually in case your class is not outdated.")
                    sys.exit(0)
                else:
                    self.log("w","Device ID="+com['id']+" not matched. Retry...")
                    real_id = "FAILED"
            else:
                self.log("i","Response received from DEV_NAME="+str(real_id))
        else:
            if self.args.selectPort:
                self.log("w","Please turn on device ID="+com['id']+".")
                sys.exit(0)
            else:
                self.log("w","Device ID="+com['id']+" not matched. Retry...")
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
            self.log("i",cmd['id']+" : WRITECMD : \""+str(cmd['cmd'])+"\".")

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
            self.log("i",cmd['id']+" : READCMD : \""+str(cmd['cmd'])+"\".")

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
            if cmd_type[-1] == "?": _cmd_type = _cmd_type[:-1]
        elif len(str(arg))!=0:
            cat = "set"
            _cmd_type = cmd_type
            if cmd_type[-1] == "?": _cmd_type = _cmd_type[:-1]
        else:
            cat = "do"
            _cmd_type = cmd_type

        #Vital commands must be defined in corresponding class
        (raw_cmd,isOK,isNOT) = self.devs[com['id']].cmd(_cmd_type, arg = arg, cat = cat)
        if (vital and len(raw_cmd)==0) or (vital and raw_cmd=="UNKNOWN"):
            self.log("e","Command: "+_cmd_type+" not defined in "+com['id']+" class. RAW_CMD = "+raw_cmd)
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
            self.log("e","Parameter: "+str(par_type)+" not defined in "+com['id']+" class.")
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
                        self.log("i","Interlock exists for "+dev_info+".")
                    else:
                        self.log("h","Interlock cable for "+dev_info+" was found but it is not connected or fixture is open!!!")
                        if safeMode: 
                            self.__terminate__("EXIT")
                else:
                    self.log("h","Interlock for "+dev_info+" does not exist!!!")
                    if safeMode: 
                        self.__terminate__("EXIT")
            else:
                self.log("i","Interlock for "+dev_info+" is not defined or implicitely checked.")

    def __checkBias__(self,com,bias):
        #######################################################
        #Check if voltage to be set is inside of allowed range.
        #Return corrected value.
        #######################################################

        if float(bias) > self.maxBias:
            self.log("w","Selected bias overflow! Setting maximum bias: "+str(self.maxBias)+"V.")
            return str(self.maxBias)
        elif float(bias) < self.minBias:
            self.log("w","Selected bias underflow! Setting minimum bias: "+str(self.minBias)+"V.")
            return str(self.minBias)
        else:
            if self.__par__(com,"decimalVolt",vital=True):
                if "." in str(bias) and len(str(bias).split(".")[-1]) > 2:
                    self.log("i","Maximum 2 decimal places are allowed. Pre-Setting bias to: "+"{:.2f}".format(bias)+"V.")
                else:
                    self.log("i","Pre-Setting bias to: "+"{:.2f}".format(bias)+"V.")
                return "{:.2f}".format(bias)
            else:
                self.log("i","Decimals not allowed. Pre-Setting bias to: "+str(int(bias))+"V.")
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
        if not self.args.debug:
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
                    if not self.args.debug:
                        continue
                    else:
                        _biasRange.append(correct_bias)
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
 
        #convert bias 
        if int(bias_point) < 0: bias_point *= -1

        #get possible current range based on expected mean resistance
        res = self.args.expOhm[0] #def=1e-9
        curr_range = 2e-3
        min_range = 2e-1 #2e0
        if int(bias_point) in range(200,1000):
            curr_range = 1000.*min_range/res #2muA
        elif int(bias_point) in range(20,200):   
            curr_range = 100.*min_range/res #200nA
        elif int(bias_point) in range(2,20): 
            curr_range = 10.*min_range/res #20nA   
        elif int(bias_point) in range(0,2):
            curr_range = min_range/res #2nA

        return curr_range

    def __getCurrentLimit__(self, irange, proposed_limit):
        #######################################################
        #Validate value to be set as current limit based on
        #momentary current range.
        #Expects that auto-range mode is disabled.
        #######################################################

        if proposed_limit > irange:
            return irange
        elif proposed_limit < irange/10.:
            return 2*irange/10.
        else:
            return proposed_limit

    def __chargingTime__(self,initBias,targetBias):
        #######################################################
        #Calculate charging time to be used in sleep function. 
        #######################################################
 
        delta = abs(targetBias-initBias)
        offset = 1.0
        biasStep = 10
        timeStep = 0.25
        isRes = delta%biasStep > 0
        nSteps = 0
        if isRes:
            nSteps = int((delta//biasStep)+1.0)
        else:
            nSteps = int(delta//biasStep)
        return (nSteps*timeStep)+offset     

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
                self.log("i","Real velocity for "+str(dev_type_info).capitalize()+" is "+str(realVelo)+".")
            if realVelo and abs(float(realVelo)) > 0.:
                self.log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info).capitalize())
                self.__abort__(dev_type)
                self.__terminate__("EXIT")
            else:
                if self.args.verbosity > 1:
                    self.log("i","All movement stopped for "+str(dev_type_info).capitalize()+".")
        else:
            return False

    def __initDevice__(self,coms,EMG):
        #############################################
        #Run sequence of commands initializing device
        #############################################

        self.log("i","Initializing starting sequence.")

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

        #Bias and Current boundaries for the source device
        if self.args.extVSource and not self.args.isEnviroOnly and not self.args.isStandByZOnly:
            self.minBias     = self.__par__(coms['source'],"minBias")
            self.maxBias     = self.__par__(coms['source'],"maxBias")
            self.maxCurrent  = self.__par__(coms['source'],"maxCurrent")
            self.userCurrent = self.__par__(coms['meas'],"userCurrent")  #defined for meas only
        elif not self.args.isEnviroOnly and not self.args.isStandByZOnly:
            self.minBias     = self.__par__(coms['meas'],"minBias")
            self.maxBias     = self.__par__(coms['meas'],"maxBias")    
            self.maxCurrent  = self.__par__(coms['meas'],"maxCurrent") 
            self.userCurrent = self.__par__(coms['meas'],"userCurrent") 
        
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
                    self.log("i",dev_type_info.capitalize()+" control velocity set to "+str(setVelo))

                #turn ON motor    
                self.__write__(self.__cmd__(coms[dev_type],"MOTOR",arg="ON",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(coms[dev_type],"MOTOR?",vital=True))))
                if not isMotorOn:
                    self.log("e",str(dev_type_info).capitalize()+" motor is turned OFF while expected working!")
                    self.__terminate__("EXIT")
                else:
                    if self.args.verbosity > 0:
                        self.log("i",str(dev_type_info).capitalize()+" motor is ON.")    
                
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
        if self.stations == 0 and not self.args.isEnviroOnly:
            self.log("w","No station device is used. User is expected to ensure bias connection manually.")

    def __prepMeasurementExternal__(self):
        ################################################################
        #Prepare measurement when external measurement device is used.
        ################################################################
 
        #Run device specific pre-routine if specified by device-specific class (for all)
        for dev_type in self.coms:
            status, message = self.devs[self.coms[dev_type]['id']].pre(self.coms[dev_type]['com'])
            self.log(status, message)
            if status in ["e","f"]:
                self.__terminate__("EXIT")

        #TODO: add options for using extVSource as well

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
            self.log("w","If not done manually, probe is not touching sensor.")
        
    def __prepMeasurement__(self):
        ################################################################
        #Run sequence of commands in order to prepare measurement device 
        #(and external source) for particular measurement. In case of
        #very particular sub-routines required by device, these are
        #invoked from here. Called only for the first measurement of 
        #IV type.
        ################################################################

        #Inform about power-on settings
        powerOnSetup = ""
        if self.args.extVSource:
            powerOnSetup = self.__read__(self.__cmd__(self.coms['source'],"POSETUP?"))
        else:
            powerOnSetup = self.__read__(self.__cmd__(self.coms['meas'],"POSETUP?"))
        if not powerOnSetup or len(powerOnSetup) == 0: powerOnSetup = "UNKNOWN"    
        self.log("i","PowerOn setup: "+str(powerOnSetup))    

        #Clear buffer of measurement device and set buffer memory size
        self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True)) 

        #Zero check ON for measurement device + sleep time until done
        self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="ON"))
        time.sleep(self.sleep_time['meas']['medium'])

        #Run device specific pre-routine if specified by device-specific class (for all)
        for dev_type in self.coms:
            status, message = self.devs[self.coms[dev_type]['id']].pre(self.coms[dev_type]['com'])
            self.log(status, message)
            if status in ["e","f"]:
                self.__terminate__("EXIT")

        #Setting source voltage limits in addition to crosschecked voltage bias
        if self.args.extVSource:
            self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['source'],"vlimitCheckable",vital=True):
                self.__write__(self.__cmd__(self.coms['source'],"SVOLTLIM",arg=str(max(abs(self.minBias),abs(self.maxBias))),vital=True)) #Set absolute voltage limit
            if self.args.verbosity > 0:
                limVSet = self.__read__(self.__cmd__(self.coms['source'],"VOLTLIM?"))
                limVDef = self.__par__(self.coms['source'],"defBias")
                if limVSet:
                    self.log("i","External Source Voltage limit was specified (manufacturer) to "+str(limVDef)+".")    
                    self.log("i","External Source Voltage limit was set (user) to "+str(limVSet)+".")
        else:
            self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['meas'],"vlimitCheckable",vital=True):
                self.__write__(self.__cmd__(self.coms['meas'],"SVOLTLIM",arg=str(max(abs(self.minBias),abs(self.maxBias))),vital=True)) #Set absolute voltage limit
            if self.args.verbosity > 0:
                limVSet = self.__read__(self.__cmd__(self.coms['meas'],"VOLTLIM?"))
                limVDef = self.__par__(self.coms['meas'],"defBias")
                if limVSet:
                    self.log("i","Measurement device Source Voltage limit was specified (manufacturer) to "+str(limVDef)+".")
                    self.log("i","Measurement device Source Voltage limit was set (user) to "+str(limVSet)+".")
        
        #Setting source current limits 
        if self.args.extVSource:
            self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['source'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
        else:
            self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['meas'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
        
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
            self.log("w","If not done manually, probe is not touching sensor.")

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
            self.log("i","Abort requested for "+dev_type+".")
        else:
            self.log("i","Abort requested for ALL followed by EXIT.")

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
                self.__write__(self.__cmd__(self.coms[dev_type],"RESET",vital=_vital)) 
            elif "station" in dev_type: 
                #MOVE STATION IN SAFE PROXIMITY (MATERIAL DMG HAZARD)
                dev_type_info = dev_type
                self.__write__(self.__cmd__(self.coms[dev_type],"MOTOR",arg="ON",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))
                if not isMotorOn:
                    self.log("e",str(dev_type_info).capitalize()+" motor is turned OFF while expected working!")
                    self.__terminate__("EXIT")
                else:
                    if self.args.verbosity > 0:
                        self.log("i",str(dev_type_info).capitalize()+" motor is ON.")

                #Return z-station to bottom position before finalizing measurement
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

                #STOP ALL MOTION 
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
            self.log("i","Terminate requested for "+dev_type+".")
        else:
            self.log("i","Terminate requested for ALL followed by EXIT.")

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
            self.log("i","Finalizing measurement.")

            #FIRST SEQUENCE
            _vital = False
            if (dev_type == "meas" and not self.args.extVSource) or (dev_type == "source" and self.args.extVSource):
                _vital = True
            if dev_type in ["meas","source"]:    
                self.__write__(self.__cmd__(self.coms[dev_type],"SVOLT",arg="0",vital=_vital))
                source_stat = self.__read__(self.__cmd__(self.coms[dev_type],"SOURCE?",vital=_vital))
                if not self.__cmd__(self.coms[dev_type],"SOURCE?",vital=_vital,check=source_stat):
                    self.log("i","Turning OFF high-voltage source for "+dev_type_info+".")
                    self.__write__(self.__cmd__(self.coms[dev_type],"SOURCE",arg="OFF",vital=_vital))
                setVolt = self.__read__(self.__cmd__(self.coms[dev_type],"VOLT?",vital=_vital))
                if self.args.verbosity > 1:
                    self.log("i","Voltage re-set to zero for "+dev_type_info+": "+str(setVolt)) 
                self.__write__(self.__cmd__(self.coms[dev_type],"RESET",vital=True))   
            elif "station" in dev_type and dev_type in self.sleep_time.keys():    
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
                    self.log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info))
                    self.__abort__(dev_type)
                else:
                    #cross check for real velocity
                    realVelo = self.__read__(self.__cmd__(self.coms[dev_type],"VELOCITY?",vital=True))
                    if realVelo and float(realVelo) > 0.:
                        self.log("h","EMERGENCY ABORT LAUNCHED for "+str(dev_type_info))
                        self.__abort__(dev_type)
                    else:
                        if self.args.verbosity > 1:
                            self.log("i","All movement stopped for "+str(dev_type_info)+".")
         
            #SECOND SEQUENCE        
            self.__write__(self.__cmd__(self.coms[dev_type],"ZCHECK",arg="ON"))
            self.__write__(self.__cmd__(self.coms[dev_type],"ZCOR",arg="OFF"))
            if "station" in dev_type and dev_type in self.sleep_time.keys():
                #turn OFF motor        
                self.__write__(self.__cmd__(self.coms[dev_type],"MOTOR",arg="OFF",vital=True))
                time.sleep(self.sleep_time[dev_type]['medium'])
                isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms[dev_type],"MOTOR?",vital=True))))
                if isMotorOn:
                    self.log("h",str(dev_type_info).capitalize()+" motor is turned ON while expected OFF!")
                    self.__abort__(dev_type)
                else:
                    if self.args.verbosity > 1:
                        self.log("i","Motor for "+str(dev_type_info)+" was turned OFF.")
            #set local
            self.__setLocal__(dev_type)

        elif dev_type == "EXIT":
            self.__terminate__("ALL")
            sys.exit(0)

    def load_socket(self,SOCKETS,EMG):
        ########################################################
        #Global function called from mkMeasure to get response
        #from all socket devices only.
        ########################################################
        try:
            for dev_type in self.args.addSocket:
                DEV_PROBE_NAME,self.coms[dev_type] = self.__getResponse__(SOCKETS[dev_type])  
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during socket selection detected.")
            sys.exit(0)

        #Initialize sequence
        try:
            self.__initDevice__(self.coms,EMG)
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during device initialization detected.")
            with warden.DelayedKeyboardInterrupt(force=False, logfile=self.args.logname):
                self.__terminate__("EXIT")
            
        #Return success if all is OK
        return { 'success' : 1 }

    def load_serial(self,COMS,EMG):
        ###########################################################
        #Global function intended to be used only without devices 
        #of type meas or source. E.g. probe
        ###########################################################   
        try:
            OTHER_DEV_NAMES = {}
            for dev_type in self.args.addPort:
                OTHER_DEV_NAMES[dev_type],self.coms[dev_type] = self.__getResponse__(COMS[dev_type])

            loadStatus = {}
            for dev_type in self.args.addPort:
                if "FAILED" in OTHER_DEV_NAMES[dev_type]:
                    loadStatus[dev_type] = (self.coms[dev_type]['port'],0)
                else:
                    loadStatus[dev_type] = (self.coms[dev_type]['port'],1)
            allOK = True
            for key in loadStatus.keys():
                port,valid = loadStatus[key]
                if valid == 0 or valid == 2:
                    allOK = False
            if not allOK: return loadStatus
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during port selection detected.")
            sys.exit(0)
        except Exception as e:
            self.log("f",str(e))
            sys.exit(0)

        #Initialize sequence
        try:
            self.__initDevice__(self.coms,EMG)
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during device initialization detected.")
            with warden.DelayedKeyboardInterrupt(force=False, logfile=self.args.logname):
                self.__terminate__("EXIT")

        #Return success if all is OK
        return { 'success' : 1 }

    def load(self,COMS,SOCKETS,EMG):
        ########################################################
        #Global function called from mkMeasure to get response
        #from all devices in use and loading their sub-routines
        #from library.
        #COMS    = serial connections
        #SOCKETS = socket connections 
        ########################################################
        try:
            if not self.args.isStandByZOnly:
                DEV_MEAS_NAME,self.coms['meas'] = self.__getResponse__(COMS['meas']) 
            if self.args.extVSource:
                DEV_SOURCE_NAME,self.coms['source'] = self.__getResponse__(COMS['source'])
            OTHER_DEV_NAMES = {}
            for dev_type in self.args.addPort:
                OTHER_DEV_NAMES[dev_type],self.coms[dev_type] = self.__getResponse__(COMS[dev_type])
            OTHER_SOCKET_NAMES = {}
            for dev_type in self.args.addSocket:    
                OTHER_SOCKET_NAMES[dev_type],self.coms[dev_type] = self.__getResponse__(SOCKETS[dev_type])
      
            loadStatus = {}
            if not self.args.isStandByZOnly:
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
            for dev_type in self.args.addSocket:
                if "FAILED" in OTHER_SOCKET_NAMES[dev_type]:
                    loadStatus[dev_type] = (self.coms[dev_type]['com']['port'],2) #Failed socket connection
                else:
                    loadStatus[dev_type] = (self.coms[dev_type]['com']['port'],3) #Good socket connection

            allOK = True        
            for key in loadStatus.keys():
                port,valid = loadStatus[key]
                if valid == 0 or valid == 2:
                    allOK = False 
            if not allOK: return loadStatus
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during port selection detected.")
            sys.exit(0)

        #-----------------------------------------------------------------------------------------------
        #From now on one can write/read commands in Device under 
        #corresponding COM using general commands: 
        #    self.__read__(self.__cmd__(COM,"command",arg="arguments",vital="if command is neccessary"))
        #Evaluating more complicated sub-routines than read/write 
        #is also possible:
        #    self.devs[COM['id']].subroutine()
        #-----------------------------------------------------------------------------------------------

        #Initialize sequence
        try:
            self.__initDevice__(self.coms,EMG)
        except KeyboardInterrupt:
            self.log("w","Keyboard interruption during device initialization detected.")
            with warden.DelayedKeyboardInterrupt(force=False, logfile=self.args.logname): 
                self.__terminate__("EXIT")

        #Return success if all is OK
        return { 'success' : 1 }

    def status(self):
        #############################################################
        #Return intrinsic status of all connected devices
        #############################################################

        status = {}
        for dev_type in self.coms.keys():
            _status = self.__read__(self.__cmd__(self.coms[dev_type],"STATUS?",vital=False))
            
            #TODO: some manipulation with returned value? 

            status[dev_type] = _status
  
        return status

    def senseExternal(self, connectTimeError=0):
        #############################################################
        #Global function called from mkMeasure.
        #Wait until connection is established and 
        #checked by external device.
        #No measurement device needed.
        #############################################################
        
        isConnected = False
        if connectTimeError >= 0:
            #Wait until user confirms connection
            self.log("i","##################################################")
            self.log("i","#Please establish connection with measured sensor.")
            self.log("i","#To cancel manual sensing mode press \"n\".")
            self.log("i","##################################################")

            userInput = ""
            connectTime = 0 
            testTimeError = True
            while not isConnected and testTimeError:
                if connectTimeError == 0: testTimeError = True
                elif connectTimeError > 0: testTimeError = bool(connectTime < connectTimeError) 
                userInput = self.log("tt","Press \"y\" to CONFIRM connection was established: ")
                try:
                    userInput.lower()
                except AttributeError:
                    self.log("w","Common! I said press \"n\" to cancel...")
                    userInput = ""
                if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["y","f"]:
                    isConnected = True
                elif len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] == "n":
                    self.log("w","Bias connection not established. Measurement interrupted by user.")
                    self.__terminate__()
                    return False

                time.sleep(1)
                connectTime += 1

        #In case of connection, move table to ready to connect relative position before closing box
        if not isConnected:
            self.log("w","Failed to establish bias connection. Repeat sensing.")
            self.__terminate__()
            return False
        else:
            self.log("i","Bias connection established.")
        time.sleep(2)
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
            self.log("w","If not removed manually, probe is now touching sensor.")

        return True



    def sense(self,connectTimeError=0, fullManual=False):
        #############################################################
        #Global function called from mkMeasure providing real time
        #sensing for a presence of current. When connection is found,
        #table is moved to safe position.
        #############################################################
        #Sensitivity settings
        nSamples = 10           #samples per measurement
        sampleTime = 0.25       #time per sample
        residualCurrent = 2e-13 #minimum current
        currentStability = 2    #meaning at least 3 positive measurements in semi-automatic mode

        #Set remote control
        self.__setRemote__("meas")

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr"))
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            self.log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))

        #Adjusting current range for measurement device
        _autoRange = "OFF"
        if self.args.autoRange:
            self.log("i","Sensing mode does not allow current auto range.")
        self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg=_autoRange))
        isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
        if not isAuto:
            self.log("i","IV measurement: Current AUTO range disabled.")
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(0.))))
            if self.args.verbosity > 0:
                setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                if setCurrRange:
                    self.log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
        else:
            self.log("i","IV measurement: Current AUTO range enabled.")
        
        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                self.log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?"))
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                self.log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        triggerType = self.__par__(self.coms['meas'],"triggerType") 
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=triggerType,vital=True))
            if "Empty" in triggerType: #Trigger is fully programable
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))    
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCLEAR",arg="1"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERMDIG",arg="2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCOUNT",arg="3, "+str(nSamples)+", 2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERLIMITBRANCH",arg="4, ABOV, 0, "+str(self.userCurrent)+", 6"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERALWAYSBRANCH",arg="5, 7"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERSOURCE",arg="6, 0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="7, 0.05"))
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True))
            else: #minimum settings
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            self.log("e","Trigger is not supported by this measurement device (or commands are not specified).")
       
        if connectTimeError == 0:
            #Wait until user confirms connection
            self.log("i","##################################################")
            self.log("i","#Please establish connection with measured sensor.")
            self.log("i","#To cancel manual sensing mode press \"n\".")
            self.log("i","##################################################")

            userInput = ""
            isConnected = False
            while not isConnected:
                userInput = self.log("tt","Press \"y\" to test connection: ")
                try:
                    userInput.lower()
                except AttributeError:
                    self.log("w","Common! I said press \"n\" to cancel...")
                    userInput = ""
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
                        _vitalTriggerOFF = False
                        if "Empty" not in triggerType:
                            time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                            self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                            _vitalTriggerOFF = True
                        readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?", arg="1, "+str(nSamples)+", \"defbuffer1\", READ", vital=True)) #Read data from full buffer
                        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=_vitalTriggerOFF))                         #Stop trigger
                        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

                        #Process read out
                        if len(readout) == 0:
                            self.log("w","Readout is empty!")
                            continue

                        current_readings = []
                        readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim",vital=True))
                        for iread,reading in enumerate(readout_list):
                            if self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))!=0 :
                                curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier"),''))
                                current_readings.append(curr)
                                if self.args.verbosity > 0:
                                    self.log("i","Current reading: "+str(curr))
                            elif self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))==0: 
                                current_readings.append(float(reading))
                                if self.args.verbosity > 0:
                                    self.log("i","Current reading: "+str(reading))

                        current = 0.0
                        if len(current_readings) == nSamples:
                            current = sum(current_readings)/float(nSamples)
                        else:
                            if len(current_readings) == 0:
                                self.log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                                continue
                            else:
                                print(str(current_readings))
                                current = sum(current_readings)/float(len(current_readings))
                        
                        #Check for current residuals
                        if abs(current) > residualCurrent:
                            isConnected = True
                elif len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] == "n":
                    self.log("w","Bias connection not established. Measurement interrupted by user.")
                    self.__terminate__()
                    return False

        else:
            #Loop until runTimeError or connection established
            self.log("i","#################################################")
            self.log("i","Please establish connection with measured sensor.")
            self.log("i","#################################################")
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
                _vitalTriggerOFF = False
                if "Empty" not in triggerType:
                    time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                    self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                    _vitalTriggerOFF = True
                readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?", arg="1, "+str(nSamples)+", \"defbuffer1\", READ", vital=True))  #Read data from full buffer
                self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=_vitalTriggerOFF))                         #Stop trigger
                self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

                #Process read out
                if len(readout) == 0:
                    self.log("w","Readout is empty!")
                    continue

                current_readings = []
                readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim"))
                for iread,reading in enumerate(readout_list):
                    if self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier")) != 0:
                        curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier",vital=True),''))
                        current_readings.append(curr)
                        if self.args.verbosity > 0:
                            self.log("i","Current reading: "+str(curr))
                    elif self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))==0:
                        current_readings.append(float(reading))
                        if self.args.verbosity > 0:
                            self.log("i","Current reading: "+str(reading))

                current = 0.0
                if len(current_readings) == nSamples:
                    current = sum(current_readings)/float(nSamples)
                else:
                    if len(current_readings) == 0:
                        self.log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
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
            self.log("w","Failed to establish bias connection. Repeat sensing.")
            self.__terminate__()
            return False
        else:
            self.log("i","Bias connection established.")
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
            self.log("w","If not removed manually, probe is now touching sensor.")

        return True   

    def box(self,mode="MEAS"):
        ###################################################################
        #Test environmental conditions and HV inhibitor after box is closed
        ###################################################################
        
        if mode == "DEBUG": #ignore
            self.log("h","Ignoring initial environmental conditions and TestBox check.")
            return True
         
        self.log("i","#################################################")
        self.log("i","Please close the TestBox.")
        self.log("i","Press \"n\" for terminate.")
        self.log("i","#################################################")
        if not self.args.extVSource:
            source_dev = 'meas'
        else:
            source_dev = 'source'
        userInput = ""
        isClosed = False
        isReady  = False
        while not isClosed or not isReady:
            userInput = self.log("tt","Press \"y\" to test environmental conditions.")
            if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["y","f"]:
                if userInput.lower().split(" ")[0] == "f":
                    isClosed = True
                    isReady  = True
                else: 
                    #check environmental conditions
                    if 'probe' not in self.args.addSocket and 'probe' not in self.args.addPort:
                        self.log("e","Device providing environmental measurements is required.")

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
                            self.log("h","Probe is still touching sensor!")   

                        #Finalize
                        self.__terminate__()
                        return False

                    #dry run needed
                    self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                    self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                    self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                    #real run
                    initTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                    initHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                    initLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
                    reqTemp = self.__par__(self.coms['probe'],"reqTemp")
                    reqHumi = self.__par__(self.coms['probe'],"reqHumi")
                    reqLumi = self.__par__(self.coms['probe'],"reqLumi")
                    isReady = True
                    if float(initTemp0) < float(reqTemp['min']) or float(initTemp0) > float(reqTemp['max']):
                        self.log("w","Measured temperature is: "+str(initTemp0)+".")
                        isReady = False
                    if float(initHumi) < float(reqHumi['min']) or float(initHumi) > float(reqHumi['max']):
                        self.log("w","Measured humidity is: "+str(initHumi)+".")
                        isReady = False
                    if float(initLumi) < float(reqLumi['min']) or float(initLumi) > float(reqLumi['max']):
                        self.log("w","Measured luminescence is: "+str(initLumi)+".")
                        isReady = False  
                    
                    #check if box and dry air ventil are closed
                    if not isReady:
                        self.log("w","Wrong environmental conditions!")
                    else:
                        self.log("i","Good environmental conditions confirmed.")
                        self.log("i","Please check if box and dry air ventil are closed.")
                        userSecondaryInput = self.log("tt","Press \"y\" to continue measurement: ")
                        if len(userSecondaryInput.lower().split(" ")) >=1 and userSecondaryInput.lower().split(" ")[0] == "y":
                            if self.__par__(self.coms[source_dev],"inhibitorCheckable",vital=True):
                                inh_status = self.__read__(self.__cmd__(self.coms[source_dev],"INHIBITOR?",vital=False))
                                if self.__cmd__(self.coms[source_dev],"INHIBITOR?",vital=False, check=str(inh_status)):
                                    isClosed = True
                                else:
                                    isClosed = False
                        elif len(userSecondaryInput.lower().split(" ")) >=1 and userSecondaryInput.lower().split(" ")[0] == "n":
                            self.log("w","Box is not closed. Measurement interrupted by user.")
                            self.__terminate__()
                            return False
                        if not isClosed:
                            self.log("w","Active inhibitor detected! Box is not closed.")
            elif len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] == "n":
                self.log("w","Environmental conditions not checked. Measurement interrupted by user.")
                self.__terminate__()
                return False

        self.log("i","Initial environmental conditions, HV inhibitor and TestBox checked.")    
        return True

    def singleENV(self, mtype="all", isLast=True, isFirst=False):
        ################################
        #Single enviro measurement
        ################################

        #initialize pre-requisities if needed 
        dev_type = 'probe'
        if isFirst and (dev_type in self.args.addSocket or dev_type in self.args.addPort):
            status, message = self.devs[self.coms[dev_type]['id']].pre(self.coms[dev_type]['com'])
            self.log(status, message)
            if status in ["e","f"]:
                self.__terminate__("EXIT") 

        #Read out enviro data
        enviro = {}
        preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
        now = dt.datetime.now()
        enviro['hour'] = str(now.hour)
        enviro['minute'] = str(now.minute)
        enviro['second'] = str(now.second) 
        if dev_type in self.args.addSocket or dev_type in self.args.addPort:
            if mtype == "all":
                preTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                preTemp1 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                preTemp2 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                preHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                preLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
            elif mtype == "temp":
                preTemp0 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                preTemp1 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                preTemp2 = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
            elif mtype == "humi":
                preHumi = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
            elif mtype == "lumi":
                preLumi = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

        enviro['temp1'] = preTemp0
        enviro['temp2'] = preTemp1
        enviro['temp3'] = preTemp2
        enviro['humi'] = preHumi
        enviro['lumi'] = preLumi
        if mtype == "all":
            self.log("i","Temperature CH0:   "+str(preTemp0))
            self.log("i","Temperature CH1:   "+str(preTemp1))
            self.log("i","Temperature CH2:   "+str(preTemp2))
            self.log("i","Relative humidity: "+str(preHumi)+"%")
            self.log("i","Lux:               "+str(preLumi))  
        elif  mtype == "temp":
            self.log("i","Temperature CH0:   "+str(preTemp0))
            self.log("i","Temperature CH1:   "+str(preTemp1))
            self.log("i","Temperature CH2:   "+str(preTemp2))
        elif mtype == "humi":
            self.log("i","Relative humidity: "+str(preHumi)+"%")
        elif mtype == "lumi":
            self.log("i","Lux:               "+str(preLumi))  

        #Finalize measurement
        if isLast:
            try:
                self.__terminate__()
            except OSError:
                self.log("h","Current limit exceeded! HV source does not response! Results stored in emergency mode.")
                self.log("h","Manual abort required.")

        #Return readings
        return enviro

    def contENV(self, mtype="all", timeStep = 5, nSteps = 10, isLast=True, isFirst=False):
        ################################
        #Continuous enviro measurement
        ################################

        #initialize pre-requisities if needed
        dev_type = 'probe'
        if isFirst and (dev_type in self.args.addSocket or dev_type in self.args.addPort):
            status, message = self.devs[self.coms[dev_type]['id']].pre(self.coms[dev_type]['com'])
            self.log(status, message)
            if status in ["e","f"]:
                self.__terminate__("EXIT")

        #clear buffer
        self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
        self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
        self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
        self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
        self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

        #Read out enviro data
        enviro = []
        try:
            if dev_type in self.args.addSocket or dev_type in self.args.addPort:
                if nSteps >= 0:
                    for step in range(0,nSteps):
                        _enviro = { 'hour' : 0, 'minute' : 0, 'second' : 0,
                                    'temp1' : 0, 'temp2' : 0, 'temp3' : 0,
                                    'humi' : 0, 'lumi' : 0 } 
                        now = dt.datetime.now()
                        _enviro['hour'] = str(now.hour)
                        _enviro['minute'] = str(now.minute)
                        _enviro['second'] = str(now.second)
                        if mtype == "all":
                            _enviro['temp1'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                            _enviro['temp2'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                            _enviro['temp3'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                            _enviro['humi'] = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                            _enviro['lumi'] = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True)) 

                            self.log("i","Temperature CH0:   "+str(_enviro['temp1']))
                            self.log("i","Temperature CH1:   "+str(_enviro['temp2']))
                            self.log("i","Temperature CH2:   "+str(_enviro['temp3']))
                            self.log("i","Relative humidity: "+str(_enviro['humi'])+"%")
                            self.log("i","Lux:               "+str(_enviro['lumi']))
                        elif mtype == "temp":
                            _enviro['temp1'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                            _enviro['temp2'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                            _enviro['temp3'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                            _enviro['humi'] = "N/A"
                            _enviro['lumi'] = "N/A"                         

                            self.log("i","Temperature CH0:   "+str(_enviro['temp1']))
                            self.log("i","Temperature CH1:   "+str(_enviro['temp2']))
                            self.log("i","Temperature CH2:   "+str(_enviro['temp3']))
                        elif mtype == "humi":
                            _enviro['temp1'] = "N/A"
                            _enviro['temp2'] = "N/A"
                            _enviro['temp3'] = "N/A"
                            _enviro['humi'] = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                            _enviro['lumi'] = "N/A"

                            self.log("i","Relative humidity: "+str(_enviro['humi'])+"%")
                        elif mtype == "lumi":
                            _enviro['temp1'] = "N/A"
                            _enviro['temp2'] = "N/A"
                            _enviro['temp3'] = "N/A"
                            _enviro['humi'] = "N/A"
                            _enviro['lumi'] = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))
                              
                            self.log("i","Lux:               "+str(_enviro['lumi']))
                        enviro.append(_enviro)
                        time.sleep(timeStep)
                else:
                    while True:
                        _enviro = { 'hour' : 0, 'minute' : 0, 'second' : 0,
                                    'temp1' : 0, 'temp2' : 0, 'temp3' : 0,
                                    'humi' : 0, 'lumi' : 0 }
                        now = dt.datetime.now()
                        _enviro['hour'] = str(now.hour)
                        _enviro['minute'] = str(now.minute)
                        _enviro['second'] = str(now.second)
                        if mtype == "all":
                            _enviro['temp1'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                            _enviro['temp2'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                            _enviro['temp3'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                            _enviro['humi'] = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                            _enviro['lumi'] = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                            self.log("i","Temperature CH0:   "+str(_enviro['temp1']))
                            self.log("i","Temperature CH1:   "+str(_enviro['temp2']))
                            self.log("i","Temperature CH2:   "+str(_enviro['temp3']))
                            self.log("i","Relative humidity: "+str(_enviro['humi'])+"%")
                            self.log("i","Lux:               "+str(_enviro['lumi'])) 
                        elif mtype == "temp":
                            _enviro['temp1'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                            _enviro['temp2'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                            _enviro['temp3'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                            _enviro['humi'] = "N/A"
                            _enviro['lumi'] = "N/A"

                            self.log("i","Temperature CH0:   "+str(_enviro['temp1']))
                            self.log("i","Temperature CH1:   "+str(_enviro['temp2']))
                            self.log("i","Temperature CH2:   "+str(_enviro['temp3']))
                        elif mtype == "humi":
                            _enviro['temp1'] = "N/A"
                            _enviro['temp2'] = "N/A"
                            _enviro['temp3'] = "N/A"
                            _enviro['humi'] = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                            _enviro['lumi'] = "N/A"

                            self.log("i","Relative humidity: "+str(_enviro['humi'])+"%")
                        elif mtype == "lumi":
                            _enviro['temp1'] = "N/A"
                            _enviro['temp2'] = "N/A"
                            _enviro['temp3'] = "N/A"
                            _enviro['humi'] = "N/A"
                            _enviro['lumi'] = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                            self.log("i","Lux:               "+str(_enviro['lumi']))
                        time.sleep(timeStep)
                        enviro.append(_enviro)
        except KeyboardInterrupt:
            self.log("w","Continuous environmental measurement interrupted.")
            pass

        #Finalize measurement
        if isLast:
            try:
                self.__terminate__()
            except OSError:
                self.log("h","Current limit exceeded! HV source does not response! Results stored in emergency mode.")
                self.log("h","Manual abort required.") 
        return enviro 

    def single(self, mtype="IV", mpoint=0, sampleTime=0.50, nSamples=10, isLast=True, isFirst=False):
        #######################################
        #Alias for all single type measurements
        #######################################

        if "IV" in mtype:
            return self.singleIV(biasPoint=mpoint, sampleTime=sampleTime, nSamples=nSamples, isLast=isLast, isFirst=isFirst)
        else:
            self.log("f","Unknown single measurement type.")
            sys.exit(0)
        
    def singleIV(self, biasPoint=0, sampleTime=0.50, nSamples=10, isLast=True, isFirst=False):
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
            self.log("w","Minimum sample time per IV measurement exceeded. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            self.log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        if nSamples < int(self.__par__(self.coms['meas'],"minNSamples")):
            self.log("w","Minimum number of samples per IV measurement not reached. Setting number of samples to minimum.")
            nSamples = int(self.__par__(self.coms['meas'],"minNSamples"))
        biasPoint = self.__checkBias__(self.coms[source_dev],biasPoint)  

        #Prepare device before first measurement including source current/voltage limits
        if isFirst:
            self.__prepMeasurement__()

        #Adjusting source voltage range
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
                self.log("i","Voltage set: "+str(setBias)+".")

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr")) 
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            self.log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))

        #Adjusting current range for measurement device if possible 
        _autoRange = "OFF"  
        if self.args.autoRange:
            _autoRange = "ON" 
        self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg=_autoRange))
        isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
        if not isAuto:
            self.log("i","IV measurement: Current AUTO range disabled.")
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(float(biasPoint)))))
            if self.args.verbosity > 0:
                setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                if setCurrRange:
                    self.log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
        else:
            self.log("i","IV measurement: Current AUTO range enabled. Unable to set custom current limits.")
       
        #Setting source current limits 
        if self.args.extVSource and not isAuto:
            self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['source'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
        elif not isAuto:
            self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['meas'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                self.log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?")) 
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                self.log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])        

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        triggerType = self.__par__(self.coms['meas'],"triggerType")
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=triggerType,vital=True))
            if "Empty" in triggerType: #Trigger is fully programable
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCLEAR",arg="1"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERMDIG",arg="2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCOUNT",arg="3, "+str(nSamples)+", 2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERLIMITBRANCH",arg="4, IN, "+str(self.maxCurrent)+", 1e-2, 6"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERALWAYSBRANCH",arg="5, 7"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERSOURCE",arg="6, 0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="7, 1.0"))
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True))
            else: #minimum settings
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            self.log("e","Trigger is not supported by this measurement device (or commands are not specified).")

        #Turn on bias!!!
        self.log("i","Turning ON high-voltage source for "+source_dev_info+".")
        self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="ON",vital=True))

        #Accomodating for charging time
        self.log("i","Charging time...")
        time.sleep(self.__chargingTime__(0.,float(biasPoint)))
        self.log("i","Released.") 

        #Read out enviro data
        enviro = {}
        preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
        if 'probe' in self.args.addSocket or 'probe' in self.args.addPort:
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
        self.log("i","Temperature CH0 before measurement: "+str(preTemp0))
        self.log("i","Temperature CH1 before measurement: "+str(preTemp1))
        self.log("i","Temperature CH2 before measurement: "+str(preTemp2))
        self.log("i","Humidity before measurement: "+str(preHumi))
        self.log("i","Lumi before measurement: "+str(preLumi))

        #Read out measurement data
        readout = ""
        self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
        _vitalTriggerOFF = False 
        if "Empty" not in triggerType:
            time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
            self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
            _vitalTriggerOFF = True
        readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?", arg="1, "+str(nSamples)+", \"defbuffer1\", READ", vital=True))  #Read data from full buffer
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=_vitalTriggerOFF))                         #Stop trigger
        self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

        #Return z-station to bottom position before finalizing measurement if it is last IV measurement
        if 'zstation' in self.coms and isLast:
            self.log("i","Cleaning after last measurement")
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
            if not isLast:
                self.log("w","Probe is still touching sensor! Another measurement continues.") 
            else: 
                self.log("h","Probe is still touching sensor!")

        #Process and return results
        if len(readout) == 0:
            self.log("w","Readout is empty!")
            self.__terminate__("EXIT")
        else:
            if self.args.verbosity > 1:
                self.log("i",str(readout))

        current_readings = []
        readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim"))
        for iread,reading in enumerate(readout_list):
            if self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier")) != 0:
                curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier"),''))
                current_readings.append(curr)
                if self.args.verbosity > 0:
                    self.log("i","Current reading: "+str(curr))
            elif self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))==0:
                current_readings.append(float(reading))
                if self.args.verbosity > 0:
                    self.log("i","Current reading: "+str(reading))

        current = 0.0
        if len(current_readings) == nSamples:
            current = sum(current_readings)/float(nSamples)
        else:
            if len(current_readings) == 0:
                self.log("e","Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                self.__terminate__("EXIT")
            else:    
                current = sum(current_readings)/float(len(current_readings))

        #Run post routine if there is one specified

        #Finalize measurement
        if isLast: 
            try: 
                self.__terminate__()
            except OSError:
                self.log("h","Current limit exceeded! HV source does not response! Results stored in emergency mode.")
                self.log("h","Manual abort required.")

        #Return to mkMeasure
        return current, biasPoint, enviro

    def continuous(self, mtype="IV", mrange=[], sampleTime=0.50, nSamples=10, isLast=True, isFirst=False): 
        ##########################################
        #Alias for all continuos type measurements
        ##########################################

        if "IV" in mtype:
            return self.continuousIV(biasRange=mrange, sampleTime=sampleTime, nSamples=nSamples, isLast=isLast, isFirst=isFirst)
        else:
            self.log("f","Unknown continuous measurement type.")
            sys.exit(0)

    def continuousIV(self, biasRange, sampleTime, nSamples, isLast=True, isFirst=False):
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
            self.log("w","Minimum sample time per IV measurement underflow. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            self.log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        if nSamples < int(self.__par__(self.coms['meas'],"minNSamples")):
            self.log("w","Minimum number of samples per IV measurement not reached. Setting number of samples to minimum.")
            nSamples = int(self.__par__(self.coms['meas'],"minNSamples"))
        biasRange = self.__checkBiasRange__(self.coms[source_dev],biasRange)

        #Prepare device before first measurement
        if isFirst:
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
            self.log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))   

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                self.log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?"))
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                self.log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        triggerType = self.__par__(self.coms['meas'],"triggerType")
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=triggerType,vital=True))
            if "Empty" in triggerType: #Trigger is fully programable
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCLEAR",arg="1"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERMDIG",arg="2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCOUNT",arg="3, "+str(nSamples)+", 2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERLIMITBRANCH",arg="4, IN, "+str(self.maxCurrent)+", 1e-2, 6"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERALWAYSBRANCH",arg="5, 7"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERSOURCE",arg="6, 0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="7, 0.05"))
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True))
            else: #minimum settings
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            self.log("e","Trigger is not supported by this measurement device (or commands are not specified).")

        #Turn on bias!!!
        self.log("i","Turning ON high-voltage source for "+source_dev_info+".")
        self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="ON",vital=True))    

        #Loop over bias values
        currentOverflow = False
        results = { 'data' : [], 'enviro' : [] }
        for ibias,biasPoint in enumerate(biasRange):
            #Set Bias
            self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg=str(biasPoint),vital=True))
            if self.args.verbosity > 0:
                setBias = self.__read__(self.__cmd__(self.coms[source_dev],"VOLT?"))
                if setBias:
                    self.log("i","Voltage set: "+str(setBias)+".")

            if len(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=False)['cmd']) == 0:
                #Accomodating for charging time
                self.log("i","Charging time...")
                if ibias == 0:
                    time.sleep(self.__chargingTime__(0.,float(biasPoint)))
                else:
                    time.sleep(self.__chargingTime__(float(biasRange[ibias-1]),float(biasPoint)))
                self.log("i","Released.")

            #Adjusting current range for measurement device
            _autoRange = "OFF"
            if self.args.autoRange and ibias == 0:
                _autoRange = "ON"
                #Pre-set maximum range
                self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(500)))) #FIXME for max bias

                #Pre-set desired limit
                if self.args.extVSource:
                    self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                    if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                        current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                        safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                        self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                    if self.args.verbosity > 0:
                        limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                        limCDef = self.__par__(self.coms['source'],"defCurrent")
                        if limCSet:
                            self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                            self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
                else:
                    self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                    if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                        current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                        safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                        self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                    if self.args.verbosity > 0:
                        limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                        limCDef = self.__par__(self.coms['meas'],"defCurrent")
                        if limCSet:
                            self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                            self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
                self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg=_autoRange))
            elif self.args.autoRange:
                _autoRange = "ON" 
            isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
            if not isAuto:
                self.log("i","IV measurement: Current AUTO range disabled.")
                self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(float(biasPoint)))))
                if self.args.verbosity > 0:
                    setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                    if setCurrRange:
                        self.log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
            else:
                self.log("i","IV measurement: Current AUTO range enabled.")

            #Setting source current limits when autoRange is OFF 
            if self.args.extVSource and not isAuto:
                self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                    current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                    safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                    self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                if self.args.verbosity > 0:
                    limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                    limCDef = self.__par__(self.coms['source'],"defCurrent")
                    if limCSet:
                        self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                        self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
            elif not isAuto:
                self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                    current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                    safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                    self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                if self.args.verbosity > 0:
                    limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                    limCDef = self.__par__(self.coms['meas'],"defCurrent")
                    if limCSet:
                        self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                        self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")    

            #Read out enviro data
            enviro = {}
            preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
            if 'probe' in self.args.addSocket or 'probe' in self.args.addPort:
                #dry run needed
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                #real run 
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
                self.log("i","Temperature CH0 before measurement: "+str(preTemp0))
                self.log("i","Temperature CH1 before measurement: "+str(preTemp1))
                self.log("i","Temperature CH2 before measurement: "+str(preTemp2))
                self.log("i","Humidity before measurement: "+str(preHumi))
                self.log("i","Lumi before measurement: "+str(preLumi))    

            #Read out measurement data
            readout = ""
            self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
            if source_dev != "meas":
                self.__write__(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=True))                              #Initialize trigger on source if needed
            if len(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=True)['cmd']) != 0:
                #Accomodating for charging time
                self.log("i","Charging time...")
                if ibias == 0:
                    time.sleep(self.__chargingTime__(0.,float(biasPoint)))
                else:
                    time.sleep(self.__chargingTime__(float(biasRange[ibias-1]),float(biasPoint)))
                self.log("i","Released.")             
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
            _vitalTriggerOFF = False
            if "Empty" not in triggerType:
                time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                _vitalTriggerOFF = True
            readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?", arg="1, "+str(nSamples)+", \"defbuffer1\", READ", vital=True))  #Read data from full buffer
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=False))                                    #Stop trigger (not needed)
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state
        
            #Process and store results
            if len(readout) == 0:
                self.log("w","Readout is empty!")
                self.__terminate__()
            else:
                if self.args.verbosity > 1:
                    self.log("i",str(readout))

            current_readings = []
            readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim"))
            for iread,reading in enumerate(readout_list):
                if self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier")) != 0:
                    curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier"),''))
                    current_readings.append(curr)
                    if self.args.verbosity > 0:
                        self.log("i","Current reading: "+str(curr))
                elif self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))==0:
                    current_readings.append(float(reading))
                    if self.args.verbosity > 0:
                        self.log("i","Current reading: "+str(reading))        

            current = 0.0
            if len(current_readings) == nSamples:
                current = sum(current_readings)/float(nSamples)
            else:
                if len(current_readings) == 0:
                    self.log("w","BiasPoint: "+str(biasPoint)+": Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                    current = "N/A"
                    #self.__terminate__("EXIT")
                else:
                    current = sum(current_readings)/float(len(current_readings))
            results['data'].append((current,biasPoint))    
            results['enviro'].append(enviro)

            #Emergency break loop in case of amps exceeding maximum user set level 
            if abs(current) > abs(float(self.userCurrent))*1e-6: 
                currentOverflow = True
                self.log("h","USER CURRENT OVERFLOW! AUTO-ABORT TRIGGERED.")
                
                #Turn off bias immediately
                self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg="0",vital=True))
                self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="OFF",vital=True))

                #Actually break loop
                break

        #Return z-station to bottom position before finalizing measurement
        if ('zstation' in self.coms and isLast) or ('zstation' in self.coms and currentOverflow):
            self.log("i","Cleaning after last measurement") 
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
            if not isLast:
                self.log("w","Probe is still touching sensor! Another measurement continues.")
            else: 
                self.log("h","Probe is still touching sensor!")

        #Finalize measurement
        if isLast or currentOverflow:
            try:
                self.__terminate__()
            except OSError:
                self.log("h","Current limit exceeded! HV source does not response! Results stored in emergency mode.")
                self.log("h","Manual abort required.")

        #Return to mkMeasure
        if currentOverflow:
            self.log("w","Attempted to recover results.")
        return results

    def multiIV(self, biasRange, sampleTime, nSamples, isLast=True, isFirst=False):
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
            self.log("w","Minimum sample time per IV measurement underflow. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            self.log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        if nSamples < int(self.__par__(self.coms['meas'],"minNSamples")):
            self.log("w","Minimum number of samples per IV measurement not reached. Setting number of samples to minimum.")
            nSamples = int(self.__par__(self.coms['meas'],"minNSamples"))
        biasRange = self.__checkBiasRange__(self.coms[source_dev],biasRange)

        #Loop over bias points
        results = { 'data' : [], 'enviro' : [] }  
        isLastLocal=True
        isFirstLocal=False   
        for ibias,biasPoint in enumerate(biasRange):
            if isLast and ibias != len(biasRange)-1:
                isLastLocal = False
            elif isLast and ibias == len(biasRange)-1:
                isLastLocal = True
            elif not isLast:
                isLastLocal = False
            if isFirst and ibias == 0:
                isFirstLocal = True
            else:
                isFirstLocal = False    
            current, bias, enviro = self.singleIV(biasPoint, sampleTime, nSamples, isLast=isLastLocal, isFirst=isFirstLocal)
            results['data'].append((current,bias))
            results['enviro'].append({ 'temp1' : enviro[0],
                                       'temp2' : enviro[1],
                                       'temp3' : enviro[2],
                                       'humi'  : enviro[3],
                                       'lumi'  : enviro[4]
                                     })

        return results    

    def standbyZ(self, waitingTime=-1, isLast=True, isFirst=False):
        #############################################################
        #Global function called from mkMeasure.
        #Will initiate z-station and move it to position as for IV.
        #Then program will hangout for waitingTime > 0.
        #If waitingTime == -1 program will wait until cancelled.
        #############################################################

        #Set remote control
        self.__setRemote__()

        #Crosscheck interlock
        self.__checkInterlock__(safeMode=True)

        #Prepare device before first usage
        if isFirst and isLast:
            self.__prepMeasurementExternal__()
        elif isFirst:
            self.__prepMeasurement__()   

        #Clear enviro buffer if needed
        if 'probe' in self.coms.keys():
            self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
            self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
            self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
            self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
            self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True)) 

        #Loop for waitingTime or until cancelled or emergency
        initialTime = dt.datetime.now()
        iround = 0
        deltaTime = 0
        enviro = [] 
        while waitingTime >= deltaTime or waitingTime == -1:
            #Read out enviro data if needed
            if 'probe' in self.coms.keys():
                _enviro = { 'hour' : 0, 'minute' : 0, 'second' : 0,
                            'temp1' : 'N/A', 'temp2' : 'N/A', 'temp3' : 'N/A',
                            'humi' : 'N/A', 'lumi' : 'N/A' }
                now = dt.datetime.now()
                _enviro['hour'] = str(now.hour)
                _enviro['minute'] = str(now.minute)
                _enviro['second'] = str(now.second)
                _enviro['temp1'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                _enviro['temp2'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                _enviro['temp3'] = self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                _enviro['humi'] = self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                _enviro['lumi'] = self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                self.log("i","Temperature CH0:   "+str(_enviro['temp1']))
                self.log("i","Temperature CH1:   "+str(_enviro['temp2']))
                self.log("i","Temperature CH2:   "+str(_enviro['temp3']))
                self.log("i","Relative humidity: "+str(_enviro['humi'])+"%")
                self.log("i","Lux:               "+str(_enviro['lumi']))

                enviro.append(_enviro)

            #Loop increment
            iround += 1

            #Timeout break loop
            time.sleep(10)
            currentTime = dt.datetime.now()
            deltaTime = (currentTime - initialTime).total_seconds()
            breakMe = False
            userInput = self.log("ttt","Press \"x\" to cancel standby mode or carry on in 5 seconds.")
            if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["x"]:
                if userInput.lower().split(" ")[0] == "x":
                    breakMe = True
            if breakMe:
                self.log("i","Cancelling standby mode.")
                waitingTime = 0
            else:
                self.log("i","FINISHED LOOP N."+str(iround))
            
        #Return z-station to bottom position before finalizing measurement
        if ('zstation' in self.coms and isLast) or ('zstation' in self.coms and currentOverflow):
            self.log("i","Cleaning after last measurement")
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
            if not isLast:
                self.log("w","Platform is still in UP position! Another measurement continues.")
            else:
                self.log("h","Platform is still in UP position!")

        #Finalize measurement
        if isLast:
            self.__terminate__()

        #Return to mkMeasure
        return enviro
 
    def standbyIV(self, biasPoint=0, sampleTime=0.50, nSamples=10, waitingTime=-1, isLast=True, isFirst=False):
        #################################################
        #As standard IV but will set bias only once. 
        #Then program will be hanging for waitingTime.
        #If waitingTime == -1 program will wait until 
        #cancelled or aborted.
        #################################################

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
            self.log("w","Minimum sample time per IV measurement underflow. Setting sample time to minimum.")
            sampleTime = float(self.__par__(self.coms['meas'],"minSampleTime"))
        if nSamples > int(self.__par__(self.coms['meas'],"maxNSamples")):
            self.log("w","Maximum number of samples per IV measurement exceeded. Setting number of samples to maximum.")
            nSamples = int(self.__par__(self.coms['meas'],"maxNSamples"))
        if nSamples < int(self.__par__(self.coms['meas'],"minNSamples")):
            self.log("w","Minimum number of samples per IV measurement not reached. Setting number of samples to minimum.")
            nSamples = int(self.__par__(self.coms['meas'],"minNSamples"))
        biasPoint = self.__checkBias__(self.coms[source_dev],biasPoint)

        #Prepare device before first measurement
        if isFirst:
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

        #Define measurement type to IV
        _function = str(self.__par__(self.coms['meas'],"fCurr"))
        self.__write__(self.__cmd__(self.coms['meas'],"SENSEF", arg=_function,vital=True))
        if self.args.verbosity > 0:
            self.log("i","Tool: "+self.__read__(self.__cmd__(self.coms['meas'],"SENSEF?")))

        #Turning OFF Zero Check if possible and Turning ON Zero Correct if possible
        _zcheck = self.__read__(self.__cmd__(self.coms['meas'],"ZCHECK?"))
        if _zcheck:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCHECK",arg="OFF"))
            if self.args.verbosity > 0:
                self.log("i","Turning OFF Zero Check.")
        _zcor = self.__read__(self.__cmd__(self.coms['meas'],"ZCOR?"))
        if not _zcor:
            self.__write__(self.__cmd__(self.coms['meas'],"ZCOR",arg="ON"))
            if self.args.verbosity > 0:
                self.log("i","Turning ON Zero Correct.")
        time.sleep(self.sleep_time['meas']['medium'])

        #Setup buffer memory size if possible
        self.__write__(self.__cmd__(self.coms['meas'],"BUFFSIZE",arg=str(nSamples),vital=True))

        #Setup trigger if possible
        triggerType = self.__par__(self.coms['meas'],"triggerType")
        if self.__read__(self.__cmd__(self.coms['meas'],"TRIGGER?")):
            self.__write__(self.__cmd__(self.coms['meas'],"STRIGGER",arg=triggerType,vital=True))
            if "Empty" in triggerType: #Trigger is fully programable
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCLEAR",arg="1"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERMDIG",arg="2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERCOUNT",arg="3, "+str(nSamples)+", 2"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERLIMITBRANCH",arg="4, IN, "+str(self.maxCurrent)+", 1e-2, 6"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERALWAYSBRANCH",arg="5, 7"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERSOURCE",arg="6, 0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="7, 0.05"))
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True))
            else: #minimum settings
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERDELAY",arg="0"))
                self.__write__(self.__cmd__(self.coms['meas'],"STRIGGERTIME",arg=str("%f"%(sampleTime)),vital=True))
        else:
            self.log("e","Trigger is not supported by this measurement device (or commands are not specified).")

        #Turn on bias!!!
        self.log("i","Turning ON high-voltage source for "+source_dev_info+".")
        self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="ON",vital=True))

        #Set Bias
        self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg=str(biasPoint),vital=True))
        if self.args.verbosity > 0:
            setBias = self.__read__(self.__cmd__(self.coms[source_dev],"VOLT?"))
            if setBias:
                self.log("i","Voltage set: "+str(setBias)+".")
        ibias = 0        

        if len(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=False)['cmd']) == 0:
            #Accomodating for charging time
            self.log("i","Charging time...")
            time.sleep(self.__chargingTime__(0.,float(biasPoint)))
            self.log("i","Released.")

        #Adjusting current range for measurement device
        _autoRange = "OFF"
        if self.args.autoRange and ibias == 0:
            _autoRange = "ON"
            #Pre-set maximum range
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(1000)))) #FIXME for max bias

            #Pre-set desired limit
            if self.args.extVSource:
                self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                    current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                    safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                    self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                if self.args.verbosity > 0:
                    limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                    limCDef = self.__par__(self.coms['source'],"defCurrent")
                    if limCSet:
                        self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                        self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
            else:
                self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
                if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                    current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                    safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                    self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
                if self.args.verbosity > 0:
                    limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                    limCDef = self.__par__(self.coms['meas'],"defCurrent")
                    if limCSet:
                        self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                        self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
            self.__write__(self.__cmd__(self.coms['meas'],"SCAUTORANGE", arg=_autoRange))
        elif self.args.autoRange:
            _autoRange = "ON"    
        isAuto = bool(int(self.__read__(self.__cmd__(self.coms['meas'],"SCAUTORANGE?"))))
        if not isAuto:
            self.log("i","IV measurement: Current AUTO range disabled.")
            self.__write__(self.__cmd__(self.coms['meas'],"SSCRANGE", arg=str(self.__getCurrentRange__(float(biasPoint)))))
            if self.args.verbosity > 0:
                setCurrRange = self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?"))
                if setCurrRange:
                    self.log("i","IV measurement: Current range set by user to: "+str(setCurrRange)+".")
        else:
            self.log("i","IV measurement: Current AUTO range enabled.")

        #Setting source current limits when autoRange is OFF 
        if self.args.extVSource and not isAuto:
            self.__write__(self.__cmd__(self.coms['source'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['source'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['source'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['source'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['source'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")
        elif not isAuto:
            self.__write__(self.__cmd__(self.coms['meas'],"LIMSTAT",arg="ON")) #Enable changing limits if needed
            if self.__par__(self.coms['meas'],"climitCheckable",vital=True):
                current_range = float(self.__read__(self.__cmd__(self.coms['meas'],"SCRANGE?")))
                safe_current_limit = self.__getCurrentLimit__(current_range, float(self.maxCurrent))
                self.__write__(self.__cmd__(self.coms['meas'],"SCURRLIM",arg=safe_current_limit,vital=True)) #Set maximum current limit
            if self.args.verbosity > 0:
                limCSet = self.__read__(self.__cmd__(self.coms['meas'],"CURRLIM?"))
                limCDef = self.__par__(self.coms['meas'],"defCurrent")
                if limCSet:
                    self.log("i","Measurement device Source Output Current limit was specified (manufacturer) to "+str(limCDef)+".")
                    self.log("i","Measurement device Source Output Current limit was set (user) to "+str(limCSet)+".")

        #Loop for waitingTime or until cancelled or emergency
        initialTime = dt.datetime.now()
        deltaTime = 0
        currentOverflow = False
        results = { 'data' : [], 'enviro' : [] }
        while waitingTime >= deltaTime or waitingTime == -1:
            #Read out enviro data
            enviro = {}
            preTemp0,preTemp1,preTemp2,preHumi,preLumi = "N/A","N/A","N/A","N/A","N/A"
            if 'probe' in self.args.addSocket or 'probe' in self.args.addPort:
                #dry run needed
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP0?",vital=True))
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP1?"))
                self.__read__(self.__cmd__(self.coms['probe'],"TEMP2?"))
                self.__read__(self.__cmd__(self.coms['probe'],"HUMI?",vital=True))
                self.__read__(self.__cmd__(self.coms['probe'],"LUMI?",vital=True))

                #real run
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
                self.log("i","Temperature CH0 before measurement: "+str(preTemp0))
                self.log("i","Temperature CH1 before measurement: "+str(preTemp1))
                self.log("i","Temperature CH2 before measurement: "+str(preTemp2))
                self.log("i","Humidity before measurement: "+str(preHumi))
                self.log("i","Lumi before measurement: "+str(preLumi))     


            #Read out measurement data
            readout = ""
            self.__write__(self.__cmd__(self.coms['meas'],"CLRBUFF",vital=True))                                                   #Clear buffer
            if source_dev != "meas":
                self.__write__(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=True))                              #Initialize trigger on source if needed
            if len(self.__cmd__(self.coms[source_dev],"TRIGGERINIT",arg="ON",vital=True)['cmd']) != 0 and ibias == 0:
                #Accomodating for charging time
                self.log("i","Charging time...")
                time.sleep(self.__chargingTime__(0.,float(biasPoint)))
                self.log("i","Released.")
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="ON",vital=True))                                      #Initialize trigger on measurement device if needed
            _vitalTriggerOFF = False
            if "Empty" not in triggerType:
                time.sleep((nSamples+1)*sampleTime)                                                                                    #Wait until measurement is done
                self.__write__(self.__cmd__(self.coms['meas'],"FILLBUFF",arg=self.__par__(self.coms['meas'],"bufferMode"),vital=True)) #Tell trigger to stop passing if buffer is full
                _vitalTriggerOFF = True
            readout = self.__read__(self.__cmd__(self.coms['meas'],"READOUT?", arg="1, "+str(nSamples)+", \"defbuffer1\", READ", vital=True))  #Read data from full buffer
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERINIT",arg="OFF",vital=False))                                    #Stop trigger (not needed)
            self.__write__(self.__cmd__(self.coms['meas'],"TRIGGERABORT"))                                                         #Send trigger to idle state

            #Process and store results
            if len(readout) == 0:
                self.log("w","Readout is empty!")
                self.__terminate__()
            else:
                if self.args.verbosity > 1:
                    self.log("i",str(readout))

            current_readings = []
            readout_list = readout.split(self.__par__(self.coms['meas'],"readoutDelim"))
            for iread,reading in enumerate(readout_list):
                if self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier")) != 0:
                    curr = float(reading.replace(self.__par__(self.coms['meas'],"readoutIdentifier"),''))
                    current_readings.append(curr)
                    if self.args.verbosity > 0:
                        self.log("i","Current reading: "+str(curr))
                elif self.__par__(self.coms['meas'],"readoutIdentifier") in reading and len(self.__par__(self.coms['meas'],"readoutIdentifier"))==0:
                    current_readings.append(float(reading))
                    if self.args.verbosity > 0:
                        self.log("i","Current reading: "+str(reading))

            current = 0.0
            if len(current_readings) == nSamples:
                current = sum(current_readings)/float(nSamples)
            else:
                if len(current_readings) == 0:
                    self.log("w","BiasPoint: "+str(biasPoint)+": Parsing readout from measurement device "+str(self.coms['meas']['id'])+" failed. Change readout parameters in device-specific class.")
                    current = "N/A"
                    #self.__terminate__("EXIT")
                else:
                    current = sum(current_readings)/float(len(current_readings))
            results['data'].append((current,biasPoint))
            results['enviro'].append(enviro)

            #Emergency break loop in case of amps exceeding maximum user set level
            if abs(current) > abs(float(self.userCurrent))*1e-6:
                currentOverflow = True
                self.log("h","USER CURRENT OVERFLOW! AUTO-ABORT TRIGGERED.")

                #Turn off bias immediately
                self.__write__(self.__cmd__(self.coms[source_dev],"SVOLT",arg="0",vital=True))
                self.__write__(self.__cmd__(self.coms[source_dev],"SOURCE",arg="OFF",vital=True))

                #Actually break loop
                break

            #Timeout break loop
            time.sleep(10)
            currentTime = dt.datetime.now()
            deltaTime = (currentTime - initialTime).total_seconds()
            breakMe = False
            userInput = self.log("ttt","Press \"x\" to cancel standby mode or carry on in 5 seconds.")
            if len(userInput.lower().split(" ")) >=1 and userInput.lower().split(" ")[0] in ["x"]:
                if userInput.lower().split(" ")[0] == "x":
                    breakMe = True
            if breakMe:
                self.log("i","Cancelling standby mode.")
                waitingTime = 0
            else:
                self.log("i","FINISHED LOOP N."+str(ibias))     

        #Return z-station to bottom position before finalizing measurement
        if ('zstation' in self.coms and isLast) or ('zstation' in self.coms and currentOverflow):
            self.log("i","Cleaning after last measurement")
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
            if not isLast:
                self.log("w","Probe is still touching sensor! Another measurement continues.")
            else:
                self.log("h","Probe is still touching sensor!")

        #Finalize measurement
        if isLast or currentOverflow:
            try:
                self.__terminate__()
            except OSError:
                self.log("h","Current limit exceeded! HV source does not response! Results stored in emergency mode.")
                self.log("h","Manual abort required.")

        #Return to mkMeasure
        if currentOverflow:
            self.log("w","Attempted to recover results.")
        return results     
                  
 
    def finalize(self):
        ################################
        # Terminate I2C servers
        ################################

        for dev_type in self.coms.keys():
            if "probe" in dev_type:
                self.log("i","Probe server termination skipped.")
                #self.__write__(self.__cmd__(self.coms[dev_type],"STOP",vital=True))
                #HACK FIX ME
                #os.system("runningMacros=`pgrep SensBoxEnvSer`; macrosArray=($(echo $runningMacros | tr ' ' \"\n\")); for macro in \"${macrosArray[@]}\"; do     kill $macro; done")
        self.log("i","All done.")        

    #----------------------------------------
    #Quick global functions for parallel use:
    #----------------------------------------

    def terminate(self):
        ############################################################
        #Terminate all devices + return z-station to bottom position
        ############################################################
        self.log("h","EMERGENCY TERMINATE SELECTED")

        #first put z-station down in controlled way, then terminate all 
        if 'zstation' in self.coms:
            #turn ON motor in case it is OFF for some reason
            self.__write__(self.__cmd__(self.coms['zstation'],"MOTOR",arg="ON",vital=True))
            time.sleep(self.sleep_time['zstation']['medium'])
            isMotorOn = bool(int(self.__read__(self.__cmd__(self.coms['zstation'],"MOTOR?",vital=True))))
            if not isMotorOn:
                self.log("e","Z-station motor is turned OFF while expected working!")
                self.__terminate__("EXIT")
            else:
                if self.args.verbosity > 0:
                    self.log("i","Z-station motor is ON.")

            #Return z-station to bottom position before finalizing measurement  
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
            self.log("h","Probe is still touching sensor!")

        self.__terminate__("EXIT")

    def abort(self):
        #############################################################
        #Abort all devices: TURN OFF HV and STOP MOVEMENT
        #############################################################
        self.log("h","EMERGENCY ABORT SELECTED")

        #Emergency stop of moving parts
        if 'zstation' in self.coms:
            self.__write__(self.__cmd__(self.coms['zstation'],"ABORT",vital=True)) 

        #Abort all
        self.__abort__("ALL")

        

