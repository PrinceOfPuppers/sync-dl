import os


import argparse

import shelve
import re
import ntpath
from random import randint

from sync_dl.ytdlWrappers import getIDs, downloadID
from sync_dl.plManagement import editPlaylist, correctStateCorruption
from sync_dl.helpers import createNumLabel, smartSyncNewOrder, getLocalSongs, rename, relabel,download
import sync_dl.config as cfg


def newPlaylist(plPath,url):
    if not os.path.exists(plPath):
        os.makedirs(plPath)

    elif len(os.listdir(path=plPath))!=0:
        cfg.logger.error(f"Directory Is Not Empty, Cannot Make Playlist in {plPath}")
        return

    cfg.logger.info(f"Creating New Playlist Named {ntpath.basename(plPath)} from URL: {url}")

    ids = getIDs(url)
    numDigits = len(str( len(ids) + 1)) #needed for creating starting number for auto ordering ie) 001, 0152

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        metaData["url"] = url
        metaData["ids"] = []

        invalidSongs = 0
        for i,songId in enumerate(ids):
            num = createNumLabel(i,numDigits)

            cfg.logger.info(f"Dowloading song Id {songId}")
            if downloadID(songId,plPath,num):
                metaData["ids"].append(songId)
                cfg.logger.debug("Download Complete")
            else:
                invalidSongs+=1

        cfg.logger.info(f"Downloaded {len(ids)-invalidSongs}/{len(ids)} Songs")


def smartSync(plPath):
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
    cfg.logger.info("Smart Syncing...")
    correctStateCorruption(plPath)


    existingFiles = os.listdir(path=f"{plPath}")
    if cfg.metaDataName not in existingFiles:
        cfg.logger.critical("Current Directory is Not Existing Playlist")
        return


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        url = metaData["url"]
        localIds = metaData["ids"]

    remoteIds = getIDs(url)


    newOrder = smartSyncNewOrder(localIds,remoteIds)

    editPlaylist(plPath,newOrder)


def hardSync():
    '''Syncs to remote playlist will delete local songs'''

def appendNew(plPath):
    '''will append new songs in remote playlist to local playlist in order that they appear'''

    cfg.logger.info("Appending New Songs...")

    correctStateCorruption(plPath)

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))

        remoteIds = getIDs(metaData['url'])

        for remoteId in remoteIds:
            if remoteId not in metaData['ids']:
                download(metaData,plPath,remoteId,len(metaData['ids']),numDigits)



def manualAdd(plPath, songPath, posistion):
    '''put song in posistion in the playlist'''

    if not os.path.exists(songPath):
        cfg.logger.error(f'{songPath} Does Not Exist')
        return

    correctStateCorruption(plPath)

    currentDir = getLocalSongs(plPath)

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))

        #clamp posistion
        if posistion > idsLen:
            posistion = idsLen
        elif posistion < 0:
            posistion = 0
        
        cfg.logger.info(f"Adding {ntpath.basename(songPath)} to {ntpath.basename(plPath)} in Posistion {posistion}")

        #shifting elements
        for i in reversed(range(posistion, idsLen)):
            oldName = currentDir[i]

            newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i+1,numDigits)}_" , oldName)

            rename(metaData,cfg.logger.debug,plPath,oldName,newName,i+1,metaData["ids"][i])

            metaData["ids"][i] = '' #wiped in case of crash, this blank entries can be removed restoring state


        newSongName = f"{createNumLabel(posistion,numDigits)}_" + ntpath.basename(songPath)

        os.rename(songPath,f'{plPath}/{newSongName}')

        if posistion >= len(metaData["ids"]):
            metaData["ids"].append(cfg.manualAddId)
        else:
            metaData["ids"][posistion] = cfg.manualAddId


def swap(plPath, index1, index2):
    '''moves song to provided posistion, shifting all below it down'''
    if index1 == index2:
        cfg.logger.info(f"Given Index are the Same")


    correctStateCorruption(plPath)

    currentDir = getLocalSongs(plPath)



    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))

        if index1>=idsLen or index2>=idsLen:
            cfg.logger.error(f"Given Index is Larger than Max {idsLen-1}")
            return
        elif index1<0 or index2<0:
            cfg.logger.error(f"Given Index is Negative")
            return

        cfg.logger.info(f"Swapping {currentDir[index1]} and {currentDir[index2]}")
        #shift index1 out of the way (to idsLen)

        oldName = currentDir[index1]
        tempName = relabel(metaData,cfg.logger.debug,plPath,oldName,index1,idsLen,numDigits)

        
        #move index2 to index1's old location

        oldName = currentDir[index2]
        relabel(metaData,cfg.logger.debug,plPath,oldName,index2,index1,numDigits)

        #move index1 (now =idsLen) to index2's old location

        oldName = tempName
        relabel(metaData,cfg.logger.debug,plPath,oldName,idsLen,index2,numDigits)

        del metaData["ids"][idsLen]

def move(plPath, currentIndex, newIndex):
    if currentIndex==newIndex:
        cfg.logger.info("Indexes Are the Same")
        return


    correctStateCorruption(plPath)

    currentDir = getLocalSongs(plPath)


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))


        if currentIndex>=idsLen:
            cfg.logger.error(f"No song has Index {currentIndex}, Largest Index is {idsLen-1}")
            return
        elif currentIndex<0:
            cfg.logger.error(f"No Song has a Negative Index")
            return

        #clamp newIndex
        if newIndex > idsLen-1:
            newIndex = idsLen-1
        elif newIndex < 0:
            newIndex = 0
        
        cfg.logger.info(f"Moving {currentDir[currentIndex]} to Index {newIndex}")
        
        #moves song to end of list
        tempName = relabel(metaData,cfg.logger.debug,plPath,currentDir[currentIndex],currentIndex,idsLen,numDigits)

        if currentIndex>newIndex:
            #shifts all songs from newIndex to currentIndex-1 by +1
            for i in reversed(range(newIndex,currentIndex)):
                
                oldName = currentDir[i]
                relabel(metaData,cfg.logger.debug,plPath,oldName,i,i+1,numDigits)
    
        
        else:
            #shifts all songs from currentIndex+1 to newIndex by -1
            for i in range(currentIndex+1,newIndex+1):
                oldName = currentDir[i]
                relabel(metaData,cfg.logger.debug,plPath,oldName,i,i-1,numDigits)
        
        #moves song back
        relabel(metaData,cfg.logger.debug,plPath,tempName,idsLen,newIndex,numDigits)
        del metaData['ids'][idsLen]



def shuffle(plPath):
    '''randomizes playlist order'''
    cfg.logger.info("Shuffling Playlist")
    correctStateCorruption(plPath)

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        plLen = len(metaData["ids"])
        ids = metaData["ids"]

        avalibleNums = [i for i in range(plLen)]
        newOrder = []
        for _ in range(plLen):
            oldIndex = avalibleNums.pop(randint(0,len(avalibleNums)-1))
            newOrder.append( (ids[oldIndex],oldIndex) )
    
    editPlaylist(plPath, newOrder)


def showPlaylist(metaData, printer, plPath, urlWithoutId = None):
    '''
    printer can be print or some level of cfg.logger
    urlWithoutId is added if you wish to print out all full urls
    '''
    cfg.logger.critical(f"Playlist URL: {metaData['url']}")

    currentDir = getLocalSongs(plPath)

    if urlWithoutId != None:
        printer(f"i: Link                                         ->   Local Title")
        for i,songId in enumerate(metaData['ids']):
            url = f"{urlWithoutId}{songId}"
            printer(f"{i}: {url}  ->  {currentDir[i]}")



def compareMetaData(metaData, printer):
    '''Tool for comparing ids held in metadata and their order compared to remote playlist ids'''
    remoteIds = getIDs(metaData["url"])
    localIds = metaData["ids"]
    printer(f"i: Local ID    -> j: Remote ID")

    for i,localId in enumerate(localIds):
        if localId in remoteIds:
            j = remoteIds.index(localId)
            printer(f"{i}: {localId} -> {j}: {localId}")

        else:
            printer(f"{i}: {localId} ->  : ")


    for j, remoteId in enumerate(remoteIds):
        if remoteId not in localIds:

            printer(f" :             -> {j}: {remoteId}")