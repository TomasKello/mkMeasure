#!/usr/bin/env python

import os, sys

def log(log_type="i",text=""):
    source = "SocketConnector: "
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

