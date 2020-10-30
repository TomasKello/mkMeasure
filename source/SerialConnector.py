#!/usr/bin/env python

import os, sys
import serial
import glob
import ColorLogger

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("SerialConnector: ")
    return clogger.log(log_type,text)

class SerialConnector:
    def __init__(self,args):
        self.args = args

    def __supported_serial_ports__(self):
        ###############################################
        #Return list of platform supported serial ports
        ###############################################

        ports = []
        if sys.platform.startswith('win'):
            #ports = ['COM%s' % (i + 1) for i in range(256)] #FIXME
            raise EnvironmentError('Unsupported platform')
        elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
            # this excludes your current terminal "/dev/tty" #FIXME
            ports = glob.glob('/dev/tty[A-Za-z]*')
        elif sys.platform.startswith('darwin'):
            #ports = glob.glob('/dev/tty.*') #FIXME
            raise EnvironmentError('Unsupported platform')
        else:
            raise EnvironmentError('Unsupported platform')

        working_ports = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                working_ports.append(port)
            except (OSError, serial.SerialException):
                pass
        return working_ports

    def __detect_devices__(self):
        ###########################################################
        #Return dictionary of devices connected in particular order
        ###########################################################
        #FIXME this is hardcoded, should be read from config
        devices = {}
        devices['meas']   = { 'id'       : "KEITHLEY",
                              'model'    : "6517A", 
                              'type'     : "meas",   
                              'port'     : "USB0", 
                              'baudrate' : 9600, 
                              'parity'   : serial.PARITY_NONE, 
                              'stopbits' : serial.STOPBITS_TWO, 
                              'bytesize' : serial.EIGHTBITS, 
                              'rtscts'   : 0,
                              'xonxoff'  : True
                            }
        devices['source'] = { 'id'       : "NHQ201",
                              'model'    : "481055-1.34", 
                              'type'     : "source", 
                              'port'     : "USB1",
                              'baudrate' : 9600,
                              'parity'   : serial.PARITY_NONE,
                              'stopbits' : serial.STOPBITS_ONE,
                              'bytesize' : serial.EIGHTBITS,
                              'rtscts'   : 0,
                              'xonxoff'  : True
                            }
        devices['zstation'] = { 'id'       : "ESP100", 
                                'model'    : "M-UZM80CC.1",
                                'type'     : "zstation",  
                                'port'     : "USB2",     
                                'baudrate' : 19200,
                                'parity'   : serial.PARITY_NONE,
                                'stopbits' : serial.STOPBITS_ONE,
                                'bytesize' : serial.EIGHTBITS,
                                'rtscts'   : 1,
                                'xonxoff'  : False
                              }
        #devices['other'] = { 'id' : ""           , 'type' : "other",  'port' : ""     }
        return devices

    def __detect_RS232__(self, failedAttempts = {}, goodAttempts = {}):
        #########################################################################
        #Return dict of ports selected/autoselected for connection with device(s)
        #########################################################################

        # listing serial ports
        COM_ports = self.__supported_serial_ports__()
        if len(COM_ports) == 0:
            log("e","No RS232 ports found!")
            sys.exit(0)
        else:
            if self.args.selectPort:
                log("i","RS232 ports detected:")
                for icom, com in enumerate(COM_ports):
                    log("n","%d) %s"%(int(icom)+1, com))
                log("n","%d) %s"%(len(COM_ports)+1,"Terminate"))    

        # listing available devices
        devices = self.__detect_devices__()
        selected_ports = {} # devices with selected/autoselected ports
  
        # matching ports to devices 
        if len(COM_ports) == 1:
            if self.args.extVSource:
                log("w","Not enough serial connections. Cannot use external VSource.")
                self.args.extVSource = False
            for dev_type in self.args.addPort:    
                if dev_type == "zstation":
                    log("w","Not enough serial connections. Cannot use motors to enable automotion.")
                else:
                    log("w","Not enough serial connections to connect additional device of type: "+str(dev_type))
            self.args.addPort = []        
            selected_ports['meas'] = devices['meas']
            selected_ports['meas']['port'] = COM_ports[0]
        elif len(COM_ports) > 1:
            if self.args.selectPort:
                # select main meas device port
                meas_port_number = 0
                while (int(meas_port_number) <= 0 or int(meas_port_number) > len(COM_ports)+1): 
                    log("t","Select port for the main Measurement device:")
                    meas_port_number = log("tt","[%d - %d]"%(1, len(COM_ports)+1))
                    try:
                        int(meas_port_number)
                    except ValueError:
                        meas_port_number = 0
                if int(meas_port_number) == len(COM_ports)+1:
                    log("i","Measurement terminated by user.")
                    sys.exit(0)
                selected_ports['meas'] = devices['meas']
                selected_ports['meas']['port'] = COM_ports[int(meas_port_number)-1]

                # select external VSource device port
                source_port_number = 0
                if self.args.extVSource:
                    while (int(source_port_number) <= 0 or int(source_port_number) > len(COM_ports)+1):
                        log("t","Select port for the external VSource device:")
                        source_port_number = log("tt","[%d - %d]"%(1, len(COM_ports)+1))
                        try:
                            int(source_port_number)
                        except ValueError:
                            source_port_number = 0
                        if source_port_number  == meas_port_number:
                            log("t","Cannot use the same port!")
                            source_port_number = 0
                    if int(source_port_number) == len(COM_ports)+1:
                        log("i","Measurement terminated by user.")
                        sys.exit(0)
                    selected_ports['source'] = devices['source']    
                    selected_ports['source']['port'] = COM_ports[int(source_port_number)-1]

                # select other devices
                confirmed_add_port_numbers = []
                not_used_devices = []
                for dev_type in self.args.addPort:
                    if dev_type not in devices:
                        log("w","Device type: \""+str(dev_type)+"\" NOT specified in device config.")
                        log("w","Device will not be used.")
                        not_used_devices.append(dev_type)
                        continue
                    add_port_number = 0
                    while (int(add_port_number) <= 0 or int(add_port_number) > len(COM_ports)+1):
                        log("t","Select port for the device of type: "+str(dev_type))
                        add_port_number = log("tt","[%d - %d]"%(1, len(COM_ports)+1))
                        try:
                            int(add_port_number)
                        except ValueError:
                            add_port_number = 0
                        if (add_port_number == meas_port_number) or (add_port_number == source_port_number) or (add_port_number in confirmed_add_port_numbers):
                            log("t","Cannot use the same port!")
                            add_port_number = 0
                    if int(add_port_number) == len(COM_ports)+1:
                        log("i","Measurement terminated by user.")
                        sys.exit(0)        
                    confirmed_add_port_numbers.append(add_port_number)
                    selected_ports[dev_type] = devices[dev_type]
                    selected_ports[dev_type]['port'] = COM_ports[int(add_port_number)-1]
                self.args.addPort = [ dev_type for dev_type in self.args.addPort if dev_type not in not_used_devices ]    
            else:
                log("i","Automatic port selection activated.")
                relevantDevs = [key for key in devices.keys() if ( (key == "source" and self.args.extVSource) or (key in self.args.addPort) or key == "meas" )]
                relevantPorts = {}
                usedPorts = []
                #refresh used ports
                for relDev in goodAttempts.keys():
                    if self.args.verbosity > 1:
                        log("i","Adding "+relDev+" to the correctly matched ports.")
                    usedPorts.append(goodAttempts[relDev])

                #loop over relevant devices and ports
                for relDev in relevantDevs:
                    #use default settings if possible
                    if relDev in goodAttempts.keys():
                        relevantPorts[relDev] = [goodAttempts[relDev]] #precisely one
                    else:    
                        relevantPorts[relDev] = [port for port in COM_ports 
                                                 if ("USB" in port 
                                                     and ( (relDev in failedAttempts.keys() and port not in failedAttempts[relDev]) or 
                                                           relDev not in failedAttempts.keys()
                                                         )
                                                     and port not in usedPorts
                                                    )
                                                ] 

                        #fixing filled buffer error
                        if len(relevantPorts[relDev]) == 0:
                            failedAttempts[relDev] = []
                            relevantPorts[relDev] = [port for port in COM_ports
                                                     if ("USB" in port and port not in usedPorts)
                                                    ]

                    isDefault = False
                    for port in relevantPorts[relDev]:
                        #print("reldev="+relDev+" port="+port)
                        if port in usedPorts:
                            if relDev in goodAttempts.keys():
                                devices[relDev]['port'] = port 
                                selected_ports[relDev] = devices[relDev]
                            continue
                        if devices[relDev]['port'] in port:
                            #print("match "+devices[relDev]['port'])
                            devices[relDev]['port'] = port
                            selected_ports[relDev] = devices[relDev]
                            usedPorts.append(port)
                            isDefault = True
                            break
                        #print(selected_ports)

                    #else find alternative                    
                    if not isDefault:
                        for port in relevantPorts[relDev]:
                            if port in usedPorts: 
                                if relDev in goodAttempts.keys():   
                                    devices[relDev]['port'] = port
                                    selected_ports[relDev] = devices[relDev]
                                continue
                            devices[relDev]['port'] = port
                            selected_ports[relDev] = devices[relDev]
                            usedPorts.append(port)
                            break

        if self.args.extVSource:
            log("i","Primary measurement device: ID=%s, port=%s"%(selected_ports['meas']['id'],selected_ports['meas']['port']))
            log("i","External VSource: ID=%s, port=%s"%(selected_ports['source']['id'],selected_ports['source']['port']))
        else:
            log("i","Primary measurement device: ID=%s, port=%s"%(selected_ports['meas']['id'],selected_ports['meas']['port']))
            log("i","External VSource port: not used")
        for key in selected_ports.keys():
            if key not in ['meas','source']:
                log("i","Device of type %s: ID=%s, port=%s"%(key,selected_ports[key]['id'],selected_ports[key]['port'])) 
        return selected_ports

    def __set_RS232__(self,this_port):
        #######################
        #Setup RS232 connection
        #######################
        this_com = serial.Serial(
                  port=this_port['port'],
                  timeout=1,
                  baudrate=this_port['baudrate'],
                  parity=this_port['parity'],
                  stopbits=this_port['stopbits'],
                  bytesize=this_port['bytesize'],
                  xonxoff=this_port['xonxoff'],
                  rtscts=this_port['rtscts'],
                  dsrdtr=False
              )
        COM = { 'id' : this_port['id'], 'model' : this_port['model'], 'port' : this_port['port'], 'com' : this_com }
        return COM

    def __open_RS232__(self,COM):
        while(True):
            try:
                COM.isOpen()
                return COM
            except serial.SerialException as e:
                log("e","Cannot open serial port!! "+str(e))
                sys.exit(0)
                #COM = set_RS232_interactive(COM) TODO: in case of wrong settings

    def connect_RS232(self, failedAttempts = {}, goodAttempts = {}):
        #####################################################################
        #Global function called from mkMeasure to setup RS232 safe connection 
        #with configured devices
        #####################################################################

        COMS = {}
        ports = self.__detect_RS232__(failedAttempts, goodAttempts)
        
        #setup communication
        try:
            COMS['meas'] = self.__set_RS232__(ports['meas'])
            if self.args.extVSource:
                COMS['source'] = self.__set_RS232__(ports['source'])
            for dev_type in self.args.addPort:
                COMS[dev_type] = self.__set_RS232__(ports[dev_type])
        except KeyError:
            log("f","Port selection failed during bit exchange. Repeat selection.")
            sys.exit(0)
    
        #initialize communication
        COMS['meas']['com'] = self.__open_RS232__(COMS['meas']['com'])
        if self.args.extVSource:
            COMS['source']['com'] = self.__open_RS232__(COMS['source']['com'])
        for dev_type in self.args.addPort:
            COMS[dev_type]['com'] = self.__open_RS232__(COMS[dev_type]['com']) 

        return COMS   
    
    def test_RS232(self):
        ###########################################
        #Global function to test port availability.
        ###########################################

        ports = self.__detect_RS232__()
        test = False
        if "meas" in ports.keys():
            if len(ports['meas']['port']) != 0:
                test = True
                if "source" in ports.keys():
                    if len(ports['source']['port']) != 0:
                        log("i","Port availability test: SUCCESSFUL")
                    else:
                        log("w","Not enough ports for external VSource.")
                        log("i","Port availability test: SUCCESSFUL")
                else:
                    log("w","Not enough ports for external VSource.")
                    log("i","Port availability test: SUCCESSFUL")
            else:
                log("e","Port availability test: FAILED")
        else:
            log("e","Port availability test: FAILED")
        
        return test

