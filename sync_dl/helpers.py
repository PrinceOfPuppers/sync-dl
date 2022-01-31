import os
import re
import shutil
from typing import Union

from sync_dl import noInterrupt
import sync_dl.config as cfg
from sync_dl.ytdlWrappers import downloadToTmp,moveFromTmp

def getNumDigets(plLen):
    return len(str( plLen+1 ))

def padZeros(s, numDigits):
    return str(s).zfill(numDigits)

def rename(metaData, printer, plPath, oldName, newName, index, newId):
    with noInterrupt:
        printer(f"Renaming {oldName} to {newName}")
        os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")

        if index >= len(metaData["ids"]):
            metaData["ids"].append(newId)
        else:
            metaData["ids"][index] = newId
        printer("Renaming Complete")

def relabel(metaData, printer,plPath, oldName, oldIndex, newIndex, numDigets):
    '''
    used for changing the number of an element in the playlist
    will blank out old posistion in the metaData

    note this does NOT prevent you from overwriting numbering of 
    an existing song

    returns new name which is needed in some cases (ie when a song is temporarily moved)
    '''

    newName = re.sub(cfg.filePrependRE, f"{createNumLabel(newIndex,numDigets)}_" , oldName)

    songId = metaData['ids'][oldIndex]
    with noInterrupt:
        printer(f"Relabeling {oldName} to {newName}")

        os.rename(f"{plPath}/{oldName}",f"{plPath}/{newName}")

        numIds = len(metaData["ids"])
        if newIndex >= numIds:
            
            for _ in range(newIndex-numIds):
                metaData["ids"].append('')
            
            metaData["ids"].append(songId)
        else:
            metaData["ids"][newIndex] = songId

        metaData['ids'][oldIndex] = ''
        printer("Relabeling Complete")
    return newName

def copy(srcMetaData, destMetaData, printer, srcPlPath, destPlPath, srcName, srcIndex, destIndex, numDigets):
    destName = re.sub(cfg.filePrependRE, f"{createNumLabel(destIndex,numDigets)}_" , srcName)
    songId = srcMetaData['ids'][srcIndex]
    numDestIds = len(destMetaData["ids"])

    with noInterrupt:
        printer(f"Copying {srcPlPath}/{srcName} to {destPlPath}/{destName}")

        shutil.copy(f"{srcPlPath}/{srcName}",f"{destPlPath}/{destName}")

        if destIndex >= numDestIds:
            for _ in range(destIndex-numDestIds):
                destMetaData["ids"].append('')
            
            destMetaData["ids"].append(songId)
        else:
            destMetaData["ids"][destIndex] = songId

        printer("Copy Complete")
    return destName


def delete(metaData, plPath, name, index):
    with noInterrupt:
        cfg.logger.debug(f"Deleting {name}")
        os.remove(f"{plPath}/{name}")

        del metaData["ids"][index]

        cfg.logger.debug("Deleting Complete")



def download(metaData,plPath, songId, index,numDigets, counter = ''):
    '''
    downloads song and adds it to metadata at index
    returns whether or not the download succeeded
    
    counter is an optional string indicating what number the download is ie) 10 or 23/149
    '''
    if index == -1:
        index = len(metaData["ids"]) 

    num = createNumLabel(index,numDigets)

    if counter:
        message = f"Dowloading song {counter}, Id {songId}"
    else:
        message = f"Dowloading song Id {songId}"
    
    cfg.logger.info(message)
    if downloadToTmp(songId,num): #returns true if succeeds

        with noInterrupt: # moving the song from tmp and editing the metadata must occur togeather
            moveFromTmp(plPath)
            if index >= len(metaData["ids"]):
                metaData["ids"].append(songId)
            else:
                metaData["ids"][index] = songId
            cfg.logger.debug("Download Complete")
            return True
    return False

def createNumLabel(n,numDigets):
    n = str(n)
    lenN = len(n)
    if lenN>numDigets:

        cfg.logger.warning(f"Number Label Too large! Expected {numDigets} but got {lenN} digets")
        #raise Exception(f"Number Label Too large! Expected {numDigets} but got {lenN} digets")
        numDigets+=1

    return (numDigets-lenN)*"0"+n


def getSongNum(element):
    '''
    returns the number in front of each song file
    '''
    match = re.match(cfg.filePrependRE,element)

    assert match is not None
    return int(match.group()[:-1])

def _filterFunc(element):
    '''
    returns false for any string not preceded by some number followed by an underscore
    used for filtering non song files
    '''
    match = re.match(cfg.filePrependRE,element)
    if match:
        return True
    
    return False


def getLocalSongs(plPath):
    '''
    returns sanatized list of all songs in local playlist, in order
    '''
    currentDir = os.listdir(path=plPath) 
    currentDir = sorted(filter(_filterFunc,currentDir), key= getSongNum) #sorted and sanitized dir
    return currentDir

def smartSyncNewOrder(localIds,remoteIds):
    '''
    used by smartSync, localIds will not be mutated but remoteIds will
    output is newOrder, a list of tuples ( Id of song, where to find it )
    the "where to find it" is the number in the old ordering (None if song is to be downloaded)
    '''
    newOrder=[]

    localIdPairs = [(localIds[index],index) for index in range(len(localIds))] #contins ( Id of song, local order )

    while True:
        if len(localIdPairs)==0:
            newOrder.extend( (remoteId,None) for remoteId in remoteIds )
            break

        elif len(remoteIds)==0:
            newOrder.extend( localIdPairs )
            break

        remoteId=remoteIds[0]
        localId,localIndex = localIdPairs[0]

        if localId==remoteId:
            #remote song is already saved locally in correct posistion
            newOrder.append( localIdPairs.pop(0) )

            remoteId = remoteIds.pop(0) #must also remove this remote element

        elif localId not in remoteIds:
            # current local song has been removed from remote playlist, it must remain in current order
            newOrder.append( localIdPairs.pop(0) )

        
        # at this point the current local song and remote song arent the same, but the current local
        # song still exists remotly, hence we can insert the remote song into the current posistion
        elif remoteId in localIds:
            # remote song exists in local but in wrong place

            index = localIds[localIndex+1:].index(remoteId)+localIndex+1
            j = -1
            for i,_ in enumerate(localIdPairs):
                if localIdPairs[i][1]==index:
                    j = i
                    break

            assert j != -1
            newOrder.append( localIdPairs.pop(j) )
            remoteId = remoteIds.pop(0) #must also remove this remote element
            
            #checks if songs after the moved song are not in remote, if so they must be moved with it
            while j<len(localIdPairs) and (localIdPairs[j][0] not in remoteIds):
                newOrder.append( localIdPairs.pop(j) )
                


        else:
            newOrder.append( (remoteIds.pop(0),None) )
    
    return newOrder

def getNthOccuranceIndex(l: list, item, n:int) -> Union[int, None]:
    '''returns the nth occurance of item in l'''
    num = 0
    lastOccuranceIndex = None
    for i,item2 in enumerate(l):
        if item == item2:
            if num == n:
                return i
            lastOccuranceIndex = i

            num+=1

    return lastOccuranceIndex

def numOccurance(l: list, index: int) -> int:
    '''
    the reverse of getNthOccuranceIndex
    let A = l[index], and this function returns 1, that means l[index] is the 1th A in l (after the 0th)
    ie) l = [A, B ,A ,C, B , B] index = 2 will return 1
    '''
    item = l[index]
    num = 0
    for i in range(0, index):
        if l[i] == item:
            num+=1

    return num

class TransferMove:
    songId: str
    songName: str

    performCopy:bool = False
    srcCopyName: str
    srcCopyIndex: int
    destCopyIndex: int

    performRemoteAdd:bool = False
    destRemoteAddIndex: int

    performLocalDelete: bool = False
    srcLocalDeleteIndex: int
    srcLocalDeleteName: str

    performRemoteDelete:bool = False
    srcRemoteDeleteIndex: int

    def __init__(self, songId, songName):
        self.songId = songId
        self.songName = songName
        return

    def copyAction(self, srcCopyName, srcCopyIndex, destCopyIndex):
        self.performCopy   = True
        self.srcCopyName   = srcCopyName
        self.srcCopyIndex  = srcCopyIndex
        self.destCopyIndex = destCopyIndex

    def remoteAddAction(self, destRemoteAddIndex):
        self.performRemoteAdd   = True
        self.destRemoteAddIndex = destRemoteAddIndex

        assert self.performCopy

    def localDeleteAction(self, srcLocalDeleteIndex, srcLocalDeleteName):
        self.performLocalDelete  = True
        self.srcLocalDeleteIndex = srcLocalDeleteIndex
        self.srcLocalDeleteName  = srcLocalDeleteName

        assert self.performCopy

        assert self.srcLocalDeleteIndex == self.srcCopyIndex
        assert self.srcCopyName == self.srcLocalDeleteName

    def remoteDeleteAction(self, srcRemoteDeleteIndex):
        self.performRemoteDelete  = True
        self.srcRemoteDeleteIndex = srcRemoteDeleteIndex 

        assert self.performRemoteAdd
        assert self.performLocalDelete


def calcuateTransferMoves(currentSrcDir: list[str], 
                          srcLocalIds:list[str],    destLocalIds:list[str], 
                          srcRemoteIds:list[str],   destRemoteIds:list[str], 
                          srcStart:int, srcEnd:int, destIndex:int) -> list[TransferMove]:

    '''calculates moves for transferSongs'''

    # number of elements to move
    blockSize = srcEnd-srcStart+1


    # get index to add songs in remote dest
    if destIndex != -1:
        destLocalNumOccurances = numOccurance(destLocalIds, destIndex)
        destRemoteIndex = getNthOccuranceIndex(destRemoteIds, destLocalIds[destIndex], destLocalNumOccurances)
        if destRemoteIndex == None:
            destRemoteIndex = 0
        else:
            destRemoteIndex += 1
    else:
        destRemoteIndex = 0


    # store moves
    songTransfers: list[TransferMove] = []

    ### Calculate moves
    copyIndex = destIndex + blockSize
    for srcIndex in reversed(range(srcStart, srcEnd+1)):
        songId = srcLocalIds[srcIndex]
        srcLocalNumOccurances = numOccurance(srcLocalIds, srcIndex)
        srcRemoteIndex = getNthOccuranceIndex(srcRemoteIds, songId, srcLocalNumOccurances)
        # if srcRemoteIndex is None, or if there are more of songId in srcLocalIds, dont delete

        # copy song to dest local
        srcName = currentSrcDir[srcIndex]
        songName = re.sub(cfg.filePrependRE,"",srcName)
        data = TransferMove(songId, songName)

        data.copyAction(srcName, srcIndex, copyIndex)
        copyIndex -= 1

        # add song to dest remote
        if srcRemoteIndex is not None:
            data.remoteAddAction(destRemoteIndex)

        # delete song from src local
        data.localDeleteAction(srcIndex, srcName)

        # delete song from src remote
        if srcRemoteIndex is not None:
            data.remoteDeleteAction(srcRemoteIndex)

        songTransfers.append(data)

    return songTransfers

