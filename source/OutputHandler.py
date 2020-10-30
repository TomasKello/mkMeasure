#!/usr/bin/env python

import os, sys
import datetime
import json
import ColorLogger

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("OutputHandler:   ")
    return clogger.log(log_type,text)

class OutputHandler:
    def __init__(self,args):
        self.args = args
        self.txtBuffer  = []
        self.jsonBuffer = {}
        self.__createArchitecture__()

    def _date(self):
        _date = datetime.datetime.now()
        month = str(_date.month)
        day = str(_date.day)
        if len(str(_date.month)) == 1: month = "0"+str(_date.month)
        if len(str(_date.day)) == 1: day = "0"+str(_date.day)
        return str(_date.year)+month+day

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
        lines.append(empty)
        lines.append(mtype)
        lines.append(header)
        for idata,data in enumerate(results['data']): 
            lines.append(self._toLine(data[1],data[0],
                                      results['enviro'][idata]['temp1'],
                                      results['enviro'][idata]['temp2'],
                                      results['enviro'][idata]['temp3'],
                                      results['enviro'][idata]['humi'],
                                      results['enviro'][idata]['lumi']
                                     ))
        return lines    

    def __formatJSON__(self,irep,results):
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
        
        return _data
    
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

    def __saveTXT__(self):
        txt_file_name = self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".txt")
        with open(txt_file_name, "a") as txt_file:
            for line in self.txtBuffer:
                txt_file.write("%s" % line)
        self.txtBuffer = []        

    def __saveJSON__(self):
        json_file_name = self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".json")
        with open(json_file_name, 'w') as json_file:
            json.dump(self.jsonBuffer, json_file)
        self.jsonBuffer = {}  
        
    def store(self):
        if self.args.isDB:
            log("i","File: "+str(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".txt")+" --> DB")

    def load(self,irep,results):
        if self.args.outTXT:
            self.__loadTXT__(self.__formatTXT__(irep,results))
        if self.args.outJSON:
            self.__loadJSON__(self.__formatJSON__(irep,results))

    def save(self):
        if self.args.outTXT:
            self.__saveTXT__()
        if self.args.outJSON:
            self.__saveJSON__()

