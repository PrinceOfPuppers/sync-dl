import configparser
from ntpath import dirname
import os

modulePath = dirname(dirname(__file__))

_defaultConfig = {
    'metaDataName' : '.metaData',
    'manualAddId' : '-manualAddition',
    'testPlPath' : 'tests/testPlaylists',
    'musicDir' : '',
    'autoScrapeCommentTimestamps': '0',
    'audioFormat': 'best',
    'embedThumbnail': '0'
}

#loading config
_parser = configparser.ConfigParser(allow_no_value=True)
_parser.optionxform = str


def writeToConfig(key,value):
    global _parser
    global _config
    _parser.set('CONFIG',key,value)
    with open(f'{modulePath}/config.ini', 'w') as configfile:
        _parser.write(configfile)

    _config[key] = value

def readConfig(key, boolean = False):
    global _config
    if boolean:
        return _config.getboolean(key)
    return _config[key]

def checkConfig():
    global _defaultConfig
    global _config
    cfgPath = f'{modulePath}/config.ini'

    if not os.path.exists(cfgPath):
        _parser['CONFIG'] = _defaultConfig
        with open(cfgPath, 'w+') as f:
            _parser.write(f)
    else:
        _parser.read(cfgPath)
    _config = _parser['CONFIG']

    for key in _defaultConfig.keys():
        if not key in _config.keys():
            writeToConfig(key, _defaultConfig[key])

checkConfig()
