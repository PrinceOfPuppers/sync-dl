import configparser
from re import compile
import logging
from ntpath import dirname

'''
contains all global variables, also parses config into global variables
'''


modulePath = dirname(__file__)

#loading config
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

