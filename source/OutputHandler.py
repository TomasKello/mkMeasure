#!/usr/bin/env python

import os, sys
import datetime
import json
import csv
import ColorLogger

class OutputHandler:
    ##################################
    #Handling all measurement results
    ##################################
    def __init__(self,args):
        self.args = args
        self.txtBuffer  = []
        self.jsonBuffer = {}
        self.csvBuffer = [] 
        self.clogger = ColorLogger.ColorLogger("OutputHandler:   ",self.args.logname)
        self.__createArchitecture__()

    def log(self,log_type="i",text=""):
        return self.clogger.log(log_type,text)

    def _date(self):
        _date = datetime.datetime.now()
        month = str(_date.month)
        day = str(_date.day)
        if len(str(_date.month)) == 1: month = "0"+str(_date.month)
        if len(str(_date.day)) == 1: day = "0"+str(_date.day)
        return str(_date.year)+month+day

    def _time(self):
        _time = datetime.datetime.now()
        hour = str(_time.hour)
        minute = str(_time.minute)
        second = str(_time.second) 
        if len(hour) == 1: hour = "0"+hour
        if len(minute) == 1: minute = "0"+minute
        if len(second) == 1: second = "0"+second

        return hour+minute+second

    def _uniqueName(self,filename):
        _uniqueName = ""
        if os.path.exists(filename):
            notUnique = True
            num = 0
            while notUnique:
                _filename = filename.split(".")[0]+"_"+str(num)+"."+filename.split(".")[1]
                if os.path.exists(_filename):
                    num += 1
                else:
                    notUnique = False
                    _uniqueName = _filename
        else:
            _uniqueName = filename

        return _uniqueName    

    def _toLine(self,*argv):
        line  = ""
        space = " "*5
        for word in argv:
            line += str(word)+space
        line += "\n"    
        return line

    def _toPattern(self,arg=""):
        pattern = "**********"
        return pattern+str(arg)+pattern+"\n"

    def __createArchitecture__(self):
        if not os.path.isdir(self.args.outputDir[:self.args.outputDir.rfind("/")]):
            os.mkdir(self.args.outputDir[:self.args.outputDir.rfind("/")])
        if not os.path.isdir(self.args.outputDir):
            os.mkdir(self.args.outputDir)    

    def __formatTXT__(self,irep,results):
        #######################################
        #Raw data are returned in plain format
        #######################################
        master_header = []
        empty  = "\n"
        if not os.path.exists(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".txt"):
            master_header.append(self._date()+empty)
            master_header.append(self.args.outputFile+empty)
        lines  = [line for line in master_header]
        mtype  = self._toPattern("#"+str(irep)+" "+results['type'])
        header = ""
        if "IV" in mtype:
            header = self._toLine("Bias [V]","Current [A]","TEMP1 [C]","TEMP2 [C]","TEMP3 [C]","HUMI [%]","LUMI")
        if "ENV" in mtype:
            header = self._toLine("TIME [h-m-s]","TEMP1 [C]","TEMP2 [C]","TEMP3 [C]","HUMI [%]","LUMI")
        lines.append(empty)
        lines.append(mtype)
        lines.append(header)
        if "IV" in mtype:  
            for idata,data in enumerate(results['data']): 
                lines.append(self._toLine(data[1],data[0],
                                          results['enviro'][idata]['temp1'],
                                          results['enviro'][idata]['temp2'],
                                          results['enviro'][idata]['temp3'],
                                          results['enviro'][idata]['humi'],
                                          results['enviro'][idata]['lumi']
                                         ))
        if "ENV" in mtype:
            for data in results['enviro']:
                lines.append(self._toLine(str(data['hour'])+"-"+str(data['minute'])+"-"+str(data['second']),
                                          data['temp1'],
                                          data['temp2'],
                                          data['temp3'],
                                          data['humi'],
                                          data['lumi']
                            ))
        return lines    

    def __formatJSON__(self,irep,results):
        ###############################################
        #Return data in json way (python dict)
        #Raw data are returned
        ###############################################
        _data = {}
        if "IV" in results['type']:
            _data = { 'type' : results['type'],
                      'irep' : irep, 
                      'bias' : [data[1] for data in results['data']],
                      'curr' : [data[0] for data in results['data']],
                      'tmp1' : [env['temp1'] for env in results['enviro']],
                      'tmp2' : [env['temp2'] for env in results['enviro']],
                      'tmp3' : [env['temp3'] for env in results['enviro']],
                      'humi' : [env['humi'] for env in results['enviro']],
                      'lumi' : [env['lumi'] for env in results['enviro']]
                    }
        if "ENV" in results['type']:
            _data = { 'type' : results['type'],
                      'irep' : irep,
                      'hour' : [env['hour'] for env in results['enviro']],
                      'minute' : [env['minute'] for env in results['enviro']],
                      'second' : [env['second'] for env in results['enviro']],
                      'tmp1' : [env['temp1'] for env in results['enviro']],
                      'tmp2' : [env['temp2'] for env in results['enviro']],
                      'tmp3' : [env['temp3'] for env in results['enviro']],
                      'humi' : [env['humi'] for env in results['enviro']],
                      'lumi' : [env['lumi'] for env in results['enviro']]
                    }  
        
        return _data

    def __formatCSV__(self,irep,results):
        ####################################################################
        #Return lines as rows represented as lists with column elements
        #Current is made positive in case that negative voltage was applied
        #and transformed from A to nA 
        ####################################################################
        _lines = []

        _generalInfo = []
        _generalInfo.append(["CR operator","Unknown"])
        _generalInfo.append(["RM operator","Unknown"])
        _generalInfo.append(["Date",str(self._date())])
        _generalInfo.append(["Time",str(self._time())])
        _generalInfo.append(["Serial Number","Unknown"])
        _generalInfo.append(["Construction Step","Unknown"])
        _generalInfo.append(["Measurement Number",str(irep)])
        _generalInfo.append(["Measurement Type",str(results['type'])])
        _generalInfo.append(["Note","None"])   
        _generalInfo.append([" "])

        _data = []
        if "IV" in results['type']:
            _data.append(["Bias [V]","Current [nA]","TEMP1 [C]","TEMP2 [C]","TEMP3 [C]","HUMI [%]","LUMI"])
            corrFactor = 1.0
            if float(results['data'][0][0]) < 0.0: 
                corrFactor = -1.0        
            unitFactor = 1e9  
            for idata, data in enumerate(results['data']):
                _data.append([str(data[1]),
                              str(data[0]*corrFactor*unitFactor),
                              str(results['enviro'][idata]['temp1']),
                              str(results['enviro'][idata]['temp2']),
                              str(results['enviro'][idata]['temp3']),
                              str(results['enviro'][idata]['humi']),
                              str(results['enviro'][idata]['lumi'])
                            ])
        if "ENV" in results['type']:
            _data.append(["TIME [h-m-s]","TEMP1 [C]","TEMP2 [C]","TEMP3 [C]","HUMI [%]","LUMI [lx]"])
            for data in results['enviro']:
                _data.append([str(data['hour'])+"-"+str(data['minute'])+"-"+str(data['second']),
                              str(data['temp1']),
                              str(data['temp2']),
                              str(data['temp3']),
                              str(data['humi']),
                              str(data['lumi'])
                            ])
        _lines = _generalInfo+_data+[" "]

        return _lines 

    def __loadTXT__(self,lines):
        for line in lines:
            self.txtBuffer.append(line)

    def __loadJSON__(self,data):        
        if "type" in data.keys(): 
            if data['type'] in self.jsonBuffer.keys():
                self.jsonBuffer[data['type']].append(data)
            else:
                self.jsonBuffer[data['type']] = []
                self.jsonBuffer[data['type']].append(data)

    def __loadCSV__(self,lines):
        for line in lines:
            self.csvBuffer.append(line)

    def __saveTXT__(self):
        txt_file_name = self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".txt")
        with open(txt_file_name, "a") as txt_file:
            for line in self.txtBuffer:
                txt_file.write("%s" % line)
        self.log("i","Saving file: "+txt_file_name)
        self.txtBuffer = []        

    def __saveJSON__(self):
        json_file_name = self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".json")
        with open(json_file_name, 'w') as json_file:
            json.dump(self.jsonBuffer, json_file)
        self.log("i","Saving file: "+json_file_name)
        self.jsonBuffer = {}  

    def __saveCSV__(self):
        csv_file_name = self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".csv")
        with open(csv_file_name, 'w') as csvfile:
            csvwriter = csv.writer(csvfile, delimiter=',')
            for row in self.csvBuffer:
                csvwriter.writerow(row)
        self.log("i","Saving file: "+csv_file_name)
        self.csvBuffer = [] 
        
    def store(self):
        if self.args.isDB:
            self.log("i","File: "+str(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".txt")+" --> DB")

    def load(self,irep,results):
        if self.args.outTXT:
            self.__loadTXT__(self.__formatTXT__(irep,results))
        if self.args.outJSON:
            self.__loadJSON__(self.__formatJSON__(irep,results))
        if self.args.outCSV:
            self.__loadCSV__(self.__formatCSV__(irep,results))

    def save(self):
        if self.args.outTXT:
            self.__saveTXT__()
        if self.args.outJSON:
            self.__saveJSON__()
        if self.args.outCSV:
            self.__saveCSV__()

