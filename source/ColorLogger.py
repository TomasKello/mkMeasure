class Colors:
    INFO    = '\033[39m'
    WARNING = '\033[93;1m'
    ERROR   = '\033[31;1m'
    FATAL   = '\033[31;1m'
    HAZARD  = '\033[41;1m'
    INPUT   = '\033[47;1m'
    ENDC    = '\033[0m'

class ColorLogger(Colors):
    def __init__(self,source):
        self.source = source
    
    def log(self,log_type="i",text=""):
        if "i" in log_type:
            print(self.INFO,self.source,"[INFO]     ",text,self.ENDC)
        elif "n" in log_type:
            print(self.INFO,"                  ",text,self.ENDC)
        elif "w" in log_type:
            print(self.WARNING,self.source,"[WARNING]  ",text,self.ENDC)
        elif "h" in log_type:
            print(self.HAZARD,self.source,"[HAZARD]   ",text,self.ENDC)
        elif "e" in log_type:
            print(self.ERROR,self.source,"[ERROR]    ",text,self.ENDC)
        elif "f" in log_type:
            print(self.FATAL,self.source,"[FATAL]    ",text,self.ENDC)
        elif "t" in log_type and "tt" not in log_type:
            print(self.INPUT,"<<     ",text,self.ENDC)
        elif "tt" in log_type:
            return input(self.INPUT+text+"  >>"+self.ENDC)
