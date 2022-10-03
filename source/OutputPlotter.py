#!/usr/bin/env python

import os, sys
import importlib
import shutil
import datetime
import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import ColorLogger

class OutputPlotter:
    ##################################
    # Class version of plotting macro
    ##################################
    def __init__(self, args):
        self.args = args
        self.jsonFile = None
        self.cfgFile  = None        
        self.plotPNG = self.args.outPNG
        self.plotPDF = self.args.outPDF
        self.safeToPlot = True
        self.show = False
        self.clogger = ColorLogger.ColorLogger("OutputPlotter:   ",self.args.logname)

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

    def __defaultConfig__(self):
        cfg = """##########################
#Plots
##########################
plots = {}
plots['default'] = { 'legendName' : r'defaultName',
                    'input'        : "<JSON_FILE>",
                    'xRange'       : [0,800],
                    'yAxis'        : 1, #allowed values 1=left, 2=right
                    'color'        : "Green",
                    'lineStyle'    : 1000,
                    'lineWidth'    : 2,
                    'markerStyle'  : "o",
                    'markerSize'   : 35,
                    'order'        : 1,
                    'internalOrder': 0
                }
##########################
#Plot groups
##########################
groups = {}
groups['defaultGroup'] = {
                            'title'         : r'defaultGroupName',
                            'titleSize'     : 25,
                            'legendPosition': "top",
                            'legendColumns' : 1,
                            'legendFontSize': 14,
                            'xAxisTitle'    : r'Bias [V]',
                            'xAxisTitleSize': 14,
                            'xRangeUser'    : [0,850],
                            'y1AxisTitle'   : r'Current [nA]',
                            'y1AxisTitleSize': 14,
                            'scaleY1'       : 1e9, #A to nA conversion
                            'logy'          : False,
                            'logyMin'       : 1.1,
                            'plots'         : plots,
                            'type'          : "contIV",
                            'plotPositive'  : False
                            }
    
###########################
#General
###########################
general = {
    'canvasSize' : [6.0,5.5]
}
        """
        return cfg

    def __createConfig__(self,jsonFile):
        cfgFile = jsonFile[:-5]+"_cfg.py"
        with open(cfgFile,"w") as _cfgFile:
            _cfgFile.write(self.__defaultConfig__().replace("<JSON_FILE>",jsonFile))
        return cfgFile    

    def __plot__(self):
        #------------------------------------
        # Read config & Basic sanity checks
        #------------------------------------
        groups = None
        general = None
        if self.cfgFile is not None:
            if os.path.isfile(self.cfgFile):
                exe = sys.executable
                exeDir = exe[:exe.rfind("/")] 
                shutil.copy(self.cfgFile,exeDir)
                _mod = importlib.import_module(self.cfgFile.split("/")[-1].replace(".py",""))
                if hasattr(_mod,"groups"):
                    groups = _mod.groups
                    self.log("i","Parsing config: "+self.cfgFile)
                if hasattr(_mod,"general"):
                    general = _mod.general
                os.remove(os.path.join(exeDir,self.cfgFile.split("/")[-1]))    
            else:
                self.log("e","Plotting configuration file not found.")
                sys.exit(0)
        else:
            self.log("w","Please specify configuration file.")
            sys.exit(0)

        orderedGroups = {}
        if groups is not None and len(groups.keys()) != 0:
            for igroup,group in groups.items():
                #TODO: check for global keys present
                if "plots" in group.keys() and len(group['plots'].keys()) != 0:
                    _plots = []
                    for iplot,plot in group['plots'].items():
                        plotCfgOk = True
                        internalOrder = 0
                        if "internalOrder" in plot.keys(): internalOrder += plot['internalOrder']
                        if internalOrder > 1 or (internalOrder == 1 and len(_plots) > 0):
                            self.log("e","Multiple files with multiple internal plots detected. This is not supported.")
                            plotCfgOk = False
                        if "order" not in plot.keys(): plotCfgOk = False
                        if "input" not in plot.keys(): plotCfgOk = False
                        else:
                            if not os.path.isfile(plot['input']) or not plot['input'].endswith(".json"):
                                self.log("w","Incorrect input source file for entry: "+iplot)
                                self.log("w","Input file must be in \'.json\' format.")
                                plotCfgOk = False
                            else:
                                #---------------------------
                                #Load data for each input
                                #---------------------------
                                dataSequence = {}
                                with open(plot['input']) as dataFile:
                                    dataSequence = json.load(dataFile)
                                data = {}
                                aliasType = group['type']
                                if group['type'] == "contHV": aliasType = "contIV"
                                if len(dataSequence.keys()) == 1 and aliasType in dataSequence.keys() and internalOrder == 0:
                                    if len(dataSequence[aliasType]) == 1:
                                        plot['data'] = dataSequence[aliasType][0] #dict
                                        group['internalOrder'] = 0
                                elif len(dataSequence.keys()) == 1 and aliasType in dataSequence.keys() and internalOrder == 1:
                                    if len(dataSequence[aliasType]) > 1:
                                        plot['data'] = dataSequence[aliasType] #list of dicts
                                        group['internalOrder'] = 1
                        if plotCfgOk:
                            _plots.append(plot)     
                        
                    #---------------------------
                    #Reorder plots in group
                    #---------------------------
                    def byOrder(elem):
                        return int(elem['order'])
                    def byInternalOrder(elem):
                        return int(elem['irep'])
                    _sortedPlots = []
                    if group['internalOrder'] == 0:
                        _sortedPlots = sorted(_plots,key=byOrder)
                    elif group['internalOrder'] == 1:
                        _data = _plots[0]['data'] #list
                        _newPlots = []
                        for internalPlot in _data:
                            _oldPlot = _plots[0] #copy all
                            _oldPlot['data'] = internalPlot #change data
                            _newPlots.append(_oldPlot) #append new plot
                        _sortedPlots = sorted(_newPlots,key=byInternalOrder)

                    if len(_sortedPlots) != 0:
                        orderedGroups[igroup] = group
                        orderedGroups[igroup]['plots'] = _sortedPlots

        else:
            self.log("e","Invalid configuration file.")
            sys.exit(0)

        if len(orderedGroups.keys()) != len(groups.keys()):
            self.log("e","Invalid configuration file (ordered list not created).")
            sys.exit(0)

        #-----------------------
        #General settings
        #-----------------------
        params = { 'text.usetex'   : True,
                   'font.family'   : 'serif',
                   'figure.figsize': general['canvasSize'],
                   'figure.autolayout' : True,
                   'ytick.labelsize' : 14,
                   'xtick.labelsize' : 14
        }
        plt.rcParams.update(params)    

        #-------------------
        #Transform data
        #-------------------
        for groupKey, group in orderedGroups.items():
            self.log("i", "Plotting group: \""+groupKey+"\" of type \""+group['type']+"\" with "+str(len(group['plots']))+" series.")
            figures = []
            formDataList = []
            maxY1 = 0.0
            if "IV" in group['type']:
                for iplot,plot in enumerate(group['plots']):
                    _data = plot['data']
                    isAllNeg = True
                    for i,bias in enumerate(_data['bias']):
                        if float(_data['curr'][i]) > 0.: isAllNeg = False
                    for i,bias in enumerate(_data['bias']):
                        sign = 1.0
                        scaleY1 = 1.0
                        if isAllNeg: sign = -1.0
                        if 'scaleY1' in group.keys(): scaleY1 = group['scaleY1']*sign
                        formData = {}
                        if sign < 0.0 and group['plotPositive']:
                            formData["bias_"+str(iplot)] = float(bias)
                        else:
                            formData["bias_"+str(iplot)] = float(bias)*sign
                        formData["curr_"+str(iplot)] = float(_data['curr'][i])*scaleY1
                        if float(_data['curr'][i])*scaleY1 >= maxY1: maxY1 = float(_data['curr'][i])*scaleY1
                        try:
                            formData["tmp1_"+str(iplot)] = float(_data['tmp1'][i])
                        except ValueError:
                            formData["tmp1_"+str(iplot)] = 0.0
                        try:
                            formData["tmp2_"+str(iplot)] = float(_data['tmp2'][i])
                        except ValueError:
                            formData["tmp2_"+str(iplot)] = 0.0
                        try:
                            formData["tmp3_"+str(iplot)] = float(_data['tmp3'][i])
                        except ValueError:
                            formData["tmp3_"+str(iplot)] = 0.0
                        try:
                            formData["humi_"+str(iplot)] = float(_data['humi'][i])
                        except ValueError:
                            formData["humi_"+str(iplot)] = 0.0
                        try:
                            formData["lumi_"+str(iplot)] = float(_data['lumi'][i])
                        except ValueError:
                            formData["lumi_"+str(iplot)] = 0.0
                        formDataList.append(formData)

                #----------------------------
                #Create and print data frame
                #----------------------------
                dataFrame = pd.DataFrame(formDataList)
                print(dataFrame)

                #---------------------
                #Plotting
                #---------------------
                for iplot,plot in enumerate(group['plots']):
                    if iplot == 0:
                        figure = dataFrame.plot.scatter(x="bias_"+str(iplot), y="curr_"+str(iplot), color=plot['color'], marker=plot['markerStyle'], s=plot['markerSize'], label=plot['legendName'], logy=group['logy'])
                    else:
                        figure = dataFrame.plot.scatter(x="bias_"+str(iplot), y="curr_"+str(iplot), color=plot['color'], marker=plot['markerStyle'], s=plot['markerSize'], label=plot['legendName'], logy=group['logy'], ax=figures[0])
                    figures.append(figure)

                #--------------------------------
                #Group global settings
                #--------------------------------
                if group['logy']:
                    plt.axis([group['xRangeUser'][0],group['xRangeUser'][1],group['logyMin'],round(maxY1+0.10*maxY1)])
                else:
                    plt.axis([group['xRangeUser'][0],group['xRangeUser'][1],0,round(maxY1+0.10*maxY1)])
                plt.xlabel(group['xAxisTitle'], fontsize=group['xAxisTitleSize'])
                plt.ylabel(group['y1AxisTitle'], fontsize=group['y1AxisTitleSize'])
                plt.title(group["title"], loc='right', fontsize=14)
                plt.title(r'\fontsize{18pt}{3em}\selectfont{}{\textbf{CMS}}\fontsize{14pt}{3em}\selectfont{}{\textit{ Internal}}', loc='left')
                plt.legend(fontsize=group['legendFontSize'], ncol=group['legendColumns'])

                ###############
                # Save & Show
                ############### 
                outFiles = []
                if self.plotPNG:
                    outFiles.append(self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".png"))
                if self.plotPDF:
                    outFiles.append(self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".pdf"))    
                for fig in figures:
                    figIV = fig.get_figure()

                    #plot canvas
                    for outFile in outFiles:
                        figIV.savefig(outFile)
                        self.log("i","Saving file: "+outFile) 
                if self.show:
                    plt.show()

            elif "HV" in group['type']:
                for iplot,plot in enumerate(group['plots']):
                    _data = plot['data']
                    isAllNeg = True
                    for bias in _data['bias']:
                        if float(bias) > 0.: isAllNeg = False
                    for i,bias in enumerate(_data['bias']):
                        sign = 1.0
                        scaleY1 = 1.0
                        if isAllNeg: sign = -1.0
                        if 'scaleY1' in group.keys(): scaleY1 = group['scaleY1']
                        formData = {}
                        if sign < 0.0 and group['plotPositive']:
                            formData["bias_"+str(iplot)] = float(bias)*sign
                        else:
                            formData["bias_"+str(iplot)] = float(bias)
                        formData["curr_"+str(iplot)] = float(_data['curr'][i])*scaleY1
                        if abs(float(_data['curr'][i])*scaleY1) >= maxY1: maxY1 = abs(float(_data['curr'][i])*scaleY1)
                        try:
                            formData["tmp1_"+str(iplot)] = float(_data['tmp1'][i])
                        except ValueError:
                            formData["tmp1_"+str(iplot)] = 0.0
                        try:
                            formData["tmp2_"+str(iplot)] = float(_data['tmp2'][i])
                        except ValueError:
                            formData["tmp2_"+str(iplot)] = 0.0
                        try:
                            formData["tmp3_"+str(iplot)] = float(_data['tmp3'][i])
                        except ValueError:
                            formData["tmp3_"+str(iplot)] = 0.0
                        try:
                            formData["humi_"+str(iplot)] = float(_data['humi'][i])
                        except ValueError:
                            formData["humi_"+str(iplot)] = 0.0
                        try:
                            formData["lumi_"+str(iplot)] = float(_data['lumi'][i])
                        except ValueError:
                            formData["lumi_"+str(iplot)] = 0.0
                        formDataList.append(formData)

                #----------------------------
                #Create and print data frame
                #----------------------------
                dataFrame = pd.DataFrame(formDataList)
                print(dataFrame)

                #---------------------
                #Plotting
                #---------------------
                for iplot,plot in enumerate(group['plots']):
                    if iplot == 0:
                        figure = dataFrame.plot.scatter(x="bias_"+str(iplot), y="curr_"+str(iplot), color=plot['color'], marker=plot['markerStyle'], s=plot['markerSize'], label=plot['legendName'], logy=group['logy'])
                    else:
                        figure = dataFrame.plot.scatter(x="bias_"+str(iplot), y="curr_"+str(iplot), color=plot['color'], marker=plot['markerStyle'], s=plot['markerSize'], label=plot['legendName'], logy=group['logy'], ax=figures[0])
                    figures.append(figure)

                #--------------------------------
                #Group global settings
                #--------------------------------
                if group['logy']:
                    plt.axis([group['xRangeUser'][0],group['xRangeUser'][1],group['logyMin'],round(maxY1+0.10*maxY1)])
                else:
                    plt.axis([group['xRangeUser'][0],group['xRangeUser'][1],-round(maxY1+0.10*maxY1),round(maxY1+0.10*maxY1)])
                plt.xlabel(group['xAxisTitle'], fontsize=group['xAxisTitleSize'])
                plt.ylabel(group['y1AxisTitle'], fontsize=group['y1AxisTitleSize'])
                plt.title(group["title"], loc='right', fontsize=14)
                plt.title(r'\fontsize{18pt}{3em}\selectfont{}{\textbf{CMS}}\fontsize{14pt}{3em}\selectfont{}{\textit{ Internal}}', loc='left')
                plt.legend(fontsize=group['legendFontSize'], ncol=group['legendColumns'])

                ###############
                # Save & Show
                ############### 
                outFiles = []
                if self.plotPNG:
                    outFiles.append(self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".png"))
                if self.plotPDF:
                    outFiles.append(self._uniqueName(self.args.outputDir+"/"+self.args.outputFile+"_"+self._date()+".pdf"))
                for fig in figures:
                    figIV = fig.get_figure()

                    #plot canvas
                    for outFile in outFiles:
                        figIV.savefig(outFile)
                        self.log("i","Saving file: "+outFile) 
                if self.show:
                    plt.show()

    def load(self, jsonFile, show):
        #----------------------------------------------
        # Load json file and create plotting config
        #----------------------------------------------
        self.jsonFile = jsonFile
        self.show = show
        if os.path.isfile(self.jsonFile):
            self.cfgFile = self.__createConfig__(self.jsonFile)
        else:
            self.safeToPlot = False
            self.log("e","Input for plotting not found!")

    def plot(self):
        if self.safeToPlot:
            self.__plot__()
