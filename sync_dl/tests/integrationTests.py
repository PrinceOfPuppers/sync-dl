
import logging
import re
import unittest
import os
import shelve
import shutil
import difflib
import random

from syncdl import smartSync,newPlaylist,swap,shuffle
import sync_dl.config as cfg
from sync_dl.helpers import smartSyncNewOrder,createNumLabel,getLocalSongs, compareMetaData, showPlaylist
from sync_dl.plManagement import editPlaylist,correctStateCorruption
from sync_dl.ytdlWrappers import getTitle,getIdsAndTitles


def metaDataSongsCorrect(metaData,plPath):
    '''
    tests if metadata ids corrispond to the correct remote songs.
    returns boolian test result and logs details

    test fails if local title does not match remote title
    manually added songs are ignored
    '''
    logging.info("Testing if Metadata IDs Corrispond to Correct Songs")

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
                logging.error(message)
                return False
    logging.info("Test Passed")
    return True

def metaDataMatches(metaData,plPath):
    '''
    metadata and local playlist must perfectly match remote playlist for this to return true
    '''
    logging.info("Testing If Metadata Perfect Matches Remote Playlist")

    currentDir = getLocalSongs(plPath)

    localIds = metaData['ids']

    remoteIds, remoteTitles = getIdsAndTitles(metaData['url'])

    if len(localIds) != len(currentDir):
        logging.error(f"metadata ids and local playlist differ in length {len(localIds)} to {len(currentDir)}")
        return False
    if len(localIds)!= len(remoteIds):
        logging.error(f"local and remote playlists differ in length {len(localIds)} to {len(remoteIds)}")
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
            logging.error(message)
            return False

        diffRatio = difflib.SequenceMatcher(None,localTitle,remoteTitle).ratio()
        if diffRatio<0.9:
                message = (f"{i}th Local Title:          {localTitle}\n"
                           f"With Id:                    {localId}\n"
                           f"Differes from Remote Title: {remoteTitle}\n"
                           f"With Id:                    {localId}"
                           f"Title Diff Ratio:           {diffRatio}")
                logging.error(message)
                return False
    return True



class test_integration(unittest.TestCase):
    '''All tests are in order, failing one will fail subsequent tests.
    This is intentional, redownloading entire playlist for each 
    test would be a waste of bandwidth'''

    PL_URL = None #must be passed 
    plName = 'integration'
    plPath = f'{cfg.testPlPath}/{plName}'

    def test_creation(self):
        logging.info("Running test_creation")
        if not os.path.exists(self.plPath):
            newPlaylist(self.plPath,self.PL_URL)

            with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
                passed = metaDataMatches(metaData,self.plPath)


            self.assertTrue(passed)
        else:
            self.skipTest('Integration Testing Playlist Already Downloaded')
    
    def test_smartSyncNoEdit(self):
        logging.info("Running test_smartSyncNoEdit")
        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)
    

    def test_smartSyncSwap(self):
        '''Simulates remote reordering by reordering local'''
        logging.info("Running test_smartSyncSwap")
        swap(self.plPath,0 , 1)

        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)
    
    def test_smartSyncShuffle(self):
        '''Simulates remote reordering by shuffling local'''
        logging.info("Running test_smartSyncShuffle")
        shuffle(self.plPath)

        smartSync(self.plPath)
        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            passed = metaDataMatches(metaData,self.plPath)

        self.assertTrue(passed)

    def test_smartSyncDelAndShuffle(self):
        logging.info("Running test_smartSyncDelAndShuffle")
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
    



    def test_stateSummery(self):
        '''logs state of playlist after all tests (should be last in test chain)'''
        logging.info("End of Integration Test Summery")

        with shelve.open(f"{self.plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            compareMetaData(metaData, logging.info)
            showPlaylist(metaData,logging.info,self.plPath,urlWithoutId='https://www.youtube.com/watch?v=')
