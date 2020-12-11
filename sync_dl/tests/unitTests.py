import unittest
import os
import shutil
import shelve

import inspect

import sync_dl.config as cfg
from sync_dl.helpers import smartSyncNewOrder,createNumLabel,getLocalSongs,getNumDigets
from sync_dl.plManagement import editPlaylist,correctStateCorruption

from sync_dl.commands import move, swap, manualAdd, moveRange


def createFakePlaylist(name,songs):
    '''creates fake playlist with all songs being as if they where locally added'''

    if not os.path.exists(cfg.testPlPath):
        os.mkdir(cfg.testPlPath)
        
    os.mkdir(f'{cfg.testPlPath}/{name}')
    
    numDigets = getNumDigets(len(songs))

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
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
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
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
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
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        name = 'editPl1'

        songs = ['A' ,'B' ,'C' ,'D'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('3', 3), ('1',1), ('2',2), ('0',0) ]
        
        correct = [ ('3', '0_D'), ('1','1_B'), ('2','2_C'), ('0','3_A') ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)


    def test_2(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        name = 'editPl2'

        songs = ['A' ,'B' ,'C' ,'D','E','F'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('3', 3), ('4',4), ('2',2), ('0',0) ]
        
        correct = [ ('3', '0_D'), ('4','1_E'), ('2','2_C'), ('0','3_A') ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder,True)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)

    def test_3(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        name = 'editPl3'

        songs = ['A' ,'B' ,'C'] 

        createFakePlaylist(name,songs)

        newOrder = [ ]
        
        correct = [ ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder,True)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)
    
    def test_4(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        name = 'editPl3'

        songs = ['A' ,'B' ,'C' ,'D', 'E', 'F', 'G'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('6',6), ('3', 3), ('4',4), ('5',5), ('2',2) ]
        
        correct = [ ('6', '0_G'), ('3','1_D'), ('4','2_E'),('5','3_F'), ('2','4_C') ]
        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder,True)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)

class test_smartSyncNewOrder(unittest.TestCase):

    def test_insertAndDelete(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'B' ,'C' ,'2']

        correct = [('A',0) ,('1',None) ,('B',1) ,('C',2) ,('D',3) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_insertDeleteSwap(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2']


        correct = [('A',0) ,('1',None) ,('C',2) ,('D',3) ,('B',1) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_3(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',0) ,('1',None) ,('C',2),('D',3),('E',4) ,('B',1) , ('2',None), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_LocalDeleteAll(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = [] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',None) ,('1',None) ,('C',None),('B',None) , ('2',None), ('F',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_RemoteDeleteAll(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = []


        correct = [('A',0) ,('B',1), ('C',2), ('D',3), ('E',4), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_Reversal(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','D','C','B','A']


        correct = [('E',4), ('D',3), ('C',2), ('B',1), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_7(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','1','D','2','B','A']


        correct = [('E',4), ('1',None),('D',3),('2',None), ('B',1), ('C',2), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


class test_move(unittest.TestCase):
    
    def test_moveLarger(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")

        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('0', '0_A'), ('2','1_C'), ('3','2_D'), ('1','3_B'), ('4','4_E') ]

        plPath = f'{cfg.testPlPath}/{name}'
        move(plPath,1,3)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    
    def test_moveSmaller(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")

        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('2', '0_C'), ('0','1_A'), ('1','2_B'), ('3','3_D'), ('4','4_E') ]

        plPath = f'{cfg.testPlPath}/{name}'
        move(plPath,2,0)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)


class test_swap(unittest.TestCase):
    
    def test_swap1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('0', '0_A'), ('3','1_D'), ('2','2_C'), ('1','3_B'), ('4','4_E') ]

        plPath = f'{cfg.testPlPath}/{name}'
        swap(plPath,1,3)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    
    def test_swap2(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('4', '0_E'), ('1','1_B'), ('2','2_C'), ('3','3_D'), ('0','4_A') ]

        plPath = f'{cfg.testPlPath}/{name}'
        swap(plPath,0,4)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)


class test_manualAdd(unittest.TestCase):
    def test_manualAdd1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        songPath = f"{cfg.testPlPath}/X"
        open(songPath,'a').close()
        
        
        correct = [ ('0', '0_A'), ('1','1_B'), ('2','2_C'), ('3','3_D'),(cfg.manualAddId,'4_X'), ('4','5_E') ]
        plPath = f'{cfg.testPlPath}/{name}'
        manualAdd(plPath,songPath,4)
        
        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    

    def test_manualAdd2(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E'] 

        createFakePlaylist(name,songs)

        songPath = f"{cfg.testPlPath}/X"
        open(songPath,'a').close()
        
        
        correct = [ (cfg.manualAddId,'0_X'), ('0', '1_A'), ('1','2_B'), ('2','3_C'), ('3','4_D'), ('4','5_E') ]
        plPath = f'{cfg.testPlPath}/{name}'
        manualAdd(plPath,songPath,0)
        
        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    


class test_moveRange(unittest.TestCase):
    
    def test_moveRangeLarger1(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('0', '0_A'), ('4','1_E'), ('1','2_B'), ('2','3_C'), ('3','4_D'), ('5','5_F'), ('6','6_G') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,1,3,5)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    
    def test_moveRangeLarger2(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('3','0_D'),('4','1_E'), ('5','2_F'), ('6','3_G'),('0', '4_A'), ('1','5_B'), ('2','6_C') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,0,2,7)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)

    def test_moveRangeSmaller1(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [  ('3','0_D'), ('4','1_E'),('5','2_F'),('0', '3_A'), ('1','4_B'), ('2','5_C') , ('6','6_G') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,3,5,0)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)


    def test_moveRangeSmaller2(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [  ('4','0_E'),('5','1_F'),('6','2_G'),('0', '3_A'), ('1','4_B'), ('2','5_C'), ('3','6_D')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,4,-1,0)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)