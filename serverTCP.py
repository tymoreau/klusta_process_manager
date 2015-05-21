NAS_PATH="./test/fakeNAS"
SERVER_PATH="./test/dataServer"
#-------------------------------------------------------------------------------------------------------------------

import signal
import sys
import socket
import os
import time

# Import Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

#from experiment import ExperimentOnServer
from experimentModel import ExperimentModelServer

#Listen on
IP="127.0.0.1"
PORT=8000

SEPARATOR='---'*15

PROGRAM="klusta"

#-------------------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py  ---- + other data on client
#-------------------------------------------------------------------------------------------------------------------
class Client(PCore.QObject):
	hasNewExperiment=PCore.Signal()
	
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
		self.connected=True
		
		#model
		self.model=ExperimentModelServer(NAS_PATH,SERVER_PATH)
		self.stateList=[]
		
		#table View
		self.tableView=PGui.QTableView()
		self.tableView.setModel(self.model)
		self.tableView.horizontalHeader().setResizeMode(PGui.QHeaderView.Stretch)
		
		#frame
		self.frame=PGui.QGroupBox()
		self.frame.setTitle("Client ip: %s connected:Yes" %self.ip)
		box=PGui.QVBoxLayout()
		box.addWidget(self.tableView)
		self.frame.setLayout(box)
		
	#client reconnected to server
	def update_socket(self,socket):
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		
		#Reading data
		self.blockSize=0
		self.dataStream=PCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(PCore.QDataStream.Qt_4_0)
		
		self.frame.setTitle("Client ip: %s connected:Yes" %self.ip)
		self.connected=True
		
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
			instruction=self.dataStream.readQString()
			if instruction=="processList":
				self.instruction_process_list()
			else:
				print("client %s sends unknown instruction:%s"%(self.ip,instruction))

	#Received a list of folder name
	def instruction_process_list(self):
		#read list
		nameList=self.dataStream.readQStringList()
		#add experiment if they are ok
		for nameLocal in nameList:
			self.model.add_experiment(nameLocal)

		#send change to client, signal server
		self.update_state_list()
		self.hasNewExperiment.emit()

	#-------------------------------------------------------------------------------------
	# Send state list
	#-------------------------------------------------------------------------------------
	def update_state_list(self):
		expDone=[]
		for experiment in self.model.experimentList:
			self.stateList+=[experiment.nameLocal,experiment.state]
			if experiment.serverFinished:
				if experiment.isBackup:
					expDone+=[experiment.nameLocal,"True"]
				else:
					expDone+=[experiment.nameLocal,"False"]
		self.send_update_state()
		if len(expDone)>0:
			self.send_exp_done(expDone)
			
	def send_exp_done(self,expDone):
		block=self.send_protocol("expDone",List=expDone)
		if block!=0:
			self.tcpSocket.write(block)

	def send_update_state(self):
		block=self.send_protocol("updateState",List=self.stateList)
		if block!=0:
			self.tcpSocket.write(block)
			self.stateList=[]

	def send_protocol(self,instruction,List=[]):
		block=PCore.QByteArray()
		out=PCore.QDataStream(block,PCore.QIODevice.WriteOnly)
		out.setVersion(PCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		out.writeString(instruction)
		if instruction=="updateState" or instruction=="expDone":
			out.writeQStringList(List)
		else:
			print "send_protocol : instruction not known"
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block


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
# console output
#--------------------------------------------------------------------------------------------------------
class ConsoleView(PGui.QGroupBox):
	def __init__(self):
		super(ConsoleView,self).__init__()
		
		#output
		self.output=PGui.QTextEdit()
		self.output.setReadOnly(True)

		#buttons
		self.button_clear=PGui.QPushButton("Clear output")
		self.button_clear.clicked.connect(self.output.clear)
		
		#Layout
		vbox=PGui.QVBoxLayout()
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

#-----------------------------------------------------------------------------
# Thread to transfer NAS -- Server
#------------------------------------------------------------------------------
class Worker(PCore.QObject):
	finished=PCore.Signal()
	workRequested=PCore.Signal()
	
	def __init__(self):
		super(Worker,self).__init__()
		self.isWorking=False
		
	def requestTransfer(self,client):
		if not self.isWorking:
			self.client=client
			self.workRequested.emit()
	
	def doWork(self):
		if not self.isWorking:
			self.isWorking=True
			self.client.model.beginResetModel()
			self.client.model.currentExperimentTransfer.transfer()
			self.isWorking=False
			self.finished.emit()
			self.client.model.endResetModel()
			self.client.update_state_list()
			self.client.tcpSocket.flush()


#-------------------------------------------------------------------------------------------------------------------
# Process View-- Table: ClientIP, Connected, filename, state 
#--------------------------------------------------------------------------------------------------------
class ProcessView(PGui.QWidget):
	def __init__(self):
		super(ProcessView,self).__init__()
		
		#TCP Server
		self.server=PNet.QTcpServer(self)
		self.server.newConnection.connect(self.new_connection)
		
		#Keep track of client and progress
		self.clientDict={}  #clientDict[ip]=Client(object)
		
		#Process
		self.process=PCore.QProcess()
		self.process.finished.connect(self.go_to_next)
		self.process.finished.connect(self.find_file_to_transfer)
		self.process.setProcessChannelMode(PCore.QProcess.MergedChannels)

		self.isRunning=False
		self.currentClient=None
		
		#Transfer
		self.thread=PCore.QThread()
		self.worker=Worker()
		self.worker.moveToThread(self.thread)
		self.worker.workRequested.connect(self.thread.start)
		self.thread.started.connect(self.worker.doWork)
		self.worker.finished.connect(self.thread.quit)
		self.thread.finished.connect(self.find_file_to_transfer)
		self.thread.finished.connect(self.try_launch_process)
		
		
		#dealing with the klusta environment
		env = PCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		self.process.setEnvironment(env)
		
		#buttons and label
		self.button_kill=PGui.QPushButton("Kill")
		self.button_kill.clicked.connect(self.kill_current)
		self.label_path=PGui.QLabel(SERVER_PATH)
		
		#Client tables
		self.vboxClient=PGui.QVBoxLayout()
		self.vboxClient.setAlignment(PCore.Qt.AlignTop)
		self.vboxClient.addWidget(self.label_path)
		self.vboxClient.addWidget(self.button_kill)
		self.setLayout(self.vboxClient)
		
		#console
		self.console=ConsoleView()

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
			else:
				#new client
				self.clientDict[ip]=Client(newTcpSocket)
				print "New Client:",ip
				self.vboxClient.addWidget(self.clientDict[ip].frame)
				self.clientDict[ip].hasNewExperiment.connect(self.try_launch_process)
				self.clientDict[ip].hasNewExperiment.connect(self.find_file_to_transfer)
				

	#--------------------------------------------------------------------------------------------
	#Process
	
	def kill_current(self):
		if self.isRunning:
			self.clientDict[self.currentClient].model.currentExperiment.crashed=True
			self.process.kill()

	def try_launch_process(self):
		if not self.isRunning:
			if self.find_file_to_process():
				self.isRunning=True
				self.console.separator(self.clientDict[self.currentClient].model.currentExperiment)
				self.clientDict[self.currentClient].model.currentExperiment.run_klusta(self.process)
				self.clientDict[self.currentClient].update_state_list()

	#loop trough every client and check if they have an experiment to process
	#if possible, choose a different client than the current one
	def find_file_to_process(self):
		found=False
		for ip,client in self.clientDict.items():
			if client.model.get_first_to_process():
				if ip==self.currentClient:
					found=True
				else:
					self.currentClient=ip
					return True
		if found:
			return True
		else:
			self.currentClient=None
			return False

	def go_to_next(self,exitcode):
		self.clientDict[self.currentClient].model.currentExperiment_isDone(exitcode)
		self.clientDict[self.currentClient].update_state_list()
		if self.find_file_to_process():
			self.console.separator(self.clientDict[self.currentClient].model.currentExperiment)
			self.clientDict[self.currentClient].model.currentExperiment.run_klusta(self.process)
			self.clientDict[self.currentClient].update_state_list()
		else:
			self.isRunning=False
			self.process.close()
		

	#--------------------------------------------------------------------------------------------
	#Transfer a file if possible 
	def find_file_to_transfer(self):
		#if there is not already a transfer running
		if not self.thread.isRunning():
			for ip,client in self.clientDict.items():
				#test if the client have a file to transfer
				if client.model.get_first_to_transfer():
					client.update_state_list()
					#do the transfer in another thread
					self.worker.requestTransfer(client)
					return


	#(try to) close everything properly
	def close(self):
		if not self.process.waitForFinished(1):
			self.process.kill()
			self.process.waitForFinished(1)
		self.thread.exit(1)
		for ip,client in self.clientDict.items():
			if client.tcpSocket.isValid():
				client.tcpSocket.flush()
				client.tcpSocket.disconnectFromHost()
		self.server.close()
		



#-------------------------------------------------------------------------------------------------------------------
# Main Window: manages view
#-------------------------------------------------------------------------------------------------------------------
class MainWindow(PGui.QWidget):
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
		
		group=PGui.QWidget()
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.serverView)
		vbox.addWidget(self.processView.console)
		group.setLayout(vbox)
		
		group.setMinimumSize(WIDTH/2 -20,HEIGHT-20)
		self.processView.setMinimumSize(WIDTH/2 -20,HEIGHT-20)
		
		splitter=PGui.QSplitter(PCore.Qt.Horizontal)
		splitter.setChildrenCollapsible(False)
		
		splitter.addWidget(self.processView)
		splitter.addWidget(group)
		
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(splitter)
		
		self.setLayout(vbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle("Server TCP + Process running")
		
	def display_output(self):
		lines=str(self.processView.process.readAll())
		self.processView.console.display(lines)

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
			self.processView.server.close()
			print "Server close: not accepting new clients"
			
	def closeEvent(self,event):
		#check if is running
		if self.processView.isRunning or self.processView.thread.isRunning():
			msgBox = PGui.QMessageBox()
			msgBox.setText("Closing the app")
			msgBox.setInformativeText("A process or transfer is running, are you sure you want to quit ? The process or transfer will be killed")
			msgBox.setStandardButtons(PGui.QMessageBox.Yes | PGui.QMessageBox.Cancel)
			msgBox.setDefaultButton(PGui.QMessageBox.Cancel)
			answer = msgBox.exec_()
			if answer==PGui.QMessageBox.Cancel:
				event.ignore()
				return
		self.processView.close()
		event.accept()
			

if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app = PGui.QApplication(sys.argv)
	
	nas=PCore.QDir(NAS_PATH)
	server=PCore.QDir(SERVER_PATH)
	if not nas.exists():
		msgBox=PGui.QMessageBox()
		msgBox.setText("NAS_PATH do not refers to a folder: "+str(NAS_PATH))
		msgBox.exec_()
	elif not server.exists():
		msgBox=PGui.QMessageBox()
		msgBox.setText("SERVER_PATH do not refers to a folder: "+str(SERVER_PATH))
		msgBox.exec_()
	else:
		#to be able to close wth ctrl+c
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		
		win=MainWindow()
		
		win.show()

		sys.exit(app.exec_())

