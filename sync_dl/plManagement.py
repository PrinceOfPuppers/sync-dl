import os
import re
import shelve

from sync_dl import noInterrupt
from sync_dl.ytdlWrappers import getIDs
from sync_dl.helpers import createNumLabel, smartSyncNewOrder,getLocalSongs,download, delete, relabel
import sync_dl.config as cfg

def _checkDeletions(plPath):
    '''
    checks if metadata has songs that are no longer in directory
    '''
    currentDir = getLocalSongs(plPath)



    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

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

def _checkBlanks(plPath):
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
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

def correctStateCorruption(plPath):
    cfg.logger.debug("Checking for playlist state Corruption")

    _checkBlanks(plPath) # must come first so later steps dont assume blanks are valid when checking len

    _checkDeletions(plPath) 

    _removeGaps(plPath) # must come after check deletions (if user manually deletes, then we only have number
                     # on song to go off of, hence removing gaps by chaning the numbers would break this)


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
                download(metaData,plPath,newId,newIndex,numDigets)

            
            else:
                #song exists locally, but must be reordered/renamed

                oldName = currentDir[oldIndex]

                relabel(metaData,cfg.logger.debug,plPath,oldName,oldIndex,newIndex,numDigets)


    if deletions:
        oldIndices = [item[1] for item in newOrder]
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            for i in reversed(range(len(currentDir))):
                if i not in oldIndices:
                    delete(metaData,plPath,currentDir[i],i)

    _checkBlanks(plPath)
    _removeGaps(plPath)