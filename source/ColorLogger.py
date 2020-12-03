import os,sys
import logging

class Colors:
    INFO    = '\033[39m'
    WARNING = '\033[93;1m'
    ERROR   = '\033[31;1m'
    FATAL   = '\033[31;1m'
    HAZARD  = '\033[41;1m'
    INPUT   = '\033[47;1m'
    ENDC    = '\033[0m'

class StreamToLogger(object):
   #########################################################################
   #Fake file-like stream object that redirects writes to a logger instance.
   #########################################################################
 
   def __init__(self, logger, log_level=logging.INFO):
      self.logger = logger
      self.log_level = log_level
      self.linebuf = ''

   def write(self, buf):
      for line in buf.rstrip().splitlines():
         self.logger.log(self.log_level, line.rstrip())

class ColorLogger(Colors):
    ############################################################
    #Print stdout and stderr to terminal and log file in color
    ############################################################
 
    def __init__(self,source,logname):
        self.source = source
        self.logname = logname
        exe = sys.executable
        exeDir = exe[:exe.rfind("/")]
        self.logDir = exeDir[:exeDir.rfind("/")]+"/logs" 
        if not os.path.isdir(self.logDir):
            os.mkdir(self.logDir) 

        #to fully redirect stderr
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(message)s',
            filename=self.logDir+"/"+self.logname,
            filemode='a'
        )
        stderr_logger = logging.getLogger('STDERR')
        sl = StreamToLogger(stderr_logger, logging.ERROR)
        sys.stderr = sl

    def log(self,log_type="i",text=""):
        try:
            #to redirect stdout but preserving original stdout
            self.filelog = open(self.logDir+"/"+self.logname, "a")

            if "i" in log_type:
                print(self.INFO,self.source,"[INFO]     ",text,self.ENDC)
                print(self.source,"[INFO]     ",text,file=self.filelog)
            elif "n" in log_type:
                print(self.INFO,"                  ",text,self.ENDC)
                print("                  ",text,file=self.filelog)
            elif "w" in log_type:
                print(self.WARNING,self.source,"[WARNING]  ",text,self.ENDC)
                print(self.source,"[WARNING]  ",text,file=self.filelog)
            elif "h" in log_type:
                print(self.HAZARD,self.source,"[HAZARD]   ",text,self.ENDC)
                print(self.source,"[HAZARD]   ",text,file=self.filelog)
            elif "e" in log_type:
                print(self.ERROR,self.source,"[ERROR]    ",text,self.ENDC)
                print(self.source,"[ERROR]    ",text,file=self.filelog)
            elif "f" in log_type:
                print(self.FATAL,self.source,"[FATAL]    ",text,self.ENDC)
                print(self.source,"[FATAL]    ",text,file=self.filelog)
            elif "t" in log_type and "tt" not in log_type:
                print(self.INPUT,"<<     ",text,self.ENDC)
                print("<<     ",text,file=self.filelog)
            elif "tt" in log_type:
                _input = input(self.INPUT+text+"  >>"+self.ENDC)
                print(text+"  >>",file=self.filelog)
                print(str(_input),file=self.filelog)          
                return _input

            #apply changes to logfile
            self.filelog.close()

        except KeyboardInterrupt:
            self.log(log_type,text)
