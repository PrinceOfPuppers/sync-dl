import configparser
import os
from re import compile
from ntpath import dirname

'''
contains all global variables, also parses config into global variables
'''

modulePath = dirname(__file__)

#loading config
_parser = configparser.ConfigParser(allow_no_value=True)
_parser.optionxform = str 

def writeToConfig(key,value):
    _parser.set('CONFIG',key,value)
    with open(f'{modulePath}/config.ini', 'w') as configfile:
        _parser.write(configfile)

def _getConfig():
    defaultConfig = {
        'metaDataName' : '.metaData',
        'manualAddId' : '-manualAddition',
        'testPlPath' : 'tests/testPlaylists',
        'tmpDownloadPath' : 'tmp',
        'musicDir' : '',
        'autoScrapeCommentTimestamps': '0'
    }
    cfgPath = f'{modulePath}/config.ini'

    if not os.path.exists(cfgPath):
        _parser['CONFIG'] = defaultConfig
        with open(cfgPath) as f:
            _parser.write(f)
    else:
        _parser.read(cfgPath)
    

    config = _parser['CONFIG']

    for key in defaultConfig.keys():
        if not key in config.keys():
            writeToConfig(key, defaultConfig[key])
            config[key] = defaultConfig[key]

    return config


_config = _getConfig()

# global config variables
filePrependRE = compile(r'\d+_')
plIdRe = compile(r'list=.{34}')

metaDataName = _config['metaDataName']
manualAddId =_config['manualAddId']
testPlPath = f"{modulePath}/{_config['testPlPath']}" 
tmpDownloadPath = f"{modulePath}/{_config['tmpDownloadPath']}"
musicDir = _config['musicDir']
ffmpegMetadataPath = f'{tmpDownloadPath}/FFMETADATAFILE'
songSegmentsPath = f'{tmpDownloadPath}/songSegmants'
autoScrapeCommentTimestamps = _config.getboolean('autoScrapeCommentTimestamps')

#TODO move add to ini
defualtPeekFmt='{index}: {url} {title}'

# logger
import logging
logger = logging.getLogger('sync_dl')


# youtube-dl params, used in downloadToTmp
params={"quiet": True, "noplaylist": True,
    'format': 'bestaudio', 
}


_ffmpegTested = False
_hasFfmpeg = False
def testFfmpeg():
    global _ffmpegTested
    global _hasFfmpeg
    if _ffmpegTested:
        return _hasFfmpeg
    try:
        import subprocess
        subprocess.check_output(['ffmpeg', '-version'])
    except:
        _ffmpegTested = True
        _hasFfmpeg = False
        return False

    _ffmpegTested = True
    _hasFfmpeg = True
    return True


if testFfmpeg(): # used to embed metadata
    params['postprocessors'] =  [
        {'key': 'FFmpegExtractAudio'},
        #{'key': 'EmbedThumbnail'},
        {'key': 'FFmpegMetadata'}
        ]
