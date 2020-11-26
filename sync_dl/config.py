import configparser
import os
from re import compile
import logging
from ntpath import dirname
from shutil import copyfile

'''
contains all global variables, also parses config into global variables
'''

def createDefaultConfig(parser):
    defaultConfig = {
        'metaDataName' : '.metaData',
        'manualAddId' : '-manualAddition',
        'testPlPath' : 'tests/testPlaylists',
        'tmpDownloadPath' : 'tmp',
        'musicDir' : '',
    }

    parser['DEFAULT'] = defaultConfig
    with open(f'{modulePath}/config.ini','w+') as f:
        parser.write(f)
    


modulePath = dirname(__file__)

#loading config
parser = configparser.ConfigParser(allow_no_value=True)
parser.optionxform = str 

if not os.path.exists(f'{modulePath}/config.ini'):
    createDefaultConfig(parser)
    

else:
    parser.read(f'{modulePath}/config.ini')
section = parser['DEFAULT']


#global config variables
filePrependRE = compile(r'\d+_')

metaDataName = section['metaDataName']

manualAddId =section['manualAddId']

testPlPath = f"{modulePath}/{section['testPlPath']}" 

tmpDownloadPath = f"{modulePath}/{section['tmpDownloadPath']}"

musicDir = section['musicDir']

