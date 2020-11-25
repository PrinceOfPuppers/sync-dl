import configparser
import os
from re import compile
import logging
from ntpath import dirname
from shutil import copyfile

'''
contains all global variables, also parses config into global variables
'''


modulePath = dirname(__file__)

#loading config
if not os.path.exists(f'{modulePath}/config.ini'):
    copyfile(f'{modulePath}/config-default.ini',f'{modulePath}/config.ini')

parser = configparser.ConfigParser(allow_no_value=True)
parser.optionxform = str 
parser.read(f'{modulePath}/config.ini')
section = parser['DEFAULT']


#global config variables
filePrependRE = compile(r'\d+_')

metaDataName = section['metaDataName']

manualAddId =section['manualAddId']

testPlPath = f"{modulePath}/{section['testPlPath']}" 

tmpDownloadPath = f"{modulePath}/{section['tmpDownloadPath']}"

musicDir = section['musicDir']

