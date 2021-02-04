import youtube_dl
import os

import subprocess
import shutil

import sync_dl.config as cfg

#ids are the unique part of each videos url
def getIDs(playlistUrl):
    try:
        params={"extract_flat": True, "quiet": True}
        with youtube_dl.YoutubeDL(params) as ydl:
            result = ydl.extract_info(playlistUrl,download=False)
            ids = []
            for videoData in result['entries']:
                ids.append(videoData["id"])
        return ids
    except:
        return []



def getIdsAndTitles(url):
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''

    params = {}
    params['extract_flat'] = True
    params['quiet'] = True
    params["outtmpl"] = f'%(title)s'
    
    with youtube_dl.YoutubeDL(params) as ydl:
        
        entries = ydl.extract_info(url,download=False)['entries']

        ids = [song['id'] for song in entries]
        titles = [ydl.prepare_filename(song) for song in entries]

    return ids,titles

def getTitle(url):
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''

    params = {}
    params['extract_flat'] = True
    params['quiet'] = True
    params["outtmpl"] = f'%(title)s'
    
    with youtube_dl.YoutubeDL(params) as ydl:
        
        song = ydl.extract_info(url,download=False)

        title = ydl.prepare_filename(song)
    return title

def downloadToTmp(videoId,numberStr):
    url = f"https://www.youtube.com/watch?v={videoId}"
    
    if not os.path.exists(cfg.tmpDownloadPath):
        os.mkdir(cfg.tmpDownloadPath)
    
    cfg.params["outtmpl"] = f'{cfg.tmpDownloadPath}/{numberStr}_%(title)s.%(ext)s'
    
    with youtube_dl.YoutubeDL(cfg.params) as ydl:

        #ensures tmp is empty
        tmp = os.listdir(path=cfg.tmpDownloadPath) 
        for f in tmp:
            os.remove(f"{cfg.tmpDownloadPath}/{f}")

        try:
            ydl.download([url])
            return True

        except Exception:
            cfg.logger.info(f"Unable to Download Song at {url}")
            return False

def moveFromTmp(path):
    tmp = os.listdir(path=cfg.tmpDownloadPath) 
    shutil.move(f"{cfg.tmpDownloadPath}/{tmp[0]}", path)

def getJsonPlData(url):
    '''returns list of dicts of data for each video in playlist at url (order is playlist order)'''
    params = {}
    params['extract_flat'] = True 

    params['quiet'] = True
    with youtube_dl.YoutubeDL(params) as ydl:
        try:
            entries = ydl.extract_info(url,download=False)['entries']
        except:
            cfg.logger.error(f"No Playlist At URL: {url}")
            entries = []
    return entries