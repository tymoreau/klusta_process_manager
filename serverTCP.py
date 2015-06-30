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
from experimentModelServer import ExperimentModelServer
from clientSocket import Client

#parameters
from parameterServer import *

class Server(QtGui.QWidget):
	def __init__(self,parent=None):
		super(Server,self).__init__(parent)
		
		#IP adress, PORT, HOST
		try:
			self.ip=[(s.connect(('8.8.8.8', 80)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
		except:
			self.ip=IP
		self.port=PORT
		self.host=QtNetwork.QHostAddress(self.ip)
		
		#TCP Server
		self.server=QtNetwork.QTcpServer(self)
		self.server.newConnection.connect(self.on_new_connection)
		if not self.server.listen(address=self.host,port=self.port):
			QtGui.QMessageBox.critical(self,"Server","Unable to start server. Maybe it's already running")
			self.close()
			return
		
		#Process
		self.process=QtCore.QProcess()
		self.process.finished.connect(self.try_process)
		self.wasKill=False
		self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
		self.process.readyRead.connect(self.display_output)

		#Transfer
		self.processSync=QtCore.QProcess()
		self.processSync.finished.connect(self.try_sync)
		
		#dealing with the klusta environment
		env = QtCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		env.append("CONDA_DEFAULT_ENV=klusta")
		self.process.setEnvironment(env)
		
		#console
		self.console=ConsoleView(self)

		#model and clients
		self.clientDict={}
		self.model=ExperimentModelServer(self)
		self.model.expStateChanged.connect(self.update_one_client)
		self.model.expDone.connect(self.one_exp_done)
		self.model.expFail.connect(self.one_exp_fail)
		
		#view
		self.tableView=QtGui.QTableView(self)
		self.tableView.setModel(self.model)
		self.tableView.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)

		#Experiments
		self.root=QtCore.QDir(SERVER_PATH)
		self.experimentDict={}

		self._layout()
		self.show()

	def _layout(self):
		self.button_kill=QtGui.QPushButton("Kill current")
		self.button_kill.setEnabled(False)
		#self.button_kill.clicked.connect(self.kill_current)
		self.button_clear=QtGui.QPushButton("Clear")
		self.button_clear.clicked.connect(self.clear)
		self.label_path=QtGui.QLabel("Data: "+SERVER_PATH)
		self.label_IP=QtGui.QLabel("IP: "+str(self.ip))
		self.label_port=QtGui.QLabel("Port: "+str(self.port))
		self.label_connectedClients=QtGui.QLabel("No clients connected")
		
		labelLayout = QtGui.QHBoxLayout()
		labelLayout.addWidget(self.label_IP)
		labelLayout.addSpacing(20)
		labelLayout.addWidget(self.label_port)
		vbox1=QtGui.QVBoxLayout()
		vbox1.addWidget(self.label_path)
		vbox1.addLayout(labelLayout)
		vbox1.addWidget(self.console)
		vbox2=QtGui.QVBoxLayout()
		vbox2.addWidget(self.tableView)
		vbox2.addWidget(self.button_kill)
		vbox2.addWidget(self.label_connectedClients)
		hbox=QtGui.QHBoxLayout()
		hbox.addLayout(vbox2)
		hbox.addLayout(vbox1)
		self.setLayout(hbox)
		
	def on_new_connection(self):
		while self.server.hasPendingConnections():
			#accept connection
			newTcpSocket=self.server.nextPendingConnection()
			ip=newTcpSocket.peerAddress().toString()
			#check if old/new client
			if ip in self.clientDict.keys():
				self.clientDict[ip].update_socket(newTcpSocket)
				#send data to client
			else:
				self.clientDict[ip]=Client(newTcpSocket)
				self.clientDict[ip].hasNewPaths.connect(self.client_has_new_paths)
				self.clientDict[ip].tcpSocket.disconnected.connect(self.update_label_client)
		self.update_label_client()

	def update_label_client(self):
		ipList=[key for key in self.clientDict if self.clientDict[key].connected]
		if len(ipList)==0:
			self.label_connectedClients.setText("No clients connected")
		else:
			self.label_connectedClients.setText("Connected: "+", ".join(ipList))

	def clear(self):
		pass
	
	#(try to) close everything properly
	def close(self):
		pass
		# if not self.process.waitForFinished(1):
		# 	self.process.kill()
		# 	self.wasKill=True
		# 	self.process.waitForFinished(1)
		# if not self.processSync.waitForFinished(1):
		# 	self.processSync.kill()
		# 	self.processSync.waitForFinished(1)
		# for ip,client in self.clientDict.items():
		# 	if client.tcpSocket.isValid():
		# 		client.tcpSocket.flush()
		# 		client.tcpSocket.disconnectFromHost()
		# self.server.close()

	def client_has_new_paths(self,ip):
		newPaths=self.clientDict[ip].get_new_paths()
		expToAdd=[]
		expFail=[]
		print(newPaths)
		for path in newPaths:
			if path not in self.experimentDict:
				expInfoDict=self.create_expInfoDict(path)
				if expInfoDict is None:
					folderName=QtCore.QFileInfo(path).baseName()
					expFail+=[folderName,"server: could not find folder in backup"]
				else:
					exp=Experiment(expInfoDict)
					if exp.folderName in self.experimentDict:
						print("client resend",path)
						#do nothing ?
					else:
						self.experimentDict[exp.folderName]=exp
						expToAdd.append(exp)
		self.model.add_experiments(expToAdd,ip)
		self.clientDict[ip].add_experiments(expToAdd)
		self.clientDict[ip].unvalid_experiments(expFail)
		self.try_sync()

	def create_expInfoDict(self,path):
		expInfo=None
		backUP=QtCore.QFileInfo(path)
		if backUP.exists() and backUP.isDir():
			expInfo={}
			expInfo["pathBackUP"]=backUP.canonicalFilePath()
			name=backUP.baseName()
			expInfo["folderName"]=name
			expInfo["icon"]=None
			expInfo["animalID"]=None
			self.root.mkdir(name)
			expInfo["pathLocal"]=self.root.filePath(name)
			expInfo["dateTime"]="_".join(name.split("_")[1:])
		return expInfo

	def try_sync(self,exitcode=0):
		if self.processSync.state()==QtCore.QProcess.Running:
			return
		else:
			if self.model.sync_done(exitcode):
				self.try_process()
			self.model.sync_one_experiment(self.processSync)
			#self.clientDict[ip].send_pathToState() signal from model
			#try send done/fail

	def try_process(self,exitcode=0):
		if self.process.state()==QtCore.QProcess.Running:
			return
		else:
			if self.wasKill:
				self.wasKill=False
				exitcode=42
			if self.model.process_is_done(exitcode):
				self.try_sync()
				#self.client.send_pathToState()
			if self.model.process_one_experiment(self.process):
				self.console.separator(self.model.expProcessing)

	def update_one_client(self,ip):
		self.clientDict[ip].send_update_state()

	def one_exp_done(self,ip,folderName):
		self.clientDict[ip].update_expDone(folderName)

	def one_exp_fail(self,ip,folderName):
		self.clientDict[ip].update_expFail(folderName)

	def display_output(self):
		byteArray=self.process.readAll()
		string="".join(byteArray)
		self.console.display(string)
	
	def closeEvent(self,event):
		pass
		# #check if is running
		# if self.processView.process.state()==QtCore.QProcess.Running
	#or self.processView.processSync.state()==QtCore.QProcess.Running :
		# 	msgBox = QtGui.QMessageBox()
		# 	msgBox.setText("Closing the app")
		# 	msgBox.setInformativeText("A process or transfer is running, are you sure you want to quit ?)
		# 	msgBox.setStandardButtons(QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel)
		# 	msgBox.setDefaultButton(QtGui.QMessageBox.Cancel)
		# 	answer = msgBox.exec_()
		# 	if answer==QtGui.QMessageBox.Cancel:
		# 		event.ignore()
		# 		return
		# self.processView.close()
		# self.close()
		# event.accept()
			

#-----------------------------------------------------------------------------------
if __name__=='__main__':
	QtGui.QApplication.setStyle("cleanlooks")
	app = QtGui.QApplication(sys.argv)
	
	nas=QtCore.QDir(BACK_UP_PATH)
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
		
		win=Server()

		sys.exit(app.exec_())
