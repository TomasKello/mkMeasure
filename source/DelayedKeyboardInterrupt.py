import signal
import ColorLogger

def log(log_type="i",text=""):
    clogger = ColorLogger.ColorLogger("KeyboardWarden:  ")
    return clogger.log(log_type,text)

class DelayedKeyboardInterrupt(object):
    ######################################
    #Class handling Keyboard interruption
    #during critical code.
    ######################################
    def __init__(self,force=True):
        self.force = force

    def __enter__(self):
        self.signal_received = False
        self.old_handler = signal.signal(signal.SIGINT, self.handler)

    def handler(self, sig, frame):
        self.signal_received = (sig, frame)
        log("e","Keyboard interruption not allowed during critical code but will be raised ASAP.")

    def __exit__(self, type, value, traceback):
        signal.signal(signal.SIGINT, self.old_handler)
        if self.signal_received and self.force:
            self.old_handler(*self.signal_received)
        elif self.signal_received:
            log("w","Keyboard interruption not needed on system exit. Terminating peacefully.")
