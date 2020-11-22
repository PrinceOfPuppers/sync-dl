import youtube_dl
import os
import logging

#ids are the unique part of each videos url
def getIDs(playlistUrl):
    params={"extract_flat": True}
    with youtube_dl.YoutubeDL(params) as ydl:
        result = ydl.extract_info(playlistUrl,download=False)
        ids = []
        for videoData in result['entries']:
            ids.append(videoData["id"])
        

    return ids

def getIdsAndTitles(playlistUrl):
    '''gets all ids and titles from playlist, used when testing for corrupted metadata'''
    params={"extract_flat": True}
    with youtube_dl.YoutubeDL(params) as ydl:
        result = ydl.extract_info(playlistUrl,download=False)
        ids = []
        titles = []
        for videoData in result['entries']:
            ids.append(videoData["id"])
            titles.append(videoData["title"])
    return ids,titles

def getTitle(url):
    '''gets title of single song, used for testing for corrupted metadata'''
    with youtube_dl.YoutubeDL() as ydl:
        result = ydl.extract_info(url,download=False)
        return result['title']

#downloads video at id, returns bool for success/failure 
def downloadID(videoId,path,number):
    url = f"https://www.youtube.com/watch?v={videoId}"

    try:
        os.system(f"youtube-dl --no-playlist -x -f bestaudio --add-metadata --output '{path}/{number}_%(title)s.%(ext)s' {url}")
        return True
    except:
        logging.info(f"song at {url} is unavalible")
        return False