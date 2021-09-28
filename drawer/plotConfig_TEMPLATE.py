##########################
#Auxiliary
##########################
color = { 'red'    : "Red",
          'orange' : "Orange",
          'magenta': "Magenta", 
          'black' : "Black"
}

##########################
#Plots
##########################
plots = {}
plots['FM3'] = { 'legendName' : r'FM3 - final',
                  'input'        : "FM3_20210927.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['black'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : 1250,
                  'markerSize'   : 10,
                  'order'        : 2,
                  'internalOrder': 0     
                }
plots['FM3_top'] = { 'legendName' : r'FM3 - 2S\_014',
                  'input'         : "FM3-TOP_20210927.json",
                  'xRange'        : [0,800],
                  'yAxis'         : 1, #allowed values 1=left, 2=right
                  'color'         : color['red'],
                  'lineStyle'     : 1000,
                  'lineWidth'     : 2,
                  'markerStyle'   : 1250,
                  'markerSize'    : 10,
                  'order'         : 1,
                  'internalOrder' : 0
                }

plots['FM3_bottom'] = { 'legendName' : r'FM3 - 2S\_031',
                  'input'         : "FM3-BOT_20210927.json",
                  'xRange'        : [0,800],
                  'yAxis'         : 1, #allowed values 1=left, 2=right
                  'color'         : color['magenta'],
                  'lineStyle'     : 1000,
                  'lineWidth'     : 2,
                  'markerStyle'   : 1250,
                  'markerSize'    : 10,
                  'order'         : 0,
                  'internalOrder' : 0
                }

##########################
#Plot groups
##########################
groups = {}
groups['ComparisonFM3'] = { 'title'         : r'Comparison FM3',
                            'titleSize'     : 25,
                            'legendPosition': "top",
                            'xAxisTitle'    : r'Bias [V]',
                            'xRangeUser'    : [0,850],
                            'y1AxisTitle'   : r'Current [nA]',
                            'scaleY1'       : 1e9, #A to nA conversion  
                            #'y2AxisTitle'  : r'RH [%]',
                            'plots'         : plots,
                            'type'          : "contIV",
                            'plotPositive'  : True     
                          }
