import os
import logging
import re
import shelve

from sync_dl.ytdlWrappers import getIDs
from sync_dl.helpers import createNumLabel, smartSyncNewOrder,getLocalSongs,showMetaData,rename,download
import sync_dl.config as cfg

def _checkDeletions(cwd):
    '''
    checks if metadata has songs that are no longer in directory
    '''
    currentDir = getLocalSongs(cwd)

    #song numbers in currentDir
    currentDirNums = [int(re.match(cfg.filePrependRE,song).group()[:-1]) for song in currentDir]

    with shelve.open(f"{cwd}/{cfg.metaDataName}", 'c',writeback=True) as metaData:


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
                    os.rename(f"{cwd}/{oldName}",f"{cwd}/{newName}")

                    if newIndex in deleted:
                        # we only remove the deleted entry from metadata when its posistion has been filled
                        logging.info(f"Removing {metaData['ids'][newIndex]} from metadata")

                        #need to adjust for number already deleted
                        removedAlready = (numDeleted - len(deleted))
                        del metaData["ids"][newIndex - removedAlready] #removing via index error
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

def _checkBlanks(cwd):
    with shelve.open(f"{cwd}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        for i in reversed(range(len(metaData["ids"]))):
            songId = metaData['ids'][i]
            if songId == '':
                logging.warning(f'Blank MetaData id Found at Index {i}, removing')
                del metaData["ids"][i]

def _removeGaps(cwd):
    currentDir = getLocalSongs(cwd)

    numDidgets = len(str(len(currentDir)))

    for i,oldName in enumerate(currentDir):
        newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i,numDidgets)}_" , oldName)
        logging.info(f"Renaming {oldName} to {newName}")
        os.rename(f"{cwd}/{oldName}",f"{cwd}/{newName}")
        logging.info("Renaming Complete")

def correctStateCorruption(cwd):
    logging.info("Checking for playlist state Corruption")
    
    _checkBlanks(cwd) # must come first so later steps dont assume blanks are valid when checking len
    _checkDeletions(cwd) 


def editPlaylist(cwd, newOrder, deletions=False):
    '''
    metaData is json as defined in newPlaylist
    newOrder is an ordered list of tuples (Id of song, where to find it )
    the "where to find it" is the number in the old ordering (None if song is to be downloaded)
    '''
    #TODO add deletions

    currentDir = getLocalSongs(cwd)

    numDidgets = len(str(len(newOrder))) #needed for creating starting number for auto ordering ie) 001, 0152



    with shelve.open(f"{cwd}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        logging.info(f"Editing Playlist, Old order: {metaData['ids']}")
        for i in range(len(newOrder)):
            newId,oldIndex = newOrder[i]

            newIndex = len(newOrder) + i # we reorder the playlist with exclusivly new numbers in case a crash occurs

            if oldIndex == None: 
                # must download new song
                num = createNumLabel(newIndex,numDidgets)
                
                download(metaData,logging.info,cwd,num,newId,newIndex)
            
            else:
                #song exists locally, but must be reordered/renamed

                oldName = currentDir[oldIndex]

                newName = re.sub(cfg.filePrependRE, f"{createNumLabel(newIndex,numDidgets)}_" , oldName)

                if newName in currentDir:
                    logging.error(f"Naming Conflict {newName}")
                

                logging.info(f"Renaming {oldName} to {newName}")

                os.rename(f"{cwd}/{oldName}",f"{cwd}/{newName}")
                metaData["ids"].append(newId)
                metaData["ids"][oldIndex] = ''
                

                logging.info("Renaming Complete")

    _checkBlanks(cwd)
    _removeGaps(cwd)