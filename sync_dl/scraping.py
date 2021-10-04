import requests
import re
import json

from collections import namedtuple
Timestamp = namedtuple('Timestamp','label time')


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
                    return Timestamp(label=label, time=time)
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

        print(lines)
        # parse lines for timestamps
        timeStamps = []
        for line in lines:
            if (len(line) != 2):
                continue
            timeStamp = getTimestamp(line,timeRe)
            if timeStamp is not None:
                timeStamps.append(timeStamp)

        if len(timeStamps) > 1:
            timeStampCandidates.append(timeStamps)
    timeStampCandidates.sort(key=lambda ele: len(ele), reverse=True)
    return timeStampCandidates


if __name__ == "__main__":
    videoId = 'NK9ByuKQlEM'
    #videoId = 'UGRJZ1LXFjA'
    url = 'https://www.youtube.com/watch?v=' + videoId
    comments = getComments('https://www.youtube.com/watch?v='+videoId)
    timeStamps = getTimeStamps(comments, videoId)[0]
    print(len(timeStamps))
    for timestamp in timeStamps:
        print(timestamp.time, timestamp.label)

    #r=requests.get('https://www.youtube.com/watch?v=NK9ByuKQlEM')
    #print(r.content.)
    #print(getTimestamps(r.text))

