import os
import logging

import argparse

import shelve
import re
import ntpath
from random import randint

from sync_dl.ytdlWrappers import getIDs, downloadID
from sync_dl.plManagement import editPlaylist, correctStateCorruption
from sync_dl.helpers import createNumLabel, smartSyncNewOrder,showPlaylist, getLocalSongs, rename, compareMetaData, relabel,download
import sync_dl.config as cfg

def newPlaylist(plPath,url):
    if not os.path.exists(plPath):
        os.makedirs(plPath)

    elif len(os.listdir(path=plPath))!=0:
        logging.error(f"Directory Is Not Empty, Cannot Make Playlist in {plPath}")
        return

    logging.info(f"Creating New Playlist Named {ntpath.basename(plPath)} from URL: {url}")

    ids = getIDs(url)
    numDigits = len(str( len(ids) + 1)) #needed for creating starting number for auto ordering ie) 001, 0152

    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        metaData["url"] = url
        metaData["ids"] = []

        invalidSongs = 0
        for i,songId in enumerate(ids):
            num = createNumLabel(i,numDigits)

            logging.info(f"Dowloading song Id {songId}")
            if downloadID(songId,plPath,num):
                metaData["ids"].append(songId)
                logging.debug("Download Complete")
            else:
                invalidSongs+=1

        logging.info(f"Downloaded {len(ids)-invalidSongs}/{len(ids)} Songs")


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
    logging.info("Smart Syncing...")
    correctStateCorruption(plPath)


    existingFiles = os.listdir(path=f"{plPath}")
    if cfg.metaDataName not in existingFiles:
        print("Current Directory is Not Existing Playlist")
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

    logging.info("Appending New Songs...")

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
        logging.error(f'{songPath} Does Not Exist')
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
        
        logging.info(f"Adding {ntpath.basename(songPath)} to {ntpath.basename(plPath)} in Posistion {posistion}")

        #shifting elements
        for i in reversed(range(posistion, idsLen)):
            oldName = currentDir[i]

            newName = re.sub(cfg.filePrependRE, f"{createNumLabel(i+1,numDigits)}_" , oldName)

            rename(metaData,logging.debug,plPath,oldName,newName,i+1,metaData["ids"][i])

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
        logging.info(f"Given Index are the Same")


    correctStateCorruption(plPath)

    currentDir = getLocalSongs(plPath)



    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))

        if index1>=idsLen or index2>=idsLen:
            logging.error(f"Given Index is Larger than Max {idsLen-1}")
            return
        elif index1<0 or index2<0:
            logging.error(f"Given Index is Negative")
            return

        logging.info(f"Swapping {currentDir[index1]} and {currentDir[index2]}")
        #shift index1 out of the way (to idsLen)

        oldName = currentDir[index1]
        tempName = relabel(metaData,logging.debug,plPath,oldName,index1,idsLen,numDigits)

        
        #move index2 to index1's old location

        oldName = currentDir[index2]
        relabel(metaData,logging.debug,plPath,oldName,index2,index1,numDigits)

        #move index1 (now =idsLen) to index2's old location

        oldName = tempName
        relabel(metaData,logging.debug,plPath,oldName,idsLen,index2,numDigits)

        del metaData["ids"][idsLen]

def move(plPath, currentIndex, newIndex):
    if currentIndex==newIndex:
        logging.info("Indexes Are the Same")
        return


    correctStateCorruption(plPath)

    currentDir = getLocalSongs(plPath)


    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:

        idsLen = len(metaData["ids"])
        numDigits = len(str( idsLen + 1 ))


        if currentIndex>=idsLen:
            logging.error(f"No song has Index {currentIndex}, Largest Index is {idsLen-1}")
            return
        elif currentIndex<0:
            logging.error(f"No Song has a Negative Index")
            return

        #clamp newIndex
        if newIndex > idsLen:
            newIndex = idsLen
        elif newIndex < 0:
            newIndex = 0
        
        logging.info(f"Moving {currentDir[currentIndex]} to Index {newIndex}")
        
        #moves song to end of list
        tempName = relabel(metaData,logging.debug,plPath,currentDir[currentIndex],currentIndex,idsLen,numDigits)

        if currentIndex>newIndex:
            #shifts all songs from newIndex to currentIndex-1 by +1
            for i in reversed(range(newIndex,currentIndex)):
                
                oldName = currentDir[i]
                relabel(metaData,logging.debug,plPath,oldName,i,i+1,numDigits)
    
        
        else:
            #shifts all songs from currentIndex+1 to newIndex by -1
            for i in range(currentIndex+1,newIndex+1):
                oldName = currentDir[i]
                relabel(metaData,logging.debug,plPath,oldName,i,i-1,numDigits)
        
        #moves song back
        relabel(metaData,logging.debug,plPath,tempName,idsLen,newIndex,numDigits)
        del metaData['ids'][idsLen]



def shuffle(plPath):
    '''randomizes playlist order'''
    logging.info("Shuffling Playlist")
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

    
#modified version of help formatter which only prints args once in help message
class ArgsOnce(argparse.HelpFormatter):
    def __init__(self,prog):
        super().__init__(prog,max_help_position=40)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            metavar, = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []

            if action.nargs == 0:
                parts.extend(action.option_strings)

            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                for option_string in action.option_strings:
                    parts.append('%s' % option_string)
                parts[-1] += ' %s'%args_string
            return ', '.join(parts)



if __name__ == "__main__":
    description = ("An application for downloading and syncing remote playlists to your computer. Created to avoid having\n"
                    "music deleted but still have the convenience of browsing and adding and reordering new music using\n"
                    "remote services such as youtube.")


    parser = argparse.ArgumentParser(description=description,formatter_class=ArgsOnce)

    #posistional
    parser.add_argument('PLAYLIST', type=str, help='the name of the directory for the playlist')

    #playlist managing
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-n','--new-playlist', metavar='URL', type=str, help='downloads new playlist from URL with name PLAYLIST')
    group.add_argument('-s','--smart-sync', action='store_true', help='apply smart sync local playlist with remote playlist')
    group.add_argument('-a','--append-new', action='store_true', help='append new songs in remote playlist to end of local playlist')

    group.add_argument('-M','--manual-add',nargs=2, metavar=('PATH','INDEX'), type=str, help = 'manually add song at PATH to playlist in posistion INDEX')

    group.add_argument('-m','--move',nargs=2, metavar=('I1','I2'), type = int, help='moves song index I1 to I2 in local playlist')
    group.add_argument('-w','--swap',nargs=2, metavar=('I1','I2'), type = int, help='swaps order of songs index I1 and I2')
    
    
    parser.add_argument('-l','--local-dir',metavar='PATH',type=str, help='sets local music directory to PATH, overrides current working directory and manages playlists in PATH in the future' )
    
    parser.add_argument('-v','--verbose',action='store_true', help='runs application in verbose mode' )
    parser.add_argument('-q','--quiet',action='store_true', help='runs application with no print outs' )

    #info 
    parser.add_argument('-p','--print',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )
    parser.add_argument('-d','--view-metadata',action='store_true', help='prints out playlist metadata information compared to remote playlist information' )
    

    args = parser.parse_args()

    #verbosity
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
        )
    elif args.quiet:
        logging.basicConfig(level=logging.ERROR,
        format="[%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler()]
        )
    else:
        logging.basicConfig(level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()]
        )


    #setting and getting cwd
    if args.local_dir:
        #TODO edit config file adding music folder
        cwd = args.local_dir
        pass
    else:
        #TODO get config file music folder if avalible
        cwd = os.getcwd()

    plPath = f"{cwd}/{args.playlist}"



    #viewing playlist     
    if args.print:
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            showPlaylist(metaData,print,plPath,"https://www.youtube.com/watch?v=")

    if args.view_metadata:
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            compareMetaData(metaData,print)



    #playlist managing
    if args.new_playlist: 
        newPlaylist(plPath,args.new_playlist)

    elif args.smart_sync:
        smartSync(plPath)

    elif args.append_new:
        appendNew(plPath)
    
    elif args.manual_add:
        if not args.manual_add[1].isdigit():
            logging.error("Index must be positive Integer")
        else:
            manualAdd(plPath,args.manual_add[0],int(args.manual_add[1]))


    elif args.move:
        move(plPath,args.move[0],args.move[1])
    elif args.swap:
        swap(plPath,args.swap[0],args.swap[1])

