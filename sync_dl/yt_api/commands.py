


import shelve
import sync_dl.config as cfg

def checkOptDepend():
    # Ensures optional dependancies are installed
    while True:
        try:
            from sync_dl.yt_api.helpers import getNewRemoteOrder,getPlId
            from sync_dl.yt_api.ytApiWrappers import getYTResource,getItemIds,moveSong
            break
        except:
            answer = input("Missing Optional Dependancies For This Command.\nWould You Like to Install Them? (y/n): ").lower()
            if answer!='y':
                return False

            import subprocess
            subprocess.call(["pip",'install','google-auth','google-auth-oauthlib','google-api-python-client'])

    return True


def pushLocalOrder(plPath):
    '''
    Acts like smart sync but in reverse, setting remote order to local order.
    Ignores songs not in remote, and keeps songs not in local after the song they are currently after.
    '''

    if not checkOptDepend():
        return
    from sync_dl.yt_api.helpers import getNewRemoteOrder,getPlId
    from sync_dl.yt_api.ytApiWrappers import getYTResource,getItemIds,moveSong
    
    cfg.logger.info("Pushing Local Order to Remote...")

    youtube = getYTResource()
    
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        url = metaData["url"]
        localIds = metaData["ids"]

    plId = getPlId(url)

    remoteIdPairs = getItemIds(youtube,plId)
    remoteIds = [pair[0] for pair in remoteIdPairs]
    plItemIdLookup = {remoteIdPair[0]:remoteIdPair[1] for remoteIdPair in remoteIdPairs}


    newOrder = getNewRemoteOrder(remoteIds,localIds) 

    # uses playlist itemIds because they are guarenteed to be unique
    workingOrder = [ plItemIdLookup[remoteId] for remoteId in remoteIds ]

    for newIndex in range(len(newOrder)):

        songId = newOrder[newIndex][0]
        itemId = plItemIdLookup[songId]

        # TODO optimize by only considering indices at or above newIndex
        oldIndex = workingOrder.index(itemId)

        if oldIndex != newIndex:
            # move the song
            cfg.logger.info(f"Moving song: {songId} from {oldIndex} to {newIndex}")
            if moveSong(youtube,plId,songId,itemId,newIndex):
                # update workingOrder
                workingOrder.insert(newIndex,workingOrder.pop(oldIndex))