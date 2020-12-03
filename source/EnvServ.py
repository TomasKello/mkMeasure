#!/usr/bin/env python

import os, sys
import time
import datetime as dt
import socket

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
                'SENSEF'   : { 'cmd' : "", 'vital' : True},                  #@Set measurement function, see parameter fCurr as possible argument
                'BUFFSIZE' : { 'cmd' : "", 'vital' : True },               #@Set buffer memory size
                'FILLBUFF' : { 'cmd' : "", 'vital' : True},             #@Set how buffer is filled 
}

#"Switch commands" switch between ON and OFF states
cmds['switch'] = { 'MATH'    : { 'cmd' : "", 'vital' : False },               #@Disable/Enable math operations
                   'ZCHECK'  : { 'cmd' : "", 'vital' : False},                 #@Enable/Disable zero check
                   'ZCOR'    : { 'cmd' : "", 'vital' : False},           #@Enable/Disable zero correction 
                   'TRIGGERINIT'  : { 'cmd' : "", 'vital' : True},            #@Enable/Disable continuous trigger initiation
}

#"Get commands" return specific device parameter
cmds['get'] = { 'ID' :        { 'cmd' : "*IDN?", 'vital' : True },                     #@Get device ID
                'INTERLOCK' : { 'cmd' : "", 'isOK' : 1 ,'vital' : True },     #@Check interlock status, if 1 is returned then OK TODO: define self.expected(cmd_type,cat="") to return isOK
                'TEMP0'     : { 'cmd' : ":MEAS:TEMP?:CH 0", 'vital' : True }, #@Return Temperature Measurement Channel 0
                'TEMP1'     : { 'cmd' : ":MEAS:TEMP?:CH 1", 'vital' : False}, #@Return Temperature Measurement Channel 1
                'TEMP2'     : { 'cmd' : ":MEAS:TEMP?:CH 2", 'vital' : False}, #@Return Temperature Measurement Channel 2
                'HUMI'      : { 'cmd' : ":MEAS:HUMI?", 'vital' : True },       #@Return Humidity Measurement
                'LUMI'      : { 'cmd' : ":MEAS:LUMI?", 'vital' : True},        #@Return Luminescence Measurement
                'ZCHECK'    : { 'cmd' : "", 'vital' : False},                 #@Get Zero Check status
                'ZCOR'      : { 'cmd' : "", 'vital' : False},           #@Get Zero Correct status
                'TRIGGER'   : { 'cmd' : "", 'vital' : True},                 #@Get measure event control source
                'READOUT'   : { 'cmd' : "", 'vital' : True},                 #@Readout data from buffer
}

#"Do commands" invoke device function which does not require additional parameter
cmds['do'] = { 'CMDINIT' : { 'cmd' : "", 'vital' : False},              #@Some devices require initial cmd to enable communication using commands
               'RESET'   : { 'cmd' : "", 'vital' : True },              #@Reset device into default settings and cancel pending cmds
               'CLRBUFF' : { 'cmd' : "", 'vital' : True},               #@Clear buffer
               'TRIGGERABORT' : { 'cmd' : "", 'vital' : False},         #@Abort operations and send trigger to idle
               'REMOTE'  : { 'cmd' : "", 'vital' : True},               #@Set device to remote control and disable front panel
               'LOCAL'   : { 'cmd' : "", 'vital' : True},               #@Set device to local control and enable front panel 
               'STOP'    : { 'cmd' : "*STOP", 'vital' : True},          #@Terminate server          
               
            }

########################################################
#----------------------PARAMETERS----------------------#
########################################################

pars = { 'tShort'  : { 'par' :  0.5, 'vital' : True, 'alt' : "" },                        #@Basic sleep time in seconds needed for proper running of device routines
         'tMedium' : { 'par' :  1.5, 'vital' : True, 'alt' : "" },                        #@Medium sleep time  
         'tLong'   : { 'par' :  3.0, 'vital' : True, 'alt' : "" },                        #@Long sleep time
         'readoutDelim'  : { 'par' : ',' , 'vital' : True, 'alt' : ""},                   #@Readout for each sample is devided by this character
         'interlockCheckable' : { 'par' : False, 'vital' : True, 'alt' : ""},             #@Checkability of interlock status
         'remoteCheckable'    : { 'par' : False, 'vital' : True, 'alt' : ""},             #@Checkability of remote control
         'vlimitCheckable'    : { 'par' : False, 'vital' : True, 'alt' : ""},             #@Checkability of voltage limits
         'reqTemp' : { 'par' : {'min' : 16., 'max' : 24.5}, 'vital' : True, 'alt' : ""},  #@Required temperature interval
         'reqHumi' : { 'par' : {'min' : 0., 'max' : 40.0}, 'vital' : True, 'alt' : ""},   #@Required humidity interval
         'reqLumi' : { 'par' : {'min' : 0., 'max' : 0.001}, 'vital' : True, 'alt' : ""},  #@Required lumi interval
}



class EnvServ():
    def __init__(self):
        ################################################
        #Device-specific class for KEITHLEY model K6517A
        ################################################
        self.delim = '\r\n'
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

        #run server
        #import subprocess
        #exe = sys.executable
        #exeDir = exe[:exe.rfind("/")]
        #subprocess.Popen([exeDir+"/SensBoxEnvSer"])
        #time.sleep(5)

    def test(self):
        ######################################################
        #Sanity check = return value must match the class name
        ######################################################
        return "EnvServ"

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

        HOST = com['host']  # The server's hostname or IP address
        PORT = com['port']  # The port used by the server

        write_status = False
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))
            except ConnectionRefusedError:
                return "REFUSED"
            s.sendall(cmd.encode())
            time.sleep(self.sleep_time) 
            write_status = True

        return write_status    
            
    def read(self,com,cmd):
        ###########################################
        #Define device-specific 'read' routine here
        ###########################################
     
        HOST = com['host']  # The server's hostname or IP address
        PORT = com['port']  # The port used by the server

        return_value = ""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.connect((HOST, PORT))
            except ConnectionRefusedError:
                return "REFUSED"
            s.sendall(cmd.encode())
            time.sleep(self.sleep_time)
            return_value = s.recv(1024)

        return return_value.decode().rstrip()
 
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
