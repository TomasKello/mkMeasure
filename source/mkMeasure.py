import argparse
import os
import sys
import serial
import pyvisa
import glob
import time
import datetime
import ColorLogger
import DelayedKeyboardInterrupt as warden
import SerialConnector
import SocketConnector
import Device
import OutputHandler
import InputParser

#constants
delim = '\n'

def _date():
    _date = datetime.datetime.now()
    month = str(_date.month)
    day = str(_date.day)
    hour = str(_date.hour)
    minute = str(_date.minute)
    second = str(_date.second)
    if len(str(_date.month)) == 1: month = "0"+str(_date.month)
    if len(str(_date.day)) == 1: day = "0"+str(_date.day)
    if len(str(_date.hour)) == 1: hour = "0"+str(_date.hour)
    if len(str(_date.minute)) == 1: minute = "0"+str(_date.minute)
    if len(str(_date.second)) == 1: second = "0"+str(_date.second)
    
    return str(_date.year)+month+day+"_"+hour+minute+second
_logname = _date()+".txt"

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("mkMeasure:       ",_logname)
    return clogger.log(log_type,text)

def range_list(arg_value):
    #######################################
    #Define argument type for -c|-m options
    #######################################
    _custom_list = []
    if "[" in arg_value and "]" in arg_value:
        #list was provided explicitely
        _custom_list = [float(value) for value in arg_value.replace("[","").replace("]","").split(",")]
    elif "[" not in arg_value and "]" not in arg_value:
        #list was provided implicitely
        delimiter = " "
        if "," in arg_value: delimiter = ","
        if ";" in arg_value: delimiter = ";"
        value_list = [float(value) for value in arg_value.split(delimiter)]
        if len(value_list) == 3:
            if value_list[0] >= value_list[1]:
                start = value_list[1]
                end   = value_list[0]
            else:
                start = value_list[0]
                end   = value_list[1]
            step = value_list[2]    
            if str(start) == str(end):
                _custom_list.append(start)
            else:
                if step > 0:
                    value_to_add = start
                    while value_to_add < end:
                        _custom_list.append(value_to_add)
                        value_to_add += step
                    _custom_list.append(end)
                else:
                    msg = log("e","Step value must be greater than 0.")
                    raise argparse.ArgumentTypeError(msg)
        else:
            msg = log("e","Too little/many arguments to create a list. USAGE: -c \"0 10 0.8\"")
            raise argparse.ArgumentTypeError(msg)
    else:
        msg = log("e","Incorrect list format given on input.")
        raise argparse.ArgumentTypeError(msg)
    return _custom_list

def arg_list(arg_value):
    ##########################################
    #Define argument type for --sampleTime
    #and --nSamples options
    ##########################################

    _custom_list = []
    if "[" in arg_value and "]" in arg_value:
        #list was provided explicitely
        _custom_list = [str(value) for value in arg_value.replace("[","").replace("]","").split(",")]
    elif "[" not in arg_value and "]" not in arg_value:
        #user requested the same number for each range point
        delimiter = " "
        if "," in arg_value: delimiter = ","
        if ";" in arg_value: delimiter = ";"
        value_list = [float(value) for value in arg_value.split(delimiter)]
        if len(value_list) == 1:
            _custom_list.append(value_list[0])
        else:
            msg = log("e","Incorrect list format given on input.")
            raise argparse.ArgumentTypeError(msg)
    else:
        msg = log("e","Incorrect list format given on input.")
        raise argparse.ArgumentTypeError(msg)
    return _custom_list

def dev_list(arg_value):
    ##########################################
    #Define argument type for --addPort option
    ##########################################

    _custom_list = []
    if "[" in arg_value and "]" in arg_value:
        #list was provided explicitely
        _custom_list = [str(value) for value in arg_value.replace("[","").replace("]","").split(",")]
    elif "[" not in arg_value and "]" not in arg_value:
        #list provided without brackets and divided by comma or space, possibly one argument only
        if len(arg_value.split(",")) > 1:
            _custom_list = arg_value.split(",")
        elif len(arg_value.split(" ")) > 1:   
            _custom_list = arg_value.split(" ")
        else:
            _custom_list.append(arg_value)
    else:
        msg = log("e","Incorrect list format given on input.")
        raise argparse.ArgumentTypeError(msg)    

    return _custom_list

def enviro_list(arg_value):
    #####################################
    #Define argument type for -g option
    #####################################

    _custom_list = []
    if "[" in arg_value and "]" in arg_value:
        #list was provided explicitely
        _custom_list = [str(value) for value in arg_value.replace("[","").replace("]","").split(",")]
    elif "[" not in arg_value and "]" not in arg_value:
        #list provided without brackets and divided by comma or space, possibly one argument only
        if len(arg_value.split(",")) > 1:
            _custom_list = arg_value.split(",")
        elif len(arg_value.split(" ")) > 1:
            _custom_list = arg_value.split(" ")
        else:
            _custom_list.append(arg_value)
    else:
        msg = log("e","Incorrect eviro argument format.")
        raise argparse.ArgumentTypeError(msg)

    if len(_custom_list) < 1:
        msg = log("e","Specify type of enviro measurement (all, temp, humi or lumi).")
        raise argparse.ArgumentTypeError(msg)
    elif len(_custom_list) == 1:
        if str(_custom_list[0]) not in ["all","temp","humi","lumi"]:
            msg = log("e","Allowed values for enviro measurement are \"all, temp, humi or lumi\".")
            raise argparse.ArgumentTypeError(msg)
        #setting defaults
        _custom_list.append(5.0)
        _custom_list.append(10)
    elif len(_custom_list) == 2:
        if str(_custom_list[0]) not in ["all","temp","humi","lumi"]:
            msg = log("e","Allowed values for enviro measurement are \"all, temp, humi or lumi\".")
            raise argparse.ArgumentTypeError(msg)
        if float(_custom_list[1]) < 0.:
            msg = log("e","Time step cannot be negative function.")
            raise argparse.ArgumentTypeError(msg)
        else:
            _custom_list[1] = float(_custom_list[1])   
        #setting defaults
        _custom_list.append(10)
    elif len(_custom_list) == 3:
        if str(_custom_list[0]) not in ["all","temp","humi","lumi"]:
            msg = log("e","Allowed values for enviro measurement are \"all, temp, humi or lumi\".")
            raise argparse.ArgumentTypeError(msg)     
        if float(_custom_list[1]) < 0.:
            msg = log("e","Time step cannot be negative function.")
            raise argparse.ArgumentTypeError(msg)
        else:
            _custom_list[1] = float(_custom_list[1])
        _stepFloat = float(_custom_list[2])
        _stepInt = int(_custom_list[2])
        if abs(_stepFloat-_stepInt) > 0.:
            log("w","Number of steps in enviro measurement cannot be floating. Truncating down.")
            _custom_list[2] = _stepInt
        else:
            _custom_list[2] = _stepInt 
        if _custom_list[2] == -1:
            log("w", "Press CTRL+C to cancel enviro measurement.")

    return _custom_list
 
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    testGroup = parser.add_mutually_exclusive_group()
    measGroup = parser.add_mutually_exclusive_group()
    immGroup =  parser.add_mutually_exclusive_group()

    #add testing options
    testGroup.add_argument('--testPort'           , dest='testPort'           , help='Find available ports and exit measurement.', 	action='store_true',   		default=False )
    testGroup.add_argument('--testMeas'           , dest='testMeas'           , help='Try single IV measurement with +-10V.',           action='store_true',            default=False )
    testGroup.add_argument('--testStatus'         , dest='testStatus'         , help='Show device status.',                             action='store_true',            default=False )

    #add control options
    parser.add_argument('--selectPort'      , dest='selectPort'         , help='Disable automatic port selection.',                       action='store_true',            default=False )
    parser.add_argument('--extVSource'      , dest='extVSource'         , help='Use the secondary device as a VSource.',                  action='store_true',            default=False )
    parser.add_argument('--addPort'         , dest='addPort', type=dev_list, help='Enable additional port to be used as RS232.',          action='store',                 default=[] )
    parser.add_argument('--addSocket'       , dest='addSocket', type=dev_list, help='Enable additional port to be used as Client.',       action='store',                 default=[] )
    parser.add_argument('--expOhm', nargs=1, type=float, dest='expOhm', metavar='expected_resistance', help='Expected resistance order.', action='store',               default=[1e9])
    parser.add_argument('--autoSensing'      , dest='autoSensing'         , help='Enable automatic current sensing when placing probe.',  action='store_true',            default=False )
    parser.add_argument('--autoRange'        , dest='autoRange'           , help='Enable automatic autorange for measured function.',     action='store_true',            default=False )

    #add output options
    parser.add_argument('-v', '--verbosity', action="count", help="Increase output verbosity", default=0)
    parser.add_argument('-o', '--outputFile', dest='outputFile', type=str, help='Output file name.', action='store', default="result" )
    parser.add_argument('-d', '--outputDir', dest='outputDir', type=str, help='Output directory.', action='store', default="results" )
    parser.add_argument('--txt',  dest='outTXT', help='Produce output in txt format.',                 action='store_true', default=False )
    parser.add_argument('--json',  dest='outJSON', help='Produce output in json format.',                 action='store_true', default=False )
    parser.add_argument('--csv',  dest='outCSV', help='Produce output in csv format.',                 action='store_true', default=False )
    parser.add_argument('--xml',  dest='outXML', help='Produce output in xml format.',                 action='store_true', default=False )
    parser.add_argument('--root', dest='outROOT', help='Produce output in root format.',               action='store_true', default=False )
    parser.add_argument('--png',  dest='outPNG', help='Produce output in png format.',                 action='store_true', default=False )
    parser.add_argument('--pdf',  dest='outPDF', help='Produce output in pdf format.',                 action='store_true', default=False )
    parser.add_argument('--db',   dest='isDB', help='Input/Outpur are taken/saved in DB.',             action='store_true', default=False )
    
    #add measurement options
    measGroup.add_argument('--cfg', dest='configFile', help='Define measurement inside of config file.', action='store', default=None)
    measGroup.add_argument('-s','--single', nargs=1, type=float, dest='single', metavar='<bias>' , help='Single IV measurement. USAGE: -s 60.5', action='store', default=None)
    measGroup.add_argument('-m','--multi',      type=range_list, dest='multi' , metavar='<bias_range>'  , help='Multiple point IV measurement. USAGE: -m start end incr OR -c [1,2,3,4]', action='store', default=None)
    measGroup.add_argument('-c','--continuous', type=range_list, dest='continuous', metavar='<bias_range>', help='Continuous IV measurement. USAGE: -c start end incr OR -c [1,2,3,4]', action='store', default=None)
    measGroup.add_argument('-e','--enviro', type=str, dest='enviro', metavar='<enviro>' , help='Enviro readings: all, temp, humi or lumi.', action='store', default=None)
    measGroup.add_argument('-g','--contenv', type=enviro_list, dest='contenv', metavar='<cont_enviro>', help='Continuous Enviro measurement. USAGE: -g <type> [<timeStep> <nSteps>]', action='store', default=None)
    measGroup.add_argument('-w','--standBy', nargs=1, type=float, dest='standBy', metavar='<stand_by_mode>' , help='Stanby mode with motion controller in position. Possible to measure enviro readings.', action='store', default=None)
    parser.add_argument('-r','--repeat', type=int, dest='repeat', metavar='<repeat>', help='Repeat selected measurement for R=1..N. Do nothing for R=0,-1. Repeat endlessly for R=-2. Value ignored if cfg provided.', action='store', default=1)
    parser.add_argument('--sampleTime', type=arg_list, dest='sampleTime', metavar='<sample_time>', help='Sample time for each range point.', action='store', default=[0.50])
    parser.add_argument('--nSamples', type=arg_list, dest='nSamples', metavar='<n_samples>', help='Number of samples for each range point.', action='store', default=[10])
    parser.add_argument('--debug'      , dest='debug'         , help='Bypass several options.',                  action='store_true',            default=False )

    #add immediate one-go functions
    immGroup.add_argument('--term'      , dest='terminate'         , help='Immediately terminate all devices.',                       action='store_true',            default=False )
    immGroup.add_argument('--abort'      , dest='abort'         , help='Immediately abort all devices.',                       action='store_true',            default=False )

    #-------------------
    #Parse user options
    #-------------------
    args = parser.parse_args()
    
    #--------------------
    #Basic sanity checks
    #--------------------
    exe = sys.executable
    exeDir = exe[:exe.rfind("/")]
    args.logname = _logname

    #---------------------------------------------------------
    #Fast probing can be evoked by using 'probeFast' keyword
    #---------------------------------------------------------
    args.probeFast = False
    if "probeFast" in args.addPort:
        args.addPort[args.addPort.index('probeFast')] = 'probe'
        args.probeFast = True

    #!!!!EMG!!!!
    EMG = False
    if args.terminate or args.abort:
        EMG         = True
        doTerminate = args.terminate
        doAbort     = args.abort
        if os.path.exists(exeDir+"/mirror.py"):
            import mirror
            args = mirror.backupNamespace  
        args.terminate  = doTerminate
        args.abort      = doAbort
        args.selectPort = False
        args.testPort   = False
        args.testMeas   = False
        args.testStatus = False
        args.isEnviroOnly = False
        args.isStandByZOnly = False
    else:
        #Create used-config mirror in case of EMG
        mirror = open(exeDir+"/mirror.py", "w")
        mirror.write("import argparse \n")
        mirror.write("backupNamespace = argparse."+str(args))
        mirror.close()
    #!!!!EMG!!!!

    isOut = False
    if (args.outTXT or args.outXML or args.outROOT or args.outJSON or args.outPNG or args.outPDF or args.outCSV) and not EMG:
        isOut = True
    if isOut:
        if args.isDB:
            log("i", "Results will be saved in database.")
        else:
            outDir = exeDir[:exeDir.rfind("/")]+"/results/"+args.outputDir 
            args.outputDir = outDir
            log("i", "Results will be saved locally: "+args.outputDir)
            if (args.outPNG or args.outPDF) and not args.outJSON:
                log("w","JSON output not specified! Result will not be plotted!")
    else:
        if not EMG:
            log("w","Results will NOT be saved.")

    if args.configFile is not None and (args.repeat > 1 or args.repeat == -2):
        if not EMG:
            log("w","Repeat option \'-r\' ignored. Config file is specified.")

    #--------------------------
    #Parse input configuration
    #--------------------------
    if not EMG:
        args.repeat = int(args.repeat)
        sequence = []
        if args.configFile is not None:
            inputParser = InputParser.InputParser(args)
            sequence    = inputParser.load(args.configFile)
        else:
            if args.single is not None:
                for ir in range(1,args.repeat+1):
                    sequence.append({ 
                                       'type'        : "singleIV", 
                                       'bias'        : args.single,
                                       'sampleTime'  : args.sampleTime,
                                       'nSamples'    : args.nSamples
                                   })
            if args.multi is not None:        
                for ir in range(1,args.repeat+1):
                    sequence.append({ 
                                       'type'        : "multiIV",
                                       'bias'        : args.multi,
                                       'sampleTime'  : args.sampleTime,
                                       'nSamples'    : args.nSamples
                                   })
            if args.continuous is not None:   
                for ir in range(1,args.repeat+1):
                    sequence.append({
                                       'type'        : "contIV",
                                       'bias'        : args.continuous,
                                       'sampleTime'  : args.sampleTime,
                                       'nSamples'    : args.nSamples
                                   })
            if args.enviro is not None:
                for ir in range(1,args.repeat+1):
                    sequence.append({
                                       'type'        : "singleENV",
                                       'subtype'     : str(args.enviro),
                                   }) 
            if args.contenv is not None:
                for ir in range(1,args.repeat+1):
                    sequence.append({
                                       'type'        : "contENV",
                                       'subtype'     : str(args.contenv[0]),
                                       'timeStep'    : float(args.contenv[1]),
                                       'nSteps'      : int(args.contenv[2])
                                   }) 
            if args.standBy is not None:
                for ir in range(1,args.repeat+1):
                    sequence.append({ 
                                       'type'        : "standbyZ", 
                                       'waitingTime' : args.standBy[0]
                                   })
 
        if len(sequence) == 0 and not args.testPort and not args.testMeas and not args.testStatus:
            log("i","No measurement tool was selected. Please select measurement inline (-s | -m | -c | -e | -g).")
            log("i","Alternatively pass configuration file using --cfg <config_file>.")
            sys.exit(0)
        for seq in sequence:
            for varToCheck in ['sampleTime','nSamples']:
                if 'bias' in seq.keys() and len(seq['bias']) > len(seq[varToCheck]): 
                    if len(seq[varToCheck]) == 1:
                        seq[varToCheck] = [seq[varToCheck][0]]*len(seq['bias'])
                    else:
                        log("e","Option --"+varToCheck+" has to be specified for each range point.")
                        sys.exit(0)
                elif 'bias' in seq and len(seq['bias']) < len(seq[varToCheck]):
                        log("e","Option --"+varToCheck+" is specified for more range points than given.")
                        sys.exit(0)
            if 'subtype' in seq and seq['subtype'] not in ["all","temp","humi","lumi"]:
                log("e","Unknown environmental reading requested.")
                sys.exit(0)  
            if seq['type'] == "contENV":
                if 'timeStep' in seq and seq['timeStep'] <= 0:
                    log("e","Time step for enviro measurement must be positive number.")
                    sys.exit(0)
            if seq['type'] == "contIV" and 'waitingTime' in seq.keys():
                if 'bias' in seq.keys() and (len(seq['bias']) > 1 or len(seq['bias']) < 1):
                    log("e", "Precisely one bias point is required for IV stand by mode.")
                    sys.exit(0)   
 
        #---------------------------------------
        #Do not initialize all devices if only
        #enviro readings are invoked
        #---------------------------------------
        _isEnviroOnly = False
        if len(sequence) == 1 and "ENV" in sequence[0]['type']:
            _isEnviroOnly = True
        args.isEnviroOnly = _isEnviroOnly

        #----------------------------------------------
        #Do not initialize measurement device if only
        #standByZ mode is requested
        #----------------------------------------------
        _isStandByZOnly = False
        if len(sequence) == 1 and "standbyZ" in sequence[0]['type']:
            _isStandByZOnly = True
        args.isStandByZOnly = _isStandByZOnly

        #-----------------------------------------------
        #Source can be specified also as port directly 
        #-----------------------------------------------
        if "source" in args.addPort: 
            args.extVSource = True

    #---------------------------------------
    #Initialize connector and device classes
    #---------------------------------------
    connectorSerial = SerialConnector.SerialConnector(args)
    connectorSocket = SocketConnector.SocketConnector(args)
    dev             = Device.Device(args)

    #-------------------------
    #1: PORT AVAILABILITY TEST
    #-------------------------
    if args.testPort:
        if not args.selectPort: 
            args.selectPort = True #DISABLE AUTO PORT
        if not args.extVSource: 
            args.extVSource = True #ENABLE USING EXT V SOURCE 
        log("i","Testing port availability:")
        connectorSerial.test_RS232()
        sys.exit(0)
   

    #---------------------------------------------
    #Port-to-Device selection loop
    #---------------------------------------------
    doRetry = False
    if not args.selectPort:
        doRetry = True
    if not doRetry:    
        #----------------------------------------------------------------
        #Detect RS232 ports, setup and open connections stored under COMS
        #----------------------------------------------------------------
        if not args.isEnviroOnly:
            COMS = connectorSerial.connect_RS232()
        else: 
            COMS = {} 

        #--------------------------------------------------
        #Detect hosts and ports allowing socket interchange
        #--------------------------------------------------
        SOCKETS = connectorSocket.gateway()

        #-----------------------------------------------------------------
        #Crosscheck device response and load device routines from library.
        #From now you can use dev.singleIV(30) and correct devices will be
        #selected.
        #-----------------------------------------------------------------
        try:
            if not args.isEnviroOnly:
                dev.load(COMS,SOCKETS,EMG)                   
            else:
                if len(args.addPort) == 0:
                    dev.load_socket(SOCKETS,EMG)
                else:
                    _COMS = {}
                    for dev_type in args.addPort:
                        _COMS[dev_type] = COMS[dev_type]
                    COMS = _COMS
                    dev.load(COMS,SOCKETS,EMG)  
        except KeyboardInterrupt:
            log("w","Keyboard interruption during device loading detected.")
            sys.exit(0)
    elif doRetry and not args.isEnviroOnly:
        allMatched = False
        SOCKETS = connectorSocket.gateway()
        failedAttempts = {}
        goodAttempts = {}
        goodCOMS = {}
        iAttempt = 0
        while not allMatched:
            COMS = connectorSerial.connect_RS232(failedAttempts,goodAttempts,goodCOMS)
            log("i","Use CTRL+C to cancel automatic selecion.")

            #Keyboard exception is controlled internally
            attempt = dev.load(COMS,SOCKETS,EMG,iAttempt)
            if "success" in attempt.keys():
                allMatched = True
            else:
                for key in attempt.keys():
                    _port,valid = attempt[key]
                    if valid == 0:
                        if key not in failedAttempts.keys():
                            failedAttempts[key] = []
                            failedAttempts[key].append(_port)
                        else:
                            failedAttempts[key].append(_port)
                    elif valid == 1:
                            goodAttempts[key] = _port
                            goodCOMS[key] = COMS[key]

            iAttempt += 1 

    elif doRetry and args.isEnviroOnly:
        #ignore other devices as meas or source 

        if len(args.addPort) == 0: 
            #only sockets
            SOCKETS = connectorSocket.gateway()
            try:
                dev.load_socket(SOCKETS,EMG)
            except KeyboardInterrupt:
                log("w","Keyboard interruption during device loading detected.")
                sys.exit(0)
        elif len(args.addSocket) == 0:
            #only ports
            COMS = {}
            allMatched = False
            failedAttempts = {}
            goodAttempts = {}
            goodCOMS = {} 
            while not allMatched:
                _COMS = connectorSerial.connect_RS232(failedAttempts,goodAttempts,goodCOMS)
                for dev_type in args.addPort:
                    COMS[dev_type] = _COMS[dev_type]
                log("i","Use CTRL+C to cancel automatic selecion.")

                #Keyboard exception is controlled internally
                attempt = dev.load_serial(COMS, EMG) 
                if "success" in attempt.keys():
                    allMatched = True
                else:
                    for key in attempt.keys():
                        _port,valid = attempt[key]
                        if valid == 0:
                            if key not in failedAttempts.keys():
                                failedAttempts[key] = []
                                failedAttempts[key].append(_port)
                            else:
                                failedAttempts[key].append(_port)
                        elif valid == 1:
                                goodAttempts[key] = _port
                                goodCOMS[key] = _COMS[key] 

    #-----------------------------------------------------------------
    #Raise argument invoked emergency functions here
    #-----------------------------------------------------------------
    if args.terminate: 
        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
            dev.terminate()
    if args.abort:
        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):     
            dev.abort()
            dev.terminate()

    #------------------------------------
    #Output Handler
    #------------------------------------
    if isOut:
        outputHandler = OutputHandler.OutputHandler(args)

    #-------------------------
    #All device test status
    #-------------------------
    if args.testStatus:
        try:
            status = dev.status()
            for dev_type in status.keys():
                log("i","Intrinsic status for "+dev_type+": "+str(status[dev_type]))
            if len(sequence) == 0:
                sys.exit(0)
        except KeyboardInterrupt:
            log("w","Keyboard interruption during status reading detected!")
            sys.exit(0)    

    #-----------------------------------------------------------------
    #Provide standalone enviro measurement here if only one
    #-----------------------------------------------------------------
    if args.isEnviroOnly:
        if "single" in sequence[0]['type']:
            try:
                _result = dev.singleENV(str(sequence[0]['subtype']),isLast=True,isFirst=True)
                dev.finalize()
                if isOut: 
                    _results = { 'type' : sequence[0]['type'], 'data' : [], 'enviro' : [] }
                    _results['enviro'].append(_result) 
                    outputHandler.load(0,_results)    
                    outputHandler.save()
            except KeyboardInterrupt:
                with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                    log("w","Keyboard interruption during standalone enviro measurement detected!")
                    dev.abort()
                    dev.terminate()
        elif "cont" in sequence[0]['type']:
            #Keyboard interruption handled internally
            _result = dev.contENV(str(sequence[0]['subtype']),sequence[0]['timeStep'],sequence[0]['nSteps'],isLast=True,isFirst=True)
            dev.finalize()
            if isOut:
                _results = { 'type' : sequence[0]['type'], 'data' : [], 'enviro' : [] }
                _results['enviro'] = _result
                outputHandler.load(0,_results)
                outputHandler.save() 
        sys.exit(0)

    #-----------------------------------------------------------------
    #Initialize current sensing until connection is achieved
    #-----------------------------------------------------------------
    try:
        if args.autoSensing:
            if not args.isStandByZOnly:
                biasRingConnected = dev.sense(connectTimeError=60) #connectTimeError has to be greater than 0
            else:
                biasRingConnected = dev.senseExternal(connectTimeError=60)    
        else:
            if not args.isStandByZOnly:
                biasRingConnected = dev.sense(connectTimeError=0)
            else:
                biasRingConnected = dev.senseExternal(connectTimeError=0)  
    except KeyboardInterrupt:
        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname): 
            log("w","Keyboard interruption during sensing mode detected.")
            dev.abort()
            dev.terminate()
    if not biasRingConnected:
        sys.exit(0)

    #-----------------------------------------------------------------
    #Check initial environment conditions and closed box
    #-----------------------------------------------------------------
    try:
        boxReady = dev.box()
    except KeyboardInterrupt:
        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
            log("w","Keyboard interruption during box crosscheck detected.")
            dev.terminate()
    if not boxReady:
        sys.exit(0)

    #--------------------------
    #3: SINGLE MEASUREMENT TEST
    #--------------------------
    if args.testMeas:
        for test_volt in [-10,10]:
            current_test, bias_test, enviro_test = dev.singleIV(test_volt)
            if int(bias_test) == test_volt:
                if float(current_test) != 0.0:
                    log("i","Single test with voltage bias = "+str(bias_test)+" returned "+str(current_test)+".")
                    if len(enviro_test) == 5:
                        log("i","T1="+str(enviro_test['temp1'])+" degrees C.")
                        log("i","T2="+str(enviro_test['temp2'])+" degrees C.")
                        log("i","T3="+str(enviro_test['temp3'])+" degrees C.")
                        log("i","H="+str(enviro_test['humi'])+"%")
                        log("i","L="+str(enviro_test['lumi']))
                        log("i","Single test was successful.")
                    else:
                        log("w","Single test failed! Enviro measurement failed.")
                else:
                    log("w","Single test with voltage bias = "+str(bias_test)+" returned "+str(current_test)+".")
                    if len(enviro_test) == 5:
                        log("i","T1="+str(enviro_test['temp1'])+" degrees C.")
                        log("i","T2="+str(enviro_test['temp2'])+" degrees C.")
                        log("i","T3="+str(enviro_test['temp3'])+" degrees C.")
                        log("i","H="+str(enviro_test['humi'])+"%")
                        log("i","L="+str(enviro_test['lumi']))
                    else:
                        log("w","Enviro measurement failed.")
                    log("w","Single test failed! Returned current is exactly zero.")
            else:    
                log("w","Single test with voltage bias = "+str(bias_test)+" returned "+str(current_test)+".")
                log("w","Single test failed! High-voltage source cannot reach "+str(test_volt)+" bias.")
        log("i","Single test done. Terminating...")
        sys.exit(0)

    #-------------------------
    #       MANUAL MODE
    #-------------------------
    if len(sequence) == 0:
        log("i","No measurement tool was selected. Please select measurement inline (-s | -m | -c).")
        log("i","Alternatively pass configuration file using --cfg <config_file>.")
        sys.exit(0)
    for iseq,seq in enumerate(sequence):
        def isIV():
            subsequence = sequence[iseq:]
            for subseq in subsequence:
                if "singleIV" in subseq['type'] or "contIV" in subseq['type']:
                    return True
            return False
        isLast = (iseq == len(sequence)-1 or not isIV())
        isFirst = (iseq == 0) 
        if 'singleIV' in seq['type']:
            _results = { 'type' : seq['type'], 'data' : [], 'enviro' : []}
            if 'bias' in seq and abs(seq['bias'][0]) > 0.:
                try:
                    current, bias, enviro = dev.singleIV(biasPoint=seq['bias'][0],sampleTime=seq['sampleTime'][0],nSamples=seq['nSamples'][0],isLast=isLast,isFirst=isFirst)
                except KeyboardInterrupt:
                    with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                        log("w","Keyboard interruption during single measurement detected!")
                        dev.abort()
                        dev.terminate()
                if bias != None:
                    _results['data'].append((current,bias))
                    _results['enviro'].append(enviro)
                    if isOut:
                        outputHandler.load(iseq,_results)    
                    if args.verbosity > 1:
                        log("i","#"+str(iseq)+" RESULT SINGLE: ")
                        log("i","Bias: "+str(bias)+"V, Current: "+str(current)+"A")
                        log("i","T="+str(enviro['temp1'])+" degrees C.")
                        log("i","H="+str(enviro['humi'])+"%")
                        log("i","L="+str(enviro['lumi']))
                else:
                    log("f","Measurement failed but should not reach this point.")
            else:
                log("i","Bias voltage = 0 V. Doing nothing...")
        elif 'contIV' in seq['type']:
            if  'bias' in seq:
                if 'waitingTime' in seq.keys() and int(seq['waitingTime']) != 0:
                    try:
                        _results = dev.standbyIV(biasPoint=seq['bias'][0],sampleTime=seq['sampleTime'][0],nSamples=seq['nSamples'][0],waitingTime=seq['waitingTime'],isLast=isLast,isFirst=isFirst)
                    except KeyboardInterrupt:
                        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                            log("w","Keyboard interruption during standby continuous measurement detected!")
                            dev.abort()
                            dev.terminate()
                elif 'waitingTime' not in seq.keys() or ('waitingTime' in seq.keys() and int(seq['waitingTime']) == 0):
                    try:
                        _results = dev.continuousIV(biasRange=seq['bias'],sampleTime=seq['sampleTime'],nSamples=seq['nSamples'],isLast=isLast,isFirst=isFirst)
                    except KeyboardInterrupt:
                        with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                            log("w","Keyboard interruption during continuous measurement detected!")
                            dev.abort()
                            dev.terminate()
                if len(_results['data']) > 0:
                    log("i","#"+str(iseq)+" RESULTS CONTINUOUS:")
                    log("i","-----------------")
                    if isOut:
                        _results['type'] = seq['type']
                        outputHandler.load(iseq,_results)
                    for imeas, (current, bias) in enumerate(_results['data']):
                        if current is None or bias is None:
                            log("f","Measurement failed but should not reach this point.")
                        else:
                            log("i","Bias: "+str(bias)+"V, Current: "+str(current)+"A")
                            log("i","T="+str(_results['enviro'][imeas]['temp1'])+" degrees C.")
                            log("i","H="+str(_results['enviro'][imeas]['humi'])+"%")
                            log("i","L="+str(_results['enviro'][imeas]['lumi']))
                            log("i","-----------------")
                else:
                    log("f","Measurement failed but should not reach this point.")
            else:
                log("e","Bias range not defined!")

        elif 'multiIV' in seq['type']:
            if  'bias' in seq:
                try:
                    _results = dev.multiIV(biasRange=seq['bias'],sampleTime=seq['sampleTime'],nSamples=seq['nSamples'],isLast=isLast,isFirst=isFirst)
                except KeyboardInterrupt:
                    with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                        log("w","Keyboard interruption during multi measurement detected!")
                        dev.abort()
                        dev.terminate()
                if len(_results['data']) > 0:
                    log("i","#"+str(irep)+" RESULTS MULTIPLE POINT:")
                    log("i","-----------------")
                    if isOut:
                        _results['type'] = seq['type']
                        outputHandler.load(iseq,_results)
                    for imeas, (current, bias) in enumerate(_results['data']):
                        if current is None or bias is None:
                            log("f","Measurement failed but should not reach this point.")
                        else:
                            log("i","Bias: "+str(bias)+"V, Current: "+str(current)+"A")
                            log("i","T="+str(_results['enviro'][imeas]['temp1'])+" degrees C.")
                            log("i","H="+str(_results['enviro'][imeas]['humi'])+"%")
                            log("i","L="+str(_results['enviro'][imeas]['lumi']))
                            log("i","-----------------")
                else:
                    log("f","Measurement failed but should not reach this point.")
            else:
                log("e","Bias range not defined!")

        elif 'singleENV' in seq['type']:
            _results = { 'type' : seq['type'], 'data' : [], 'enviro' : [] } 
            if 'subtype' in seq:
                try:
                    _results['enviro'].append( dev.singleENV(str(seq['subtype'],isLast=isLast,isFirst=isFirst)) )
                except KeyboardInterrupt:
                    with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                        log("w","Keyboard interruption during standalone enviro measurement detected!")
                        dev.abort()
                        dev.terminate()
                if len(_results['enviro']) > 0:
                    if isOut:
                        _results['type'] = seq['type']
                        outputHandler.load(iseq,_results)
            else:
                log("e","Environmental measurement not defined!")

        elif 'standbyZ' in seq['type']: 
            _results = { 'type' : seq['type'], 'data' : [], 'enviro' : [] }
            try:
                _results['enviro'] = dev.standbyZ(waitingTime=int(seq['waitingTime']),isLast=isLast,isFirst=isFirst) 
            except KeyboardInterrupt:
                with warden.DelayedKeyboardInterrupt(force=False, logfile=args.logname):
                    log("w","Keyboard interruption during standby mode detected! Results will not be saved!") 
                    dev.abort()
                    dev.terminate()
            if len(_results['enviro']) > 0:
                if isOut:
                    outputHandler.load(iseq,_results)
            

    #-------------------------------------
    #Finalize devices after full sequence
    #-------------------------------------
    dev.finalize()

    #------------------
    #Save output localy
    #------------------
    if isOut:
        outputHandler.save()

    #------------------
    #Store output in DB
    #------------------
    if isOut and args.isDB:
        outputHandler.store()


