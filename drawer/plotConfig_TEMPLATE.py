##########################
#Auxiliary
##########################
color = { 'red'    : "Red",
          'orange' : "Orange",
          'magenta': "Magenta", 
          'black' : "Black",
          'blue'  : "Blue",
          'green' : "Green",
          'yellow': "Yellow",
          'violet': "Violet",
          'grey'  : "Grey"
}

##########################
#Plots
##########################
plots = {}
plots['bare2S031'] = { 'legendName' : r'2S\_031 - bare sensor',
                  'input'        : "2S_031_20210706.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['blue'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 5,
                  'internalOrder': 0     
                }
plots['metro2S031'] = { 'legendName' : r'2S\_031 - after metrology',
                  'input'        : "2S_031_20210708_0.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['red'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 6,
                  'internalOrder': 0
                }
plots['pigtail2S031'] = { 'legendName' : r'2S\_031 - pigtail encapsulated',
                  'input'        : "2S_031_20210715_0.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['green'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 7,
                  'internalOrder': 0
                }
plots['sand2S031'] = { 'legendName' : r'2S\_031 - sandwich',
                  'input'        : "2S_031_20210722.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['violet'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 8,
                  'internalOrder': 0
                }

plots['hybrid2S031'] = { 'legendName' : r'2S\_031 - hybrid glued',
                  'input'        : "2S_031_20210816.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['orange'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 9,
                  'internalOrder': 0
                }

plots['bare2S014'] = { 'legendName' : r'2S\_014 - bare sensor',
                  'input'        : "2S_014_20210706.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['blue'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 0,
                  'internalOrder': 0
                }
plots['metro2S014'] = { 'legendName' : r'2S\_014 - after metrology',
                  'input'        : "2S_014_20210708.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['red'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 1,
                  'internalOrder': 0
                }
plots['pigtail2S014'] = { 'legendName' : r'2S\_014 - pigtail encapsulated',
                  'input'        : "2S_014_20210715_0.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['green'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 2,
                  'internalOrder': 0
                }

plots['sand2S014'] = { 'legendName' : r'2S\_014 - sandwich',
                  'input'        : "2S_014_20210722.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['violet'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 3,
                  'internalOrder': 0
                }

plots['hybrid2S014'] = { 'legendName' : r'2S\_014 - hybrid glued',
                  'input'        : "2S_014_20210816.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['orange'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 4,
                  'internalOrder': 0
                }
plotsFM3 = {}
plotsFM3['hybrid2S031'] = { 'legendName' : r'2S\_031 - hybrid glued',
                  'input'        : "2S_031_20210816.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['orange'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "o",
                  'markerSize'   : 45,
                  'order'        : 0,
                  'internalOrder': 0
                }
plotsFM3['hybrid2S014'] = { 'legendName' : r'2S\_014 - hybrid glued',
                  'input'        : "2S_014_20210816.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['orange'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "^",
                  'markerSize'   : 45,
                  'order'        : 1,
                  'internalOrder': 0
                }
plotsFM3['hybridBondedFM3'] = { 'legendName' : r'FM3 (2S\_014+2S\_031) - hybrid bonded',
                  'input'        : "2S_014_031_20210831.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['grey'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "s",
                  'markerSize'   : 45,
                  'order'        : 2,
                  'internalOrder': 0
                }
plotsFM3['hybridEncapsFM3'] = { 'legendName' : r'FM3 (2S\_014+2S\_031) - hybrid encapsulated',
                  'input'        : "2S_014_031_20210909.json",
                  'xRange'       : [0,800],
                  'yAxis'        : 1, #allowed values 1=left, 2=right
                  'color'        : color['black'],
                  'lineStyle'    : 1000,
                  'lineWidth'    : 2,
                  'markerStyle'  : "s",
                  'markerSize'   : 45,
                  'order'        : 3,
                  'internalOrder': 0
                }


##########################
#Plot groups
##########################
groups = {}
groups['ComparisonFM3_afterHybridBonding'] = {
                            'title'         : r'Comparison FM3',
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
                            'logy'          : True,
                            'logyMin'       : 10.1,
                            'plots'         : plotsFM3,
                            'type'          : "contIV",
                            'plotPositive'  : True
                          }
'''
groups['ComparisonFM3_afterHybridGluing'] = {
                            'title'         : r'Comparison FM3',
                            'titleSize'     : 25,
                            'legendPosition': "top",
                            'legendColumns' : 2,
                            'legendFontSize': 14,
                            'xAxisTitle'    : r'Bias [V]',
                            'xAxisTitleSize': 14,
                            'xRangeUser'    : [0,850],
                            'y1AxisTitle'   : r'Current [nA]',
                            'y1AxisTitleSize': 14,
                            'scaleY1'       : 1e9, #A to nA conversion
                            'logy'          : True,
                            'logyMin'       : 1.1,
                            'plots'         : plots,
                            'type'          : "contIV",
                            'plotPositive'  : True
                          }
'''

###########################
#General
###########################
general = {
 'canvasSize' : [6.0,5.5]
}


