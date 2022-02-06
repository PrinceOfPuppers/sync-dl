import os
import re
import shelve

from sync_dl import noInterrupt
from sync_dl.helpers import createNumLabel, getLocalSongs,download, delete, relabel, getNumDigets, getSongNum, addTimestampsIfNoneExist
import sync_dl.config as cfg

def _checkDeletions(plPath,metaData):
    '''
    checks if metadata has songs that are no longer in directory
    '''
    currentDir = getLocalSongs(plPath)
    idsLen = len(metaData['ids'])

    # there have been no deletions, however there may be a gap in numberings
    # which would be falsely detected as a deletion if this check wheren't here
    if idsLen == len(currentDir):
        return

    #song numbers in currentDir
    currentDirNums = [int(re.match(cfg.filePrependRE,song).group()[:-1]) for song in currentDir]
    
    numRange = range(idsLen)

    #difference between whats in the folder and whats in metadata
    deleted = [i for i in numRange if i not in currentDirNums]
    numDeleted = len(deleted)

    if numDeleted > 0:
        cfg.logger.debug(f"songs numbered {deleted} are no longer in playlist")

        numDidgets = len(str( len(metaData["ids"]) - numDeleted ))
        newIndex = 0

        for newIndex, oldIndex in enumerate(currentDirNums):
            if newIndex != oldIndex:
                oldName = currentDir[newIndex]
                newName = re.sub(cfg.filePrependRE, f"{createNumLabel(newIndex,numDidgets)}_" , oldName)

                with noInterrupt:
                    cfg.logger.debug(f"Renaming {oldName} to {newName}")
                    os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")

                    if newIndex in deleted:
                        # we only remove the deleted entry from metadata when its posistion has been filled
                        cfg.logger.debug(f"Removing {metaData['ids'][newIndex]} from metadata")

                        #need to adjust for number already deleted
                        removedAlready = (numDeleted - len(deleted))
                        del metaData["ids"][newIndex - removedAlready]
                        del deleted[0]

                    cfg.logger.debug("Renaming Complete")
        


        while len(deleted)!=0:
            index = deleted[0]
            # we remove any remaining deleted entries from metadata 
            # note even if the program crashed at this point, running this fuction
            # again would yeild an uncorrupted state
            removedAlready = (numDeleted - len(deleted))
            with noInterrupt:
                cfg.logger.debug(f"Removing {metaData['ids'][index - removedAlready]} from metadata")
                del metaData["ids"][index - removedAlready]
                del deleted[0]

def _checkBlanks(plPath,metaData):
    for i in reversed(range(len(metaData["ids"]))):
        songId = metaData['ids'][i]
        if songId == '':
            cfg.logger.debug(f'Blank MetaData id Found at Index {i}, removing')
            del metaData["ids"][i]

def _removeGaps(plPath):
    currentDir = getLocalSongs(plPath)
    numDidgets = len(str(len(currentDir)))

    for i,oldName in enumerate(currentDir):
        newPrepend = f"{createNumLabel(i,numDidgets)}_"
        oldPrepend = re.search(cfg.filePrependRE, oldName).group(0)
        if oldPrepend!=newPrepend:
            newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i,numDidgets)}_" , oldName)
            cfg.logger.debug(f"Renaming {oldName} to {newName}")
            os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")
            cfg.logger.debug("Renaming Complete")



def _restorePrepend(plPath,metaData):

    if "removePrependOrder" not in metaData:
        #prepends already restored 
        return
    
    cfg.logger.debug("Restoring Prepends")
    
    currentDir = os.listdir(path=plPath)
    idsLen = len(metaData["ids"])
    numDigets = getNumDigets(idsLen)

    for file in currentDir:
        try:
            index = metaData["removePrependOrder"][file]
        except KeyError:
            # file isn't in playlist (or its the metadata
            continue

        # at this point we add the prepend to the file
        label = createNumLabel(index,numDigets)

        cfg.logger.debug(f"Adding Prepend {label} to {file}")
        with noInterrupt:
            os.rename(f"{plPath}/{file}",f"{plPath}/{label}_{file}")

            # removed item from dictionary to prevent double restoring 
            del metaData["removePrependOrder"][file]

    # metaData["removePrependOrder"] is removed, this is used to signal that all the prepends are there 
    # and the playlist can be treated like normal

    del metaData["removePrependOrder"]


def correctStateCorruption(plPath,metaData):
    cfg.logger.debug("Checking for playlist state Corruption")

    _checkBlanks(plPath,metaData) # must come first so later steps dont assume blanks are valid when checking len

    _restorePrepend(plPath,metaData) # can only restore if prepends where removed by remove prepends

    _checkDeletions(plPath,metaData) 

    _removeGaps(plPath) # must come after check deletions (if user manually deletes, then we only have number
                     # on song to go off of, hence removing gaps by chaning the numbers would break this)


def removePrepend(plPath, metaData):    
    #TODO this step might be unnessisary because its already done in togglePrepend
    if "removePrependOrder" in metaData:
        # prepends already removed or partially removed 
        return
    
    currentDir = getLocalSongs(plPath)

    metaData["removePrependOrder"] = {}

    for oldName in currentDir:
        index = getSongNum(oldName)
        newName = re.sub(cfg.filePrependRE, "" , oldName)

        with noInterrupt:
            os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")
            metaData["removePrependOrder"][newName] = index


def editPlaylist(plPath, newOrder, deletions=False):
    '''
    metaData is json as defined in newPlaylist
    newOrder is an ordered list of tuples (Id of song, where to find it )
    the "where to find it" is the number in the old ordering (None if song is to be downloaded)

    note if song is in playlist already the id of song in newOrder will not be used
    '''

    currentDir = getLocalSongs(plPath)
    numDigets = len(str(2*len(newOrder))) #needed for creating starting number for auto ordering ie) 001, 0152
                                           # len is doubled because we will be first numbering with numbers above the
                                           # so state remains recoverable in event of crash

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        idsLen = len(metaData['ids'])
        cfg.logger.info(f"Editing Playlist...")
        cfg.logger.debug(f"Old Order: {metaData['ids']}")

        for i in range(len(newOrder)):
            newId,oldIndex = newOrder[i]
            newIndex = idsLen + i # we reorder the playlist with exclusivly new numbers in case a crash occurs

            if oldIndex == None: 
                # must download new song
                songName = download(metaData,plPath,newId,newIndex,numDigets)
                if songName and cfg.autoScrapeCommentTimestamps:
                    addTimestampsIfNoneExist(plPath, songName, newId)
            
            else:
                #song exists locally, but must be reordered/renamed
                oldName = currentDir[oldIndex]
                relabel(metaData,cfg.logger.debug,plPath,oldName,oldIndex,newIndex,numDigets)


        if deletions:
            oldIndices = [item[1] for item in newOrder]

            for i in reversed(range(len(currentDir))):
                if i not in oldIndices:
                    delete(metaData,plPath,currentDir[i],i)
        
        _checkBlanks(plPath,metaData)
        _removeGaps(plPath)
