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
                'STRIGGER' : { 'cmd' : "TRIG:SOUR ", 'vital' : True},                  #@Set measure event control source
                'STRIGGERDELAY' : { 'cmd' : "TRIG:DEL ", 'vital' : False},             #@Set trigger delay in seconds
                'STRIGGERTIME'  : { 'cmd' : "TRIG:TIM ", 'vital' : True},              #@Set interval for measure layer timer
                'SVELOCITY'     : { 'cmd' : "1VA", 'vital' : False},                   #@Set motor velocity
                'SGOTO'         : { 'cmd' : "1PA", 'vital' : True},                    #@Set absolute position and go there
                'SGOTOREL'      : { 'cmd' : "1PR", 'vital' : False},                   #@Move in relative coordinates 
}

#"Switch commands" switch between ON and OFF states
cmds['switch'] = { 'SOURCE'  : { 'cmd' : "", 'vital' : True },                          #@Switch high voltage source ON/OFF
                   'TRIGGERINIT'  : { 'cmd' : "", 'vital' : True},                      #@Enable/Disable continuous trigger initiation
                   'MOTOR'   : { 'cmd' : "1M", 'vital' : True},                         #@Turn ON/OFF z-station motor
}

#"Get commands" return specific device parameter
cmds['get'] = { 'ID' :        { 'cmd' : "1ID?", 'vital' : True },                                       #@Get device ID
                'INTERLOCK' : { 'cmd' : "1TE?;1TE?", 'isOK' : ['0'], 'isNOT' : ['8','129'] , 'vital' : True },#@Check interlock status, if isOK is returned then OK 
                'POSETUP'   : { 'cmd' : "", 'isOK' : "", 'vital' : False},                              #@Get power-on default settings status, if RST then it is set to *RST settings for power up  
                'SOURCE'    : { 'cmd' : "", 'isOK' : 0, 'vital' : True},                                #@Check if high voltage source is ON (1) or OFF (0) 
                'TRIGGER'   : { 'cmd' : "", 'vital' : True},                                            #@Get measure event control source
                'READOUT'   : { 'cmd' : "", 'vital' : True},                                            #@Readout data from buffer
                'VELOCITY'  : { 'cmd' : "1TV?", 'vital' : False},                                       #@Get motor real velocity value
                'SETVELO'   : { 'cmd' : "1VA?", 'vital' : False},                                       #@Get motor set velocity value 
                'MOTOR'     : { 'cmd' : "1MO?", 'vital' : True},                                        #@Get motor turn ON/OFF status
                'MOVE'      : { 'cmd' : "1MD?", 'vital' : True},                                        #@Check if motor is in motion 
}

#"Do commands" invoke device function which does not require additional parameter
cmds['do'] = { 'RESET'   : { 'cmd' : "*RST", 'vital' : True },                      #@Reset device into default settings and cancel pending cmds
               'CMDINIT' : { 'cmd' : "\r", 'vital' : False},                      #@Some devices require initial cmd to enable communication using commands
               'POSETUP' : { 'cmd' : "SYST:POS RST", 'vital' : False},              #@Set Power On default settings (settings after power up) to settings defined by *RST
               'CLRBUFF' : { 'cmd' : "TRAC:CLE", 'vital' : True},                   #@Clear buffer
               'TRIGGERABORT' : { 'cmd' : "ABORT", 'vital' : False},                #@Abort operations and send trigger to idle
               'REMOTE'  : { 'cmd' : "", 'vital' : False},                          #@Set device to remote control and disable front panel
               'LOCAL'   : { 'cmd' : "", 'vital' : False},                          #@Set device to local control and enable front panel 
               'STOP'    : { 'cmd' : "1ST", 'vital' : True},                        #@Gradually stop motion with set deceleration
               'ABORT'   : { 'cmd' : "AB", 'vital' : True},                         #@Immediate stop for emergency cases
               'GOHOME'  : { 'cmd' : "1OR1", 'vital' : True},                       #@Go to home position
}

########################################################
#----------------------PARAMETERS----------------------#
########################################################

pars = { 'tShort'  : { 'par' :  0.10, 'vital' : True, 'alt' : "" },                  #@Basic sleep time in seconds needed for proper running of device routines
         'tMedium' : { 'par' :  0.25, 'vital' : True, 'alt' : "" },                  #@Medium sleep time  
         'tLong'   : { 'par' :  3.00, 'vital' : True, 'alt' : "" },                  #@Long sleep time
         'safeVelo': { 'par' :  0.2, 'vital' : False,'alt' : "safeVelocity"},        #@Safe motor velocity
         'topPosition'      : { 'par' : 2.0, 'vital' : True, 'alt' : "top"},           #@Table top position coordinates
         'bottomPosition'   : { 'par' : -2.0, 'vital' : True, 'alt' : "bottom"},       #@Table bottom position coordinates
         'touchPosition'    : { 'par' : 0.5, 'vital' : True, 'alt' : "touch"},         #@Table connection established coordinates
         'detouchPosition'  : { 'par' : -0.5, 'vital' : True, 'alt' : "detouch"},      #@Table ready to connect position
         'fCurr'         : { 'par' : '\'CURR\'', 'vital' : True, 'alt' : "" },      #@SENSE argument defining CurrentMeasurement function 
         'fVolt'         : { 'par' : '\'VOLT\'', 'vital' : True, 'alt' : "" },      #@SENSE argument defining VoltageMeasurement function
         'readoutDelim'  : { 'par' : ',' , 'vital' : True, 'alt' : ""},             #@Readout for each sample is devided by this character
         'readoutIdentifier' : { 'par' : "NADC", 'vital' : True, 'alt' : ""},       #@Each readout reading consists of this string
         'interlockCheckable' : { 'par' : True, 'vital' : True, 'alt' : ""},        #@Checkability of interlock status
         'remoteCheckable'    : { 'par' : False, 'vital' : True, 'alt' : ""},        #@Checkability of remote control
}



class ESP100():
    def __init__(self):
        ################################################
        #Device-specific class for KEITHLEY model K6517A
        ################################################
        self.delim = '\r'
        self.sleep_time = 0.10
        self.medium_sleep_time = 0.8
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
        return "ESP100"

    def cmd(self,cmd_type,arg="",cat=""):
        ###############################
        #Return device-specific command
        ###############################
        
        cmd= "" 
        if cmd_type in cmds[cat]:
            if cat == "switch": 
                if "OFF" in arg.upper():
                    arg = "F"
                elif "ON" in arg.upper():
                    arg = "O"
                cmd = cmds[cat][cmd_type]['cmd']+str(arg)    
            elif cat == "set":
                cmd = cmds[cat][cmd_type]['cmd']+str(arg)
            else:
                cmd   = cmds[cat][cmd_type]['cmd']
                if 'isOK' in cmds[cat][cmd_type]:
                    isOK  = cmds[cat][cmd_type]['isOK']
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
        time.sleep(self.sleep_time)
        write_status = com.write((cmd+self.delim).encode())
        return write_status

    def read(self,com,cmd):
        ###########################################
        #Define device-specific 'read' routine here
        ###########################################
        
        time.sleep(self.sleep_time)
        com.write((cmd+self.delim).encode("ascii"))
        time.sleep(self.medium_sleep_time)
        read_value = ""
        while com.inWaiting() > 0:
            try:
                part = com.read(1).decode().strip('\r')
                read_value += part
            except UnicodeDecodeError:
                WARNING = '\033[93;1m'
                ENDC    = '\033[0m'
                print(WARNING+" ESP100:           [WARNING]   Decoding error detected. Residual bits found in buffer."+ENDC)
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
