import shutil
from tempfile import TemporaryDirectory
import os


def _clearSubPath(path):
    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.unlink(path)
            return
        for f in os.listdir(path=path):
            p = f"{path}/{f}"
            if os.path.isfile(p) or os.path.islink(p):
                os.unlink(p)
            elif os.path.isdir(p):
                shutil.rmtree(p)
    except OSError:
        pass
            #cfg.logger.error(f"Error Clearing Directory: {dir}")
            #cfg.logger.debug(f"Reason: {e}")

# tmp paths
_tmpDir = None
tmpDownloadPath = '' #top level

# dirs
songSegmentsPath = ''
thumbnailPath = ''
songDownloadPath = ''
songEditPath = ''

# files
ffmpegMetadataPath = ''

def _createSubDirs():
    os.mkdir(songSegmentsPath)
    os.mkdir(thumbnailPath)
    os.mkdir(songDownloadPath)
    os.mkdir(songEditPath)

def createTmpDir():
    global _tmpDir
    global tmpDownloadPath
    global ffmpegMetadataPath
    global songSegmentsPath
    global thumbnailPath
    global songDownloadPath
    global songEditPath
    _tmpDir = TemporaryDirectory()
    tmpDownloadPath = _tmpDir.name
    ffmpegMetadataPath = f'{tmpDownloadPath}/FFMETADATAFILE'
    songSegmentsPath = f'{tmpDownloadPath}/songSegmants'
    thumbnailPath  = f'{tmpDownloadPath}/thumbnails'
    songDownloadPath  = f'{tmpDownloadPath}/songDownloads'
    songEditPath  = f'{tmpDownloadPath}/songEdit'
    _createSubDirs()
createTmpDir()

def clearTmpDir():
    if not os.path.exists(tmpDownloadPath):
        createTmpDir()

    _clearSubPath(tmpDownloadPath)
    _createSubDirs()

def clearTmpSubPath(path:str):
    '''clears file or directory subtree'''
    if not path.startswith(tmpDownloadPath):
        raise Exception(f"{path} is not contained in {tmpDownloadPath}")

    if not os.path.exists(tmpDownloadPath):
        createTmpDir()
    _clearSubPath(path)
