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

        
        correct = [ ('0', '0_A'), ('4','1_E'), ('5','2_F'), ('1','3_B'), ('2','4_C'), ('3','5_D'), ('6','6_G') ]

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
        moveRange(plPath,0,2,6)

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
        moveRange(plPath,3,5,-1)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)


    def test_moveRangeSmaller2(self):

        name = inspect.currentframe().f_code.co_name
        cfg.logger.info(f"Running {name}")
        songs = ['A' ,'B' ,'C' ,'D','E','F','G'] 

        createFakePlaylist(name,songs)
        
        correct = [  ('0', '0_A'), ('1','1_B'),('4','2_E'),('5','3_F'),('6','4_G'), ('2','5_C'), ('3','6_D')  ]

        plPath = f'{cfg.testPlPath}/{name}'
        moveRange(plPath,4,-1,1)

        result = getPlaylistData(name)

        shutil.rmtree(plPath)
        self.assertEqual(result,correct)



#################################
## youtube api submodule tests ##
#################################
from sync_dl.yt_api.helpers import longestIncreasingSequence,oldToNewPushOrder


class test_yt_api_helpers(unittest.TestCase):
    def test_longestIncreasingSequence(self):

        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        
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
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds = ['A','1' ,'C','2' ,'D'] 
        remoteIds = ['A','B','C','D']
        

        correct = [0, 1 ,2 ,3]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
    def test_insertDeleteSwap(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")


        localIds = ['C','1','A','2' ,'D'] 
        remoteIds = ['A','B','C','D']

        correct = [1,2,0,3]


        result = oldToNewPushOrder(remoteIds,localIds)

        self.assertEqual(result,correct)

    def test_3(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds =  ['A', '1', 'E','B', 'D', 'C', '2'] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  4,  6,  5,  1,  2,  3 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)


    def test_4(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds =  ['1', 'E', 'D', 'C', '2'] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  1,  6,  5,  2,  3,  4 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
    def test_5(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds =  [] 
        remoteIds = ['A','B','C','D','E','F','G']
        correct =   [ 0,  1,  2,  3,  4,  5,  6 ]


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)
    
        
    def test_6(self):
        cfg.logger.info(f"Running {inspect.currentframe().f_code.co_name}")
        localIds =  ['A','B','C','D','E','F','G']
        remoteIds = []
        correct =   []


        result = oldToNewPushOrder(remoteIds,localIds)
        self.assertEqual(result,correct)