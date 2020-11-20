import os
import json
import re

import config as cfg

def showMetaData(metaData, printer,urlWithoutId = None):
    '''
    printer can be print or some level of logging
    urlWithoutId is added if you wish to print out all full urls
    '''
    for item in metaData.items():
        printer(f"{item[0]}: {item[1]}")
    
    if urlWithoutId != None:
        printer(f"\n Links:")
        for songId in metaData['ids']:
            url = f"{urlWithoutId}{songId}"
            printer(url)

    

def createNumLabel(n,numDigets):
    n = str(n)
    lenN = len(n)
    if lenN>numDigets:
        raise Exception(f"Number Label Too large! Expected {numDigets} but got {lenN} digets")

    return (numDigets-lenN)*"0"+n


def sortByNum(element):
    '''
    returns the number in front of each song file
    '''
    match = re.match(cfg.filePrependRE,element)

    return int(match.group()[:-1])

def filterFunc(element):
    '''
    returns false for any string not preceded by some number followed by an underscore
    used for filtering non song files
    '''
    match = re.match(cfg.filePrependRE,element)
    if match:
        return True
    
    return False


def getLocalSongs(cwd):
    '''
    returns sanatized list of all songs in local playlist, in order
    '''
    currentDir = os.listdir(path=cwd) 
    currentDir = sorted(filter(filterFunc,currentDir), key= sortByNum) #sorted and sanitized dir
    return currentDir

def smartSyncNewOrder(localIds,remoteIds):
    '''
    used by smartSync, localIds will not be mutated but remtoeIds will
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
            for i,_ in enumerate(localIdPairs):
                if localIdPairs[i][1]==index:
                    j = i
                    break

            newOrder.append( localIdPairs.pop(j) )
            remoteId = remoteIds.pop(0) #must also remove this remote element
            
            #checks if songs after the moved song are not in remote, if so they must be moved with it
            while j<len(localIdPairs) and (localIdPairs[j][0] not in remoteIds):
                newOrder.append( localIdPairs.pop(j) )
                


        else:
            newOrder.append( (remoteIds.pop(0),None) )
    
    return newOrder

