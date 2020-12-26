import re

import sync_dl.config as cfg


def getPlId(plUrl):
    match = re.search(cfg.plIdRe,plUrl)
    return match.group()[5:]
    
def getNewRemoteOrder(remoteIds, localIds):
    '''
    Acts Like SmartSyncOrder but in reverse.
    
    '''
    # to avoid mutating localIds
    localIds = localIds.copy()

    newOrder = []
    remoteIdPairs = [(remoteIds[index],index) for index in range(len(remoteIds))] 

    # Removes all localIds which arent in remoteIds (we arent going to upload songs)
    for i,localId in enumerate(localIds):
        if localId not in remoteIds:
            del localIds[i]


    while True:

        # all songs in remote have been moved
        # note these to len==0 statements are likley redundant
        if len(remoteIdPairs)==0:
            break
        
        if len(localIds)==0:
            newOrder.extend( remoteIdPairs )
            break


        localId=localIds[0]

        remoteId,remoteIndex = remoteIdPairs[0]

        if localId==remoteId:
            # remote song is in correct posistion
            newOrder.append( remoteIdPairs.pop(0) )

            localId = localIds.pop(0) #must also remove this remote element

        elif remoteId not in localIds:
            # current remote song is not in local playlist, it must remain in current order
            newOrder.append( remoteIdPairs.pop(0) )
        
        
        # at this point the current remote song and local song arent the same, but the current remote
        # song still exists locally, hence we can insert the local song into the current posistion
        else:
            # local song exists in remote but in wrong place

            index = remoteIds[remoteIndex+1:].index(localId)+remoteIndex+1
            for i,_ in enumerate(remoteIdPairs):
                if remoteIdPairs[i][1]==index:
                    j = i
                    break

            newOrder.append( remoteIdPairs.pop(j) )
            localId = localIds.pop(0) #must also remove this local element
            
            #checks if songs after the moved song are not in local, if so they must be moved with it
            while j<len(remoteIdPairs) and (remoteIdPairs[j][0] not in localIds):
                newOrder.append( remoteIdPairs.pop(j) )


    return newOrder