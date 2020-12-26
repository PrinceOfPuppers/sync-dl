
from sync_dl.yt_api.helpers import getNewRemoteOrder,getPlId
from sync_dl.yt_api.ytApiWrappers import getYTResource,getItemIds,moveSong

import shelve
import sync_dl.config as cfg


def pushLocalOrder(plPath):
    '''
    Acts like smart sync but in reverse, setting remote order to local order.
    Ignores songs not in remote, and keeps songs not in local after the song they are currently after.
    '''

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
            moveSong(youtube,plId,songId,itemId,newIndex)

            # update workingOrder
            workingOrder.insert(newIndex,workingOrder.pop(oldIndex))