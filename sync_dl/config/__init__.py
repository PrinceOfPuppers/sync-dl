from re import compile
from yt_dlp.postprocessor import FFmpegExtractAudioPP

from sync_dl.config.tmpdir import createTmpDir, clearTmpDir, clearTmpSubPath, \
                                  tmpDownloadPath, songSegmentsPath, thumbnailPath, songDownloadPath, ffmpegMetadataPath, songEditPath

from sync_dl.config.parsing import modulePath, writeToConfig, readConfig

from sync_dl.config.ytdlParams import setAudioFormat, setEmbedThumbnails, dlParams

'''
contains all global variables, also parses config into global variables
'''

# global config variables
filePrependRE = compile(r'\d+_')
plIdRe = compile(r'list=.{34}')

knownFormats = (*FFmpegExtractAudioPP.SUPPORTED_EXTS, 'best')

metaDataName = readConfig('metaDataName')
manualAddId = readConfig('manualAddId')
testPlPath = f"{modulePath}/{readConfig('testPlPath')}"
testSongName = "test.mp3"
testSongPath = f"{modulePath}/tests/{testSongName}"
musicDir = readConfig('musicDir')
autoScrapeCommentTimestamps = readConfig('autoScrapeCommentTimestamps', boolean=True)
audioFormat = readConfig('audioFormat')
embedThumbnail = readConfig('embedThumbnail', boolean=True)


#TODO move add to ini
defualtPeekFmt='{index}: {url} {title}'

# logger
import logging
logger = logging.getLogger('sync_dl')


