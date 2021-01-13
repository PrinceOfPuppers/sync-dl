


import shelve
import sync_dl.config as cfg

def checkOptDepend():
    '''Ensures optional dependancies are installed'''
    while True:
        try:
            from sync_dl.yt_api.helpers import getPlId,pushOrderMoves
            from sync_dl.yt_api.ytApiWrappers import getYTResource,getItemIds,moveSong
            break
        except:
            answer = input("Missing Optional Dependancies For This Command.\nWould You Like to Install Them? (y/n): ").lower()
            if answer!='y':
                return False

            import subprocess
            subprocess.call(["pip",'install','google-auth','google-auth-oauthlib','google-api-python-client','cryptography'])

    return True




def pushLocalOrder(plPath):
    
    if not checkOptDepend():
        return
    from sync_dl.yt_api.helpers import getPlId,pushOrderMoves
    from sync_dl.yt_api.ytApiWrappers import getYTResource,getItemIds,moveSong
    
    cfg.logger.info("Pushing Local Order to Remote...")

    youtube = getYTResource()
    
    with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        url = metaData["url"]
        localIds = metaData["ids"]

    plId = getPlId(url)

    remoteIdPairs = getItemIds(youtube,plId)

    remoteIds,remoteItemIds = zip(*remoteIdPairs)

    cfg.logger.debug(f'Order Before Push: \n'+'\n'.join( [f'{i}: {str(remoteId)}' for i,remoteId in enumerate(remoteIds) ] ))

    moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)



    for move in moves:
        newIndex, songId,itemId = move

        moveSong(youtube,plId,songId,itemId,newIndex)

