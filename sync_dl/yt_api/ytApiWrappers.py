import os
import pickle
from math import ceil

import sync_dl.config as cfg
from sync_dl.yt_api.newCredentials import getYTResource


def getItemIds(youtube,plId):
    makeRequest = lambda pageToken: youtube.playlistItems().list(part = "contentDetails", playlistId = plId, pageToken = pageToken)
    request = makeRequest('')
    
    response = request.execute()

    ids = [] # contains tuples (songId, plItemId)
    for item in response['items']:
        ids.append((item["contentDetails"]['videoId'], item["id"]))

    #repeat the above process for all pages
    plLen = response['pageInfo']['totalResults']
    pageLen = response['pageInfo']['resultsPerPage']
    
    numPages = ceil(plLen/pageLen) - 1
    for _ in range(numPages):
        # TODO Try catch block for quota exceeding
        request = makeRequest(response['nextPageToken'])
        response = request.execute()
        for item in response['items']:
            ids.append((item["contentDetails"]['videoId'], item["id"]))

    return ids

def moveSong(youtube, plId, songId, plItemId, index):
    '''
    song and plItem Id corrispond to what is being moved index is the where it is moved.
    returns true/false on success/failure
    '''
    # TODO sanitize/ clamp input index 
    request = youtube.playlistItems().update(
        part="snippet",
        body={
          "id": plItemId,
          "snippet": {
            "playlistId": plId,
            "position": index,
            "resourceId": {
              "kind": "youtube#video",
              "videoId": songId
            }
          }
        }
    )
    try:
        from time import sleep
        r = request.execute()
        title = r['snippet']['title']
        cfg.logger.info(f'Moved Song: {title} to Index: {index}')
    except Exception as e:
        cfg.logger.error(f"Unable to Move song: {songId} to Index: {index} in Playlist: {plId}")
        #TODO detect exception type and replace with custom message (ie 403/quota exceeding)
        cfg.logger.debug(f'Response {e}')
        return False

    return True
