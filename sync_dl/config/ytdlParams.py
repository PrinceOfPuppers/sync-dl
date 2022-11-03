import subprocess
from sync_dl.config.parsing import writeToConfig, readConfig

# youtube-dl dlParams, used in downloadToTmp
dlParams={"quiet": True, "noplaylist": True, 'format': 'bestaudio'}


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


dlParams['postprocessors'] = []
if testFfmpeg():
    dlParams['postprocessors'].append(
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
    global audioFormat
    global dlParams
    audioFormat = readConfig('audioFormat')

    if audioFormat == 'best':
        dlParams['format'] = f'bestaudio'
        if testFfmpeg():
            _addIfNotExists(dlParams['postprocessors'], 'FFmpegExtractAudio', {'key': 'FFmpegExtractAudio'})
    else:
        if not testFfmpeg():
            writeToConfig('audioFormat', 'best')
            raise Exception("ffmpeg is Required to Use Audio Format Other Than 'best'")
        dlParams['format'] = f'{audioFormat}/bestaudio'
        _addIfNotExists(dlParams['postprocessors'], 'FFmpegExtractAudio', {
            'key': 'FFmpegExtractAudio',
            'preferredcodec': audioFormat,
            'preferredquality': 'bestaudio',
            'nopostoverwrites': True
        })

setAudioFormat()

def setEmbedThumbnails():
    global embedThumbnail
    embedThumbnail = readConfig('embedThumbnail', boolean=True)
    if embedThumbnail:
        dlParams['writethumbnail'] = True
        _addIfNotExists(dlParams['postprocessors'], 'EmbedThumbnail', {
            'key': 'EmbedThumbnail',
            'already_have_thumbnail': False
        })
    else:
        _removeIfExists(dlParams['postprocessors'], 'EmbedThumbnail')
        if 'writethumbnail' in dlParams:
            dlParams.pop('writethumbnail')

setEmbedThumbnails()
