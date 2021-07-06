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
cmds['set'] = { 'STIME'    : { 'cmd' : "", 'vital' : False},                    #@Set current system time
                'SDATE'    : { 'cmd' : "", 'vital' : False},                    #@Set current system date
                'SVOLT'    : { 'cmd' : "D1=", 'vital' : True},                  #@Set high voltage source to <arg> value
                'SVOLTLIM' : { 'cmd' : "", 'vital' : True},                     #@Set voltage limit in absolute value
                'SCURRLIM' : { 'cmd' : "L1=", 'vital' : False},                 #@Set output current limit
                'SVRANGE'  : { 'cmd' : "", 'vital' : False},                    #@Set voltage range (0-1000), but results in 100 for V<=100 or 1000 if V>100
                'SENSEF'   : { 'cmd' : "", 'vital' : True},                     #@Set measurement function, see parameter fCurr as possible argument
                'SSCRANGE' : { 'cmd' : "", 'vital' : False},                    #@Set SENS Current range if AUTO range is disabled
                'BUFFSIZE' : { 'cmd' : "", 'vital' : True },                    #@Set buffer memory size
                'STRIGGER' : { 'cmd' : "", 'vital' : True},                     #@Set measure event control source
                'STRIGGERDELAY' : { 'cmd' : "", 'vital' : False},               #@Set trigger delay in seconds
                'STRIGGERTIME'  : { 'cmd' : "", 'vital' : True},                #@Set interval for measure layer timer
                'FILLBUFF' : { 'cmd' : "", 'vital' : True},                     #@Set how buffer is filled 
}

#"Switch commands" switch between ON and OFF states
cmds['switch'] = { 'MATH'    : { 'cmd' : "", 'vital' : False },                 #@Disable/Enable math operations
                   'SOURCE'  : { 'cmd' : "G1", 'vital' : True },                #@Switch high voltage source ON/OFF
                   'ZCHECK'  : { 'cmd' : "", 'vital' : False},                  #@Enable/Disable zero check
                   'ZCOR'    : { 'cmd' : "", 'vital' : False},                  #@Enable/Disable zero correction 
                   'LIMSTAT' : { 'cmd' : "", 'vital' : False},                  #@Enable/Disable changes in VSource limits  
                   'CURRLIM' : { 'cmd' : "", 'vital' : False},                  #@Enable/Disable resistive current limit
                   'VOLTLIM' : { 'cmd' : "", 'vital' : False},                  #@Enable/Disable resistive voltage limit  
                   'SCAUTORANGE'  : { 'cmd' : "", 'vital' : False},             #@Enable/Disable SENS Current AUTO Range
                   'TRIGGERINIT'  : { 'cmd' : "G1", 'vital' : True},            #@Enable/Disable continuous trigger initiation
}

#"Get commands" return specific device parameter
cmds['get'] = { 'ID' :        { 'cmd' : "#", 'vital' : True },                          #@Get device ID
                'INTERLOCK' : { 'cmd' : "", 'isOK' : 1 ,'vital' : True },               #@Check interlock status, if 1 is returned then OK TODO: define self.expected(cmd_type,cat="") to return isOK
                'INHIBITOR' : { 'cmd' : "T1", 'isOK' : ["0:5"], 'vital' : False},       #@Check inhibitor status
                'POSETUP'   : { 'cmd' : "", 'isOK' : "RST", 'vital' : False},           #@Get power-on default settings status, if RST then it is set to *RST settings for power up  
                'ZCHECK'    : { 'cmd' : "", 'vital' : False},                           #@Get Zero Check status
                'ZCOR'      : { 'cmd' : "", 'vital' : False},                           #@Get Zero Correct status
                'SOURCE'    : { 'cmd' : "T1", 'isOK' : ["1:3"], 'vital' : True},        #@Check if high voltage source is ON (0) or OFF (1) 
                'VOLTLIM'   : { 'cmd' : "M1", 'vital' : False},                         #@Get absolute voltage limit set by user 
                'CURRLIM'   : { 'cmd' : "N1", 'vital' : False},                         #@Get output current limit set by user 
                'VOLT'      : { 'cmd' : "D1", 'vital' : True},                          #@Get set voltage
                'SCAUTORANGE'  : { 'cmd' : "", 'vital' : False},                        #@Check SENS Current AUTO range status (manufacturer)
                'SCRANGE'      : { 'cmd' : "", 'vital' : False},                        #@Get SENS Current range (user)
                'TRIGGER'   : { 'cmd' : "", 'vital' : True},                            #@Get measure event control source
                'READOUT'   : { 'cmd' : "I1", 'vital' : True},                          #@Readout data from buffer
                'STATUS' : { 'cmd' : "S1", 'vital' : True},                          #@Get device internal status 
}

#"Do commands" invoke device function which does not require additional parameter
cmds['do'] = { 'CMDINIT' : { 'cmd' : "\r\n", 'vital' : False},              #@Some devices require initial cmd to enable communication using commands
               'RESET'   : { 'cmd' : "S1", 'vital' : True },                      #@Reset device into default settings and cancel pending cmds
               'POSETUP' : { 'cmd' : "", 'vital' : False},              #@Set Power On default settings (settings after power up) to settings defined by *RST
               'CLRBUFF' : { 'cmd' : "", 'vital' : True},                   #@Clear buffer
               'TRIGGERABORT' : { 'cmd' : "", 'vital' : False},                #@Abort operations and send trigger to idle
               'REMOTE'  : { 'cmd' : "", 'vital' : True},                #@Set device to remote control and disable front panel
               'LOCAL'   : { 'cmd' : "", 'vital' : True},                 #@Set device to local control and enable front panel 
}

########################################################
#----------------------PARAMETERS----------------------#
########################################################

pars = { 'minBias' : { 'par' : -1000, 'vital' : True, 'alt' : "minV" },              #@Extreme minimum voltage to be set on this device (user). Can be set up to -defBias.
         'maxBias' : { 'par' :  1000, 'vital' : True, 'alt' : "maxV" },              #@Extreme maximum voltage to be set on this device (user). Can be set up to defBias.
         'defBias' : { 'par' : 1000, 'vital' : True, 'alt' : "defaultMaxV"},         #@Factory settings total (absolute) maximum of voltage to be set on this device (manufacturer)
         'defCurrent' : { 'par' : 100, 'vital' : True, 'alt' : "defaultMaxC"},       #@Factory settings total maximum of output current [muA] to be set on this device (manufacturer)
         'maxCurrent' : { 'par' : 30, 'vital' : True, 'alt' : "maxC" },              #@Extreme maximum output current [muA] set by user
         'tShort'  : { 'par' :  0.08, 'vital' : True, 'alt' : "" },                  #@Basic sleep time in seconds needed for proper running of device routines
         'tMedium' : { 'par' :  1.5, 'vital' : True, 'alt' : "" },                   #@Medium sleep time  
         'tLong'   : { 'par' :  3.0, 'vital' : True, 'alt' : "" },                   #@Long sleep time
         'minSampleTime' : { 'par' : 0.50, 'vital' : False, 'alt' : "minSTime"},     #@Minimum sample time for a single IV measurement
         'maxNSamples'   : { 'par' : 8,    'vital' : False, 'alt' : "" },            #@Maximum number of samples per single IV measurement
         'fCurr'         : { 'par' : 'CURR', 'vital' : True, 'alt' : "" },           #@SENSE argument defining CurrentMeasurement function 
         'fVolt'         : { 'par' : 'VOLT', 'vital' : True, 'alt' : "" },           #@SENSE argument defining VoltageMeasurement function
         'triggerType'   : { 'par' : 'IMM', 'vital' : True, 'alt' : ""},             #@Trigger source, supported type is IMMEDIATE (pass first layer immediately)
         'bufferMode'    : { 'par' : 'NEXT', 'vital' : False, 'alt' : ""},           #@Buffer mode, NEXT = fill buffer and stops
         'readoutDelim'  : { 'par' : ',' , 'vital' : True, 'alt' : ""},              #@Readout for each sample is devided by this character
         'readoutIdentifier' : { 'par' : "NADC", 'vital' : True, 'alt' : ""},        #@Each readout reading consists of this string
         'decimalVolt'       : { 'par' : False, 'vital' : True, 'alt' : ""},         #@Check if decimal accuracy for setting volts is allowed
         'interlockCheckable' : { 'par' : False, 'vital' : True, 'alt' : ""},        #@Checkability of interlock status
         'inhibitorCheckable' : { 'par' : True, 'vital' : True, 'alt' : ""},         #@Checkability of inhibitor status
         'remoteCheckable'    : { 'par' : False, 'vital' : True, 'alt' : ""},        #@Checkability of remote control
         'vlimitCheckable'    : { 'par' : False, 'vital' : True, 'alt' : ""},        #@Checkability of voltage limits
         'climitCheckable'    : { 'par' : True, 'vital' : True, 'alt' : ""},         #@Checkability of current limits   
}



class NHQ201():
    def __init__(self):
        ################################################
        #Device-specific class for KEITHLEY model K6517A
        ################################################
        self.delim = '\r\n'
        self.sleep_time = 0.10 #FIXME: read from par
        self.medium_sleep_time = 1.0
        self.long_sleep_time = 3.0 
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
        return "NHQ201"

    def cmd(self,cmd_type,arg="",cat=""):
        ###############################
        #Return device-specific command
        ###############################
        
        cmd= "" 
        if cmd_type in cmds[cat]:
            if cat == "set":
                if len(cmds[cat][cmd_type]['cmd']) != 0: 
                    cmd = cmds[cat][cmd_type]['cmd']+str(arg)
                else:
                    cmd = ""
            else:
                cmd = cmds[cat][cmd_type]['cmd']
                if 'isOK' in cmds[cat][cmd_type]:
                    isOK = cmds[cat][cmd_type]['isOK']
                else:
                    isOK = []
                if 'isNOT' in cmds[cat][cmd_type]:
                    isNOT = cmds[cat][cmd_type]['isNOT']
                else:
                    isNOT = []
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

    def write(self,com,cmd):
        ############################################
        #Define device-specific 'write' routine here
        ############################################

        for char in cmd:
            com.write((char).encode())
            time.sleep(self.sleep_time)
        if self.delim not in cmd:    
            com.write((self.delim).encode())
        time.sleep(self.medium_sleep_time)
        write_echo = ""
        while com.inWaiting() > 0:
            part = com.read(1).decode('ascii').strip(self.delim)
            write_echo += part
        return write_echo

    def read(self,com,cmd):
        ###########################################
        #Define device-specific 'read' routine here
        ###########################################
      
        for char in cmd:
            com.write((char).encode())
            time.sleep(self.sleep_time)
        if self.delim not in cmd:    
            com.write((self.delim).encode())
        time.sleep(self.medium_sleep_time)
        read_value = ""
        while com.inWaiting() > 0:
            part = com.read(1).decode('ascii')
            read_value += part
        return_value = ""
        
        if len(read_value) == 0:
            return_value = read_value
        elif "=" in read_value.split(self.delim)[1]:
            return_value = read_value.split(self.delim)[1].split("=")[-1]
            if "ON" in return_value: return_value = "1"
            elif "OFF" in return_value: return_value = "0"    
        else:
            return_value = read_value.split(self.delim)[1]
        return return_value
 
    def pre(self,com):
        ####################################################
        #Define device-specific pre-measurement routine here
        #This is discouraged unless very specific treatment.
        #Returns to-be-printed text or "ABORT" command.
        ####################################################

        #Return message
        status = "i" #message will be displayed as INFO; w-WARNING, e-ERROR (initialize ABORT)
        message = self.test()+": "

        #Set ramp speed to 50V/s
        self.write(com,"V1=50")
        set_ramp_speed = str(self.read(com,"V1"))
        message += "Set ramp speed to "+set_ramp_speed+"V/s."

        return status,message    
