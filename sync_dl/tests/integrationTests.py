

import re
import unittest
import os
import shelve
import shutil
import random

from sync_dl.commands import smartSync,newPlaylist,swap,shuffle,move
import sync_dl.config as cfg
from sync_dl.commands import compareMetaData, showPlaylist
from sync_dl.helpers import getLocalSongs
from sync_dl.ytdlWrappers import getTitle,getIdsAndTitles

from sync_dl.timestamps.timestamps import getTimestamps, createChapterFile, wipeChapterFile, addTimestampsToChapterFile, applyChapterFileToSong
from sync_dl.timestamps.scraping import Timestamp, scrapeCommentsForTimestamps


def metaDataSongsCorrect(metaData,plPath):
    '''
    tests if metadata ids corrispond to the correct remote songs.
    returns boolian test result and logs details

    test fails if local title does not match remote title
    manually added songs are ignored
    '''
    cfg.logger.info("Testing if Metadata IDs Corrispond to Correct Songs")

    currentDir = getLocalSongs(plPath)

    localIds = metaData['ids']
    localTitles = map(lambda title: re.sub(cfg.filePrependRE,'',title), currentDir)

    for i,localTitle in enumerate(localTitles):
        localId = localIds[i]
        if localId!=cfg.manualAddId:

            remoteTitle = getTitle(f"https://www.youtube.com/watch?v={localId}")
            if localTitle != remoteTitle:
                message = (f"{i}th Local Title:          {localTitle}\n"
                           f"Differes from Remote Title: {remoteTitle}\n"
                           f"With same Id:               {localId}")
                cfg.logger.error(message)
                return False
    cfg.logger.info("Test Passed")
    return True

def metaDataMatches(metaData,plPath):
    '''
    metadata and local playlist must perfectly match remote playlist for this to return true
    '''
    cfg.logger.info("Testing If Metadata Perfectly Matches Remote Playlist")

    currentDir = getLocalSongs(plPath)

    localIds = metaData['ids']

    remoteIds, remoteTitles = getIdsAndTitles(metaData['url'])

    if len(localIds) != len(currentDir):
        cfg.logger.error(f"metadata ids and local playlist differ in length {len(localIds)} to {len(currentDir)}")
        return False
    if len(localIds)!= len(remoteIds):
        cfg.logger.error(f"local and remote playlists differ in length {len(localIds)} to {len(remoteIds)}")
        return False


    for i,localTitle in enumerate(currentDir):
        localTitle,_ = os.path.splitext(localTitle)
        localTitle = re.sub(cfg.filePrependRE,'',localTitle)

        localId = localIds[i]
        remoteId = remoteIds[i]
        remoteTitle = remoteTitles[i]

        if localId!=remoteId:
            message = (f"{i}th Local id:          {localId}\n"
                       f"With title:              {localTitle}\n"
                       f"Differes from Remote id: {remoteId}\n"
                       f"With title:              {remoteTitle}")
            cfg.logger.error(message)
            return False


        if localTitle!=remoteTitle:
                message = (f"{i}th Local Title:          {localTitle}\n"
                           f"With Id:                    {localId}\n"
                           f"Differes from Remote Title: {remoteTitle}\n"
                           f"With Id:                    {localId}")
                cfg.logger.error(message)
                return False
    return True



class test_integration(unittest.TestCase):
    '''All tests are in order, failing one will fail subsequent tests.
    This is intentional, redownloading entire playlist for each 
    test would be a waste of bandwidth'''

    PL_URL = None #must be passed 
    plName = 'integration'
    plPath = f'{cfg.testPlPath}/{plName}'

    def test_0_creation(self):

        cfg.logger.info("Running test_creation")

        if os.path.exists(self.plPath):
            shutil.rmtree(self.plPath)

        newPlaylist(self.plPath,self.PL_URL)

        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)


        self.assertTrue(passed)


    
    def test_1_smartSyncNoEdit(self):
        cfg.logger.info("Running test_smartSyncNoEdit")
        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)
    

    def test_2_smartSyncSwap(self):
        '''Simulates remote reordering by reordering local'''
        cfg.logger.info("Running test_smartSyncSwap")
        swap(self.plPath,0 , 1)

        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)

    def test_3_smartSyncMove(self):
        cfg.logger.info("Running test_smartSyncSwap")

        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            numIds = len(metaData['ids'])

        move(self.plPath,0 , int(numIds/2))
        
        smartSync(self.plPath)

        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)


    def test_4_smartSyncShuffle(self):
        '''Simulates remote reordering by shuffling local'''
        cfg.logger.info("Running test_smartSyncShuffle")
        shuffle(self.plPath)

        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)

    def test_5_smartSyncDelAndShuffle(self):
        cfg.logger.info("Running test_smartSyncDelAndShuffle")
        shuffle(self.plPath)

        currentDir = getLocalSongs(self.plPath)
        
        #deletes a third (rounded down) of the songs in the playlist
        toDelete = []
        for _ in range(int(len(currentDir)/3)):
            randSong = random.choice(currentDir)

            while randSong in toDelete:
                #ensures we dont try to delete the same song twice
                randSong = random.choice(currentDir)
            
            toDelete.append(randSong)

        for song in toDelete:
            os.remove(f'{self.plPath}/{song}')


        smartSync(self.plPath)

        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)
    

    def test_6_addTimeStamps(self):
        currentDir = getLocalSongs(self.plPath)

        songName = currentDir[0]
        songPath = f"{self.plPath}/{songName}"

        # Get timestamps
        timestamps = [Timestamp(time=0, label="test 0"), Timestamp(time = 1, label="test1"), Timestamp(time=2, label="test2")]

        if not createChapterFile(songPath, songName):
            self.fail("Chapter Creation Failed")

        wipeChapterFile()

        addTimestampsToChapterFile(timestamps, songPath)

        if not applyChapterFileToSong(songPath, songName):
            cfg.logger.error(f"Failed to Add Timestamps To Song {songName}")
            self.fail("Chapter Creation Failed")

        appliedTimestamps = getTimestamps(cfg.ffmpegMetadataPath)

        self.assertEqual(len(timestamps), len(appliedTimestamps))

        for i in range(0,len(timestamps)):
            self.assertEqual(timestamps[i], appliedTimestamps[i])

    def test_7_scrapeTimeStamps(self):
        videoId = '9WbtgupHTPA'
        knownTimeStamps = [
            Timestamp(time = 0, label = 'beginning'),
            Timestamp(time = 20, label = 'some stuff'),
            Timestamp(time = 90, label = 'shaking up the format'),
            Timestamp(time = 201, label = 'more shaking up the format'),
            Timestamp(time = 361, label = 'wowee whats this'),
        ]

        scrapedTimestamps = scrapeCommentsForTimestamps(videoId)


        self.assertEqual(len(knownTimeStamps), len(scrapedTimestamps))

        for i in range(0,len(scrapedTimestamps)):
            self.assertEqual(scrapedTimestamps[i], knownTimeStamps[i])

    def test_8_stateSummery(self):
        '''logs state of playlist after all tests (should be last in test chain)'''
        cfg.logger.info("Integration Test End Report:")
        
        compareMetaData(self.plPath)
        showPlaylist(self.plPath)

