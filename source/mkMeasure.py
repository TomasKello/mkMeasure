import argparse
import os
import sys
import serial
import glob
import time
import ColorLogger
import DelayedKeyboardInterrupt as warden
import SerialConnector
import SocketConnector
import Device
import OutputHandler
import InputParser

#constants
delim = '\n'

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("mkMeasure:       ")
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

    #add output options
    parser.add_argument('-v', '--verbosity', action="count", help="Increase output verbosity", default=0)
    parser.add_argument('-o', '--outputFile', dest='outputFile', type=str, help='Output file name.', action='store', default="result" )
    parser.add_argument('-d', '--outputDir', dest='outputDir', type=str, help='Output directory.', action='store', default="results" )
    parser.add_argument('--txt',  dest='outTXT', help='Produce output in txt format.',                 action='store_true', default=False )
    parser.add_argument('--json',  dest='outJSON', help='Produce output in json format.',                 action='store_true', default=False )
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
    parser.add_argument('-r','--repeat', type=int, dest='repeat', metavar='<repeat>', help='Repeat selected measurement. Ignore for cfg.', action='store', default=1)
    parser.add_argument('--sampleTime', type=arg_list, dest='sampleTime', metavar='<sample_time>', help='Sample time for each range point.', action='store', default=[0.50])
    parser.add_argument('--nSamples', type=arg_list, dest='nSamples', metavar='<n_samples>', help='Number of samples for each range point.', action='store', default=[5])
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
    else:
        #Create used-config mirror in case of EMG
        mirror = open(exeDir+"/mirror.py", "w")
        mirror.write("import argparse \n")
        mirror.write("backupNamespace = argparse."+str(args))
        mirror.close()
    #!!!!EMG!!!!

    isOut = False
    if (args.outTXT or args.outXML or args.outROOT or args.outPNG or args.outPDF) and not EMG:
        isOut = True
    if isOut:
        if args.isDB:
            log("i", "Results will be saved in database.")
        else:
            outDir = exeDir[:exeDir.rfind("/")]+"/results/"+args.outputDir 
            args.outputDir = outDir
            log("i", "Results will be saved locally: "+args.outputDir)
    else:
        if not EMG:
            log("w","Results will NOT be saved.")

    if args.configFile is not None and args.repeat > 1:
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
                    print(args.continuous)
                    sequence.append({
                                       'type'        : "contIV",
                                       'bias'        : args.continuous,
                                       'sampleTime'  : args.sampleTime,
                                       'nSamples'    : args.nSamples
                                   })
        if len(sequence) == 0 and not args.testPort and not args.testMeas:
            log("i","No measurement tool was selected. Please select measurement inline (-s | -m | -c).")
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
        COMS = connectorSerial.connect_RS232()

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
            dev.load(COMS,SOCKETS,EMG) 
        except KeyboardInterrupt:
            log("w","Keyboard interruption during device loading detected.")
            sys.exit(0)
    else:
        allMatched = False
        SOCKETS = connectorSocket.gateway()
        failedAttempts = {}
        goodAttempts = {}
        while not allMatched:
            COMS = connectorSerial.connect_RS232(failedAttempts,goodAttempts)
            log("i","Use CTRL+C to cancel automatic selecion.")

            #Keyboard exception is controlled internally
            attempt = dev.load(COMS,SOCKETS,EMG)
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

    #-----------------------------------------------------------------
    #Raise argument invoked emergency functions here
    #-----------------------------------------------------------------
    if args.terminate: 
        with warden.DelayedKeyboardInterrupt(force=False):
            dev.terminate()
    if args.abort:
        with warden.DelayedKeyboardInterrupt(force=False):     
            dev.abort()
            dev.terminate()

    #-----------------------------------------------------------------
    #Initialize current sensing until connection is achieved
    #-----------------------------------------------------------------
    try:
        if args.autoSensing:
            biasRingConnected = dev.sense(connectTimeError=60) #connectTimeError has to be greater than 0
        else:
            biasRingConnected = dev.sense(connectTimeError=0)
    except KeyboardInterrupt:
        log("w","Keyboard interruption during sensing mode detected.")
        with warden.DelayedKeyboardInterrupt(force=False): 
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
        log("w","Keyboard interruption during box crosscheck detected.")
        with warden.DelayedKeyboardInterrupt(force=False):
            dev.terminate()
    if not boxReady:
        sys.exit(0)

    #--------------------------
    #2: SINGLE MEASUREMENT TEST
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
    #3: ALL DEVICE TEST STATUS
    #-------------------------
    #TODO

    #------------------------------------
    #Output Handler
    #------------------------------------
    if isOut:
        outputHandler = OutputHandler.OutputHandler(args)

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
                    log("w","Keyboard interruption during single measurement detected!")
                    with warden.DelayedKeyboardInterrupt(force=False):
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
                try:
                    _results = dev.continuousIV(biasRange=seq['bias'],sampleTime=seq['sampleTime'],nSamples=seq['nSamples'],isLast=isLast,isFirst=isFirst)
                except KeyboardInterrupt:
                    log("w","Keyboard interruption during continuous measurement detected!")
                    with warden.DelayedKeyboardInterrupt(force=False):
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
                    log("w","Keyboard interruption during multi measurement detected!")
                    with warden.DelayedKeyboardInterrupt(force=False):
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

    #-------------------------------------
    #Finalize devices after full sequence
    #-------------------------------------
    dev.finalize()

    #------------------
    #Save output localy
    #------------------
    outputHandler.save()

    #------------------
    #Store output in DB
    #------------------
    if isOut and args.isDB:
        outputHandler.store()


