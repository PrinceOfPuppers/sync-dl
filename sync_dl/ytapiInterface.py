import os
import shelve
import re

from sync_dl import noInterrupt
from sync_dl.ytdlWrappers import getIDs
from sync_dl.plManagement import correctStateCorruption
from sync_dl.helpers import getLocalSongs, relabel, getNumDigets, copy, delete, padZeros, calcuateTransferMoves, logTransferInfo, promptAndSanitize
import sync_dl.config as cfg

_sync_dl_api_installed = False

def promptInstall():
    global _sync_dl_api_installed

    if _sync_dl_api_installed:
        return True

    try:
        from sync_dl_ytapi.commands import pushLocalOrder, logout, getPlAdder, getPlRemover
    except:

        answer = input("Missing Optional Dependancies For This Command.\nWould You Like to Install Them? (y)es/(n)o: ").lower().strip()
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
        currentDestDir = getLocalSongs(destPlPath)
        destPlName = os.path.basename(destPlPath)

        cfg.logger.info("Loading Youtube Api Resources...")
        plAdder = getPlAdder(destPlUrl)
        if plAdder is None:
            return

        destRemoteIds = getIDs(destPlUrl)

        plRemover, srcRemoteIds = getPlRemover(srcPlUrl)
        if plRemover is None:
            return


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
        if destIndex >= destIdsLen:
            destIndex = destIdsLen -1
        elif destIndex < -1:
            destIndex = -1


        # number of elements to move
        blockSize = srcEnd-srcStart+1

        numDestDigits = getNumDigets(destIdsLen + blockSize)

        songTransfers = calcuateTransferMoves(currentSrcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)

        ### Inform User
        logTransferInfo(songTransfers, srcPlName, destPlName, srcIdsLen, destIdsLen, srcRemoteIds, destRemoteIds, currentDestDir, srcStart, srcEnd, destIndex)

        ### Prompt User
        cfg.logger.info(f"\n------------[Prompt]-----------")
        answer = input("Prefrom Transfer? (y)es/(n)o: ").lower().strip()
        if answer != 'y':
            return

        cfg.logger.info("")

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

            cfg.logger.info(f"Transfering Song: {move.songName}")
            with noInterrupt:
                if move.performCopy:
                    copyDestName = copy(srcMetaData, destMetaData, cfg.logger.debug, srcPlPath, destPlPath, move.srcCopyName, move.srcCopyIndex, move.destCopyIndex, numDestDigits)
                    cfg.logger.debug(f"Locally Copied Song {move.songName} from {srcPlName} to {destPlName}")

                if move.performRemoteAdd:
                    if not plAdder(move.songId, move.destRemoteAddIndex):
                        if not move.performRemoteDelete:
                            cfg.logger.error(f"Error When Adding {move.songName} to Remote Dest: {destPlName}, URL: {destPlUrl}")
                            cfg.logger.error(f"This Song Does Not Occur in Remote Src: {srcPlName}, So It was Probably Removed from Youtube")
                            cfg.logger.info(f"Continuing with Transfer")
                        else:
                            cfg.logger.error(f"Error When Adding {move.songName} to Remote Dest: {destPlName}, URL: {destPlUrl}")
                            cfg.logger.error(f"Fix by Either:")
                            cfg.logger.error(f"- (r)evert Transfer for This Song")
                            cfg.logger.error(f"- (m)anually Adding https://www.youtube.com/watch?v={move.songId} to Remote Playlist Provided Above And (c)ontinuing or (f)inishing this song.")

                
                            answer = promptAndSanitize("Would You Like to: (r)evert song, (m)anual fix, (q)uit: ", 'r', 'm', 'q')

                            if answer == 'r':
                                if move.performCopy:
                                    delete(destMetaData, destPlPath, copyDestName, move.destCopyIndex)
                                    answer = promptAndSanitize("Would You Like to finish the rest of the transfer (y)es/(n)o: ", 'y','n')

                                    if answer != 'y':
                                        break
                                    continue

                            elif answer == 'q':
                                songsPartiallyCompleated += 1
                                break

                            elif answer == 'm':
                                cfg.logger.info(f"Please Add, {move.songName}: https://www.youtube.com/watch?v={move.songId} \nTo Playlist {destPlName}: {destPlUrl}")
                                input("Hit Enter to Proceed: ")


                            answer = promptAndSanitize("Would You Like to: (c)ontinue transfer, (f)inish this song, (q)uit: ", 'c', 'f', 'q')
                            if answer == 'f':
                                endEarly = True
                            if answer == 'q':
                                songsPartiallyCompleated += 1
                                break


                if move.performLocalDelete:
                    delete(srcMetaData, srcPlPath, move.srcLocalDeleteName, move.srcLocalDeleteIndex)
                    cfg.logger.debug(f"Locally Deleted Song {move.songName} from {srcPlName}")

                if move.performRemoteDelete:
                    if not (plRemover(move.srcRemoteDeleteIndex)):
                        cfg.logger.error(f"Error When Removing {move.songName} from Remote Src: {srcPlName}, URL: {srcPlUrl}")
                        cfg.logger.error(f"Fix by:")
                        cfg.logger.error(f"- Manually Removing Song Index: {move.srcRemoteDeleteIndex} URL: https://www.youtube.com/watch?v={move.songId} from Remote Playlist Provided Above")
                        input("Hit Enter to Proceed: ")
                        answer = promptAndSanitize("Would You Like to: (c)ontinue transfer, (q)uit: ", 'c', 'q')
                        if answer == 'q':
                            songsPartiallyCompleated += 1
                            break

                songsCompleted += 1

        #remove gaps, removeBlanks
        correctStateCorruption(srcPlPath, srcMetaData)
        correctStateCorruption(destPlPath, destMetaData)

        # end transfer summery:
        cfg.logger.info(f"{songsCompleted}/{len(songTransfers)} Songs Transfered Successfully")
        if songsPartiallyCompleated != 0:
            cfg.logger.error(f"{songsPartiallyCompleated} / {len(songTransfers)} Songs Had Issues with Transfering, logged above")

        cfg.logger.info("\nTransfer Complete.")
        return


