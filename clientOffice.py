import Pyro4

Pyro4.config.COMMTIMEOUT = 10 #wait 10 sec maximum for the call to return

URI='PYRO:JobManager@linux-workstation:8000'

# with : when  you're done or an error occur, the connection is released (proxy=disconnected)
# can re connect anytime
with Pyro4.Proxy(URI) as jobManagerProxy:
	print jobManagerProxy.method1()
	
print jobManagerProxy.method1()