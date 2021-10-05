import requests
import re
import json
from typing import NamedTuple

import sync_dl.config as cfg


labelSanitizeRe = re.compile(r'^[:\-\s>]*(.*)\s*$')

class Timestamp(NamedTuple):
    time: int
    label: str

    chapterFmt ="[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={title}\n\n"

    def __eq__(self, other):
        return (self.time == other.time) and (self.label == other.label)

    def __repr__(self):
        secondsRemainder = self.time%60
        
        minutes = (self.time//60)
        minutesRemainder = minutes % 60

        hours = minutes//60

        return f"{hours}:{minutesRemainder:02d}:{secondsRemainder:02d} - {self.label}"

    @classmethod
    def fromFfmpegChapter(cls, timeBase:str, start, title):
        timeBaseNum = eval(timeBase)
        return cls(label = title, time = int(timeBaseNum*int(start)))

    def toFfmpegChapter(self, nextTime):
        return self.chapterFmt.format(start = 1000*self.time, end = int(1000*nextTime) - 1, title = self.label) 


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

def _sanitizeLabel(label):
    match = labelSanitizeRe.match(label)
    if match:
        return match.group(1)
    return label



def _getComments(url):
    r=requests.get(url)

    apiKeyRe = re.compile(r'[\'\"]INNERTUBE_API_KEY[\'\"]:[\'\"](.*?)[\'\"]')
    continuationTokenRe = re.compile(r'[\'\"]token[\'\"]:[\'\"](.*?)[\'\"]')
    clientVersionRe = re.compile(r'[\'\"]cver[\'\"]: [\'|\"](.*?)[\'\"]')

    x,y,z = apiKeyRe.search(r.text), continuationTokenRe.search(r.text), clientVersionRe.search(r.text)

    if not x:
        cfg.logger.debug("Unable to Find INNERTUBE_API_KEY")
        return []

    if not y:
        cfg.logger.debug("Unable to Find Continuation Token")
        return []

    if not z:
        cfg.logger.debug("Unable to Find Youtube Client Version")
        return []

    key = x.group(1)
    continuationToken = y.group(1)
    clientVersion = z.group(1)

    r=requests.get(url)
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



def _getTime(url, timeRe):
    matches = timeRe.search(url)
    if matches and matches.group(0):
        if not matches.group(2):
            return 0
        return int(matches.group(2))
    return None

def _getTimestamp(line, timeRe):
    '''line must be of len 2  checks if line is [timestamp, label] or [label, timestamp]'''
    for i in range(0,1):
        url = scrapeFirstJson(line[i], "url")
        if url is not None:
            time = _getTime(url,timeRe)
            if time!=None:
                label = line[(i+1)%2]['text']
                if not scrapeFirstJson(label,"url"):
                    return Timestamp(label=_sanitizeLabel(label), time=time)
    return None


def _getTimeStamps(comments, videoId):
    timeRe = re.compile(r'\/watch\?v=' + videoId + r'(&t=(\d+)s)?')

    timeStampCandidates = []
    for comment in comments:
        runs = scrapeFirstJson(comment,'runs')

        if runs is None:
            return []

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
        timeStamps:list[Timestamp] = []
        for line in lines:
            if (len(line) != 2):
                continue
            timeStamp = _getTimestamp(line,timeRe)
            if timeStamp is not None:
                timeStamps.append(timeStamp)

        if len(timeStamps) > 1:
            cfg.logger.debug(timeStamps)
            timeStamps.sort(key = lambda ele: ele.time)
            timeStampCandidates.append(timeStamps)
    timeStampCandidates.sort(key=lambda ele: len(ele), reverse=True)

    if len(timeStampCandidates) > 0:
        return timeStampCandidates[0]
    return []


def scrapeCommentsForTimestamps(videoId):
    url = 'https://www.youtube.com/watch?v=' + videoId

    comments = _getComments(url)
    timeStamps = _getTimeStamps(comments, videoId)

    return timeStamps

if __name__ == "__main__":
    videoId = 'NK9ByuKQlEM'
    #videoId = 'UGRJZ1LXFjA'
    timestamps = scrapeCommentsForTimestamps(videoId)

    print(len(timestamps))
    for timestamp in timestamps:
        print(timestamp.time, timestamp.label)
