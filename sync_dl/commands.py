import os


import argparse

import shelve
import re
import ntpath
from random import randint


from sync_dl import noInterrupt
from sync_dl.ytdlWrappers import getIDs,getJsonPlData
from sync_dl.plManagement import editPlaylist, correctStateCorruption
from sync_dl.helpers import createNumLabel, smartSyncNewOrder, getLocalSongs, rename, relabel,download,getNumDigets
import sync_dl.config as cfg



def newPlaylist(plPath,url):
    if not os.path.exists(plPath):
        os.makedirs(plPath)

    elif len(os.listdir(path=plPath))!=0:
        cfg.logger.error(f"Directory Is Not Empty, Cannot Make Playlist in {plPath}")
        return
    

    cfg.logger.info(f"Creating New Playlist Named {ntpath.basename(plPath)} from URL: {url}")

    ids = getIDs(url)
    idsLen = len(ids)
    if idsLen == 0:
        cfg.logger.error(f"No Songs Found at {url}\nMake Sure the Playlist is Public!")
        return
        
    numDigits = getNumDigets(idsLen) #needed for creating starting number for auto ordering ie) 001, 0152

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        metaData["url"] = url
        metaData["ids"] = []

        invalidSongs = 0
        for i,songId in enumerate(ids):

            counter = f'{i+1}/{idsLen}'
            success = download(metaData,plPath,songId,-1,numDigits,counter)
            if not success:
                invalidSongs+=1

        cfg.logger.info(f"Downloaded {idsLen-invalidSongs}/{idsLen} Songs")


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
        numDigits = getNumDigets(idsLen)

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
        numDigits = getNumDigets(idsLen)

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

            with noInterrupt:
                rename(metaData,cfg.logger.debug,plPath,oldName,newName,i+1,metaData["ids"][i])

                metaData["ids"][i] = '' #wiped in case of crash, this blank entries can be removed restoring state


        newSongName = f"{createNumLabel(posistion,numDigits)}_" + ntpath.basename(songPath)

        with noInterrupt:
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
        numDigits = getNumDigets(idsLen)

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
        numDigits = getNumDigets(idsLen)


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


def moveRange(plPath, start, end, newStart):
    '''
    moves block of songs from start to end indices, to newStart
    ie) start = 4, end = 6, newStart = 2
    0 1 2 3 4 5 6 7 -> 0 1 4 5 6 2 3
    '''

    correctStateCorruption(plPath)

    if start == newStart:
        return

    currentDir = getLocalSongs(plPath)

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = getNumDigets(idsLen)


        if start>=idsLen:
            cfg.logger.error(f"No song has Index {start}, Largest Index is {idsLen-1}")
            return

        elif start<0:
            cfg.logger.error(f"No Song has a Negative Index")
            return
            
        #clamp end index
        if end>=idsLen or end == -1:
            end = idsLen-1

        elif end<=start:
            cfg.logger.error("End Index Must be Greater Than Start Index (or -1)")
            return

        #clamp newStart
        if newStart > idsLen:
            newStart = idsLen
        elif newStart < -1:
            newStart = -1
        
        # Sanatization over

        # number of elements to move
        blockSize = end-start+1

        # make room for block
        for i in reversed(range(newStart+1,idsLen)):
            oldName = currentDir[i]
            newIndex =i+blockSize
            relabel(metaData,cfg.logger.debug,plPath,oldName,i,newIndex,numDigits)
        

        #accounts for block of songs being shifted if start>newStart
        offset = 0
        if start>newStart:
            currentDir = getLocalSongs(plPath)
            offset = blockSize
        
        # shift block into gap made
        for i,oldIndex in enumerate(range(start,end+1)):

            oldName = currentDir[oldIndex]
            newIndex = i + newStart+1
            relabel(metaData,cfg.logger.debug,plPath,oldName,oldIndex+offset,newIndex,numDigits)

    # remove number gap in playlist and remove blanks in metadata
    correctStateCorruption(plPath)

# TODO not yet added to CLI
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


def showPlaylist(plPath, lineBreak='', urlWithoutId = "https://www.youtube.com/watch?v="):
    '''
    printer can be print or some level of cfg.logger
    lineBreak can be set to newline if you wish to format for small screens
    urlWithoutId is added if you wish to print out all full urls
    '''
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        cfg.logger.critical(f"Playlist URL: {metaData['url']}")

        currentDir = getLocalSongs(plPath)

        if urlWithoutId != None:
            spacer=' '*(len(urlWithoutId)+11)

            cfg.logger.critical(f"i: ID{spacer}{lineBreak}->   Local Title{lineBreak}")
            for i,songId in enumerate(metaData['ids']):
                url = f"{urlWithoutId}{songId}"
                cfg.logger.critical(f"{i}: {url}{lineBreak}  ->  {currentDir[i]}{lineBreak}")



def compareMetaData(plPath):
    '''Tool for comparing ids held in metadata and their order compared to remote playlist ids'''
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        remoteIds = getIDs(metaData["url"])
        localIds = metaData["ids"]
        cfg.logger.critical(f"i: Local ID    -> j: Remote ID")

        for i,localId in enumerate(localIds):
            if localId in remoteIds:
                j = remoteIds.index(localId)
                cfg.logger.critical(f"{i}: {localId} -> {j}: {localId}")

            else:
                cfg.logger.critical(f"{i}: {localId} ->  : ")


        for j, remoteId in enumerate(remoteIds):
            if remoteId not in localIds:

                cfg.logger.critical(f" :             -> {j}: {remoteId}")

def peek(url,fmt="{index}: {url} {title}"):
    '''
    prints out data about the playlist without downloading it, fmt parameters include:
        - id
        - url
        - title
        - description (currently bugged in youtube-dl, will always be none)
        - duration
        - view_count (currently bugged in youtube-dl, will always be none), 
        - uploader (currently bugged in youtube-dl, will always be none)
    '''
    
    plData = getJsonPlData(url)


    for i,songData in enumerate(plData):

        songData["url"] = "https://www.youtube.com/watch?v="+songData["url"]
        songStr = fmt.format(index = i,**songData)
        cfg.logger.critical(songStr)