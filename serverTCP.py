import signal
import sys
import socket

#Remove Qvariant and all from PyQt (for python2 compatibility)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

#QT
#import QT
from PyQt4 import QtCore,QtGui,QtNetwork

from experimentModel import ExperimentModelBase

#parameters
from parameter import SERVER_PATH, NAS_PATH, PROGRAM, PORT, SEPARATOR
from parameter import IP_server as IP

#-------------------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py
#-------------------------------------------------------------------------------------------------------------------
class Client(QtCore.QObject):
	hasNewExperiment=QtCore.pyqtSignal()
	
	def __init__(self,socket):
		super(Client,self).__init__()
		
		#TCP socket
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		
		#server folder
		self.server=QtCore.QDir(SERVER_PATH)
		
		#Reading data
		self.blockSize=0
		self.dataStream=QtCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(QtCore.QDataStream.Qt_4_0)
		
		#Client infos
		self.ip=self.tcpSocket.peerAddress().toString()
		self.connected=True
		
		#model
		self.model=ExperimentModelBase(NAS_PATH)
		self.stateList=[]
		self.expDone=[]
		
		#table View
		self.tableView=QtGui.QTableView()
		self.tableView.setModel(self.model)
		self.tableView.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
		
		#frame
		self.frame=QtGui.QGroupBox()
		self.frame.setTitle("Client ip: %s connected:Yes" %self.ip)
		box=QtGui.QVBoxLayout()
		box.addWidget(self.tableView)
		self.frame.setLayout(box)
		
	#client reconnected to server
	def update_socket(self,socket):
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		
		#Reading data
		self.blockSize=0
		self.dataStream=QtCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(QtCore.QDataStream.Qt_4_0)
		
		self.frame.setTitle("Client ip: %s connected:Yes" %self.ip)
		self.connected=True
		
		#catch up
		self.update_state_list()
		
	#client disconnected
	def on_disconnect(self):
		self.frame.setTitle("Client ip: %s connected:No" %self.ip)
		try:
			self.tcpSocket.deleteLater()
		except RuntimeError:
			pass
		self.connected=False

	#-------------------------------------------------------------------------------------
	# Receive instruction
	#-------------------------------------------------------------------------------------
	def read(self):
		while self.tcpSocket.bytesAvailable():
			#read size of block
			if self.tcpSocket.bytesAvailable() < 2:
				print("client %s: bytes inf 2"%self.ip)
				return False
			self.blockSize = self.dataStream.readUInt16()
			#check if all data is available
			if self.tcpSocket.bytesAvailable() < self.blockSize:
				print("client %s: bytes inf block size"%self.ip)
				return False
			#read instruction
			instr=self.dataStream.readString()
			instruction=str(instr,encoding='ascii')
			if instruction=="processList":
				self.instruction_process_list()
			else:
				print("client %s sends unknown instruction:%s"%(self.ip,instruction))

	#Received a list of folder name
	def instruction_process_list(self):
		#read list
		NASpathList=self.dataStream.readQStringList()
		print("receive",NASpathList)
		#add experiment if they are ok
		for NASpath in NASpathList:
			#extract name and create folder
			name=NASpath.split('/')[-1]
			self.server.mkdir(name)   #will not erase if already there
			path=self.server.filePath(name)
			#add exp
			self.model.add_experiment(folderPath=path,NASFolderPath=NASpath)
		#send change to client, signal server
		self.update_state_list()
		self.hasNewExperiment.emit()


	#-------------------------------------------------------------------------------------
	# Send state list
	#-------------------------------------------------------------------------------------
	def update_state_list(self):
		for experiment in self.model.experimentList:
			self.stateList+=[experiment.name,experiment.state]
			if experiment.finish:
				if experiment.toSync or experiment.isSyncing:
					continue
				elif experiment.isDone:
					self.expDone+=[experiment.name,"True"]
				else:
					self.expDone+=[experiment.name,"False"]
		if self.connected and len(self.stateList)>0:
			self.send_update_state()
			if len(self.expDone)>0:
				self.send_exp_done()
			
	def send_exp_done(self):
		print("exp done:",self.expDone)
		block=self.send_protocol("expDone",List=self.expDone)
		if block!=0:
			self.tcpSocket.write(block)
			self.expDone=[]
			#self.model.clear()  problem=change index

	def send_update_state(self):
		print("send",self.stateList)
		block=self.send_protocol("updateState",List=self.stateList)
		if block!=0:
			self.tcpSocket.write(block)
			self.stateList=[]

	def send_protocol(self,instruction,List=[]):
		block=QtCore.QByteArray()
		out=QtCore.QDataStream(block,QtCore.QIODevice.WriteOnly)
		out.setVersion(QtCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		instr=bytes(instruction,encoding="ascii")
		out.writeString(instr)
		if instruction=="updateState" or instruction=="expDone":
			out.writeQStringList(List)
		else:
			print("send_protocol : instruction not known")
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block


#-------------------------------------------------------------------------------------------------------------------
# TcpServer: Launch a server
#-------------------------------------------------------------------------------------------------------------------
class ServerView(QtGui.QGroupBox):
	def __init__(self):
		super(ServerView,self).__init__()
		self.setTitle("Server informations")
		
		#IP adress, PORT, HOST
		try:
			self.ip=[(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
		except:
			self.ip=IP
			
		self.port=PORT
		self.host=QtNetwork.QHostAddress(self.ip) 

		self._layout()
		
	def _layout(self):
		self.label_IP=QtGui.QLabel("IP: "+str(self.ip))
		self.label_port=QtGui.QLabel("Port: "+str(self.port))
		
		self.button_listen=QtGui.QPushButton("\n Accepts new clients \n")
		self.button_listen.setCheckable(True)
		
		labelLayout = QtGui.QHBoxLayout()
		labelLayout.addWidget(self.label_IP)
		labelLayout.addSpacing(20)
		labelLayout.addWidget(self.label_port)
		
		vbox= QtGui.QVBoxLayout()
		vbox.addLayout(labelLayout)
		vbox.addWidget(self.button_listen)
		vbox.setContentsMargins(10,10,10,10)
		self.setLayout(vbox)



#-------------------------------------------------------------------------------------------------------------------
# console output
#--------------------------------------------------------------------------------------------------------
class ConsoleView(QtGui.QGroupBox):
	def __init__(self):
		super(ConsoleView,self).__init__()
		
		#output
		self.output=QtGui.QTextEdit()
		self.output.setReadOnly(True)

		#buttons
		self.button_clear=QtGui.QPushButton("Clear output")
		self.button_clear.clicked.connect(self.output.clear)
		
		#Layout
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(self.output)
		vbox.addWidget(self.button_clear)
		self.setLayout(vbox)
		
	def display(self,lines):
		self.output.append(lines)
		
	def separator(self,experiment):
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b> Experiment: '+str(experiment.name)+'</b> \n'
		sep2='Working directory: '+str(experiment.folder.absolutePath())+' \n'
		sep3='Do: %s %s \n'%(PROGRAM," ".join(experiment.arguments))
		sep4='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.output.append(sep)
		self.output.append(sep1)
		self.output.append(sep2)
		self.output.append(sep3)
		self.output.append(sep4)

#-------------------------------------------------------------------------------------------------------------------
# Process View-- Table: ClientIP, Connected, filename, state 
#--------------------------------------------------------------------------------------------------------
class ProcessView(QtGui.QWidget):
	def __init__(self):
		super(ProcessView,self).__init__()
		
		#TCP Server
		self.server=QtNetwork.QTcpServer(self)
		self.server.newConnection.connect(self.new_connection)
		
		#Keep track of client and progress
		self.clientDict={}  #clientDict[ip]=Client(object)
		
		#Process
		self.process=QtCore.QProcess()
		self.process.finished.connect(self.try_process)
		self.process.finished.connect(self.try_sync)
		self.wasKill=False
		self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

		self.currentClient=None
		
		#Transfer
		self.processSync=QtCore.QProcess()
		self.processSync.finished.connect(self.try_sync)
		self.processSync.finished.connect(self.try_process)
		self.currentClientSync=None
		
		#dealing with the klusta environment
		env = QtCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		env.append("CONDA_DEFAULT_ENV=klusta")
		self.process.setEnvironment(env)
		
		#buttons and label
		self.button_kill=QtGui.QPushButton("Kill current")
		self.button_kill.clicked.connect(self.kill_current)
		self.button_clear=QtGui.QPushButton("Clear")
		self.button_clear.clicked.connect(self.clear)
		self.label_path=QtGui.QLabel(SERVER_PATH)
		
		#Client tables
		self.vboxClient=QtGui.QVBoxLayout()
		self.vboxClient.setAlignment(QtCore.Qt.AlignTop)
		self.vboxClient.addWidget(self.label_path)
		self.vboxClient.addWidget(self.button_kill)
		self.vboxClient.addWidget(self.button_clear)
		self.setLayout(self.vboxClient)
		
		#console
		self.console=ConsoleView()

	def new_connection(self):
		while self.server.hasPendingConnections():
			#accept connection
			newTcpSocket=self.server.nextPendingConnection()
			ip=newTcpSocket.peerAddress().toString()
			
			#check if old/new client
			if ip in self.clientDict.keys():
				#client is already known
				self.clientDict[ip].update_socket(newTcpSocket)
				print("Client",ip,"is back")
				
			else:
				#new client
				self.clientDict[ip]=Client(newTcpSocket)
				print("New Client:",ip)
				self.vboxClient.addWidget(self.clientDict[ip].frame)
				self.clientDict[ip].hasNewExperiment.connect(self.try_process)
				self.clientDict[ip].hasNewExperiment.connect(self.try_sync)
				

	def clear(self):
		for ip,client in self.clientDict.items():
			client.model.clear()
			
	#(try to) close everything properly
	def close(self):
		if not self.process.waitForFinished(1):
			self.process.kill()
			self.wasKill=True
			self.process.waitForFinished(1)
		if not self.processSync.waitForFinished(1):
			self.processSync.kill()
			self.processSync.waitForFinished(1)
		for ip,client in self.clientDict.items():
			if client.tcpSocket.isValid():
				client.tcpSocket.flush()
				client.tcpSocket.disconnectFromHost()
		self.server.close()

	#--------------------------------------------------------------------------------------------
	#Process
	#-------------------------------------------------------------------------------------------
	def kill_current(self):
		if self.currentClient==None:
			return
		if self.clientDict[self.currentClient].model.kill_current():
			self.process.kill()
			self.wasKill=True

	def try_process(self,exitcode=0):
		#if there is not already a transfer running
		if self.process.state()==QtCore.QProcess.Running:
			return
		else:
			if self.wasKill:
				self.wasKill=False
				exitcode=42
			if self.currentClient!=None:
				self.clientDict[self.currentClient].model.process_done(exitcode)
				self.clientDict[self.currentClient].update_state_list()
			#find new client if possible
			if self.search_client_toProcess():
				self.clientDict[self.currentClient].model.process_one_experiment(self.process)
				self.console.separator(self.clientDict[self.currentClient].model.experimentList[self.clientDict[self.currentClient].model.indexProcess])
				self.clientDict[self.currentClient].update_state_list()
				return

	def search_client_toProcess(self):
		same=False
		for ip,client in self.clientDict.items():
			if client.model.has_exp_to_process():
				if ip==self.currentClient:
					same=True
				else:
					self.currentClient=ip
					return True
		if same:
			return True
		else:
			self.currentClient=None
			return False

	#--------------------------------------------------------------------------------------------
	#Transfer
	#-------------------------------------------------------------------------------------------

	def try_sync(self,exitcode=None):
		#if there is not already a transfer running
		if self.processSync.state()==QtCore.QProcess.Running:
			return
		else:
			if self.currentClientSync!=None:
				self.clientDict[self.currentClientSync].model.sync_done(exitcode)
				self.clientDict[self.currentClientSync].update_state_list()
			if self.search_client_toSync():
				if self.clientDict[self.currentClientSync].model.has_exp_to_sync():
					self.clientDict[self.currentClientSync].model.sync_one_experiment(self.processSync)
					self.clientDict[self.currentClientSync].update_state_list()
					return
			
			
	def search_client_toSync(self):
		same=False
		for ip,client in self.clientDict.items():
			if client.model.has_exp_to_sync():
				if ip==self.currentClientSync:
					same=True
				else:
					self.currentClientSync=ip
					return True
		if same:
			return True
		else:
			self.currentClientSync=None
			return False

#-------------------------------------------------------------------------------------------------------------------
# Main Window: manages view
#-------------------------------------------------------------------------------------------------------------------
class MainWindow(QtGui.QWidget):
	def __init__(self):
		super(MainWindow,self).__init__()

		#Views
		self.serverView=ServerView()
		self.processView=ProcessView()
		
		#connect view
		self.serverView.button_listen.toggled.connect(self.listen)
		self.processView.process.readyRead.connect(self.display_output)
		
		#Layout
		self._layout()
		
	def _layout(self):
		WIDTH=800
		HEIGHT=600
		
		group=QtGui.QWidget()
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(self.serverView)
		vbox.addWidget(self.processView.console)
		group.setLayout(vbox)
		
		group.setMinimumSize(WIDTH/2 -20,HEIGHT-20)
		self.processView.setMinimumSize(WIDTH/2 -20,HEIGHT-20)
		
		splitter=QtGui.QSplitter(QtCore.Qt.Horizontal)
		splitter.setChildrenCollapsible(False)
		
		splitter.addWidget(self.processView)
		splitter.addWidget(group)
		
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(splitter)
		
		self.setLayout(vbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle("Server TCP + Process running")
		
	def display_output(self):
		byteArray=self.processView.process.readAll()
		string="".join(byteArray)
		self.console.display(string)

	def listen(self,checked):
		if checked:
			host=self.serverView.host
			port=self.serverView.port
			if not self.processView.server.listen(address=host,port=port):
				QtGui.QMessageBox.critical(self,"Server","Unable to start server. Maybe it's already running")
				self.close()
				return
		else:
			self.processView.server.close()

			
	def closeEvent(self,event):
		#check if is running
		if self.processView.process.state()==QtCore.QProcess.Running or self.processView.processSync.state()==QtCore.QProcess.Running :
			msgBox = QtGui.QMessageBox()
			msgBox.setText("Closing the app")
			msgBox.setInformativeText("A process or transfer is running, are you sure you want to quit ? The process or transfer will be killed")
			msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel)
			msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
			answer = msgBox.exec_()
			if answer==QtGui.QMessageBox.Cancel:
				event.ignore()
				return
		self.processView.close()
		self.close()
		event.accept()
			

if __name__=='__main__':
	QtGui.QApplication.setStyle("cleanlooks")
	app = QtGui.QApplication(sys.argv)
	
	nas=QtCore.QDir(NAS_PATH)
	server=QtCore.QDir(SERVER_PATH)
	if not nas.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("NAS_PATH do not refers to a folder: "+str(NAS_PATH))
		msgBox.exec_()
	elif not server.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("SERVER_PATH do not refers to a folder: "+str(SERVER_PATH))
		msgBox.exec_()
	else:
		#to be able to close wth ctrl+c
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		
		win=MainWindow()
		
		win.show()

		sys.exit(app.exec_())
