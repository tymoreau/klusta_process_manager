import signal
import sys
import socket

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtNetwork

from experiment import Experiment
from consoleView import ConsoleView

#parameters
SERVER_PATH="./test/dataServer"
NAS_PATH="./test/fakeNAS"
PROGRAM="klusta"
PORT=8000
SEPARATOR="---"*10
IP="127.0.0.1"

#--------------------------------------------------------------------------------------------------------
# TcpServer: Launch a server
#--------------------------------------------------------------------------------------------------------
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
		
		labelLayout = QtGui.QHBoxLayout()
		labelLayout.addWidget(self.label_IP)
		labelLayout.addSpacing(20)
		labelLayout.addWidget(self.label_port)
		
		vbox= QtGui.QVBoxLayout()
		vbox.addLayout(labelLayout)
		vbox.setContentsMargins(10,10,10,10)
		self.setLayout(vbox)





#-------------------------------------------------------------------------------------------------------
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

#-------------------------------------------------------------------------------------------------------------
# Main Window: manages view
#--------------------------------------------------------------------------------------------------------------
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
