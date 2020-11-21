import unittest

from sync_dl.helpers import smartSyncNewOrder


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
