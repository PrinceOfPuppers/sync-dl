import configparser
import os
from re import compile
from ntpath import dirname
from shutil import copyfile

'''
contains all global variables, also parses config into global variables
'''

def testFfmpeg():
    try:
        import subprocess
        subprocess.check_output(['ffmpeg', '-version'])
    except:
        return False
    return True

def createDefaultConfig(parser):
    defaultConfig = {
        'metaDataName' : '.metaData',
        'manualAddId' : '-manualAddition',
        'testPlPath' : 'tests/testPlaylists',
        'tmpDownloadPath' : 'tmp',
        'musicDir' : '',
    }

    parser['CONFIG'] = defaultConfig
    with open(f'{modulePath}/config.ini','w+') as f:
        parser.write(f)
    
def writeToConfig(key,value):
    parser.set('CONFIG',key,value)
    with open(f'{modulePath}/config.ini', 'w') as configfile:
        parser.write(configfile)

modulePath = dirname(__file__)

#loading config
parser = configparser.ConfigParser(allow_no_value=True)
parser.optionxform = str 

if not os.path.exists(f'{modulePath}/config.ini'):
    createDefaultConfig(parser)
    

else:
    parser.read(f'{modulePath}/config.ini')


section = parser['CONFIG']

# global config variables
filePrependRE = compile(r'\d+_')
plIdRe = compile(r'list=.{34}')

metaDataName = section['metaDataName']

manualAddId =section['manualAddId']

testPlPath = f"{modulePath}/{section['testPlPath']}" 

tmpDownloadPath = f"{modulePath}/{section['tmpDownloadPath']}"

musicDir = section['musicDir']

#TODO move add to ini
defualtPeekFmt='{index}: {url} {title}'

# logger
import logging
logger = logging.getLogger('sync_dl')


# youtube-dl params, used in downloadToTmp
params={"quiet": True, "noplaylist": True,
    'format': 'bestaudio', 
}


#checks if ffmpeg is installed once and updates config file
try:
    ffmpegInstalled = int(section['ffmpegInstalled'])
except:
    ffmpegInstalled = int(testFfmpeg())
    writeToConfig('ffmpegInstalled',str(ffmpegInstalled))

if ffmpegInstalled:
    params['postprocessors'] =  [
        {'key': 'FFmpegExtractAudio'},
        #{'key': 'EmbedThumbnail'},
        {'key': 'FFmpegMetadata'}
        ]