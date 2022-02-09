import os

import shelve
import re
import ntpath
import shutil

from sync_dl import noInterrupt

from sync_dl.ytdlWrappers import getIDs, getIdsAndTitles,getJsonPlData
from sync_dl.plManagement import editPlaylist, correctStateCorruption, removePrepend
from sync_dl.helpers import createNumLabel, smartSyncNewOrder, getLocalSongs, rename, relabel,download,getNumDigets, numOccurance, getNthOccuranceIndex, getOrdinalIndicator, addTimestampsIfNoneExist, padZeros

from sync_dl.timestamps.scraping import scrapeCommentsForTimestamps
from sync_dl.timestamps.timestamps import createChapterFile, addTimestampsToChapterFile, applyChapterFileToSong, wipeChapterFile

import sync_dl.config as cfg



def newPlaylist(plPath,url):
    dirMade = False # if sync-dl cant download any songs, it will delete the directory only if it made it
    if not os.path.exists(plPath):
        dirMade = True
        os.makedirs(plPath)

    elif len(os.listdir(path=plPath))!=0:
        cfg.logger.error(f"Directory Exists and is Not Empty, Cannot Make Playlist in {plPath}")
        return
    

    cfg.logger.info(f"Creating New Playlist Named {ntpath.basename(plPath)} from URL: {url}")

    ids = getIDs(url)
    idsLen = len(ids)
    if idsLen == 0:
        cfg.logger.error(f"No Songs Found at {url}\nMake Sure the Playlist is Public!")
        answer = input("Proceed with Creating Empty Playlist (y)es/(n)o: ").lower().strip()
        if answer != 'y':
            os.rmdir(plPath)
            return
        
    numDigits = getNumDigets(idsLen) #needed for creating starting number for auto ordering ie) 001, 0152

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        metaData["url"] = url
        metaData["ids"] = []

        invalidSongs = 0
        for i,songId in enumerate(ids):

            counter = f'{i+1}/{idsLen}'
            songName = download(metaData,plPath,songId,-1,numDigits,counter)
            if not songName:
                invalidSongs+=1
                continue
            if cfg.autoScrapeCommentTimestamps:
                addTimestampsIfNoneExist(plPath, songName, songId)


        cfg.logger.info(f"Downloaded {idsLen-invalidSongs}/{idsLen} Songs")
    
    if (idsLen-invalidSongs == 0) and dirMade and idsLen!=0:
        cfg.logger.error(f"Unable to Download any Songs from {url}")
        answer = input("Proceed with Creating Empty Playlist (y)es/(n)o: ").lower().strip()
        if answer != 'y':
            shutil.rmtree(plPath)


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



    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)
        url = metaData["url"]
        localIds = metaData["ids"]

    remoteIds = getIDs(url)


    newOrder = smartSyncNewOrder(localIds,remoteIds)

    editPlaylist(plPath,newOrder)


def appendNew(plPath):
    '''will append new songs in remote playlist to local playlist in order that they appear'''

    cfg.logger.info("Appending New Songs...")


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        idsLen = len(metaData["ids"])
        numDigits = getNumDigets(idsLen)

        remoteIds = getIDs(metaData['url'])

        for remoteId in remoteIds:
            if remoteId not in metaData['ids']:
                songName = download(metaData,plPath,remoteId,idsLen,numDigits)
                if songName and cfg.autoScrapeCommentTimestamps:
                    addTimestampsIfNoneExist(plPath, songName, remoteId)



def manualAdd(plPath, songPath, posistion):
    '''put song in posistion in the playlist'''

    if not os.path.exists(songPath):
        cfg.logger.error(f'{songPath} Does Not Exist')
        return

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        currentDir = getLocalSongs(plPath)

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


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        currentDir = getLocalSongs(plPath)

        idsLen = len(metaData["ids"])
        numDigits = getNumDigets(idsLen)

        if index1>=idsLen or index2>=idsLen:
            cfg.logger.error(f"Given Index is Larger than Max {idsLen-1}")
            return
        elif index1<0 or index2<0:
            cfg.logger.error(f"Given Index is Negative")
            return

        cfg.logger.info(f"Swapping: \n{currentDir[index1]} \nand \n{currentDir[index2]}")
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


# move is no longer used in CLI, functionality has been merged with moveRange to be more consistant
# move is still used in integration tests to reorder playlists before testing smart sync
def move(plPath, currentIndex, newIndex):
    if currentIndex==newIndex:
        cfg.logger.info("Indexes Are the Same")
        return


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        currentDir = getLocalSongs(plPath)

        idsLen = len(metaData["ids"])
        numDigits = getNumDigets(idsLen)


        if currentIndex>=idsLen:
            cfg.logger.error(f"No song has Index {currentIndex}, Largest Index is {idsLen-1}")
            return
        elif currentIndex<0:
            cfg.logger.error(f"No Song has a Negative Index")
            return

        #clamp newIndex
        if newIndex >= idsLen:
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
    moves block of songs from start to end indices, to after newStart
    ie) start = 4, end = 6, newStart = 2
    0 1 2 3 4 5 6 7 -> 0 1 2 4 5 6 3
    '''    

    if start == newStart:
        return


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        currentDir = getLocalSongs(plPath)
        
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

        elif end<start:
            cfg.logger.error("End Index Must be Greater Than or Equal To Start Index (or -1)")
            return

        #clamp newStart
        if newStart >= idsLen:
            newStart = idsLen - 1
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
        correctStateCorruption(plPath,metaData)
    
    # logged changes
    startSong = re.sub(cfg.filePrependRE,"",currentDir[start])
    endSong = re.sub(cfg.filePrependRE,"",currentDir[end])
    leaderSong = re.sub(cfg.filePrependRE,"",currentDir[newStart]) # the name of the song the range will come after

    ######## Single song moved ##########
    if start==end:
        cfg.logger.info(f"Song {start}: {startSong}")        
        if newStart == -1:
            cfg.logger.info(f"Is Now First in The Playlist")        
        else:
            cfg.logger.info(f"Is Now After Song {newStart}: {leaderSong}")       

        return 
    #####################################


    ####### Multiple Songs Moved ########
    cfg.logger.info(f"Moved Songs in Range [{start}, {end}] to After {newStart}")
    
    cfg.logger.info(f"Start Range:   {startSong}")
    cfg.logger.info(f"End Range:     {endSong}")

    if newStart != -1: 
        leaderSong = re.sub(cfg.filePrependRE,"",currentDir[newStart]) # the name of the song the range will come after
        cfg.logger.info(f"Are Now After: {leaderSong}")
    else:
        cfg.logger.info(f"Are Now First in the Playlist")
    
    ######################################



# TODO not yet added to CLI (doesnt seem useful)
def shuffle(plPath):
    '''randomizes playlist order'''
    from random import randint

    cfg.logger.info("Shuffling Playlist")
    

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

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
    lineBreak can be set to newline if you wish to format for small screens
    urlWithoutId is added if you wish to print out all full urls
    '''
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        cfg.logger.info(f"Playlist URL: {metaData['url']}")

        correctStateCorruption(plPath,metaData)
        
        currentDir = getLocalSongs(plPath)

        maxNum = len(currentDir)
        numDigits = len(str(maxNum))

        if urlWithoutId != None:
            spacer=' '*(len(urlWithoutId)+10)

            cfg.logger.info(f"{' '*numDigits}: URL{spacer}{lineBreak}-> Local Title{lineBreak}")
            for i,songId in enumerate(metaData['ids']):
                url = f"{urlWithoutId}{songId}"
                title = re.sub(cfg.filePrependRE, '' , currentDir[i])
                cfg.logger.info(f"{str(i).zfill(numDigits)}: {url}{lineBreak}  ->  {title}{lineBreak}")



def compareMetaData(plPath):
    '''Tool for comparing ids held in metadata and their order compared to remote playlist ids'''
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath, metaData)
        
        remoteIds, remoteTitles = getIdsAndTitles(metaData["url"])
        localIds = metaData["ids"]
        assert isinstance(localIds, list)
        currentDir = getLocalSongs(plPath)

        maxNum = max(len(localIds), len(remoteIds))
        numDigits = len(str(maxNum))
        

        cfg.logger.info(f"\n==================[Playlist Data]==================")
        cfg.logger.info(f"{' '*numDigits}: Local ID    -> {' '*numDigits}: Remote ID   : Title")

        inLocalNotRemote = []
        inRemoteNotLocal = [(i,numOccurance(remoteIds, i),remoteId,remoteTitles[i]) for i,remoteId in enumerate(remoteIds)]

        for i,localId in enumerate(localIds):
            localOccuranceNum = numOccurance(localIds, i)

            title = re.sub(cfg.filePrependRE, '' , currentDir[i])
            remoteIndex = getNthOccuranceIndex(remoteIds, localId, localOccuranceNum)
            if remoteIndex is not None:
                cfg.logger.info(f"{str(i).zfill(numDigits)}: {localId} -> {str(remoteIndex).zfill(numDigits)}: {localId} : {title}")
                inRemoteNotLocal[remoteIndex] = None

            else:
                cfg.logger.info(f"{str(i).zfill(numDigits)}: {localId} -> {' '*numDigits}:             : {title}")
                inLocalNotRemote.append((i,localOccuranceNum,localId,title))


        j=0
        while j<len(inRemoteNotLocal):
            item = inRemoteNotLocal[j]
            if item == None:
                inRemoteNotLocal.pop(j)
                continue
            j,_ , remoteId, title = item
            cfg.logger.info(f"{' '*numDigits}:             -> {str(j).zfill(numDigits)}: {remoteId} : {title}")
            j+=1

        # summery
        cfg.logger.info(f"\n=====================[Summary]=====================")

        if len(inLocalNotRemote)>0:
            cfg.logger.info(f"\n------------[In Local But Not In Remote]-----------")
            cfg.logger.info(f"{' '*numDigits}: Local ID    : Local Title")
            for i, localOccuranceNum, localId, title in inLocalNotRemote:
                    occuranceText = '' if localOccuranceNum == 0 else f' : {str(localOccuranceNum+1)}{getOrdinalIndicator(localOccuranceNum+1)} Occurance'
                    cfg.logger.info(f"{str(i).zfill(numDigits)}: {localId} : {title}{occuranceText}")

        if len(inRemoteNotLocal)>0:
            cfg.logger.info(f"\n------------[In Remote But Not In Local]-----------")
            cfg.logger.info(f"{' '*numDigits}: Remote ID   : Remote Title")
            for j, remoteOccuranceNum, remoteId, title in inRemoteNotLocal:
                    occuranceText = '' if remoteOccuranceNum== 0 else f' : {str(remoteOccuranceNum+1)}{getOrdinalIndicator(remoteOccuranceNum+1)} Occurance'
                    cfg.logger.info(f"{str(j).zfill(numDigits)}: {remoteId} : {title}{occuranceText}")

        if len(inLocalNotRemote) == 0 and len(inRemoteNotLocal) == 0:
            cfg.logger.info(f"Local And Remote Contain The Same Songs")

         

def peek(urlOrPlName,fmt="{index}: {url} {title}"):
    '''
    prints out data about the playlist without downloading it, fmt parameters include:
        - id
        - url
        - title
        - duration
        - view_count (currently bugged in youtube-dl, will always be none)
        - uploader (soon to be fixed in youtube-dl)
    '''
    
    # check if urlOrPlName is playlist name
    if not cfg.musicDir:
        musicPath = os.getcwd()
    else:
        musicPath = cfg.musicDir

    musicDir = os.listdir(path= musicPath) 

    if urlOrPlName in musicDir:
        with shelve.open(f"{musicPath}/{urlOrPlName}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            urlOrPlName = metaData['url']


    # at this point urlOrPlName is a url
    plData = getJsonPlData(urlOrPlName)

    for i,songData in enumerate(plData):
        songStr = fmt.format(index = i,**songData)
        cfg.logger.info(songStr)


def togglePrepends(plPath):
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        if "removePrependOrder" in metaData:
            # prepends where removed, hence we must add them
            correctStateCorruption(plPath,metaData) # part of correcting state corruption is re-adding prepends 
            cfg.logger.info("Prepends Added")
            return
        removePrepend(plPath,metaData)
        cfg.logger.info("Prepends Removed")


def addTimestampsFromComments(plPath, start, end, autoAccept = False, overwrite = False, autoOverwrite = False):

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        correctStateCorruption(plPath,metaData)

        currentDir = getLocalSongs(plPath)
        idsLen = len(metaData["ids"])

        ### Sanitize Inputs ###
        if start >= idsLen:
            cfg.logger.error(f"No song has Index {start}, Largest Index is {idsLen-1}")
            return

        elif start < 0:
            cfg.logger.error(f"No Song has a Negative Index")
            return
            
        #clamp end index
        if end >= idsLen or end == -1:
            end = idsLen-1

        elif end < start:
            cfg.logger.error("End Index Must be Greater Than or Equal To Start Index (or -1)")
            return
        ### Sanitize Inputs Over ###


        multipleSongs = start!=end
        for i in range(start,end+1):

            if autoOverwrite and not overwrite:
                cfg.logger.error("auto-overwrite can only be enabled if overwrite is")
                return

            if autoOverwrite and not autoAccept:
                cfg.logger.error("auto-overwrite can only be enabled if auto-accept is")
                return

            songName = currentDir[i]
            songPath = f"{plPath}/{songName}"
            videoId = metaData['ids'][i]

            if not createChapterFile(songPath, songName):
                continue

            # Check for existing chapters in ffmpegMetadata file, wipe them, and prompt user to continue
            existingTimestamps = wipeChapterFile()
            if len(existingTimestamps) > 0:
                if not overwrite:
                    cfg.logger.info(f"{i}: Existing Timestamps Detected on Song: {songName}\nSkipping...\n")
                    continue

            # Get timestamps
            cfg.logger.info(f"{i}: Scraping Comments for Timestamps of Song: {songName}")
            timestamps = scrapeCommentsForTimestamps(videoId)

            if len(timestamps) == 0:
                cfg.logger.info(f"No Timestamps Found\n")
                continue

            if existingTimestamps == timestamps:
                cfg.logger.info("Timestamps Found are Idential to Existing Timestamps\n")
                continue

            if len(existingTimestamps) > 0:
                if not overwrite:
                    cfg.logger.info("Comment Timestamps and Existing Timestamps Found but Overwrite is Disabled\n")
                    continue

                # existing timestamps, plus timestamps found
                cfg.logger.info(f"\nExisting Timestamps Found:")
                numDigitsExistingTimestamps = len(str(len(existingTimestamps)))
                numDigitsCommentTimestamps = len(str(len(timestamps)))
                for i,timestamp in enumerate(existingTimestamps):
                    leadChar = ' '
                    if timestamp not in timestamps:
                        leadChar = '-'
                    cfg.logger.info(f"{leadChar} {padZeros(i, numDigitsExistingTimestamps)}) {timestamp}")
                cfg.logger.info(f"\nComment Timestamps Found:")
                for i,timestamp in enumerate(timestamps):
                    leadChar = ' '
                    if timestamp not in existingTimestamps:
                        leadChar = '+'
                    cfg.logger.info(f"{leadChar} {padZeros(i, numDigitsCommentTimestamps)}) {timestamp}")

                cfg.logger.info('\n')

                if autoOverwrite and autoAccept:
                    cfg.logger.info("Auto Overwriting\n")

                else:
                    cfg.logger.info("Existing and Comment Timestamps Found")
                    response = (input(f"OVERWRITE Timestamps for: {songName}? \n[y]es, [n]o" + (", [a]uto-overwrite/accepts, [d]eny-overwrites" if multipleSongs else "") + ":")).lower()
                    if response == 'a':
                        autoAccept = True
                        overwrite = True
                        autoOverwrite = True
                    elif response == 'd':
                        overwrite = False
                        continue
                    elif response != 'y' and response != 'a':
                        cfg.logger.info('\n')
                        continue

            else:
                # comment timestamps found, no existing timestamps found
                cfg.logger.info(f"\nComment Timestamps Found:")
                for timestamp in timestamps:
                    cfg.logger.info(timestamp)
                cfg.logger.info('\n')

                
                if not autoAccept:
                    response = (input(f"\nAccept Timestamps for: {songName}? \n[y]es, [n]o" + (", [a]uto-accept" if multipleSongs else "") + ":")).lower()
                    if response == 'a':
                        autoAccept = True
                    if response != 'y' and response != 'a':
                        cfg.logger.info('\n')
                        continue
                else:
                    cfg.logger.info("Auto Accepting Timestamps")

            addTimestampsToChapterFile(timestamps, songPath)

            if not applyChapterFileToSong(songPath, songName):
                cfg.logger.error(f"Failed to Add Timestamps To Song {songName}\n")
                continue

            cfg.logger.info("Timestamps Applied!\n")



