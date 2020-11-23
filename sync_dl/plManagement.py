import os
import logging
import re
import shelve

from sync_dl.ytdlWrappers import getIDs
from sync_dl.helpers import createNumLabel, smartSyncNewOrder,getLocalSongs,download, delete, relabel
import sync_dl.config as cfg

def _checkDeletions(plPath):
    '''
    checks if metadata has songs that are no longer in directory
    '''
    currentDir = getLocalSongs(plPath)

    #song numbers in currentDir
    currentDirNums = [int(re.match(cfg.filePrependRE,song).group()[:-1]) for song in currentDir]

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:


        numRange = range(len(metaData['ids']))

        #difference between whats in the folder and whats in metadata
        deleted = [i for i in numRange if i not in currentDirNums]
        

        numDeleted = len(deleted)


        if numDeleted > 0:
            logging.warning(f"songs numbered {deleted} are no longer in playlist")

            numDidgets = len(str( len(metaData["ids"]) - numDeleted ))
            newIndex = 0

            for newIndex, oldIndex in enumerate(currentDirNums):
                if newIndex != oldIndex:
                    oldName = currentDir[newIndex]
                    newName = re.sub(cfg.filePrependRE, f"{createNumLabel(newIndex,numDidgets)}_" , oldName)
                    logging.info(f"Renaming {oldName} to {newName}")
                    os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")

                    if newIndex in deleted:
                        # we only remove the deleted entry from metadata when its posistion has been filled
                        logging.info(f"Removing {metaData['ids'][newIndex]} from metadata")

                        #need to adjust for number already deleted
                        removedAlready = (numDeleted - len(deleted))
                        del metaData["ids"][newIndex - removedAlready]
                        del deleted[0]

                    logging.info("Renaming Complete")
            


            while len(deleted)!=0:
                index = deleted[0]

                # we remove any remaining deleted entries from metadata 
                # note even if the program crashed at this point, running this fuction
                # again would yeild an uncorrupted state
                removedAlready = (numDeleted - len(deleted))
                logging.info(f"Removing {metaData['ids'][index - removedAlready]} from metadata")
                del metaData["ids"][index - removedAlready]
                del deleted[0]

def _checkBlanks(plPath):
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        for i in reversed(range(len(metaData["ids"]))):
            songId = metaData['ids'][i]
            if songId == '':
                logging.warning(f'Blank MetaData id Found at Index {i}, removing')
                del metaData["ids"][i]

def _removeGaps(plPath):
    currentDir = getLocalSongs(plPath)

    numDidgets = len(str(len(currentDir)))

    for i,oldName in enumerate(currentDir):
        newPrepend = f"{createNumLabel(i,numDidgets)}_"
        oldPrepend = re.search(cfg.filePrependRE, oldName).group(0)
        if oldPrepend!=newPrepend:
            newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i,numDidgets)}_" , oldName)
            logging.info(f"Renaming {oldName} to {newName}")
            os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")
            logging.info("Renaming Complete")

def correctStateCorruption(plPath):
    logging.info("Checking for playlist state Corruption")

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

        logging.info(f"Editing Playlist, Old order: {metaData['ids']}")
        for i in range(len(newOrder)):
            newId,oldIndex = newOrder[i]

            newIndex = len(newOrder) + i # we reorder the playlist with exclusivly new numbers in case a crash occurs

            if oldIndex == None: 
                # must download new song
                download(metaData,logging.info,plPath,newId,newIndex,numDigets)

            
            else:
                #song exists locally, but must be reordered/renamed

                oldName = currentDir[oldIndex]

                relabel(metaData,logging.info,plPath,oldName,oldIndex,newIndex,numDigets)


    if deletions:
        oldIndices = [item[1] for item in newOrder]
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            for i in reversed(range(len(currentDir))):
                if i not in oldIndices:
                    while True:
                        answer = input(f"Would you like to Delete {currentDir[i]}? (y)es, (n)o: ")

                        if answer == 'y' or answer == 'Y':
                            delete(metaData,logging.info,plPath,currentDir[i],i)
                            break

                        elif answer == 'n' or answer == 'N':
                            break
    _checkBlanks(plPath)
    _removeGaps(plPath)