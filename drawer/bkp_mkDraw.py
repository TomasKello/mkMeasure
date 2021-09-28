import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import sys,os
import argparse

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

if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    #add options
    parser.add_argument('-i', '--inputFile', nargs=1, dest='inputFile', help='Supported input format is JSON.', action='store', default=None )
    parser.add_argument('--save', dest='save', help='Save plots as png.', action='store_true', default=True )
    parser.add_argument('--show', dest='show', help='Show plots in interactive GUI.', action='store_true', default=False )

    #-------------------
    #Parse user options
    #-------------------
    args = parser.parse_args()

    #--------------------
    #Basic sanity checks
    #--------------------
    if len(args.inputFile) == 0:
        log("e","Please provide your input file.")
        sys.exit(0)
    elif len(args.inputFile) > 1:
        log("e","More than one input file is not supported.")
        sys.exit(0)
    else:    
        inputFile = args.inputFile[0]

    if ".json" not in inputFile:
        log("e","Sorry. Your format \"."+inputFile.split(".")[-1]+" is not supported.")
        sys.exit(0)
    else:
        log("i","Getting data from "+inputFile)

    #-------------------
    #Plotting details
    #-------------------
    labels = {}
    labels['IV'] = { 'bias'  : "Bias [V]",
                     'curr'  : "Current [A]",
                     'tempC' : "Temperature [C]",
                     'tempK' : "Temperature [K]",
                     'humi'  : "Humidity [%]",
                     'lumi'  : "Illuminance [lux]"
                   }

    #-------------------
    #Load data
    #-------------------
    with open(inputFile) as dataFile:
        dataSequence = json.load(dataFile)

    #-------------------
    #Transform data
    #-------------------
    for datatype, data in dataSequence.items():
        if "IV" in datatype:
            formDataList = []
            for irep in data:
                for i,bias in enumerate(irep['bias']):
                    sign = 1.
                    if float(irep['curr'][i]) < 0:
                        sign = -1.
                    formData = {}
                    formData['type'] = irep['type']
                    formData['irep'] = irep['irep']
                    formData['bias'] = float(bias)*sign
                    formData['curr'] = float(irep['curr'][i])*sign
                    formData['tmp1'] = float(irep['tmp1'][i])
                    formData['tmp2'] = float(irep['tmp2'][i])
                    formData['tmp3'] = float(irep['tmp3'][i])
                    formData['humi'] = float(irep['humi'][i])
                    formData['lumi'] = float(irep['lumi'][i])
                    formDataList.append(formData)    
                
                #----------------------------
                #Create and print data frame
                #----------------------------
                dataFrame = pd.DataFrame(formDataList)
                print(dataFrame)

                #---------------------
                #Main plot
                #---------------------
                plotIV = dataFrame.plot.scatter(x='bias', y='curr', color='Black',label='baby sensor')
                plt.xlabel(labels['IV']['bias'])
                plt.ylabel(labels['IV']['curr'])

                plotT  = dataFrame.plot.scatter(x='bias', y='tmp1', color='Red',  label='baby sensor')
                plt.xlabel(labels['IV']['bias'])
                plt.ylabel(labels['IV']['tempC'])

                #set yaxis label precision
                plotIV.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0e'))
                plotT.yaxis.set_major_formatter(mtick.FormatStrFormatter('%2.2f'))

                #show or save
                if args.show:
                    #show
                    plt.show()
                elif args.save:
                    #create arch
                    tag = inputFile.split("/")[-1].replace(".json","")
                    if not os.path.exists("./"+tag):
                        os.mkdir(tag)

                    #retrieve figure canvas
                    figIV = plotIV.get_figure()
                    figT  = plotT.get_figure()
                    
                    #plot canvas
                    figIV.savefig(tag+"/"+tag+"_IV.png")
                    figT.savefig(tag+"/"+tag+"_T.png")

    
