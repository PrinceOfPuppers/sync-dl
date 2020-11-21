import unittest
import logging
from sync_dl.tests.tests import test_smartSyncNewOrder, test_editPlaylist, test_correctStateCorruption


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("sync_dl/tests/testing.log"),
            #logging.StreamHandler()
        ]
    )
    unittest.main()