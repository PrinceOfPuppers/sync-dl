import unittest
import logging
from sync_dl.tests.unitTests import test_smartSyncNewOrder, test_editPlaylist, test_correctStateCorruption
from sync_dl.tests.integrationTests import test_integration

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("sync_dl/tests/testing.log"),
            #logging.StreamHandler()
        ]
    )
    test_integration.PL_URL = 'https://www.youtube.com/playlist?list=PLbg8uA1JzGJD56Lfl7aYK4iW2vJHDo0DE'
    unittest.main()

