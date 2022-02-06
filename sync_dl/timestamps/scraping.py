import requests
import re
import json
from typing import NamedTuple, List, Union

import sync_dl.config as cfg


def jsonRegex(*args, surroundingBrace = False):
    r = ""

    numPairs = len(args)//2
    for i in range(numPairs):
        r += r"\s*[\'\"]" + args[2*i] + r"[\'\"]\s*:\s*"
        r += r"[\'\"]" + args[2*i+1] + r"[\'\"]\s*.?"

    if surroundingBrace:
        r = "{" + r + "}"
    return r

apiKeyRe = re.compile(jsonRegex("INNERTUBE_API_KEY", "(.*?)"))
clientVersionRe = re.compile(jsonRegex("key", "cver", "value", "(.*?)" , surroundingBrace = True))
continuationTokenRe = re.compile(r'[\'\"]token[\'\"]:[\'\"](.*?)[\'\"]')

labelSanitizeRe = re.compile(r'^(?:[:\-|\s>]*)(?:\d{1,3}[\.:|\)])?\]?(?:\s)?(.*?)[:\-|\s>]*$')

class Timestamp(NamedTuple):
    time: int
    label: str

    chapterFmt ="[CHAPTER]\nTIMEBASE=1/1000\nSTART={start}\nEND={end}\ntitle={title}\n\n"

    reprFmt = "{hh}:{mm:02d}:{ss:02d} - {ll}"

    def __eq__(self, other):
        return (self.time == other.time) and (self.label == other.label)

    def __repr__(self):
        secondsRemainder = self.time%60
        
        minutes = (self.time//60)
        minutesRemainder = minutes % 60

        hours = minutes//60

        return self.reprFmt.format(hh=hours, mm=minutesRemainder, ss=secondsRemainder, ll=self.label)

    @classmethod
    def fromFfmpegChapter(cls, timeBase:str, start, title) -> 'Timestamp':
        timeBaseNum = eval(timeBase)
        return cls(label = title, time = int(timeBaseNum*int(start)))


    def toFfmpegChapter(self, nextTime):
        return self.chapterFmt.format(start = 1000*self.time, end = int(1000*nextTime) - 1, title = self.label) 

    


def scrapeJson(j, desiredKey: str, results:List):
    if isinstance(j,List):
        for value in j:
            if isinstance(value,List) or isinstance(value,dict):
                scrapeJson(value, desiredKey, results)
        return

    if isinstance(j, dict):
        for key,value in j.items():
            if key == desiredKey:
                results.append(value)
            elif isinstance(value, dict) or isinstance(value, List):
                scrapeJson(value, desiredKey, results)
        return

def scrapeFirstJson(j, desiredKey: str):
    if isinstance(j,List):
        for value in j:
            if isinstance(value,List) or isinstance(value,dict):
                res = scrapeFirstJson(value, desiredKey)
                if res is not None:
                    return res
        return None

    if isinstance(j, dict):
        for key,value in j.items():
            if key == desiredKey:
                return value
            elif isinstance(value, dict) or isinstance(value, List):
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


    x,y,z = apiKeyRe.search(r.text), continuationTokenRe.search(r.text), clientVersionRe.search(r.text)

    if not x:
        raise Exception("Unable to Find INNERTUBE_API_KEY")

    if not y:
        raise Exception("Unable to Find Continuation Token")

    if not z:
        raise Exception("Unable to Find Youtube Client Version")

    key = x.group(1)
    continuationToken = y.group(1)
    clientVersion = z.group(1)

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

def _getTimestamp(line, timeRe) -> Union[Timestamp, None]:
    '''line must be of form [text] [time] or [time] [text]'''
    text = ""
    url = ""
    time = -1
    if len(line) == 0:
        return None

    urlFirst = False
    ele = line[0]
    foundUrl = scrapeFirstJson(ele, "url")
    if foundUrl is None:
        text+=ele['text']
    else:
        urlFirst = True
        url = foundUrl
        foundTime = _getTime(url,timeRe)
        if foundTime is None:
            return None
        time=foundTime

    for i in range(1,len(line)):
        ele = line[i]
        foundUrl = scrapeFirstJson(ele, "url")

        # found text
        if foundUrl is None:
            if url and not urlFirst:
                if ele['text'].isspace():
                    continue
                return None

            text+=ele['text']
            continue

        # found url
        if foundUrl is not None:
            if urlFirst:
                return None
            if url:
                return None

            url = foundUrl
            foundTime = _getTime(url,timeRe)
            if foundTime is None:
                return None
            time = foundTime

    if text and url and time != -1:
        return Timestamp(label=_sanitizeLabel(text), time=time)
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
        timeStamps:List[Timestamp] = []
        for line in lines:
            timeStamp = _getTimestamp(line,timeRe)
            if timeStamp is not None:
                timeStamps.append(timeStamp)

        if len(timeStamps) > 1:
            timeStamps.sort(key = lambda ele: ele.time)
            timeStampCandidates.append(timeStamps)
    timeStampCandidates.sort(key=lambda ele: len(ele), reverse=True)

    if len(timeStampCandidates) > 0:
        return timeStampCandidates[0]
    return []


def scrapeCommentsForTimestamps(videoId):
    url = 'https://www.youtube.com/watch?v=' + videoId

    try:
        comments = _getComments(url)
    except:
        cfg.logger.info("No Comments Found")
        return []

    timeStamps = _getTimeStamps(comments, videoId)
    return timeStamps

if __name__ == '__main__':
    tests = ['- 01. "Goodmorning America!"',
    '- 01. "Goodmorning America!"',
    '- 00: "Goodmorning America!"',
    '- 00:"Goodmorning America!"',
    '-00: "Goodmorning America!"',
    '|->: 01. "Goodmorning America!"',
    '- "Goodmorning America!"',
    '-> "Goodmorning America!"',
    '04.1 "Goodmorning America!"',
    '04.1 "Goodmorning America!"',
    '104. "Goodmorning America!"',
    "01. ＬＯＯＫＩＮＧ ＵＰ_______________ "
    ]
