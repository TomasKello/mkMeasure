import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import sys,os
import argparse
import importlib
import datetime

def log(log_type="i",text=""):
    source = "mkDraw:          "
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

def _date():
    _date = datetime.datetime.now()
    month = str(_date.month)
    day = str(_date.day)
    if len(str(_date.month)) == 1: month = "0"+str(_date.month)
    if len(str(_date.day)) == 1: day = "0"+str(_date.day)
    return str(_date.year)+month+day

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    #add options
    parser.add_argument('--cfg', dest='configFile', help='Configuration file.', action='store', default=None )
    parser.add_argument('--save', dest='save', help='Save plots as png.', action='store_true', default=True )
    parser.add_argument('--show', dest='show', help='Show plots in interactive GUI.', action='store_true', default=False )

    #-------------------
    #Parse user options
    #-------------------
    args = parser.parse_args()

    #------------------------------------
    #Read config & Basic sanity checks
    #------------------------------------
    config = None
    groups = None
    general = None
    if args.configFile is not None:
        if os.path.isfile(args.configFile):
            _mod = importlib.import_module(args.configFile.replace(".py","")) 
            if hasattr(_mod,"groups"):
                groups = _mod.groups    
                log("i","Parsing config: "+args.configFile)
            if hasattr(_mod,"general"):
                general = _mod.general
        else:
            log("e","Plotting configuration file not found.")
            sys.exit(0)  
    else:
        log("w","Please specify configuration file.")
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
                        log("e","Multiple files with multiple internal plots detected. This is not supported.") 
                        plotCfgOk = False
                    if "order" not in plot.keys(): plotCfgOk = False
                    if "input" not in plot.keys(): plotCfgOk = False
                    else:
                        if not os.path.isfile(plot['input']) or not plot['input'].endswith(".json"):
                            log("w","Incorrect input source file for entry: "+iplot)
                            log("w","Input file must be in \'.json\' format.")
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
        log("e","Invalid configuration file.")
        sys.exit(0) 

    if len(orderedGroups.keys()) != len(groups.keys()):
        log("e","Invalid configuration file (ordered list not created).")
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
    #plt.rc('font', family='serif')

    #-------------------
    #Transform data
    #-------------------
    for groupKey, group in orderedGroups.items():
        log("i", "Plotting group: \""+groupKey+"\" of type \""+group['type']+"\" with "+str(len(group['plots']))+" series.") 
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

            #set yaxis label precision
            #for fig in figures:
            #     fig.set_yscale('log')
            #    fig.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0e'))

            if args.show:
                plt.show()
            elif args.save:
                #create arch
                tag = "output_"+_date()+"_"+groupKey.replace(" ","_")
                if not os.path.exists("./"+tag):
                    os.mkdir(tag)

                #retrieve figure canvas
                for fig in figures:
                    figIV = fig.get_figure()

                    #plot canvas
                    figIV.savefig(tag+"/"+group['type']+".png")
                    figIV.savefig(tag+"/"+group['type']+".pdf")

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

            #set yaxis label precision
            #for fig in figures:
            #     fig.set_yscale('log')
            #    fig.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0e'))

            if args.show:
                plt.show()
            elif args.save:
                #create arch
                tag = "output_"+_date()+"_"+groupKey.replace(" ","_")
                if not os.path.exists("./"+tag):
                    os.mkdir(tag)

                #retrieve figure canvas
                for fig in figures:
                    figHV = fig.get_figure()

                    #plot canvas
                    figHV.savefig(tag+"/"+group['type']+".png")
                    figHV.savefig(tag+"/"+group['type']+".pdf")
