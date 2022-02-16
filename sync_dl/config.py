import configparser
from tempfile import TemporaryDirectory
import os
from re import compile
from ntpath import dirname
import subprocess
from yt_dlp.postprocessor import FFmpegExtractAudioPP

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
        'musicDir' : '',
        'autoScrapeCommentTimestamps': '0',
        'audioFormat': 'best',
        'embedThumbnail': '0'
    }
    cfgPath = f'{modulePath}/config.ini'

    if not os.path.exists(cfgPath):
        _parser['CONFIG'] = defaultConfig
        with open(cfgPath, 'w+') as f:
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
_tmpDir = TemporaryDirectory()

# global config variables
filePrependRE = compile(r'\d+_')
plIdRe = compile(r'list=.{34}')

knownFormats = FFmpegExtractAudioPP.SUPPORTED_EXTS

metaDataName = _config['metaDataName']
manualAddId =_config['manualAddId']
testPlPath = f"{modulePath}/{_config['testPlPath']}" 
tmpDownloadPath = _tmpDir.name
musicDir = _config['musicDir']
ffmpegMetadataPath = f'{tmpDownloadPath}/FFMETADATAFILE'
songSegmentsPath = f'{tmpDownloadPath}/songSegmants'
autoScrapeCommentTimestamps = _config.getboolean('autoScrapeCommentTimestamps')
audioFormat = _config['audioFormat']
embedThumbnail = _config.getboolean('embedThumbnail')

#TODO move add to ini
defualtPeekFmt='{index}: {url} {title}'

# logger
import logging
logger = logging.getLogger('sync_dl')


# youtube-dl params, used in downloadToTmp
params={"quiet": True, "noplaylist": True, 'format': 'bestaudio'}


_ffmpegTested = False
_hasFfmpeg = False

def testFfmpeg():
    global _ffmpegTested
    global _hasFfmpeg
    if _ffmpegTested:
        return _hasFfmpeg
    try:
        subprocess.check_output(['ffmpeg', '-version'])
    except:
        _ffmpegTested = True
        _hasFfmpeg = False
        return False

    _ffmpegTested = True
    _hasFfmpeg = True
    return True


params['postprocessors'] = []
if testFfmpeg():
    params['postprocessors'].append(
        {'key': 'FFmpegMetadata'}
    )

def _addIfNotExists(l, key, val):
    for i in range(len(l)):
        if l[i]['key'] == key:
            l[i] = val
            return

    l.append(val)

def _removeIfExists(l, key):
    for i in range(len(l)):
        if l[i]['key'] == key:
            l.pop(i)
            return


def setAudioFormat():
    audioFormat = _config['audioFormat']

    if audioFormat == 'best':
        params['format'] = f'bestaudio'
        if testFfmpeg():
            _addIfNotExists(params['postprocessors'], 'FFmpegExtractAudio', {'key': 'FFmpegExtractAudio'})
    else:
        if not testFfmpeg():
            writeToConfig('audioFormat', 'best')
            audioFormat = _config['audioFormat']
            raise Exception("ffmpeg is Required to Use Audio Format Other Than 'best'")
        params['format'] = f'{_config["audioFormat"]}/bestaudio'
        _addIfNotExists(params['postprocessors'], 'FFmpegExtractAudio', {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audioFormat,
            'preferredquality': 'bestaudio',
            'nopostoverwrites': True
        })

setAudioFormat()

def setEmbedThumbnails():
    global embedThumbnail
    embedThumbnail = _config.getboolean('embedThumbnail')
    if embedThumbnail:
        params['writethumbnail'] = True
        _addIfNotExists(params['postprocessors'], 'EmbedThumbnail', {
            'key': 'EmbedThumbnail',
            'already_have_thumbnail': False
        })
    else:
        _removeIfExists(params['postprocessors'], 'EmbedThumbnail')
        if 'writethumbnail' in params:
            params.pop('writethumbnail')

setEmbedThumbnails()
