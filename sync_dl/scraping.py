import requests
import re
import json
import os
import ntpath
import subprocess
import sync_dl.config as cfg
from sync_dl import noInterrupt

from collections import namedtuple
Timestamp = namedtuple('Timestamp','label time')

labelSanitizeRe = re.compile(r'^[:\-\s>]*(.*)\s*$')

def sanitizeLabel(label):
    match = labelSanitizeRe.match(label)
    if match:
        return match.group(1)
    return label


def scrapeJson(j, desiredKey: str, results:list):
    if isinstance(j,list):
        for value in j:
            if isinstance(value,list) or isinstance(value,dict):
                scrapeJson(value, desiredKey, results)
        return

    if isinstance(j, dict):
        for key,value in j.items():
            if key == desiredKey:
                results.append(value)
            elif isinstance(value, dict) or isinstance(value, list):
                scrapeJson(value, desiredKey, results)
        return

def scrapeFirstJson(j, desiredKey: str):
    if isinstance(j,list):
        for value in j:
            if isinstance(value,list) or isinstance(value,dict):
                res = scrapeFirstJson(value, desiredKey)
                if res is not None:
                    return res
        return None

    if isinstance(j, dict):
        for key,value in j.items():
            if key == desiredKey:
                return value
            elif isinstance(value, dict) or isinstance(value, list):
                res = scrapeFirstJson(value, desiredKey)
                if res is not None:
                    return res
        return None

    return None

def getComments(url):
    r=requests.get(url)

    apiKeyRe = re.compile(r'[\'\"]INNERTUBE_API_KEY[\'\"]:[\'\"](.*?)[\'\"]')
    continuationTokenRe = re.compile(r'[\'\"]token[\'\"]:[\'\"](.*?)[\'\"]')
    clientVersionRe = re.compile(r'[\'\"]cver[\'\"]: [\'|\"](.*?)[\'\"]')

    x,y,z = apiKeyRe.search(r.text), continuationTokenRe.search(r.text), clientVersionRe.search(r.text)

    if x and y and z:
        key = x.group(1)
        continuationToken = y.group(1)
        clientVersion = z.group(1)
    else:
        return []

    r=requests.get('https://www.youtube.com/watch?v='+videoId)
    requestData = '''{
        "context": {
            "adSignalsInfo": {
            },
            "clickTracking": {
            },
            "client": {
                "clientName": "WEB",
                "clientVersion": "'''+clientVersion+'''",
            },
            "request": {
            },
            "user": {
            }
        },
        "continuation": "'''+continuationToken+'''"
    }'''
    
    b = requests.post('https://www.youtube.com/youtubei/v1/next?key='+key,data=requestData)
    commentJson:dict = json.loads(b.text)
    comments = []
    scrapeJson(commentJson,"contentText",comments)
    return comments



def getTime(url, timeRe):
    matches = timeRe.search(url)
    if matches and matches.group(0):
        if not matches.group(2):
            return 0
        return matches.group(2)
    return None

def getTimestamp(line, timeRe):
    '''line must be of len 2  checks if line is [timestamp, label] or [label, timestamp]'''
    for i in range(0,1):
        url = scrapeFirstJson(line[i], "url")
        if url is not None:
            time = getTime(url,timeRe)
            if time!=None:
                label = line[(i+1)%2]['text']
                if not scrapeFirstJson(label,"url"):
                    return Timestamp(label=sanitizeLabel(label), time=time)
    return None


def getTimeStamps(comments, videoId):
    timeRe = re.compile(r'\/watch\?v=' + videoId + r'(&t=(\d+)s)?')

    timeStampCandidates = []
    for comment in comments:
        runs = scrapeFirstJson(comment,'runs')

        if runs is None:
            return

        lines = []
        line = []
        # group into lines
        for ele in runs:
            if ele['text'] == '\n':
                lines.append(line)
                line = list()
            else:
                line.append(ele)

        lines.append(line)

        # parse lines for timestamps
        timeStamps = []
        for line in lines:
            if (len(line) != 2):
                continue
            timeStamp = getTimestamp(line,timeRe)
            if timeStamp is not None:
                timeStamps.append(timeStamp)

        if len(timeStamps) > 1:
            timeStamps.sort(key = lambda ele: ele.time)
            timeStampCandidates.append(timeStamps)
    timeStampCandidates.sort(key=lambda ele: len(ele), reverse=True)
    return timeStampCandidates


def getSongLengthSeconds(songPath):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", songPath],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)
    return float(result.stdout)


def addTimestampsToSong(songPath, timestamps:list[Timestamp]):
    '''
    writes timestamps to file, formatted to add chapters to file using ffmpeg
    '''

    timestamps.sort(key = lambda ele: ele.time)

    if not os.path.exists(songPath):
        cfg.logger.error(f"No Song at Path {songPath}")
        return
    
    if not os.path.exists(cfg.tmpDownloadPath):
        os.mkdir(cfg.tmpDownloadPath)

    for f in os.listdir(path=cfg.tmpDownloadPath):
        os.remove(f"{cfg.tmpDownloadPath}/{f}")

    songName = ntpath.basename(songPath)
    
    ffmpegChapterFile = f'{cfg.tmpDownloadPath}/FFMETADATAFILE'
    createChapterFile = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', songPath,'-f', 'ffmetadata', ffmpegChapterFile]

    try:
        subprocess.run(createChapterFile, check=True)
    except subprocess.CalledProcessError as e:
        cfg.logger.debug(e)
        cfg.logger.error(f"Failed to Create ffmpeg Chapter File For Song {songName}")
        return

    chapterFmt ="[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={title}\n\n"

    with open(ffmpegChapterFile, "a") as f:
        for i in range(0, len(timestamps) - 1):
            t1 = timestamps[i]
            t2 = timestamps[i+1]
            f.write( chapterFmt.format(start = 1000*t1.time, end = 1000*t2.time - 1, title = t1.label) )

        t1 = timestamps[-1]
        end = int(1000*getSongLengthSeconds(songPath))
        f.write( chapterFmt.format(start = 1000*t1.time, end = end - 1, title = t1.label) )

    applyChapterFile = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', songPath, '-i', ffmpegChapterFile, '-map_metadata', '1', '-codec', 'copy', f"{cfg.tmpDownloadPath}/{songName}"]

    try:
        subprocess.run(applyChapterFile,check=True)
    except subprocess.CalledProcessError as e:
        cfg.logger.debug(e)
        cfg.logger.error(f"Failed to Add Timestamps To Song {songName}")
        return

    with noInterrupt:
        os.replace(f"{cfg.tmpDownloadPath}/{songName}", songPath)
    return



def test1():
    videoId = 'NK9ByuKQlEM'
    #videoId = 'UGRJZ1LXFjA'
    url = 'https://www.youtube.com/watch?v=' + videoId
    comments = getComments('https://www.youtube.com/watch?v='+videoId)
    timeStamps = getTimeStamps(comments, videoId)[0]
    print(len(timeStamps))
    for timestamp in timeStamps:
        print(timestamp.time, timestamp.label)


def test2():
    timestamps = [Timestamp(time = 0, label = "the zeroeth time stamp" ), Timestamp(time = 10, label = "the first time stamp" ), Timestamp(time = 40, label = "the second time stamp")]
    addTimestampsToSong('/home/princeofpuppers/Music/test/INPUT.opus', timestamps)

if __name__ == "__main__":
    test2()

    #r=requests.get('https://www.youtube.com/watch?v=NK9ByuKQlEM')
    #print(r.content.)
    #print(getTimestamps(r.text))

