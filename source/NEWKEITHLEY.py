#!/usr/bin/env python

import os, sys
import time
import datetime as dt

########################################################
#----------------------COMMANDS------------------------#
########################################################

#Note: 'vital' = False indicates that 'cmd' can be left empty.
#      If 'vital' = False and Device class requires 'vital' = True 
#      error is raised.

cmds = {}

#"Set commands" are usually followed by argument which can be defined here (if global) or in Device class (if user-given)
cmds['set'] = { 'STIME'    : { 'cmd' : "SYST:TIME ", 'vital' : False},                 #@Set current system date & time
                #'SDATE'    : { 'cmd' : "", 'vital' : False},                           #@Set current system date & time
                'SVOLT'    : { 'cmd' : "SOUR:VOLT ", 'vital' : True},                  #@Set high voltage source to <arg> value
                'SVOLTLIM' : { 'cmd' : "SOUR:CURR:VLIM ", 'vital' : True},             #@Set source voltage limit in abs value
                'SCURRLIM' : { 'cmd' : "SOUR:VOLT:ILIM ", 'vital' : True},             #@Set source current limit in abs value
                'SVRANGE'  : { 'cmd' : "SOUR:VOLT:RANGE ", 'vital' : False},           #@Set source voltage range (0-1000)
                'SCRANGE'  : { 'cmd' : "SOUR:CURR:RANGE ", 'vital' : False},           #@Set source current range
                'SOURF'    : { 'cmd' : "SOUR:FUNC ", 'vital' : True},                  #@Set source function, see parameter fCurr/fVolt as possible argument
                'SENSEF'   : { 'cmd' : "SENS:FUNC ", 'vital' : True},                  #@Set measurement function, see parameter fCurr/fVolt as possible argument
                'SSVRANGE' : { 'cmd' : "SENS:VOLT:RANGE ", 'vital' : False},           #@Set meas current range
                'SSCRANGE' : { 'cmd' : "SENS:CURR:RANGE ", 'vital' : False},           #@Set meas current range
                'BUFFSIZE' : { 'cmd' : "TRAC:POINts ", 'vital' : True },               #@Resize existent buffer memory size
                'STRIGGER' : { 'cmd' : "TRIG:LOAD ", 'vital' : True},                  #@Set trigger model
                'STRIGGERDELAY' : { 'cmd' : "TRIG:BLOC:DEL:CONS ", 'vital' : False},   #@Set trigger delay in seconds
                'STRIGGERTIME'  : { 'cmd' : "SENS:CURR:NPLC ", 'vital' : False},       #@Set interval for measure layer timer (cannot be specified for this trigger model)
                'STRIGGERCLEAR' : { 'cmd' : "TRIG:BLOC:BUFF:CLEAR ", 'vital' : False}, #@Set trigger buffer to clear (double measure with TRAC:CLE)
                'STRIGGERMDIG'  : { 'cmd' : "TRIG:BLOC:MDIG ", 'vital' : False},       #@Set trigger to digitize measurement   
                'STRIGGERCOUNT' : { 'cmd' : "TRIG:BLOC:BRAN:COUN ", 'vital' : True},   #@Set trigger to execute nSample readings     
                'STRIGGERALWAYSBRANCH': { 'cmd' : "TRIG:BLOC:BRAN:ALW ", 'vital' : False}, #@Set trigger branch that always redirect from block A to B
                'STRIGGERLIMITBRANCH': { 'cmd' : "TRIG:BLOC:BRAN:LIM:CONS ", 'vital' : False}, #@Set trigger branch that redirect from block A to C when condition is applied          
                'STRIGGERSOURCE' : { 'cmd' : "TRIG:BLOC:SOUR:STAT ", 'vital' : False}, #@Set trigger to turn ON/OFF source in trigger sequence             
                'SPANEL' : { 'cmd' : "ROUT:TERM ", 'vital' : False},                   #@Set output panel to be used
                'FILLBUFF' : { 'cmd' : "TRAC:FILL:MODE ", 'vital' : False},            #@Set how buffer is filled 
}

#"Switch commands" switch between ON and OFF states
cmds['switch'] = { 'MATHVOLT'   : { 'cmd' : "CALC:VOLT:MATH:STAT ", 'vital' : False },      #@Disable/Enable VOLT math operations
                   'MATHCURR'   : { 'cmd' : "CALC:CURR:MATH:STAT ", 'vital' : False },      #@Disable/Enable CURR math operations
                   'MATHRES'    : { 'cmd' : "CALC:RES:MATH:STAT ", 'vital' : False },       #@Disable/Enable RES math operations
                   'MATH'       : { 'cmd' : "", 'vital' : False, 
                                    'children' : { 'ON' : ['switch:MATHVOLT', 'switch:MATHCURR', 'switch:MATHRES'],
                                                   'OFF': ['switch:MATHVOLT', 'switch:MATHCURR', 'switch:MATHRES']
                                                 } 
                                  }, #@Disable/Enable ALL math operations 
                   'INTERLOCK'  : { 'cmd' : "OUTP:INT:STAT ", 'vital' : False},            #@Enable Interlock settings (DISCOURAGED TO DISABLE)  
                   'SOURCE'     : { 'cmd' : "OUTP ", 'vital' : True },                     #@Switch high voltage source ON/OFF
                   'ZCHECKVOLT' : { 'cmd' : "VOLT:AZER:STAT ", 'vital' : False},           #@Enable/Disable autozero correction for VOLT
                   'ZCHECKCURR' : { 'cmd' : "CURR:AZER:STAT ", 'vital' : False},           #@Enable/Disable autozero correction for CURR 
                   'ZCHECKRES'  : { 'cmd' : "RES:AZER:STAT ", 'vital' : False},            #@Enable/Disable autozero correction for RES
                   'ZCHECK'     : { 'cmd' : "", 'vital' : False, 
                                    'children' : { 'ON' : ['switch:ZCHECKVOLT','switch:ZCHECKCURR','switch:ZCHECKRES'],
                                                   'OFF': ['switch:ZCHECKVOLT','switch:ZCHECKCURR','switch:ZCHECKRES']
                                                 }
                                  }, #@Enable/Disable autozero correction for ALL
                   'ZCOR'    : { 'cmd' : "", 'vital' : False, 
                                 'children' : { 'ON' : ['do:ZCOR'], 'OFF' : [] }
                               }, #@Enable/Disable zero correction for ALL
                   'LIMSTAT' : { 'cmd' : "", 'vital' : False},                          #@Enable/Disable changes in VSource limits (not needed for this device) 
                   'CURRLIM' : { 'cmd' : "", 'vital' : False},                          #@Enable/Disable resistive current limit by inserting serial resistance (not available)
                   'VOLTLIM' : { 'cmd' : "", 'vital' : False},                          #@Enable/Disable resistive voltage limit (not available)
                   'SCAUTORANGE'  : { 'cmd' : "SENS:CURR:RANG:AUTO ", 'vital' : False},                        #@Enable/Disable SENS Current AUTO Range
                   'TRIGGERINIT'  : { 'cmd' : "", 'children' : { 'ON' : ['do:TRIGGERINIT'], 'OFF' : []}, 'vital' : True},            #@Enable/Disable continuous trigger initiation
}

#"Get commands" return specific device parameter
cmds['get'] = { 'ID' :        { 'cmd' : "*IDN?", 'vital' : True },                                            #@Get device ID
                'INTERLOCK' : { 'cmd' : "OUTP:INT:TRIP?", 'isOK' : ['1'] , 'isNOT' : ['0'], 'vital' : True }, #@Check interlock status, if isOK is returned then OK 
                'INHIBITOR' : { 'cmd' : "OUTP:INT:TRIP?", 'isOK' : ['1'] , 'isNOT' : ['0'], 'vital' : True},  #@Check inhibitor status, the same as Interlock here
                'POSETUP'   : { 'cmd' : "SYST:POS?", 'isOK' : ["RST"], 'vital' : False},                      #@Get power-on default settings status  
                'ZCHECK'    : { 'cmd' : "CURR:AZER:STAT?", 'vital' : False},                                  #@Get AutoZero Correct status
                'ZCOR'      : { 'cmd' : "CURR:AZER:STAT?", 'vital' : False},                                  #@Get AutoZero Correct status
                'SOURCE'    : { 'cmd' : "OUTP?", 'isOK' : ['0'], 'vital' : True},                             #@Check if high voltage source is ON (1) or OFF (0) 
                'VOLTLIM'   : { 'cmd' : "SOUR:CURR:VLIM?", 'vital' : False},                                   #@Get absolute source voltage limit set by user 
                'CURRLIM'   : { 'cmd' : "SOUR:VOLT:ILIM?", 'vital' : False},                                   #@Get source current limit set by user  
                'VOLT'      : { 'cmd' : "SOUR:VOLT?", 'vital' : True},                                        #@Get user-set voltage
                'SENSEF'    : { 'cmd' : "SENS:FUNC?", 'vital' : False},                                       #@Check measurement function
                'SOURF'     : { 'cmd' : "SOUR:FUNC?", 'vital' : False},                                       #@Check source function
                'SCAUTORANGE'  : { 'cmd' : "SENS:CURR:RANG:AUTO?", 'vital' : False},                          #@Check Measurement Current AUTO range status (manufacturer)
                'SCRANGE'      : { 'cmd' : "SENS:CURR:RANG?", 'vital' : False},                               #@Get Measurement Current range (user)
                'TRIGGER'   : { 'cmd' : "TRIG:STAT?", 'vital' : True},                                        #@Get trigger state (returns string)
                'READOUT'   : { 'cmd' : "TRAC:DATA? ", 'vital' : True},                                       #@Readout data from buffer
                'INBUFFER'  : { 'cmd' : "TRAC:ACT?", 'vital' : True},                                        #@Return number of readings in buffer
                'BUFFEREND' : { 'cmd' : "TRAC:ACT:END?", 'vital' : False},                                    #@Get last index of buffer
}

#"Do commands" invoke device function which does not require additional parameter
cmds['do'] = { 'RESET'   : { 'cmd' : "*RST", 'vital' : True },                      #@Reset device into default settings and cancel pending cmds
	       'CMDINIT' : { 'cmd' : "", 'vital' : False},                          #@Some devices require initial cmd to enable communication using commands	
               'POSETUP' : { 'cmd' : "SYST:POS RST", 'vital' : False},              #@Set Power On default settings (settings after power up) to settings defined by *RST
               'ZCOR'    : { 'cmd' : "SENS:AZER:ONCE", 'vital' : False},            #@Execute ZeroCorrect once
               'CLRBUFF' : { 'cmd' : "TRAC:CLE;*WAI", 'vital' : True},              #@Clear buffer and wait for this action
               'TRIGGERINIT'  : { 'cmd' : "INIT;*WAI", 'vital' : True},             #@Initialize trigger operations and wait until all is done
               'TRIGGERABORT' : { 'cmd' : "ABORT", 'vital' : False},                #@Abort operations and send trigger to idle
               'REMOTE'  : { 'cmd' : "login", 'vital' : False},                     #@Set device to remote control and disable front panel 
               'LOCAL'   : { 'cmd' : "logout", 'vital' : True},                     #@Set device to local control and enable front panel 
}

########################################################
#----------------------PARAMETERS----------------------#
########################################################

pars = { 'minBias' : { 'par' : -1000, 'vital' : True, 'alt' : "minV" },              #@Extreme minimum voltage to be set on this device (user). Can be set up to -defBias.
         'maxBias' : { 'par' :  1000, 'vital' : True, 'alt' : "maxV" },                #@Extreme maximum voltage to be set on this device (user). Can be set up to defBias.
         'maxCurrent' : { 'par' :  30e-6, 'vital' : True, 'alt' : "maxC" },         #@Extreme maximum output current [A] to be set on this device (user). Can be set up to defCurrent.
         'userCurrent' : { 'par' : 29.9, 'vital' : False, 'alt' : "userC" },        #@User defined maximum output current [muA] to be checked after each readout due to fragile measurement target.
         'defBias' : { 'par' : 1100, 'vital' : True, 'alt' : "defaultMaxV"},        #@Factory settings total (absolute) maximum of voltage to be set on this device (manufacturer)
         'defCurrent' : { 'par' : 1.05e-4, 'vital' : True, 'alt' : "defaultMaxC"},  #@Factory settings total maximum of current [A] to be set on this device (manufacturer) 
         'tShort'  : { 'par' :  0.5, 'vital' : True, 'alt' : "" },                  #@Basic sleep time in seconds needed for proper running of device routines
         'tMedium' : { 'par' :  1.5, 'vital' : True, 'alt' : "" },                  #@Medium sleep time  
         'tLong'   : { 'par' :  3.0, 'vital' : True, 'alt' : "" },                  #@Long sleep time
         'minSampleTime' : { 'par' : 0.50, 'vital' : False, 'alt' : "minSTime"},    #@Minimum sample time for a single IV measurement
         'maxNSamples'   : { 'par' : 50,    'vital' : False, 'alt' : "" },         #@Maximum number of samples per single IV measurement
         'minNSamples'   : { 'par' : 10,    'vital' : False, 'alt' : "" },          #@Minimum number of samples per single IV measurement
         'fCurr'         : { 'par' : '\'CURR\'', 'vital' : True, 'alt' : "" },      #@SENSE argument defining CurrentMeasurement function 
         'fVolt'         : { 'par' : '\'VOLT\'', 'vital' : True, 'alt' : "" },      #@SENSE argument defining VoltageMeasurement function
         'triggerType'   : { 'par' : '\"Empty\"', 'vital' : True, 'alt' : ""},      #@Trigger source, build trigger from scratch
         'triggerIdle'   : { 'par' : 'IDLE', 'vital' : True, 'alt' : ""},           #@String returned when Trigger is on Idle
         'bufferMode'    : { 'par' : 'ONCE', 'vital' : False, 'alt' : ""},          #@Buffer mode, ONCE = fill buffer and stops
         'readoutDelim'  : { 'par' : ',' , 'vital' : True, 'alt' : ""},             #@Readout for each sample is devided by this character
         'readoutIdentifier' : { 'par' : "", 'vital' : True, 'alt' : ""},           #@Each readout reading consists of this string
         'decimalVolt'       : { 'par' : True, 'vital' : True, 'alt' : ""},         #@Check if decimal accuracy for setting volts is allowed
         'interlockCheckable' : { 'par' : True, 'vital' : True, 'alt' : ""},        #@Checkability of interlock status
         'inhibitorCheckable' : { 'par' : True,'vital' : True, 'alt' : ""},         #@Checkability of inhibitor status
         'remoteCheckable'    : { 'par' : True, 'vital' : True, 'alt' : ""},        #@Checkability of remote control
         'vlimitCheckable'    : { 'par' : True, 'vital' : True, 'alt' : ""},        #@Checkability of voltage limits
         'climitCheckable'    : { 'par' : True, 'vital' : True, 'alt' : ""},        #@Checkability of current limits
         'biasPolarity'       : { 'par' : -1., 'vital' : False, 'alt' : ""},        #@Specify device default polarity (if not defined then bias sign is accepted as on input)
}

##########

class NEWKEITHLEY():
    def __init__(self):
        ################################################
        #Device-specific class for KEITHLEY model K6517A
        ################################################
        self.delim = '\n'
        self.sleep_time = pars['tShort']['par']
        self.medium_sleep_time = pars['tMedium']['par']
        self.long_sleep_time = pars['tLong']['par']
        now = dt.datetime.now()
        self.year = str(now.year)
        self.month = str(now.month)
        self.day = str(now.day)
        self.hr = str(now.hour)
        self.min = str(now.minute)
        self.sec = str(now.second)
        #TODO: run selfcheck on cmds: if 'cmd' is empty, set 'vital' to False, then add crosscheck in self.cmd

    def test(self):
        ######################################################
        #Sanity check = return value must match the class name
        ######################################################
        return "NEWKEITHLEY"

    def cmd(self,cmd_type,arg="",cat=""):
        ###############################
        #Return device-specific command
        ###############################
        
        cmd   = '' 
        isOK  = []
        isNOT = [] 
        if cmd_type in cmds[cat]:
            if cat == "switch" or cat == "set" or (cat == "get" and len(arg) != 0):
                if len(cmds[cat][cmd_type]['cmd']) == 0 and 'children' in cmds[cat][cmd_type].keys():
                    _cmd = ''  
                    if cat == "switch":
                        for child in cmds[cat][cmd_type]['children'][str(arg)]:
                            if ":" in child:
                                _childType = child.split(":")[0] 
                                _childKey  = child.split(":")[-1]
                            else: 
                                _childType = cat
                                _childKey  = child
                            if _childType in cmds.keys():
                                if _childKey in cmds[_childType].keys():
                                    if _childType == "switch" or _childType == "set": 
                                        _cmd += cmds[_childType][_childKey]['cmd'] + str(arg) + ";"
                                    else:
                                        _cmd += cmds[_childType][_childKey]['cmd'] + ";" 
                                else:
                                    cmd = "UNKNOWN"
                                    return (cmd,[],[]) 
                            else:
                                cmd = "UNKNOWN"
                                return (cmd,[],[])
                    else:
                        for child in cmds[cat][cmd_type]['children']:
                            if ":" in child:
                                _childType = child.split(":")[0]
                                _childKey  = child.split(":")[-1]
                            else:
                                _childType = cat
                                _childKey  = child
                            if _childType in cmds.keys():
                                if _childKey in cmds[_childType].keys():
                                    if _childType == "switch" or _childType == "set":
                                        _cmd += cmds[_childType][_childKey]['cmd'] + str(arg) + ";"
                                    else:
                                        _cmd += cmds[_childType][_childKey]['cmd'] + ";"                 
                                else:
                                    cmd = "UNKNOWN"
                                    return (cmd,[],[]) 
                            else:
                                cmd = "UNKNOWN"
                                return (cmd,[],[])
                    cmd = _cmd.strip(";")         
                else:
                    if len(cmds[cat][cmd_type]['cmd']) == 0:
                        cmd = ""
                    else:    
                        cmd = cmds[cat][cmd_type]['cmd']+str(arg)
                if 'isOK' in cmds[cat][cmd_type].keys():
                    isOK = cmds[cat][cmd_type]['isOK']
                if 'isNOT' in cmds[cat][cmd_type].keys():
                    isNOT = cmds[cat][cmd_type]['isNOT']
            else:
                cmd = cmds[cat][cmd_type]['cmd']
                #TODO: add children feature 
                if 'isOK' in cmds[cat][cmd_type].keys():
                    isOK = cmds[cat][cmd_type]['isOK']
                if 'isNOT' in cmds[cat][cmd_type].keys():
                    isNOT = cmds[cat][cmd_type]['isNOT']
        else:
            cmd = "UNKNOWN"
            return (cmd,[],[])

        if cat == "get":
            return (cmd,isOK,isNOT)

        return (cmd,[],[])

    def par(self,par_type):
        #################################
        #Return device-specific constants
        #################################
        _par = ""
        if par_type in pars:
            _par = pars[par_type]['par']
        else:
            for key in pars:
                if par_type == pars[key]['alt']:
                    _par = pars[key]['par']

        return _par    

    def write(self,com,raw_cmd):
        ############################################
        #Define device-specific 'write' routine here
        ############################################
        time.sleep(self.sleep_time)
        raw_cmds = raw_cmd.split(";")
        queries = []
        args = []
        arg_types = []
        for _cmd in raw_cmds:
            if len(_cmd.split(" ")) > 1:
                queries.append(_cmd.split(" ")[0])
                raw_args = (_cmd.replace(_cmd.split(" ")[0],"")).split(",")
                _args = []
                _arg_types = []
                for arg in raw_args:
                    _arg = ""
                    try:
                        _arg = int(arg)
                        _arg_types.append("int")
                    except ValueError:
                        try:
                            _arg = float(arg)
                            _arg_types.append("float")
                        except ValueError:
                            _arg = str(arg)
                            _arg_types.append("str")
                    _args.append(_arg)
                args.append(_args)
                arg_types.append(_arg_types)
            else:
                queries.append(_cmd)
                args.append([])
                arg_types.append([])       

        _response = ""
        for iq,query in enumerate(queries):
            try:
                if not query.endswith("?"):
                    #set/switch/do commands 
                    isNum = True
                    if not query.endswith(" "): query+=" "
                    for argType in arg_types[iq]:
                        if argType != "int" and argType != "float":
                            isNum = False
                    if len(args[iq]) != 0 and isNum:
                        if len(args[iq])==1:
                            if(str(args[iq][0]).startswith(" ")): args[iq][0] = str(args[iq][0])[1:]
                            #print(query+".NUM")
                            #print(str(args[iq][0]))
                            com.write(query+str(args[iq][0]))
                        else:
                            #print(query+".")
                            #print(args[iq])
                            com.write_ascii_values(query,args[iq])
                    else:
                        if len(args[iq])==1:
                            if(str(args[iq][0]).startswith(" ")): args[iq][0] = str(args[iq][0])[1:]
                            #print(query+".STR")
                            #print(args[iq][0])
                            com.write(query,args[iq][0])
                        else:
                            if "log" in query:
                                _response += com.query(query).rstrip()+";"
                            elif "LIM:CONS" in query:
                                str_args = [str(arg) for arg in args[iq]]
                                one_arg = ", ".join(str_args).strip(", ")
                                #print(query)
                                #print(one_arg)
                                com.write(query,one_arg)
                            else:
                                #print(query)
                                #print(args[iq])
                                com.write(query,args[iq])
                    _response += "RECEIVED;"
            except Exception as e:
                _response += str(e)+";" 

        write_status = _response.strip(";")
        return write_status

    def read(self,com,raw_cmd):
        ###########################################
        #Define device-specific 'read' routine here
        ###########################################
        time.sleep(self.sleep_time)
        raw_cmds = raw_cmd.split(";")
        queries = []
        args = []
        arg_types = []
        for _cmd in raw_cmds:
            if len(_cmd.split(" ")) > 1:
                queries.append(_cmd.split(" ")[0])
                raw_args = (_cmd.replace(_cmd.split(" ")[0],"")).split(",") 
                _args = []
                _arg_types = []
                for arg in raw_args:
                    _arg = ""
                    try:
                        _arg = int(arg)
                        _arg_types.append("int")
                    except ValueError:
                        try:
                            _arg = float(arg)
                            _arg_types.append("float")
                        except ValueError:
                            _arg = str(arg)
                            _arg_types.append("str")
                    _args.append(_arg)        
                args.append(_args)
                arg_types.append(_arg_types)
            else:
                queries.append(_cmd)
                args.append([])
                arg_types.append([])

        _response = ""
        for iq,query in enumerate(queries):
            try:
                if (query.endswith("?") and len(args[iq]) == 0) or "log" in query:
                    #query without extra specifier
                    _response += com.query(query).rstrip()+";"
                elif query.endswith("?") and len(args[iq]) != 0:
                    #query with exta specifier
                    _response += com.query(query+" "+", ".join([str(arg) for arg in args[iq]])).rstrip()+";"
            except Exception as e:
                _response += str(e)+";"    
                
        read_value = _response.strip(";")   
        return read_value.rstrip()

    def pre(self,com):
        ####################################################
        #Define device-specific pre-measurement routine here
        #This is discouraged unless very specific treatment.
        #Returns to-be-printed text or "ABORT" command.
        ####################################################

        #Return message
        status = "i" #message will be displayed as INFO; w-WARNING, e-ERROR (initialize ABORT)
        message = self.test()+": "

        return status,message    
