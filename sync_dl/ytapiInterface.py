import os
import shelve

from sync_dl.ytdlWrappers import getIDs
from sync_dl.plManagement import correctStateCorruption
from sync_dl.helpers import getLocalSongs, relabel, getNumDigets, copy, delete, padZeros, calcuateTransferMoves
import sync_dl.config as cfg

_sync_dl_api_installed = False

def promptInstall():
    global _sync_dl_api_installed

    if _sync_dl_api_installed:
        return True

    try:
        from sync_dl_ytapi.commands import pushLocalOrder, logout, getPlAdder, getPlRemover
    except:

        answer = input("Missing Optional Dependancies For This Command.\nWould You Like to Install Them? (y/n): ").lower()
        if answer!='y':
            return False

        try:
            import subprocess
            subprocess.run(["pip","install", '-U','sync-dl-ytapi'],check=True)
        except:
            cfg.logger.error("Unable to Install Optional Dependancies")
            return False
        cfg.logger.info("Optional Dependancies Installed")

        _sync_dl_api_installed = True
        cfg.logger.info("----------------------------------")

    _sync_dl_api_installed = True
    return True
    

def pushLocalOrder(plPath):

    installed = promptInstall()

    if not installed:
        return 

    from sync_dl_ytapi.commands import pushLocalOrder
    pushLocalOrder(plPath)


def logout():
    installed = promptInstall()

    if not installed:
        return 

    from sync_dl_ytapi.commands import logout
    logout()


def transferSongs(srcPlPath: str, destPlPath: str, srcStart: int, srcEnd: int, destIndex: int):
    '''
    transfers block of songs in srcPl from srcStart to srcEnd indices, to after destIndex in destPl

    ie)srcStart = 4, srcEnd = 6, destIndex = 2
    srcPl: s0 s1 s2 s3 s4 s5 s6 s7   destPl: d0 d1 d2 d3 d4 d5 d6

    becomes:
    srcPl: s0 s1 s2 s3 s7   destPl: d0 d1 d2 s4 s5 s6 d3 d4 d5 d6
    '''    

    installed = promptInstall()

    if not installed:
        return 

    from sync_dl_ytapi.commands import getPlAdder, getPlRemover


    srcMetaDataPath = f"{srcPlPath}/{cfg.metaDataName}"
    destMetaDataPath = f"{destPlPath}/{cfg.metaDataName}"
    with shelve.open(srcMetaDataPath, 'c',writeback=True) as srcMetaData, shelve.open(destMetaDataPath, 'c',writeback=True) as destMetaData:
        correctStateCorruption(srcPlPath, srcMetaData)
        correctStateCorruption(destPlPath, destMetaData)

        ### Loading
        srcPlUrl    = srcMetaData["url"]
        srcLocalIds = srcMetaData["ids"]
        assert isinstance(srcLocalIds, list)
        srcIdsLen = len(srcLocalIds)
        currentSrcDir = getLocalSongs(srcPlPath)
        srcPlName = os.path.basename(srcPlPath)

        destPlUrl    = destMetaData["url"]
        destLocalIds = destMetaData["ids"]
        assert isinstance(destLocalIds, list)
        destIdsLen = len(destLocalIds)
        numDestDigits = getNumDigets(destIdsLen)
        currentDestDir = getLocalSongs(destPlPath)
        destPlName = os.path.basename(destPlPath)

        plAdder = getPlAdder(destPlUrl)
        destRemoteIds = getIDs(destPlUrl)

        plRemover, srcRemoteIds = getPlRemover(srcPlUrl)


        ### Src start/end sanitization
        if srcStart>=srcIdsLen:
            cfg.logger.error(f"No Song has Index {srcStart} in {srcPlName}, Largest Index is {srcIdsLen-1}")
            return

        elif srcStart<0:
            cfg.logger.error(f"No Song has a Negative Index")
            return
            
        if srcEnd>=srcIdsLen or srcEnd == -1:
            srcEnd = srcIdsLen-1

        elif srcEnd<srcStart:
            cfg.logger.error("End Index Must be Greater Than or Equal To Start Index (or -1)")
            return

        ### Clamp destIndex
        if destIndex > destIdsLen:
            destIndex = destIdsLen
        elif destIndex < -1:
            destIndex = -1


        # number of elements to move
        blockSize = srcEnd-srcStart+1

        songTransfers = calcuateTransferMoves(currentSrcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)

        ### Inform User
        maxNum = max(srcIdsLen, destIdsLen, len(srcRemoteIds), len(destRemoteIds))
        numMoveDigits = len(str(maxNum))

        xs = 'x'* numMoveDigits
        cfg.logger.info(f"------------[Transfer {srcPlName} [{srcStart}, {srcEnd}] -> {destPlName} {destIndex}]-----------")
        cfg.logger.info(f"Song Actions| Song Id | Song name \nLocal Move: {xs} -> {xs} | Remote Move: {xs} -> {xs}")
        for move in songTransfers:
            actionPrompt  = f"{'LC' if move.copyAction else '  '} "
            actionPrompt += f"{'RA' if move.remoteAddAction else '  '} "
            actionPrompt += f"{'LR' if move.localDeleteAction else '  '} "
            actionPrompt += f"{'RR' if move.remoteDeleteAction else '  '} | "
            prompt  = f"{move.songId} | {move.songName}\n"
            prompt += ' '*len(actionPrompt)
            prompt += f"Local {srcPlName}: {padZeros(move.srcLocalDeleteIndex, numMoveDigits)} -> {destPlName}: {padZeros(move.destCopyIndex, numMoveDigits)} | "
            prompt += f"Remote {srcPlName}: {padZeros(move.srcRemoteDeleteIndex, numMoveDigits)} -> {destPlName}: {padZeros(move.destRemoteAddIndex, numMoveDigits)}\n"
            cfg.logger.info(actionPrompt+prompt)


        cfg.logger.info(f"------------[Legend]-----------\n")
        cfg.logger.info ( 
             f"LC: Local  Copy, from {srcPlName} to {destPlName}\n" \
             f"RA: Remote  Add to {destPlName} \n" \
             f"LR: Local  Remove from {srcPlName} \n" \
             f"RR: Remote Remove from {srcPlName}\n" \
        )

        ### Prompt User
        answer = input("Prefrom With Transfer? (y)es/(n)o: ")
        if answer.lower() != 'y':
            return


        #actual editing
        # make room for block
        for i in reversed(range(destIndex+1,destIdsLen)):
            oldName = currentDestDir[i]
            newIndex =i+blockSize
            relabel(destMetaData, cfg.logger.debug, destPlPath, oldName, i,newIndex, numDestDigits)



        endEarly = False
        songsCompleted = 0
        songsPartiallyCompleated = 0
        for i,move in enumerate(songTransfers):
            if endEarly:
                break
            if move.performCopy:
                copyDestName = copy(srcMetaData, destMetaData, cfg.logger.debug, srcPlPath, destPlPath, move.srcCopyName, move.srcCopyIndex, move.destCopyIndex, numDestDigits)

            if move.remoteAddAction:
                if not plAdder(move.songId, move.destRemoteAddIndex):
                    cfg.logger.error(f"Error When Adding {move.songName} to Remote Dest: {destPlName}, URL: {destPlUrl}")
                    cfg.logger.error(f"Local Copy for this song Already Happened")
                    cfg.logger.error(f"Fix by Either:")
                    cfg.logger.error(f"- Manually Adding https://www.youtube.com/watch?v={move.songId} to Remote Playlist Provided Above And (c)ontinuing or (f)inishing this song.")
                    cfg.logger.error(f"- Removing File {copyDestName} in {destPlName} and (e)nd transfer")
                    answer = input("Would You Like to: (e)nd transfer, (c)ontinue transfer, (s)kip song, (f)inish this song").lower()
                    if answer == 'e':
                        songsPartiallyCompleated += 1
                        break
                    if answer == 's':
                        songsPartiallyCompleated += 1
                        continue
                    if answer == 'f':
                        endEarly = True


            if move.localDeleteAction:
                delete(srcMetaData, srcPlPath, move.srcLocalDeleteName, move.srcLocalDeleteIndex)

            if move.remoteDeleteAction:
                if not (plRemover(move.srcRemoteDeleteIndex)):
                    cfg.logger.error(f"Error When Removing {move.songName} from Remote Src: {srcPlName}, URL: {srcPlUrl}")
                    cfg.logger.error(f"All Other Steps, Completed. ")
                    cfg.logger.error(f"Fix by:")
                    cfg.logger.error(f"- Manually Removing https://www.youtube.com/watch?v={move.songId} from Remote Playlist Provided Above")
                    answer = input("Would You Like to: (e)nd transfer, (c)ontinue").lower()
                    if answer == 'e':
                        songsPartiallyCompleated += 1
                        break

            songsCompleted += 1

        # end transfer summery:
        cfg.logger.info(f"{songsCompleted}/{len(songTransfers)} Songs Transfered Successfully")
        if songsPartiallyCompleated != 0:
            cfg.logger.error(f"{songsPartiallyCompleated} / {len(songTransfers)} Songs Had Issues with Transfering, logged above")

        return


