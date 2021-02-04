
from sync_dl import config as cfg
# from sync_dl.plManagement import correctStateCorruption #used to clean up state in the event of sigint
from signal import signal,SIGINT,SIGABRT,SIGTERM,Signals
import sys


class _NoInterrupt:
    inNoInterrupt = False
    signalReceived=False

    def __enter__(self):
        if self.signalReceived:
            self.signalReceived = False
            sys.exit()

        self.inNoInterrupt=True


    def __exit__(self, type, value, traceback):
        self.inNoInterrupt=False
        if self.signalReceived:
            self.signalReceived = False
            sys.exit()

    def handler(self,sig,frame):
        if not self.inNoInterrupt:
            sys.exit()

        self.signalReceived = True
        cfg.logger.info(f'{Signals(2).name} Received, Closing after this Operation')

    def simulateSigint(self):
        '''can be used to trigger intrrupt from another thread'''
        self.signalReceived = True


noInterrupt = _NoInterrupt()
signal(SIGINT,noInterrupt.handler)

def main():
    from sync_dl.cli import cli

    cli()
