
from sync_dl import config as cfg
from signal import signal,SIGINT,SIGABRT,SIGTERM,Signals

class _NoInterrupt:
    inNoInterrupt = False
    signalReceived=False
    def __enter__(self):
        self.inNoInterrupt=True


    def __exit__(self, type, value, traceback):
        self.inNoInterrupt=False
        if self.signalReceived:
            exit()

    def handler(self,sig,frame):
        if not self.inNoInterrupt:
            exit()

        self.signalReceived = True
        cfg.logger.info(f'{Signals(2).name} Received, Closing after this Operation')


noInterrupt = _NoInterrupt()

def main():
    from sync_dl.cli import cli
    signal(SIGINT,noInterrupt.handler)

    cli()