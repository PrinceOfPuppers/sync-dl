import re

import sync_dl.config as cfg


def getPlId(plUrl):
    match = re.search(cfg.plIdRe,plUrl)
    return match.group()[5:]
    

def oldToNewPushOrder(remoteIds, localIds):
    '''
    Used in pushLocalOrder
    '''

    
    blankingStr = ''
    localIds = [localId for localId in localIds]
    remoteIds = [remoteId for remoteId in remoteIds]


    # Removes all localIds which arent in remoteIds (we arent going to upload songs)
    for i,localId in enumerate(localIds):
        if localId not in remoteIds:
            del localIds[i]

    lenRemote = len(remoteIds)
    oldToNew=[-1]*lenRemote

    prevOldIndex = -1
    newIndex = 0

    while True:

        while prevOldIndex+1 != lenRemote and remoteIds[prevOldIndex+1] not in localIds and remoteIds[prevOldIndex+1] != blankingStr:
            oldToNew[prevOldIndex+1] = newIndex
            prevOldIndex+=1
            newIndex+=1

            continue

        if newIndex == lenRemote:
            break

        localId = localIds.pop(0)

        oldIndex = remoteIds.index(localId)
        remoteIds[oldIndex] = blankingStr

        oldToNew[oldIndex] = newIndex

        prevOldIndex = oldIndex
        newIndex+=1
    return oldToNew




def longestIncreasingSequence(numList):
    '''
    returns indices of longest increasing sequence
    '''

    candidates = []

    candidates.append([numList[0]])
    
    new = []
    
    for i in range(1,len(numList)):
        num = numList[i]

        new.clear()
        prevAppended = -1
        
        for j,candidate in enumerate(candidates):
            if num > candidate[-1]:
                if prevAppended == -1 or len(candidates[prevAppended]) < len(candidate)+1:
                    new.append(candidate.copy())
                    candidate.append(num)
                    prevAppended = j
                    
        if prevAppended == -1:
            candidates.append([num])
            continue

        candidates.extend(new)


    # find longest candidate
    maximum = 0
    longest = None

    for candidate in candidates:
        if len(candidate)>maximum:
            longest = candidate
            maximum = len(candidate)
    return longest

def pushOrderMoves(remoteIds,remoteItemIds,localIds):
    oldToNew = oldToNewPushOrder(remoteIds, localIds)

    # songs in the longest increasing subsequence of oldToNew are left untouched
    dontMove = longestIncreasingSequence(oldToNew)

    # moves = [ (newIndex, remoteId, remoteItemId), ... ]
    moves = []

    prevNewIndex = -1

    i = 0
    while i<len(dontMove):
        newIndex = dontMove[i]
        
        if newIndex-prevNewIndex > 1:
            # somthing must be shoved in between prevNewIndex and newIndex

            betweenNewIndex = prevNewIndex + 1
            betweenOldIndex = oldToNew.index(betweenNewIndex) #newToOld[betweenNewIndex]
            
            remoteId = remoteIds[betweenOldIndex] 
            itemId = remoteItemIds[betweenOldIndex] 

            move = (betweenNewIndex,remoteId,itemId)
            moves.append(move)

            prevNewIndex = betweenNewIndex
            continue
            
            # TODO issue with last element not being updated if its misplaced

        prevNewIndex = newIndex
        i+=1
    
    return moves