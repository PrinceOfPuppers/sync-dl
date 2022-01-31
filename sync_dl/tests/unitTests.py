import unittest
import os
import shutil
import shelve
import sys
import inspect
from string import ascii_uppercase

import sync_dl.config as cfg
from sync_dl.helpers import smartSyncNewOrder,createNumLabel,getLocalSongs,getNumDigets, calcuateTransferMoves, TransferMove
from sync_dl.plManagement import editPlaylist,correctStateCorruption

from sync_dl.commands import move, swap, manualAdd, moveRange,togglePrepends

try:
    from sync_dl_ytapi.helpers import longestIncreasingSequence,oldToNewPushOrder,pushOrderMoves
except:
    cfg.logger.error("Please Install sync_dl_ytapi to Run Unittests")
    sys.exit(1)

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
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D', 'E'] 

        plPath = f'{cfg.testPlPath}/{name}'

        createFakePlaylist(name,songs)

        os.remove(f'{plPath}/0_A')
        os.remove(f'{plPath}/4_E')
        os.remove(f'{plPath}/2_C')
        
        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            correctStateCorruption(f'{cfg.testPlPath}/{name}',metaData)

        correct = [ ('1', '0_B'), ('3','1_D') ]


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)
    
    def test_blankMetaData(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        
        plPath = f'{cfg.testPlPath}/{name}'
        
        songs = ['A' ,'B' ,'C' ,'D'] 

        createFakePlaylist(name,songs)

        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            metaData['ids'].insert(2,'')
        
            correctStateCorruption(plPath,metaData)

        correct = [ ('0', '0_A'), ('1', '1_B'), ('2','2_C'), ('3','3_D') ]


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)


    def test_removePrepend(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D'] 
        createFakePlaylist(name,songs)

        correct = [  ('0', '0_A'), ('1','1_B'), ('2','2_C'), ('3','3_D')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        
        togglePrepends(plPath)

        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            correctStateCorruption(plPath,metaData)
        
        result = getPlaylistData(name)
        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    
    def test_removeSongsAndPrepends(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D', 'E'] 

        createFakePlaylist(name,songs)

        plPath = f'{cfg.testPlPath}/{name}'

        os.remove(f'{plPath}/0_A')
        os.remove(f'{plPath}/4_E')
        os.remove(f'{plPath}/2_C')
        togglePrepends(plPath)
        

        with shelve.open(f"{plPath}/{cfg.metaDataName}", 'c',writeback=True) as metaData:
            correctStateCorruption(plPath,metaData)

        correct = [ ('1', '0_B'), ('3','1_D') ]


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)

class test_togglePrepends(unittest.TestCase):
    def test_togglePrepends1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D'] 
        plPath = f'{cfg.testPlPath}/{name}'
        
        createFakePlaylist(name,songs)
        
        togglePrepends(plPath)
        togglePrepends(plPath)
        
        correct = [  ('0', '0_A'), ('1','1_B'), ('2','2_C'), ('3','3_D')  ]
        
        result = getPlaylistData(name)
        shutil.rmtree(plPath)
        self.assertEqual(result,correct)



class test_editPlaylist(unittest.TestCase):
    
    def test_editPl1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('3', 3), ('1',1), ('2',2), ('0',0) ]
        
        correct = [ ('3', '0_D'), ('1','1_B'), ('2','2_C'), ('0','3_A') ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)


    def test_editPl2(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C' ,'D','E','F'] 

        createFakePlaylist(name,songs)

        newOrder = [ ('3', 3), ('4',4), ('2',2), ('0',0) ]
        
        correct = [ ('3', '0_D'), ('4','1_E'), ('2','2_C'), ('0','3_A') ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder,True)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)

    def test_editPl3(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        songs = ['A' ,'B' ,'C'] 

        createFakePlaylist(name,songs)

        newOrder = [ ]
        
        correct = [ ]

        editPlaylist(f'{cfg.testPlPath}/{name}',newOrder,True)


        result = getPlaylistData(name)

        shutil.rmtree(f'{cfg.testPlPath}/{name}')
        self.assertEqual(result,correct)
    
    def test_editPl4(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

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
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'B' ,'C' ,'2']

        correct = [('A',0) ,('1',None) ,('B',1) ,('C',2) ,('D',3) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_insertDeleteSwap(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        localIds = ['A' ,'B' ,'C' ,'D'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2']


        correct = [('A',0) ,('1',None) ,('C',2) ,('D',3) ,('B',1) ,('2',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)
    
    def test_3(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',0) ,('1',None) ,('C',2),('D',3),('E',4) ,('B',1) , ('2',None), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_LocalDeleteAll(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = [] 
        remoteIds = ['A' ,'1' ,'C' ,'B' ,'2','F']


        correct = [('A',None) ,('1',None) ,('C',None),('B',None) , ('2',None), ('F',None)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_RemoteDeleteAll(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['A' ,'B' ,'C' ,'D', 'E', 'F','G'] 
        remoteIds = []


        correct = [('A',0) ,('B',1), ('C',2), ('D',3), ('E',4), ('F',5), ('G',6)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)

    def test_Reversal(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        
        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','D','C','B','A']


        correct = [('E',4), ('D',3), ('C',2), ('B',1), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


    def test_7(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['A' ,'B' ,'C' ,'D', 'E'] 
        remoteIds = ['E','1','D','2','B','A']


        correct = [('E',4), ('1',None),('D',3),('2',None), ('B',1), ('C',2), ('A',0)]


        result = smartSyncNewOrder(localIds,remoteIds)
        self.assertEqual(result,correct)


class test_move(unittest.TestCase):
    
    def test_moveLarger(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
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
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('0', '0_A'), ('4','1_E'), ('5','2_F'), ('1','3_B'), ('2','4_C'), ('3','5_D'), ('6','6_G') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,1,3,5)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)
    
    def test_moveRangeLarger2(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [ ('3','0_D'),('4','1_E'), ('5','2_F'), ('6','3_G'),('0', '4_A'), ('1','5_B'), ('2','6_C') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,0,2,6)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)

    def test_moveRangeSmaller1(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)

        
        correct = [  ('3','0_D'), ('4','1_E'),('5','2_F'),('0', '3_A'), ('1','4_B'), ('2','5_C') , ('6','6_G') ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,3,5,-1)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)


    def test_moveRangeSmaller2(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)
        
        correct = [  ('0', '0_A'), ('1','1_B'),('4','2_E'),('5','3_F'),('6','4_G'), ('2','5_C'), ('3','6_D')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,4,-1,1)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)

    def test_moveRangeSingleSmaller(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)
        
        correct = [  ('0', '0_A'), ('1','1_B'),('4','2_E'), ('2','3_C'), ('3','4_D'),('5','5_F'),('6','6_G')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,4,4,1)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)

    def test_moveRangeSingleLarger(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)
        
        correct = [  ('0', '0_A'), ('1','1_B'), ('2','2_C'),('4','3_E'),('5','4_F'), ('3','5_D'),('6','6_G')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,3,3,5)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)

#################################
## youtube api submodule tests ##
#################################

class test_yt_api_helpers(unittest.TestCase):
    def test_longestIncreasingSequence(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")
        
        def acending(numList):
            
            for i in range(1,len(numList)):
                if numList[i] <= numList[i-1]:
                    return False
            return True

        def isSubSequenceInSequence(subSequence, sequence):
            prevIndex = 0
            for _,num in enumerate(subSequence):
                try:
                    prevIndex = sequence[prevIndex:].index(num) + 1
                except:
                    return False
            return True

        pairs = [
            ([7, 9, 1, 4, 0, 8, 3, 6, 5, 2],3),
            ([5, 4, 2, 1, 0, 6, 3, 9, 8, 7],3),
            ([4, 1, 9, 5, 3, 7, 0, 6, 2, 8],4),
            ([2, 0, 5, 7, 4, 9, 8, 6, 1, 3],4),
            ([0, 1, 7, 5, 9, 6, 4, 8, 3, 2],5),
            ([0, 4, 5, 7, 9, 8, 2, 3, 1, 6],5),
            ([5, 0, 9, 1, 2, 8, 4, 3, 7, 6],5),
            ([5, 4, 6, 0, 2, 8, 3, 9, 1, 7],4),
            ([5, 2, 1, 4, 0, 8, 9, 6, 7, 3],4),
            ([2, 0, 3, 8, 5, 6, 4, 7, 9, 1],6),
            ([1, 3, 5, 9, 4, 8, 2, 0, 6, 7],5),
            ([9, 2, 6, 4, 3, 5, 7, 0, 8, 1],5),
            ([7, 1, 2, 8, 9, 0, 5, 3, 4, 6],5),
            ([3, 4, 8, 1, 9, 5, 6, 2, 0, 7],5),
            ([4, 1, 2, 8, 7, 0, 9, 3, 5, 6],5),
            ([1, 4, 2, 0, 7, 9, 3, 6, 5, 8],5),
            ([6, 0, 2, 3, 8, 9, 1, 4, 5, 7],6),
            ([4, 1, 5, 2, 8, 0, 9, 3, 6, 7],5),
            ([4, 8, 0, 2, 9, 7, 6, 1, 3, 5],4),
        ]

        for pair in pairs:
            numList,correctLen = pair
            ans = longestIncreasingSequence(numList)

            if not acending(ans):
                self.fail(f'Answer is not acending! \nanswer: {ans} \ninput: {numList}')
            if len(ans)!=correctLen:
                self.fail(f'Answer has Length {len(ans)}, correct Length is {correctLen}. \nanswer: {ans} \ninput: {numList}')
                
            if not isSubSequenceInSequence(ans,numList):
                self.fail(f'Answer Subsequence is not in Input Sequence. \nanswer: {ans} \ninput: {numList}')



class test_yt_api_getNewRemoteOrder(unittest.TestCase):
    def test_insertAndDelete(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['A','1' ,'C','2' ,'D'] 
        remoteIds = ['A','B','C','D']
        

        correct = [0, 1 ,2 ,3]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
    def test_insertDeleteSwap(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = ['C','1','A','2' ,'D'] 
        remoteIds = ['A','B','C','D']

        correct = [1,2,0,3]


        result = oldToNewPushOrder(remoteIds,localIds)

        self.assertEqual(result,correct)

    def test_3(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['A', '1', 'E','B', 'D', 'C', '2'] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  4,  6,  5,  1,  2,  3 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)


    def test_4(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['1', 'E', 'D', 'C', '2'] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  1,  6,  5,  2,  3,  4 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
    def test_5(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  [] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  1,  2,  3,  4,  5,  6 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
        
    def test_6(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['A','B','C','D','E','F','G']
        remoteIds = []
        correct =   []


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    

    def test_7(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds = [
            'NigPr2mmENA',#0
            'DzoYNerl4P8',#1
            '6WYsoeVNEDY',#2
            '0Wc2Og4vr2I',#3
            'jhFDyDgMVUI',#4
            'MfB3l3PHEFQ',#5
            'I3EEhcLlKdo',#6
            'bYwnf8r92G0',#7
            'HiLKVdNJt_o',#8
            'irIxkjXOp5M',#9
            '8Yuorb-rB9A',#
            'lUYZJRlOHyw',#10
            'p1cymwvDf0w',#11
            '4TAGhEVNCFc',#12
            'RkMzJGAV7Vs',#13
            'BhEfvGZM6jw',#14
        ]
        remoteIds = [
            'MfB3l3PHEFQ',#5
            'DzoYNerl4P8',#1
            '6WYsoeVNEDY',#2
            '0Wc2Og4vr2I',#3
            'jhFDyDgMVUI',#4
            'I3EEhcLlKdo',#6
            'bYwnf8r92G0',#7
            'HiLKVdNJt_o',#8
            'irIxkjXOp5M',#9
            'lUYZJRlOHyw',#10
            'p1cymwvDf0w',#11
            '4TAGhEVNCFc',#12
            'RkMzJGAV7Vs',#13
            'BhEfvGZM6jw',#14
            'NigPr2mmENA',#0
        ]

        correct = [5,1,2,3,4,6,7,8,9,10,11,12,13,14,0]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)



# Helpers for test_yt_api_pushOrderMoves
def simulateMove(remoteIds,remoteItemIds,move):
    newIndex,_,remoteItemId = move
    oldIndex = remoteItemIds.index(remoteItemId)

    remoteIds.insert(newIndex,remoteIds.pop(oldIndex))
    remoteItemIds.insert(newIndex,remoteItemIds.pop(oldIndex))

def compareLocalAndRemote(remoteIds, localIds):
    remoteIndex = 0
    localIndex = 0
    while True:
        if remoteIndex>=len(remoteIds) or localIndex>=len(localIds):
            break

        remoteId = remoteIds[remoteIndex]
        localId = localIds[localIndex]
        if remoteId not in localIds:
            remoteIndex+=1
            continue
            
        if localId not in remoteIds:
            localIndex+=1
            continue
        
        if remoteId!=localId:
            return False
        
        remoteIndex+=1
        localIndex+=1

    return True

def remoteCorrectOrder(remoteIds,localIds):
    ''' any id not in local must remain after the id that came before it before moving '''


    alphaToNum = lambda char: ord(char.lower()) - 96

    for i in range(1,len(remoteIds)):
        currentId = remoteIds[i]
        prevId = remoteIds[i-1]

        if currentId not in localIds:
            if alphaToNum(currentId)!= alphaToNum(prevId)+1:
                return False

    return True



class test_yt_api_pushOrderMoves(unittest.TestCase):
    def test_1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['A','1','B','C'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
    
    def test_2(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['1','B','E','A','C'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')

    def test_3(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['1','F','B','A','C'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')

    def test_reversal(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['G','F','E','D','C','B','A'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')


    def test_partialReversal(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['F','E','C','B'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')



    def test_firstLastSwap(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        localIds =  ['G','1','B','E','C','A'] 
        remoteIds = ['A','B','C','D','E','F','G'] # must be in alphabetical order for remoteCorrectOrder
        remoteItemIds = ['A','B','C','D','E','F','G']

        moves = pushOrderMoves(remoteIds,remoteItemIds,localIds)
        for move in moves:
            simulateMove(remoteIds,remoteItemIds,move)
        
        # Checks if remote ids have taken on localIds order
        if not compareLocalAndRemote(remoteIds,localIds):
            self.fail(f'RemoteIds Do Not Match LocalIds After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')
        
        # Checks if any remoteIds not in localIds stayed after the correct Id
        if not remoteCorrectOrder(remoteIds,localIds):
            self.fail(f'RemoteIds Ids Not In Correct Order After Moves\nremoteIds: {remoteIds}\nlocalIds:  {localIds}')

# helper for test_calculateTransferMoves
def getGenericState(length: int, filePrepends: str = '', idPrepends: str = ''):
    if length > len(ascii_uppercase):
        raise Exception()
    files = list(ascii_uppercase[0:length])
    ids = list(ascii_uppercase[0:length])
    for i in range(0, length):
        files[i] = filePrepends + files[i]
        ids[i] = idPrepends + ids[i]

    return files, ids


def _setPadded(l: list, index: int, ele):
    for _ in range(index - len(l) + 1):
        l.append('')
    l[index] = ele

def _movePadded(l: list, srcIndex: int, destIndex: int):
    for _ in range(destIndex - len(l) + 1):
        l.append('')
    l[destIndex] = l[srcIndex]
    l[srcIndex] = ''


def simulateTransferMoves(moves: list[TransferMove], srcStart: int, srcEnd: int, destIndex: int, 
                          srcDir:list, destDir:list, srcLocalIds:list, destLocalIds:list, srcRemoteIds:list, destRemoteIDs:list):

    # make room for block
    blockSize = srcEnd - srcStart + 1
    for i in reversed(range(destIndex+1,len(destLocalIds))):
        _movePadded(destDir, i, i+blockSize)
        _movePadded(destLocalIds, i, i+blockSize)


    for move in moves:
        if move.performCopy:
            _setPadded(destDir, move.destCopyIndex, srcDir[move.srcCopyIndex])
            _setPadded(destLocalIds, move.destCopyIndex, srcLocalIds[move.srcCopyIndex])

        if move.performRemoteAdd:
            destRemoteIDs.insert(move.destRemoteAddIndex, move.songId)

        if move.performLocalDelete:
            srcDir.pop(move.srcLocalDeleteIndex)
            srcLocalIds.pop(move.srcLocalDeleteIndex)

        if move.performRemoteDelete:
            srcRemoteIds.pop(move.srcRemoteDeleteIndex)




class test_calculateTransferMoves(unittest.TestCase):
    def test_emptyDestIdenticalRemote(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 'f', 'i')
        srcRemoteIds = srcLocalIds.copy()

        destLocalIds   = []
        destRemoteIds  = []
        destDir = []

        srcStart = 1
        srcEnd = 3
        destIndex = -1

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, ['fA', 'fE'])
        self.assertListEqual(srcLocalIds, ['iA', 'iE'])
        self.assertListEqual(srcRemoteIds, ['iA', 'iE'])

        self.assertListEqual(destDir, ['fB', 'fC', 'fD'])
        self.assertListEqual(destLocalIds, ['iB', 'iC', 'iD'])
        self.assertListEqual(destRemoteIds, ['iB', 'iC', 'iD'])

    def test_appendDestIdenticalRemote(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 's', 's')
        srcRemoteIds = srcLocalIds.copy()

        destDir, destLocalIds = getGenericState(3, 'd', 'd')
        destRemoteIds = destLocalIds.copy()

        srcStart = 1
        srcEnd = 3
        destIndex = len(destDir) - 1

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, ['sA', 'sE'])
        self.assertListEqual(srcLocalIds, ['sA', 'sE'])
        self.assertListEqual(srcRemoteIds, ['sA', 'sE'])

        self.assertListEqual(destDir, ['dA', 'dB', 'dC', 'sB', 'sC', 'sD'])
        self.assertListEqual(destLocalIds, ['dA', 'dB', 'dC', 'sB', 'sC', 'sD'])
        self.assertListEqual(destRemoteIds, ['dA', 'dB', 'dC', 'sB', 'sC', 'sD'])

    def test_prependDestIdenticalRemote(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 's', 's')
        srcRemoteIds = srcLocalIds.copy()

        destDir, destLocalIds = getGenericState(3, 'd', 'd')
        destRemoteIds = destLocalIds.copy()

        srcStart = 1
        srcEnd = 3
        destIndex = -1

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, ['sA', 'sE'])
        self.assertListEqual(srcLocalIds, ['sA', 'sE'])
        self.assertListEqual(srcRemoteIds, ['sA', 'sE'])

        self.assertListEqual(destDir, ['sB', 'sC', 'sD', 'dA', 'dB', 'dC'])
        self.assertListEqual(destLocalIds, ['sB', 'sC', 'sD', 'dA', 'dB', 'dC'])
        self.assertListEqual(destRemoteIds, ['sB', 'sC', 'sD', 'dA', 'dB', 'dC'])

    def test_middleDestIdenticalRemote(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 's', 's')
        srcRemoteIds = srcLocalIds.copy()

        destDir, destLocalIds = getGenericState(3, 'd', 'd')
        destRemoteIds = destLocalIds.copy()

        srcStart = 0
        srcEnd = 3
        destIndex = 0

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, ['sE'])
        self.assertListEqual(srcLocalIds, ['sE'])
        self.assertListEqual(srcRemoteIds, ['sE'])

        self.assertListEqual(destDir, ['dA', 'sA', 'sB', 'sC', 'sD', 'dB', 'dC'])
        self.assertListEqual(destLocalIds, ['dA', 'sA', 'sB', 'sC', 'sD', 'dB', 'dC'])
        self.assertListEqual(destRemoteIds, ['dA', 'sA', 'sB', 'sC', 'sD', 'dB', 'dC'])

    def test_AllSrcIdenticalRemote(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 's', 's')
        srcRemoteIds = srcLocalIds.copy()

        destDir, destLocalIds = getGenericState(3, 'd', 'd')
        destRemoteIds = destLocalIds.copy()

        srcStart = 0
        srcEnd = len(srcDir) - 1
        destIndex = 0

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, [])
        self.assertListEqual(srcLocalIds, [])
        self.assertListEqual(srcRemoteIds, [])

        self.assertListEqual(destDir, ['dA', 'sA', 'sB', 'sC', 'sD', 'sE', 'dB', 'dC'])
        self.assertListEqual(destLocalIds, ['dA', 'sA', 'sB', 'sC', 'sD', 'sE', 'dB', 'dC'])
        self.assertListEqual(destRemoteIds, ['dA', 'sA', 'sB', 'sC', 'sD', 'sE', 'dB', 'dC'])

    def test_srcRemoteIsSubset1(self):
        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {self.__class__.__name__}: {name}")

        srcDir, srcLocalIds = getGenericState(5, 's', 's')
        srcRemoteIds = srcLocalIds.copy()
        srcRemoteIds.pop(1)

        destDir, destLocalIds = getGenericState(3, 'd', 'd')
        destRemoteIds = destLocalIds.copy()

        srcStart = 1
        srcEnd = 2
        destIndex = 0

        moves = calcuateTransferMoves(srcDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds, srcStart, srcEnd, destIndex)
        simulateTransferMoves(moves, srcStart, srcEnd, destIndex, srcDir, destDir, srcLocalIds, destLocalIds, srcRemoteIds, destRemoteIds)

        self.assertListEqual(srcDir, ['sA', 'sD', 'sE'])
        self.assertListEqual(srcLocalIds, ['sA', 'sD', 'sE'])
        self.assertListEqual(srcRemoteIds, ['sA', 'sD', 'sE'])

        self.assertListEqual(destDir, ['dA', 'sB', 'sC', 'dB', 'dC'])
        self.assertListEqual(destLocalIds, ['dA', 'sB', 'sC', 'dB', 'dC'])
        self.assertListEqual(destRemoteIds, ['dA', 'sC', 'dB', 'dC'])
