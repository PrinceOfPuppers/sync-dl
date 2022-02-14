import re
import os
import subprocess
import shutil

import sync_dl.config as cfg
from sync_dl.timestamps.scraping import Timestamp
from typing import List
from sync_dl import noInterrupt


chapterRe = re.compile(r"\[CHAPTER\]\nTIMEBASE=(.+)\nSTART=(.+)\nEND=(.+)\ntitle=(.+)\n",flags = re.M)

def _getSongLengthSeconds(songPath:str) -> float:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", songPath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)


def getTimestamps(ffmpegMetadataPath:str) -> List[Timestamp]:
    with open(ffmpegMetadataPath, "r") as f:
        contents = f.read()
        timestamps = []
        for (timebase, start, _, title) in chapterRe.findall(contents):
            timestamps.append(Timestamp.fromFfmpegChapter(timebase, start, title))

        return timestamps



def createChapterFile(songPath:str, songName:str) -> bool:
    if not os.path.exists(songPath):
        cfg.logger.error(f"No Song at Path {songPath}")
        return False
    
    if not os.path.exists(cfg.tmpDownloadPath):
        os.mkdir(cfg.tmpDownloadPath)

    for f in os.listdir(path=cfg.tmpDownloadPath):
        os.remove(f"{cfg.tmpDownloadPath}/{f}")

    
    createChapterFileCmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', songPath,'-f', 'ffmetadata', cfg.ffmpegMetadataPath]

    try:
        cfg.logger.debug(f"Creating FFMPEG Metadata File")
        subprocess.run(createChapterFileCmd, check=True)
    except subprocess.CalledProcessError as e:
        cfg.logger.debug(e)
        cfg.logger.error(f"Failed to Create ffmpeg Chapter File For Song {songName}")
        return False

    return True

def wipeChapterFile() -> List[Timestamp]:
    '''detects chapters in file and wipes them. returns list of existing timestamps'''

    existingTimestamps = []
    with open(cfg.ffmpegMetadataPath, "r+") as f:
        contents = f.read()

        for (timebase, start, _, title) in chapterRe.findall(contents):
            existingTimestamps.append(Timestamp.fromFfmpegChapter(timebase, start, title))

        if len(existingTimestamps) > 0:
            cfg.logger.debug(f"Wiping Chapters from FFMPEG Metadata File")
            newContents = chapterRe.sub("", contents)
            f.seek(0)
            f.write(newContents)
            f.truncate()

    return existingTimestamps


def addTimestampsToChapterFile(timestamps:List[Timestamp], songPath:str):

    timestamps.sort(key = lambda ele: ele.time)

    if len(timestamps) > 0:
        with open(cfg.ffmpegMetadataPath, "a") as f:
            for i in range(0, len(timestamps) - 1):
                t1 = timestamps[i]
                t2 = timestamps[i+1]
                ch = t1.toFfmpegChapter(t2.time)
                cfg.logger.debug(f"Adding Chapter to FFMPEG Metadata File: \n{ch}")
                f.write(ch)

            t1 = timestamps[-1]
            end = _getSongLengthSeconds(songPath)
            ch = t1.toFfmpegChapter(end)
            cfg.logger.debug(f"Adding Chapter to FFMPEG Metadata File: \n{ch}")
            f.write(ch)


def applyChapterFileToSong(songPath:str, songName:str) -> bool:
    applyChapterFile = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', songPath, '-i', cfg.ffmpegMetadataPath, '-map_metadata', '1', '-map_chapters', '1', '-codec', 'copy', f"{cfg.tmpDownloadPath}/{songName}"]

    try:
        subprocess.run(applyChapterFile,check=True)
    except subprocess.CalledProcessError as e:
        cfg.logger.debug(e)
        return False

    with noInterrupt:
        shutil.move(f"{cfg.tmpDownloadPath}/{songName}", songPath)
    return True

