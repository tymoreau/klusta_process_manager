import signal
import sys
import socket
import os
import time

# PRM file NOT WITH full path

# Import Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

#Listen on
IP="127.0.0.1"
HOST=PNet.QHostAddress(IP) 
PORT=8000

#Command to perform on list
PROGRAM="klusta"
ARGUMENTS=["--overwrite"]

SEPARATOR='---'*15

NAS_PATH="/home/david/fakeNAS"
SERVER_PATH="/home/david/dataServer"

#-------------------------------------------------------------------------------------------------------------------
#  Experiment
#-------------------------------------------------------------------------------------------------------------------
class Experiment(object):
	
	def __init__(self,name,pathNAS="",pathServer="",state="Object just created",isDone=False):
		
		#where to find the prmFile
		self.name=name
		self.pathNAS=pathNAS
		self.pathServer=pathServer
		
		#where is the processing
		self.state=state
		self.isDone=isDone



#-------------------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py  ---- other data on client
#-------------------------------------------------------------------------------------------------------------------
class Client(PCore.QObject):
	hasQuit=PCore.Signal()
	hasList=PCore.Signal(object)
	
	def __init__(self,socket):
		super(Client,self).__init__()
		
		#TCP socket
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		
		#Reading data
		self.blockSize=0
		self.dataStream=PCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(PCore.QDataStream.Qt_4_0)
		
		#Client infos
		self.ip=self.tcpSocket.localAddress().toString()
		self.state="None"
		self.connected="Yes"
		
		#Keep track of list and process
		self.prmFileList=[] #last list received (can be full path)
		self.experimentDict={} #experimentDict[name]=Experiment(object)
		self.impossibleList=[] #files which won't be process 
		self.waitingSince=0

	def update_socket(self,socket):
		self.tcpSocket=socket
		print "Client",self.ip,"- update socket"
		self.connected="Yes"


	def read(self):
		print "enter read"
		#read size of block
		if self.tcpSocket.bytesAvailable() < 2:
			print "client: bytes inf 2"
			return 0
		self.blockSize = self.dataStream.readUInt16()

		#check if all data is available
		if self.tcpSocket.bytesAvailable() < self.blockSize:
			print "client :bytes inf block size"
			return 0
		
		#read instruction
		instruction=self.dataStream.readQString()
		if instruction=="processList":
			self.instruction_process_list()
		else:
			print "received unknown instruction:",instruction


	def instruction_process_list(self):
		print "received: processList"
		#read list
		self.prmFileList+=self.dataStream.readQStringList()
		#check it
		for prmFile in self.prmFileList:
			self.check_file(prmFile)
		self.prmFileList=[]
		#send signal to ProcessView
		self.hasList.emit(self.ip)
		#client is waiting since this moment
		self.waitingSince=time.time()
		#send check result to client
		self.send_process_state()


	def check_file(self,prmFile):
		#get the name of the file (prmFile can be the full path)
		name=prmFile.split('/')[-1]
		
		#check if not already in list
		if name in self.experimentDict:
			self.impossibleList+=[name,"already in list"]
			return
		
		#check if indeed prm file
		if not name.endswith(".prm"):
			self.impossibleList+=[name,"not a .prm"]
			return

		#look for file in NAS
		found=False
		for path,dirs,files in os.walk(NAS_PATH):
			if name in files:
				prmFileNAS=os.path.join(path,name)
				self.experimentDict[name]=Experiment(name,pathNAS=prmFileNAS,state="found in NAS")
				found=True
				break
		if not found:
			self.impossibleList+=[name,"not find in NAS"]


	def send_process_state(self):
		listToSend=self.impossibleList
		for name,experiment in self.experimentDict.items():
			listToSend+=[name,experiment.state]
		block=self.send_protocol("updateDict",listToSend)
		self.tcpSocket.write(block)
		print "Send updateDict to client",self.ip
		
	def send_protocol(self,instruction,List=[]):
		block=PCore.QByteArray()
		out=PCore.QDataStream(block,PCore.QIODevice.WriteOnly)
		out.setVersion(PCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		out.writeString(instruction)
		if instruction=="updateDict" and len(List)!=0:
			out.writeQStringList(List)
		else:
			print "send_protocol : instruction not known"
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block

	def on_disconnect(self):
		try:
			self.tcpSocket.deleteLater()
		except RuntimeError:
			pass
		self.connected="No"
		self.hasQuit.emit()


#-------------------------------------------------------------------------------------------------------------------
# TcpServer: Launch a server
#-------------------------------------------------------------------------------------------------------------------
class ServerView(PGui.QGroupBox):
	def __init__(self):
		super(ServerView,self).__init__()
		self.setTitle("Server informations")
		
		#IP adress, PORT, HOST
		try:
			self.ip=[(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
		except:
			self.ip=IP
			
		self.port=PORT
		self.host=PNet.QHostAddress(self.ip) 

		self._layout()
		
	def _layout(self):
		self.label_IP=PGui.QLabel("IP: "+str(self.ip))
		self.label_port=PGui.QLabel("Port: "+str(self.port))
		
		self.button_listen=PGui.QPushButton("\n Accepts new clients \n")
		self.button_listen.setCheckable(True)
		
		labelLayout = PGui.QHBoxLayout()
		labelLayout.addWidget(self.label_IP)
		labelLayout.addSpacing(20)
		labelLayout.addWidget(self.label_port)
		
		vbox= PGui.QVBoxLayout()
		vbox.addLayout(labelLayout)
		vbox.addWidget(self.button_listen)
		vbox.setContentsMargins(10,10,10,10)
		self.setLayout(vbox)
		



#-------------------------------------------------------------------------------------------------------------------
# Process View-- Table: ClientIP, Connected, filename, state 
#--------------------------------------------------------------------------------------------------------
class ProcessView(PGui.QGroupBox):
	def __init__(self):
		super(ProcessView,self).__init__()
		self.setTitle("Process")
		
		#TCP Server
		self.server=PNet.QTcpServer(self)
		self.server.newConnection.connect(self.new_connection)
		
		#Keep track of client and progress
		self.clientDict={}  #clientDict[ip]=Client(object)
		
		#View: Table
		self.table=PGui.QTableWidget(0,4)
		self.table.setMinimumSize(200,100)
		self.table.setHorizontalHeaderLabels(["Client IP","Connected","File","State"])
		self.table.horizontalHeader().setResizeMode(PGui.QHeaderView.Stretch)
		self.table.setEditTriggers(PGui.QAbstractItemView.NoEditTriggers)
		
		#Process
		self.isRunning=False
		

	def update_table(self):
		self.table.clear()
		self.table.setRowCount(0)
		self.table.setHorizontalHeaderLabels(["Client IP","Connected","File","State"])
		row=0
		for ip in self.clientDict:
			self.table.insertRow(row)
			itemIP=PGui.QTableWidgetItem(ip)
			itemConnected=PGui.QTableWidgetItem(self.clientDict[ip].connected)
			self.table.setItem(row,0,itemIP)
			self.table.setItem(row,1,itemConnected)
			firstLine=True
			for name,experiment in self.clientDict[ip].experimentDict.items():
				if firstLine:
					firstLine=False
				else:
					row+=1
					self.table.insertRow(row)
				itemState=PGui.QTableWidgetItem(experiment.state)
				itemFile=PGui.QTableWidgetItem(name)
				self.table.setItem(row,2,itemFile)
				self.table.setItem(row,3,itemState)
			row+=1

	def new_connection(self):
		while self.server.hasPendingConnections():
			#accept connection
			newTcpSocket=self.server.nextPendingConnection()
			ip=newTcpSocket.localAddress().toString()
			
			#check if old/new client
			if ip in self.clientDict.keys():
				#client is already known
				self.clientDict[ip].update_socket(newTcpSocket)
				print "Client",ip,"is back"
				self.update_table()
				
			else:
				#new client
				self.clientDict[ip]=Client(newTcpSocket)
				print "New Client:",ip
				self.update_table()
				#connect client input to functions
				self.clientDict[ip].hasQuit.connect(self.update_table)
				self.clientDict[ip].hasList.connect(self.client_has_list)


	#client has new file to process
	def client_has_list(self,ip):
		self.update_table()
		for name,experiment in self.clientDict[ip].experimentDict.items():
			if experiment.state=="found in NAS":
				#copy the folder from the NAS to the server
				if self.copy_NAS_to_server(experiment.pathNAS):
					#copy was successful
					self.clientDict[ip].experimentDict[name].state="transfered to server"
				else:
					#could not copy
					self.clientDict[ip].experimentDict[name].state="could not transfer to server"
				self.update_table()
		
		if not self.isRunning:
			#prmFile=self.clientDict[ip].toProcessList[0]
			#self.run_one(prmFile)
			pass
		
		
	def copy_NAS_to_server(self,pathNAS):
		try:
			#extract folder path and folder name from prmFile path
			folderPath='/'.join(pathNAS.split('/')[:-1])
			folderName=pathNAS.split('/')[-2]
			
			#Move entire folder from NAS to server
			os.system('cp -r '+folderPath+' '+SERVER_PATH+'/')
			print('copy cp -r '+folderPath+' '+SERVER_PATH+'/')
			return True
		except Exception,e:
			print "could not copy, move on"
			print "exception:",e
			return False
		
		
	def run_one(self,prmFile):
		pass
		
		
		#print "Server: dealing with prmFile",prmFile
		#arguments=[prmFile] + ARGUMENTS
		
		#self.currentName=prmFile.split('/')[-1]
		
		#self.pathNAS=self.locate(self.currentName,NAS_PATH)
		
		#if self.pathNAS!="":
		
			#self.folderPathNAS='/'.join(self.pathNAS.split('/')[:-1])
		
			#self.folderName=self.pathNAS.split('/')[-2]
			
			#print "path given by client:",prmFile
			#print "corresponding file on NAS:", self.pathNAS
			
			##Move file from NAS to server
			#os.system('cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/')
			#print 'Just did: cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/'
			
			#self.process.setWorkingDirectory(SERVER_PATH+'/'+self.folderName)
			#print "Working directory",SERVER_PATH+'/'+self.folderName
			
			#self.process.start(self.program,arguments)
			#print "Processing file "+str(self.nbFileDone+1)+"/"+str(self.nbFile)+": "+str(self.currentName)
		#else:
			#print "could not find file in NAS"
			#self.go_to_next(1)



#-------------------------------------------------------------------------------------------------------------------
# Display console output
#--------------------------------------------------------------------------------------------------------
class ConsoleView(PGui.QGroupBox):
	def __init__(self):
		super(ConsoleView,self).__init__()
		self.setTitle("Console Output")



#-------------------------------------------------------------------------------------------------------------------
# Main Window: manages view
#-------------------------------------------------------------------------------------------------------------------
class MainWindow(PGui.QWidget):
	def __init__(self):
		super(MainWindow,self).__init__()

		#Views
		self.serverView=ServerView()
		self.processView=ProcessView()
		self.consoleView=ConsoleView()
		
		#connect view
		self.serverView.button_listen.toggled.connect(self.listen)
		
		#Layout
		self._layout()
		
	def _layout(self):
		
		WIDTH=800
		HEIGHT=600
		
		self.consoleView.setMinimumSize(WIDTH/2 -20,HEIGHT*0.75)
		self.processView.table.setMinimumSize(WIDTH/2 -20,HEIGHT -20)
		
		group=PGui.QWidget()
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.serverView)
		vbox.addWidget(self.consoleView)
		group.setLayout(vbox)
		
		splitter=PGui.QSplitter(PCore.Qt.Horizontal)
		splitter.setChildrenCollapsible(False)
		
		splitter.addWidget(self.processView.table)
		splitter.addWidget(group)
		
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(splitter)
		
		self.setLayout(vbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle("Server TCP + Process running")

	def listen(self,checked):
		if checked:
			host=self.serverView.host
			port=self.serverView.port
			if not self.processView.server.listen(address=host,port=port):
				PGui.QMessageBox.critical(self,"Server","Unable to start server. Maybe it's already running")
				self.close()
				return
			print "Server listen for new connections"
		else:
			self.serverView.server.close()
			print "Server close: not accepting new clients"


		#self.clientList=[]
		
		#self.program=PROGRAM
		#self.prmFileList=[]
		#self.nbFile=0
		#self.nbFileDone=0
		#self.errorsList=[]
		#self.successList=[]
		#self.currentName=""
		
		#self.stopNext=False
		#self.isRunning=False
		
		#self._labels()
		#self._buttons()
		#self._layout()


	#def new_client(self):
		#
	
	#def client_quit(self,ip):
		#print "client ",ip, "has quit"
		#self.connectedList.remove(ip)
		#self.label_connectedList.setText("Client(s) connected:\n"+"\n".join(self.connectedList))
		
	#def client_feed_list(self,ID):
		#self.prmFileList+=self.clientList[ID].prmFileList
		#print "full list: ",self.prmFileList
		#self.nbFile=len(self.prmFileList)
		
		#if not self.isRunning:
			#self.isRunning=True
			#self.process=PCore.QProcess()
			#self.nbFileDone=0
			#self.currentName=""
			
			##dealing with the klusta environment
			#env = PCore.QProcess.systemEnvironment()
			#itemToReplace=[item for item in env if item.startswith('PATH=')]
			#for item in itemToReplace:
				#newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
				#env.remove(item)
				#env.append(newitem)
			#self.process.setEnvironment(env)
			
			#self.process.finished.connect(self.go_to_next)
			#self.run_one(self.prmFileList[0])


	#def run_one(self,prmFile):
		#print "ProcessManager Server: dealing with prmFile",prmFile
		#arguments=[prmFile] + ARGUMENTS
		
		#self.currentName=prmFile.split('/')[-1]
		
		#self.pathNAS=self.locate(self.currentName,NAS_PATH)
		
		#if self.pathNAS!="":
		
			#self.folderPathNAS='/'.join(self.pathNAS.split('/')[:-1])
		
			#self.folderName=self.pathNAS.split('/')[-2]
			
			#print "path given by client:",prmFile
			#print "corresponding file on NAS:", self.pathNAS
			
			##Move file from NAS to server
			#os.system('cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/')
			#print 'Just did: cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/'
			
			#self.process.setWorkingDirectory(SERVER_PATH+'/'+self.folderName)
			#print "Working directory",SERVER_PATH+'/'+self.folderName
			
			#self.process.start(self.program,arguments)
			#print "Processing file "+str(self.nbFileDone+1)+"/"+str(self.nbFile)+": "+str(self.currentName)
		#else:
			#print "could not find file in NAS"
			#self.go_to_next(1)
		
		
	#def locate(self,filename,root):
		#
		#return ""

		
	#def go_to_next(self,exitcode):
		#if exitcode!=0:
			#print "ProcessManager Server: exitcode",exitcode
			#self.errorsList.append(self.currentName)
			#print("Klusta crashed with file(s): \n"+'\n'.join(self.errorsList))
		#else:
			#self.successList.append(self.currentName)
			#print("Klusta ran with file(s): \n"+'\n'.join(self.successList))
			#for files in os.listdir(SERVER_PATH+'/'+self.folderName):
				#if not files.endswith(".dat") and not files.endswith('.raw.kwd'):
					#os.system('cp '+SERVER_PATH+'/'+files+' '+self.folderPathNAS+'/'+files)
					#print 'Just did cp '+SERVER_PATH+'/'+files+' '+self.folderPathNAS+'/'+files

		#self.nbFileDone+=1
		
		#if self.nbFile==self.nbFileDone:
			#print "ProcessManager Server: every file was processed"
			#print("List done")
			#self.prmFileList=[]
			#self.nbFile=0
			#self.nbFileDone=0
			#self.currentName=""
			#self.process.close()
			#self.isRunning=False
		##elif self.stopNext:
			##print "ProcessManager: stop next"
			##self.label_general.setText("<b>List done partially:</b> "+str(self.nbFileDone)+"/"+str(self.nbFile))
			##self.button_clear.setEnabled(True)
			##self.prmFileList=[]
			##self.nbFile=0
			##self.nbFileDone=0
			##self.currentName=""
			##self.process.close()
			##self.button_stopNext.setEnabled(False)
		#else:
			#print "ProcessManager Server: move to next file"
			#self.run_one(self.prmFileList[self.nbFileDone])
		

if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()
	
	win.processView.clientDict["fakeIP"]=Client(PNet.QTcpSocket())
	win.processView.update_table()
	
	win.show()

	sys.exit(app.exec_())

