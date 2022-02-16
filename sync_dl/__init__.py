
from threading import current_thread
from sync_dl import config as cfg
from signal import signal, SIGINT, Signals#,SIGABRT,SIGTERM

__version__ = "2.3.2"

class InterruptTriggered(Exception):
    pass

class _NoInterrupt:
    noInterruptDepth = 0
    signalReceived=False

    def __enter__(self):
        if self.interruptible() and self.signalReceived:
            self.signalReceived = False
            self.interrupt()

        self.noInterruptDepth += 1


    def __exit__(self, type, value, traceback):
        self.noInterruptDepth -= 1
        self.noInterruptDepth = max(0, self.noInterruptDepth)
        if self.interruptible() and self.signalReceived:
            self.signalReceived = False
            self.interrupt()

    def interrupt(self):
        raise InterruptTriggered

    def notInterruptible(self):
        return self.noInterruptDepth > 0

    def interruptible(self):
        return self.noInterruptDepth == 0

    def handler(self,sig,frame):
        if current_thread().__class__.__name__ != '_MainThread':
            return

        if self.interruptible():
            self.interrupt()

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
