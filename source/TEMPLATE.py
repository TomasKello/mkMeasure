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
cmds['set'] = { 'STIME'    : { 'cmd' : "SYST:TIME ", 'vital' : False},                 #@Set current system time
                'SDATE'    : { 'cmd' : "SYST:DATE ", 'vital' : False},                 #@Set current system date
                'SVOLT'    : { 'cmd' : "SOUR:VOLT ", 'vital' : True},                  #@Set high voltage source to <arg> value
                'SVOLTLIM' : { 'cmd' : "SOUR:VOLT:LIM ", 'vital' : True},              #@Set voltage limit in absolute value
                'SVRANGE'  : { 'cmd' : "SOUR:VOLT:RANGE ", 'vital' : False},           #@Set voltage range (0-1000), but results in 100 for V<=100 or 1000 if V>100
                'SENSEF'   : { 'cmd' : "SENS:FUNC ", 'vital' : True},                  #@Set measurement function, see parameter fCurr as possible argument
                'SSCRANGE' : { 'cmd' : "SENS:CURR:RANG ", 'vital' : False},            #@Set SENS Current range if AUTO range is disabled
                'BUFFSIZE' : { 'cmd' : "TRAC:POINts ", 'vital' : True },               #@Set buffer memory size
                'STRIGGER' : { 'cmd' : "TRIG:SOUR ", 'vital' : True},                  #@Set measure event control source
                'STRIGGERDELAY' : { 'cmd' : "TRIG:DEL ", 'vital' : False},             #@Set trigger delay in seconds
                'STRIGGERTIME'  : { 'cmd' : "TRIG:TIM ", 'vital' : True},              #@Set interval for measure layer timer
                'FILLBUFF' : { 'cmd' : "TRAC:FEED:CONT ", 'vital' : True},             #@Set how buffer is filled 
}

#"Switch commands" switch between ON and OFF states
cmds['switch'] = { 'MATH'    : { 'cmd' : "CALC:STAT ", 'vital' : False },               #@Disable/Enable math operations
                   'SOURCE'  : { 'cmd' : "OUTP ", 'vital' : True },                     #@Switch high voltage source ON/OFF
                   'ZCHECK'  : { 'cmd' : "SYST:ZCH ", 'vital' : False},                 #@Enable/Disable zero check
                   'ZCOR'    : { 'cmd' : "SYST:ZCOR:STAT ", 'vital' : False},           #@Enable/Disable zero correction 
                   'LIMSTAT' : { 'cmd' : "SOUR:VOLT:LIM:STAT ", 'vital' : False},       #@Enable/Disable changes in VSource limits  
                   'SCAUTORANGE'  : { 'cmd' : "SENS:CURR:RANG:AUTO ", 'vital' : False}, #@Enable/Disable SENS Current AUTO Range
                   'TRIGGERINIT'  : { 'cmd' : "INIT:CONT ", 'vital' : True},            #@Enable/Disable continuous trigger initiation
}

#"Get commands" return specific device parameter
cmds['get'] = { 'ID' :        { 'cmd' : "*IDN?", 'vital' : True },                     #@Get device ID
                'INTERLOCK' : { 'cmd' : "SYST:INT?", 'isOK' : 1 ,'vital' : True },     #@Check interlock status, if 1 is returned then OK TODO: define self.expected(cmd_type,cat="") to return isOK
                'POSETUP'   : { 'cmd' : "SYST:POS?", 'isOK' : "RST", 'vital' : False}, #@Get power-on default settings status, if RST then it is set to *RST settings for power up  
                'ZCHECK'    : { 'cmd' : "SYST:ZCH?", 'vital' : False},                 #@Get Zero Check status
                'ZCOR'      : { 'cmd' : "SYST:ZCOR:STAT?", 'vital' : False},           #@Get Zero Correct status
                'SOURCE'    : { 'cmd' : "OUTP?", 'isOK' : 0, 'vital' : True},          #@Check if high voltage source is ON (1) or OFF (0) 
                'VOLTLIM'   : { 'cmd' : "SOUR:VOLT:LIM?", 'vital' : False},            #@Get absolute voltage limit set by user 
                'VOLT'      : { 'cmd' : "SOUR:VOLT?", 'vital' : True},                 #@Get set voltage
                'SCAUTORANGE'  : { 'cmd' : "SENS:CURR:RANG:AUTO?", 'vital' : False},   #@Check SENS Current AUTO range status (manufacturer)
                'SCRANGE'      : { 'cmd' : "SENS:CURR:RANG?", 'vital' : False},        #@Get SENS Current range (user)
                'TRIGGER'   : { 'cmd' : "TRIG:SOUR?", 'vital' : True},                 #@Get measure event control source
                'READOUT'   : { 'cmd' : "TRAC:DATA?", 'vital' : True},                 #@Readout data from buffer
}

#"Do commands" invoke device function which does not require additional parameter
cmds['do'] = { 'RESET'   : { 'cmd' : "*RST", 'vital' : True },                      #@Reset device into default settings and cancel pending cmds
               'POSETUP' : { 'cmd' : "SYST:POS RST", 'vital' : False},              #@Set Power On default settings (settings after power up) to settings defined by *RST
               'CLRBUFF' : { 'cmd' : "TRAC:CLE", 'vital' : True},                   #@Clear buffer
               'TRIGGERABORT' : { 'cmd' : "ABORT", 'vital' : False},                #@Abort operations and send trigger to idle
               'REMOTE'  : { 'cmd' : "SYST:REMote", 'vital' : True},                #@Set device to remote control and disable front panel
               'LOCAL'   : { 'cmd' : "SYST:LOCal", 'vital' : True},                 #@Set device to local control and enable front panel 
}

########################################################
#----------------------PARAMETERS----------------------#
########################################################

pars = { 'minBias' : { 'par' : -100, 'vital' : True, 'alt' : "minV" },              #@Extreme minimum voltage to be set on this device (user). Can be set up to -defBias.
         'maxBias' : { 'par' :  100, 'vital' : True, 'alt' : "maxV" },              #@Extreme maximum voltage to be set on this device (user). Can be set up to defBias.
         'defBias' : { 'par' : 1000, 'vital' : True, 'alt' : "defaultMaxV"},        #@Factory settings total (absolute) maximum of voltage to be set on this device (manufacturer)
         'tShort'  : { 'par' :  0.5, 'vital' : True, 'alt' : "" },                  #@Basic sleep time in seconds needed for proper running of device routines
         'tMedium' : { 'par' :  1.5, 'vital' : True, 'alt' : "" },                  #@Medium sleep time  
         'tLong'   : { 'par' :  3.0, 'vital' : True, 'alt' : "" },                  #@Long sleep time
         'minSampleTime' : { 'par' : 0.50, 'vital' : False, 'alt' : "minSTime"},    #@Minimum sample time for a single IV measurement
         'maxNSamples'   : { 'par' : 8,    'vital' : False, 'alt' : "" },           #@Maximum number of samples per single IV measurement
         'fCurr'         : { 'par' : 'CURR', 'vital' : True, 'alt' : "" },          #@SENSE argument defining CurrentMeasurement function 
         'fVolt'         : { 'par' : 'VOLT', 'vital' : True, 'alt' : "" },          #@SENSE argument defining VoltageMeasurement function
         'triggerType'   : { 'par' : 'IMM', 'vital' : True, 'alt' : ""},            #@Trigger source, supported type is IMMEDIATE (pass first layer immediately)
         'bufferMode'    : { 'par' : 'NEXT', 'vital' : False, 'alt' : ""},          #@Buffer mode, NEXT = fill buffer and stops
         'readoutDelim'  : { 'par' : ',' , 'vital' : True, 'alt' : ""},             #@Readout for each sample is devided by this character
         'readoutIdentifier' : { 'par' : "NADC", 'vital' : True, 'alt' : ""},       #@Each readout reading consists of this string 
}



class TEMPLATE():
    def __init__(self):
        ################################################
        #Device-specific class for <TEMPLATE>
        ################################################
        self.delim = '\n'
        self.sleep_time = 0.5
        self.medium_sleep_time = 1.5
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
        return "TEMPLATE"

    def cmd(self,cmd_type,arg="",cat=""):
        ###############################
        #Return device-specific command
        ###############################
        
        cmd= "" 
        if cmd_type in cmds[cat]:
            if cat == "switch" or cat == "set":
                cmd = cmds[cat][cmd_type]['cmd']+str(arg)
            else:
                cmd = cmds[cat][cmd_type]['cmd']
        else:
            cmd = "UNKNOWN"

        return cmd

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
        time.sleep(self.sleep_time)
        write_status = com.write((cmd+self.delim).encode())
        return write_status

    def read(self,com,cmd):
        ###########################################
        #Define device-specific 'read' routine here
        ###########################################
        time.sleep(self.sleep_time)
        com.write((cmd+self.delim).encode())
        time.sleep(self.medium_sleep_time)
        read_value = ""
        while com.inWaiting() > 0:
            part = com.read(1).decode().strip('\r')
            read_value += part
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

        <TEMPLATE>

        return status,message    
