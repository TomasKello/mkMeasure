#!/usr/bin/env python

import os, sys
import ColorLogger

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("SocketConnector: ")
    return clogger.log(log_type,text)

class SocketConnector:
    def __init__(self,args):
        self.args = args

    def __detect_devices__(self):
        ########################################################
        #Return dictionary of available hosts and ports used for
        #communication with additional devices.
        ########################################################
        #FIXME this is hardcoded, should be read from config
        devices = {}
        devices['probe']   = { 'id'       : "EnvServ",
                               'model'    : "V1.2",
                               'type'     : "probe",
                               'port'     : 9090,
                               'host'     : '127.0.0.1'
                             }
        return devices

    def gateway(self):
        ###############################################
        #Return information neccessary for establishing
        #socket based communication.
        ###############################################
        
        devs = {}

        #-------------------------
        #Detect available devices
        #-------------------------
        _devs = self.__detect_devices__()


        for dev in self.args.addSocket:
            if dev in _devs:
                devs[dev] = { 'id' : _devs[dev]['id'], 'model' : _devs[dev]['model'], 'com' : { 'host' : _devs[dev]['host'], 'port' : _devs[dev]['port'] }}
        return devs

