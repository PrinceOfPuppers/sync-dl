import unittest
import os
import shutil
import shelve

import sync_dl.config as cfg
from sync_dl.helpers import smartSyncNewOrder,createNumLabel,getLocalSongs
from sync_dl.plManagement import editPlaylist,correctStateCorruption

def createFakePlaylist(name,songs):
    '''creates fake playlist with all songs being as if they where locally added'''

    if not os.path.exists(cfg.testPlPath):
        os.mkdir(cfg.testPlPath)
        
    os.mkdir(f'{cfg.testPlPath}/{name}')
    
    numDigets = len(str(len(songs)))

    with shelve.open(f"{cfg.testPlPath}/{name}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        metaData["url"] = "placeholder"
        metaData["ids"] = []

        for i,song in enumerate(songs):
            songName = f"{createNumLabel(i,numDigets)}_{song}"
            open(f"{cfg.testPlPath}/{name}/{songName}",'a').close()
            metaData["ids"].append(str(i)) # i is used to trace songs in metadata during testing
        

def getPlaylistData(name):
    '''used to validate playlist returns list of tups (id, song name)'''
    result = []
    songs = getLocalSongs(f"{cfg.testPlPath}/{name}")
    with shelve.open(f"{cfg.testPlPath}/{name}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
        for i,songId in enumerate(metaData['ids']):
            result.append( (songId,songs[i]) )
    
    return result


class test_correctStateCorruption(unittest.TestCase):

    def test_removedSongs(self):
        name = 'RemovedSongs'

        songs = ['A' ,'B' ,'C' ,'D', 'E'] 



        createFakePlaylist(name,songs)

        os.remove(f'{cfg.testPlPath}/{name}/0_A')
        os.remove(f'{cfg.testPlPath}/{name}/4_E')
        os.remove(f'{cfg.testPlPath}/{name}/2_C')
        
        correctStateCorruption(f'{cfg.testPlPath}/{name}')

        correct = [ ('1', '0_B'), ('3','1_D') ]


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)
    
    def test_blankMetaData(self):
        name = 'blankMetaData'

        songs = ['A' ,'B' ,'C' ,'D'] 



        createFakePlaylist(name,songs)


        with shelve.open(f"{cfg.testPlPath}/{name}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            metaData['ids'].insert(2,'')
        
        correctStateCorruption(f'{cfg.testPlPath}/{name}')

        correct = [ ('0', '0_A'), ('1', '1_B'), ('2','2_C'), ('3','3_D') ]


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)

class test_editPlaylist(unittest.TestCase):
    
    def test_1(self):
        name = 'testPl'

        songs = ['A' ,'B' ,'C' ,'D'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('3', 3), ('1',1), ('2',2), ('0',0) ]
        
        correct = [ ('3', '0_D'), ('1','1_B'), ('2','2_C'), ('0','3_A') ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)






class test_smartSyncNewOrder(unittest.TestCase):

    def test_insertAndDelete(self):
        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'B' ,'C' ,'2']

        correct = [('A',0) ,('1',None) ,('B',1) ,('C',2) ,('D',3) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_insertDeleteSwap(self):
        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2']


        correct = [('A',0) ,('1',None) ,('C',2) ,('D',3) ,('B',1) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_3(self):
        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',0) ,('1',None) ,('C',2),('D',3),('E',4) ,('B',1) , ('2',None), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_LocalDeleteAll(self):
        localIds = [] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',None) ,('1',None) ,('C',None),('B',None) , ('2',None), ('F',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_RemoteDeleteAll(self):
        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = []


        correct = [('A',0) ,('B',1), ('C',2), ('D',3), ('E',4), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_Reversal(self):
        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','D','C','B','A']


        correct = [('E',4), ('D',3), ('C',2), ('B',1), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_7(self):
        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','1','D','2','B','A']


        correct = [('E',4), ('1',None),('D',3),('2',None), ('B',1), ('C',2), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


