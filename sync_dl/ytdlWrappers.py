import youtube_dl
import os

import subprocess
import shutil

import sync_dl.config as cfg

#ids are the unique part of each videos url
def getIDs(playlistUrl):
    params={"extract_flat": True, "quiet": True}
    with youtube_dl.YoutubeDL(params) as ydl:
        result = ydl.extract_info(playlistUrl,download=False)
        ids = []
        for videoData in result['entries']:
            ids.append(videoData["id"])
        

    return ids


def getIdsAndTitles(playlistUrl):
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''
    command = f'youtube-dl --get-filename -o "%(title)s\n%(id)s" {playlistUrl}'
    idsAndTitles = subprocess.getoutput(command).split('\n')
    numSongs = int(len(idsAndTitles)/2)
    titles = [idsAndTitles[2*i] for i in range(numSongs)]
    ids = [idsAndTitles[2*i+1] for i in range(numSongs)]

    return ids,titles

def getTitle(url):
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''
    command = f'youtube-dl --no-playlist --get-filename -o "%(title)s" {url}'
    title = subprocess.getoutput(command)
    return title

def downloadID(videoId, path,numberStr, embedThumbnail=True):
    url = f"https://www.youtube.com/watch?v={videoId}"
    
    if not os.path.exists(cfg.tmpDownloadPath):
        os.mkdir(cfg.tmpDownloadPath)
    
    params={"quiet": True, "noplaylist": True, "outtmpl": f'{cfg.tmpDownloadPath}/{numberStr}_%(title)s.%(ext)s',
        'format': 'bestaudio', 
        'postprocessors': [
            {'key': 'FFmpegExtractAudio'},
            #{'key': 'EmbedThumbnail'},
            {'key': 'FFmpegMetadata'}
            ],
    }


    with youtube_dl.YoutubeDL(params) as ydl:

        #ensures tmp is empty
        tmp = os.listdir(path=cfg.tmpDownloadPath) 
        for f in tmp:
            os.remove(f"{cfg.tmpDownloadPath}/{f}")

        try:
            ydl.download([url])

            tmp = os.listdir(path=cfg.tmpDownloadPath) 
            shutil.move(f"{cfg.tmpDownloadPath}/{tmp[0]}", path)


            return True
        except:
            cfg.logger.info(f"Song No longer avalible at {url}")
            return False
