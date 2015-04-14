import sys
import subprocess
import time
import threading

#derived from http://stefaanlippens.net/python-asynchronous-subprocess-pipe-reading
 
class AsynchronousFileReader(threading.Thread):
    def __init__(self, fd,table):
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self._fd = fd
        self._table=table
 
    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        for line in iter(self._fd.readline, ''):
            self._table.append(line.strip())
 
    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive()

class CommandLineProcess(object):
	
	def __init__(self,command):
		self.stdOutput=[]
		self.stdErrors=[]
		self.start=False
		self.command=command

	def start_process(self):
		# Launch the command as subprocess.
		self.process = subprocess.Popen(self.command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	
		# Launch the asynchronous readers of the process' stdout and stderr.
		self.stdout_reader = AsynchronousFileReader(self.process.stdout,self.stdOutput)
		self.stdout_reader.start()
		self.stderr_reader = AsynchronousFileReader(self.process.stderr,self.stdErrors)
		self.stderr_reader.start()
		
		self.start=True

	def close_process(self):
		# join the threads we've started.
		# wait til the process is over
		self.stdout_reader.join()
		self.stderr_reader.join()

		# Close subprocess' file descriptors.
		self.process.stdout.close()
		self.process.stderr.close()
		
		self.start=False

	def read_std(self,stdType):
		if stdType=='output':
			return self.stdOutput
		elif stdType=='errors':
			return self.stdErrors
		else:
			return 0
		
	def read_last_std(self,stdType):
		if stdType=='output':
			if self.stdOutput:
				return self.stdOutput[-1]
			else:
				return ""
		elif stdType=='errors':
			if self.stdErrors:
				return self.stdErrors[-1]
			else:
				return ""
		else:
			return 0



#Example with SpikeDetekt only
if __name__ == '__main__':
	
	prmFile='Rat034_shank0.prm'
	
	process=CommandLineProcess(['klusta',prmFile,'--overwrite','--detect-only']) 
	process.start_process() 
	print "start process"

	end=False
	lastline=""
	while not end:
		line=process.read_last_std("output")
		if line==lastline:
			time.sleep(1)
		else:
			print "receive on standard output:",line
			lastline=line
		if "100% complete, 0s elapsed, 0s remaining" in line:
			end=True

	process.close_process()
	print "close the process"


