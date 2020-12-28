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
    localIds = localIds.copy()
    remoteIds = remoteIds.copy()


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