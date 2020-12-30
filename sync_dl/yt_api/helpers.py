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

    # songs in the longest increasing subsequence of oldToNew are left untouched (ensures most efficent
    # usage of the api)
    dontMove = longestIncreasingSequence(oldToNew)


    # groups = [ (finalIndex, remoteId, remoteItemId), ... ]
    groups = [] # current working order to new order, sorting this while recording the moves
                # is how we determine the moves needed to sort the playlist
                
    for i in range(len(oldToNew)):
        num = oldToNew[i]
        groups.append( (num,remoteIds[i],remoteItemIds[i]) )

    def getGroupIndex(groups,newIndex):
        for currentIndex,group in enumerate(groups):
            if group[0]==newIndex:
                return currentIndex
        

        raise Exception(f'newIndex {newIndex} Not in Group')

    

    # moves = [ (moveIndex, remoteId, remoteItemId), ... ]
    moves = []

    def addMove(moveIndex,oldIndex):
        group = groups.pop(oldIndex)
        moves.append( (moveIndex,group[1],group[2]) )
        groups.insert(moveIndex,group)


    if groups[0][0] != 0:
        i = getGroupIndex(groups,0)
        newIndex,_,_ = groups[i]
        if newIndex not in dontMove:
            addMove(0,i)


    for newIndex in range(1,len(groups)):

        i = getGroupIndex(groups,newIndex)
        newIndex,_,_ = groups[i]
        if newIndex in dontMove:
            i+=1
            continue

        
        j=0
        compIndex = groups[j][0]
        while newIndex != compIndex+1:
            j+=1
            compIndex = groups[j][0]
        
        if j>=i:
            moveIndex=j
        else:
            moveIndex=j+1

        addMove(moveIndex,i)

    cfg.logger.debug('Moves To Push: \n'+'\n'.join( [str(move) for move in moves ] ))
    cfg.logger.debug('Groups Post Sort: \n'+'\n'.join([str(group) for group in groups ]))
    return moves