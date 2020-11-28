import unittest
import logging


import argparse
import sys

import sync_dl.tests.unitTests as unitTests
import sync_dl.tests.integrationTests as integrationTests

import sync_dl.config as cfg


def parseArgs():
    description = ("unit and integration testing for sync-dl")


    parser = argparse.ArgumentParser(description=description)

    #posistional
    parser.add_argument('URL',nargs='?', type=str, help='the name of the directory for the playlist')


    parser.add_argument('-u','--unit', action='store_true', help='runs all unit tests')
    parser.add_argument('-i','--integration',action='store_true',  help='tests integration using playlist at URL')

    parser.add_argument('-p','--print',action='store_true', help='prints to terminal in addition to tests/testing.log' )

    args,other = parser.parse_known_args()

    sys.argv[1:] = other #additional unittest args

    return args

def setLogging(args):
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh = logging.FileHandler(f"{cfg.modulePath}/tests/testing.log")
    fh.setFormatter(formatter)

    cfg.logger.addHandler(fh)

    if args.print:
        sh = logging.StreamHandler()
        sh.setFormatter(formatter)
        cfg.logger.addHandler(sh)

    cfg.logger.setLevel(level=logging.DEBUG)

if __name__ == "__main__":

    args = parseArgs()

    setLogging(args)


    runall = not (args.unit or args.integration)

    #checks if integration test has to run (whenever -i is used, or if all tests are run)
    if args.integration or runall:
        # if no playlist was provided all further functions cannot run
        if not args.URL:
            print("URL Required for Integration Testing, Use -u to Run Only Unit Tests")
            exit()
        integrationTests.test_integration.PL_URL = args.URL

    if runall:
        unittest.main(unitTests,exit=False)
        unittest.main(integrationTests)

    elif args.unit:
        unittest.main(unitTests)
        
    elif args.integration:
        unittest.main(integrationTests)
