import os
import logging
import re
import shelve

from ytdlWrappers import getIDs
from helpers import createNumLabel, smartSyncNewOrder,getLocalSongs,showMetaData,rename,download
import config as cfg

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
            logging.info(f"songs numbered {deleted} are no longer in playlist")

            numDidgets = len(str( len(metaData["ids"]) - numDeleted ))
            newIndex = 0

            for newIndex, oldIndex in enumerate(currentDirNums):
                print(newIndex,oldIndex)
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
                print(index,removedAlready)
                logging.info(f"Removing {metaData['ids'][index - removedAlready]} from metadata")
                del metaData["ids"][index - removedAlready]
                del deleted[0]

def _checkBlanks(cwd):
    with shelve.open(f"{cwd}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        for i,songId in metaData["ids"]:
            if songId == '':
                del metaData["ids"][i]

def correctStateCorruption(cwd):
    logging.info("Checking for playlist state Corruption")
    _checkDeletions(cwd)
    _checkBlanks(cwd)



def editPlaylist(cwd, newOrder):
    '''
    metaData is json as defined in newPlaylist
    newOrder is an ordered list of tuples (Id of song, where to find it )
    the "where to find it" is the number in the old ordering (None if song is to be downloaded)
    '''

    #files will be labled with several numbers then an underscore, followed by the file name

    currentDir = getLocalSongs(cwd)

    numDidgets = len(str(len(newOrder))) #needed for creating starting number for auto ordering ie) 001, 0152

    with shelve.open(f"{cwd}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        logging.info(f"Editing Playlist, \nOld order:\n {metaData['ids']}")

        for i in range(len(newOrder)):
            newId,oldIndex = newOrder[i]


            if oldIndex == None: 
                # must download new song
                num = createNumLabel(i,numDidgets)
                
                download(metaData,logging.info,cwd,num,newId,i)

            else:
                #song exists locally, but must be reordered/renamed

                if i == oldIndex:
                    # song is already in correct posisiton
                    continue

                oldName = currentDir[oldIndex]

                newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i,numDidgets)}_" , oldName)

                if newName in currentDir:
                    logging.error(f"Naming Conflict {newName}")
                    #TODO solve this naming conflict possibility (will only occur if 2 different songs have the same name and one is moving
                    # into the posistion that the other once had)
                    pass
                
                rename(metaData,logging.info,cwd,oldName,newName,i,newId)

    


    #TODO Deletions? ie if old order contains songs which arent in new order, likley should also ask for permission
    # check if song actually exists
