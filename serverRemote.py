import Pyro4

Pyro4.config.SERVERTYPE = "multiplex" #process all remote method calls sequentially, no thread

HOST="linux-workstation"  #if DNS setup with assign hostname to loopbackIP, else use IP
PORT=8000

class JobManager(object):
	def __init__(self):
		print "Job manager initialized"
		
	def method1(self):
		print "this is method 1"
		return "the return value of method 1"



if __name__=='__main__':
	
	#Create server
	jobManager=JobManager()
	daemon=Pyro4.Daemon(host=HOST,port=PORT)
	
	SERVERTYPE="multiplex"
	
	#Register one object of the class JobManager
	uri=daemon.register(jobManager, objectId="JobManager")
	print "Register with URI:",uri
	
	#wait for calls
	daemon.requestLoop()  
	#optionnal : loop condition with boolean (to stop loop, then daemon.close() to close everything)
	#OR close everything with daemon.shutdown()
	