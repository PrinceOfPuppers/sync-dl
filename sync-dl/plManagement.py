import os


from ytdlWrappers import getIDs, downloadID
from helpers import createNumLabel, loadJson, atomicWriteJson, smartSyncNewOrder
import config as cfg

def newPlaylist(cwd,name,url):
    if name in os.listdir(path=f"{cwd}"):
        print("Directory Is Not Empty, Cannot Make Playlist Here")
        return


    ids = getIDs(url)
    numDidgets = len(str(len(ids))) + 1 #needed for creating starting number for auto ordering ie) 001, 0152

    metaData = loadJson(cwd,cfg.metaDataName)
    metaData["url"] = url
    metaData["labelDigets"] = numDidgets

    metaData["ids"] = []


    for i,vidId in enumerate(ids):
        num = createNumLabel(i,numDidgets)
        downloadID(vidId,cwd,num)
        metaData["ids"].append(vidId)

    atomicWriteJson(metaData,cwd,cfg.metaDataName)





def smartSync(cwd):
    '''
    Syncs to remote playlist however will Not delete local songs (will reorder). Songs not in remote (ie ones deleted) 
    will be after the song they are currently after in local
    Example 1
        Local order: A B C D 
        Remote order: A 1 B C 2

        Local becomes: A 1 B C D 2

        notice D was removed from remote but is still after C in Local
    
    Example 2
        Local order: A B C D 
        Remote order: A 1 C B 2

        Local becomes: A 1 C D B 2

        notice C and B where swapped and D was deleted from Remote
    
    see test_smartSyncNewOrder in tests.py for more examples
    '''

    existingFiles = os.listdir(path=f"{cwd}")
    if cfg.metaDataName not in existingFiles:
        print("Current Directory is Not Existing Playlist")
        return


    metaData = loadJson(cwd,cfg.metaDataName)
    url = metaData["url"]

    remoteIds = getIDs(url)
    localIds = metaData["ids"]


    newOrder = smartSyncNewOrder(localIds,remoteIds)    



def hardSync():
    '''Syncs to remote playlist will delete local songs'''

def appendNew():
    '''will append new songs in remote playlist to local playlist in order that they appear'''


if __name__ == "__main__":
    #newPlaylist("/home/princeofpuppers/coding/python/pl-sync/test")
    pass