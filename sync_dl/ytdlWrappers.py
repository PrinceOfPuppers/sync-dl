#import youtube_dl
import yt_dlp as youtube_dl
import os
import time

import shutil

import sync_dl.config as cfg


class MyLogger:
    def debug(self, msg):
        cfg.logger.debug(msg)

    def info(self, msg):
        cfg.logger.debug(msg)

    def warning(self, msg):
        cfg.logger.debug(msg)

    def error(self, msg):
        cfg.logger.debug(msg)


#ids are the unique part of each videos url
def getIDs(playlistUrl):
    try:
        params={"extract_flat": True, "quiet": True}
        params['logger'] = MyLogger()
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
    try:
        params={"extract_flat": True, "quiet": True, "outtmpl": f'%(title)s'}
        params['logger'] = MyLogger()
        with youtube_dl.YoutubeDL(params) as ydl:
            result = ydl.extract_info(url,download=False)
            ids = []
            titles = []
            for videoData in result['entries']:
                ids.append(videoData["id"])
                titles.append(ydl.prepare_filename(videoData))
        return ids, titles
    except:
        return [],[]


def getTitle(url):
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''

    params = {}
    params['extract_flat'] = True
    params['quiet'] = True
    params["outtmpl"] = f'%(title)s'
    params['logger'] = MyLogger()

    with youtube_dl.YoutubeDL(params) as ydl:

        song = ydl.extract_info(url,download=False)

        title = ydl.prepare_filename(song)
    return title


def downloadToTmp(videoId,numberStr):
    url = f"https://www.youtube.com/watch?v={videoId}"

    cfg.dlParams["outtmpl"] = f'{cfg.songDownloadPath}/{numberStr}_%(title)s.%(ext)s'
    cfg.dlParams['logger'] = MyLogger()

    with youtube_dl.YoutubeDL(cfg.dlParams) as ydl:

        cfg.clearTmpSubPath(cfg.songDownloadPath)

        attemptNumber = 1
        numAttempts = 2

        while True:
            try:
                ydl.download([url])
                return True
            except Exception as e:
                cfg.logger.debug(e)
                cfg.logger.info(f"Unable to Download Song at {url}")
                if attemptNumber == numAttempts:
                    cfg.logger.info(f"Max Download Retries Reached! If Song URL is Accessable Try Updating yt-dlp")
                    return False
                cfg.logger.info("Retrying...")
                time.sleep(0.5)
                attemptNumber += 1


def moveFromTmp(path):
    tmp = os.listdir(path=cfg.songDownloadPath)
    shutil.move(f"{cfg.songDownloadPath}/{tmp[0]}", path)
    return tmp[0]

def getJsonPlData(url):
    '''returns list of dicts of data for each video in playlist at url (order is playlist order)'''
    params = {}
    params['extract_flat'] = True

    params['quiet'] = True
    params['logger'] = MyLogger()
    with youtube_dl.YoutubeDL(params) as ydl:
        try:
            entries = ydl.extract_info(url,download=False)['entries']
        except:
            cfg.logger.error(f"No Playlist At URL: {url}")
            entries = []
    return entries


def _getBestThumbnail(thumbnails):
    maxWidth = 0
    best = None
    for thumbnail in thumbnails:
        width = thumbnail['width']
        if width > maxWidth:
            maxWidth = width
            best = thumbnail['url']

    if best is None:
        return None

    return best.split('?')[0]

def getThumbnailUrls(url:str) -> dict:
    '''
    used to check for corrupted metadata in integration tests
    Title will differ from what is on youtube because it is sanitized for use in filenames
    '''

    params = {
        "extract_flat": True, 
        "quiet": True, 
        "simulate": True,
        #"list_thumbnails": True,
        "logger": MyLogger(),
    }

    with youtube_dl.YoutubeDL(params) as ydl:
        result = ydl.extract_info(url,download=False)

    try:
        entries = result['entries']
    except KeyError:
        return {}

    thumbnails = {}
    for entry in entries:
        try:
            thumbnail = _getBestThumbnail(entry['thumbnails'])
            if thumbnail is None:
                continue
            thumbnails[entry['id']] = thumbnail
        except KeyError:
            continue

    return thumbnails
