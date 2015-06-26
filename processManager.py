import sys
import signal

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtNetwork

from processListModel import ProcessListModel
from parameter import *

#---------------------------------------------------------------------------------------------------------
# console output
#---------------------------------------------------------------------------------------------------------
class ConsoleView(QtGui.QWidget):
	
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
		sep1='<b> Experiment: '+str(experiment.folderName)+'</b> \n'
		sep2='Working directory: '+str(experiment.pathLocal)+' \n'
		sep3='Do: %s %s\n'%(PROGRAM,experiment.folder.prm.fileName())
		sep4='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.output.append(sep)
		self.output.append(sep1)
		self.output.append(sep2)
		self.output.append(sep3)
		self.output.append(sep4)

#---------------------------------------------------------------------------------------------------------
# Process Manager
#---------------------------------------------------------------------------------------------------------
class ProcessManager(QtGui.QWidget):
	sendsMessage=QtCore.pyqtSignal(object)

	def __init__(self,NASPath):
		super(ProcessManager,self).__init__()
		
		#experimentModel
		self.model= ProcessListModel()
		self.model.changeChecked.connect(self.update_buttons)
		
		#table View
		self.tableView=QtGui.QTableView()
		self.tableView.setModel(self.model)
		self.tableView.setHorizontalHeader(self.model.header)
		
		#console
		self.console=ConsoleView()
		
		#server
		self.tcpSocket=QtNetwork.QTcpSocket(self)
		self.tcpSocket.error.connect(self.display_error)
		self.tcpSocket.stateChanged.connect(self.on_state_change)
		self.tcpSocket.disconnected.connect(self.on_disconnection)
		self.tcpSocket.readyRead.connect(self.read)
		
		#Reading data
		self.blockSize=0
		self.dataStream=QtCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(QtCore.QDataStream.Qt_4_0)
		
		#Transfer
		self.processSync=QtCore.QProcess()
		self.processSync.finished.connect(self.try_sync)
		
		#process Here
		self.process=QtCore.QProcess()
		self.process.finished.connect(self.try_process)
		self.wasKill=False
		self.process.readyRead.connect(self.display_output)
		self.process.setProcessChannelMode(QtCore.QProcess.MergedChannels)

		#dealing with the klusta environment (not perfect)
		env = QtCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			newitem=newitem.replace('/miniconda/bin:','/miniconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
			env.append(PROGRAM)
		env.append("CONDA_DEFAULT_ENV=klusta")
		self.process.setEnvironment(env)
		
		#Layout
		self._buttons()
		self.update_buttons(False)
		self._edits()
		self._frames()
		self._layout()
		
#---------------------------------------------------------------------------------------------------------
	#Layout
#---------------------------------------------------------------------------------------------------------
	def _buttons(self):
		#process here
		self.button_processHere=QtGui.QPushButton("\nProcess here\n (klusta) \n")
		self.button_processHere.clicked.connect(self.process_local)
		self.button_processHere.setToolTip("On this computer, process the selected experiments")
		
		#process on server
		self.button_connectServer=QtGui.QPushButton("\nConnect to server\n")
		self.button_connectServer.clicked.connect(self.connect_to_server)
		self.button_processServer=QtGui.QPushButton("\nProcess on server\n (klusta) \n")
		self.button_processServer.clicked.connect(self.process_server)
		self.button_processServer.setToolTip("Back up, process on server, Sync from back up")

		#sync
		self.button_backUP=QtGui.QPushButton("Back UP")
		self.button_backUP.clicked.connect(self.backUP)
		self.button_sync=QtGui.QPushButton("Sync from back up")
		self.button_sync.clicked.connect(self.sync_from_backUP)

	def update_buttons(self,nbChecked):
		if nbChecked>0:
			boolean=True
		else:
			boolean=False
		self.button_processHere.setEnabled(boolean)
		self.button_processServer.setEnabled(boolean)
		
	def _edits(self):
		self.label_ip=QtGui.QLabel("IP")
		self.edit_ip=QtGui.QLineEdit(IP)
		self.label_port=QtGui.QLabel("Port")
		self.edit_port=QtGui.QLineEdit(str(PORT))
		self.edit_port.setValidator(QtGui.QIntValidator(1,65535,self))
		
	def _frames(self):
		#server frame (not connected)
		grid=QtGui.QGridLayout()
		grid.addWidget(self.label_ip,0,0)
		grid.addWidget(self.edit_ip,0,1)
		grid.addWidget(self.label_port,1,0)
		grid.addWidget(self.edit_port,1,1)
		grid.addWidget(self.button_connectServer,2,0,1,2)
		self.frameServer=QtGui.QGroupBox("Server")
		self.frameServer.setLayout(grid)
		
		#"on selection" frame
		self.vboxSelection=QtGui.QVBoxLayout()
		self.vboxSelection.addWidget(self.button_processHere)
		self.vboxSelection.addWidget(self.button_processServer)
		self.vboxSelection.addWidget(self.button_backUP)
		self.vboxSelection.addWidget(self.button_sync)
		frameSelection=QtGui.QGroupBox("On Selection")
		frameSelection.setLayout(self.vboxSelection)
		self.button_processServer.hide()
		
		#Middle pannel 
		self.vboxFrame=QtGui.QVBoxLayout()
		self.vboxFrame.addWidget(self.frameServer)
		self.vboxFrame.addWidget(frameSelection,1)
		self.middlePannel=QtGui.QWidget()
		self.middlePannel.setLayout(self.vboxFrame)
		
	def _layout(self):
		hbox=QtGui.QHBoxLayout()
		hbox.addWidget(self.tableView,2)
		hbox.addWidget(self.middlePannel)
		hbox.addWidget(self.console,2)
		self.setLayout(hbox)

	def update_Layout(self,connected=True):
		if connected:
			self.frameServer.hide()
			self.button_processServer.show()
		else:
			self.frameServer.show()
			self.button_processServer.hide()

#---------------------------------------------------------------------------------------------------------
#List
#---------------------------------------------------------------------------------------------------------
	def add_experiments(self,expList):
		self.model.add_experiments(expList)

	def clear_list(self):
		nbRemove=self.model.clear()
		self.sendsMessage.emit("Clear: removed %i experiment(s)" %nbRemove)

#---------------------------------------------------------------------------------------------------------
#Transfer
#---------------------------------------------------------------------------------------------------------
	def backUP(self):
		self.model.selection_backUP()
		self.try_sync()

	def sync_from_backUP(self):
		self.model.selection_sync_from_backUP()
		self.try_sync()
	
	#Transfer a file if possible 
	def try_sync(self,exitcode=0):
		#if there is not already a transfer running
		if self.processSync.state()==QtCore.QProcess.Running:
			return
		else:
			self.model.sync_done(exitcode)
			self.try_send()
			self.try_process()
			self.model.sync_one_experiment(self.processSync)

	#Send experiment path on NAS to server
	def try_send(self):
		if self.tcpSocket.isValid():
			pathBackUPList=self.model.list_to_send_server()
			pathBackUPList.insert(0,BACK_UP)
			if len(pathBackUPList)>0:
				block=self.send_protocol("processList",List=pathBackUPList)
				if block!=0:
					self.tcpSocket.write(block)
					return
				self.model.server_unreachable(pathBackUPList)
			
#---------------------------------------------------------------------------------------------------------
#Process Here: use QProcess localy
#---------------------------------------------------------------------------------------------------------
	#user click on Process Here: 
	# -update status of experiments "ready to be process" -> "waiting to be process"
	# -if klusta not already running, starts klusta
	def process_local(self):
		self.model.selection_process_local()
		self.try_process()
		self.try_sync()

	def try_process(self,exitcode=0):
		#if there is not already a transfer running
		if self.process.state()==QtCore.QProcess.Running:
			return
		else:
			if self.wasKill:
				self.wasKill=False
				exitcode=42
			if self.model.process_is_done(exitcode):
				self.try_sync()
			if self.model.process_one_experiment(self.process):
				self.console.separator(self.model.expProcessing)

	def kill_process(self):
		pass
		#if self.model.kill_current():
			#self.process.kill()
			#self.wasKill=True
			#self.sendsMessage.emit("Kill: killed process")
		#else:
			#self.sendsMessage.emit("Kill: did nothing")

	#print output of the console in the console view
	def display_output(self):
		byteArray=self.process.readAll()
		string="".join(byteArray)
		self.console.display(string)
		
#---------------------------------------------------------------------------------------------------------
#	Server related
#---------------------------------------------------------------------------------------------------------
	def process_server(self):
		self.model.selection_process_server()
		self.try_sync()

	def server_send_finished(self,expDoneList):
		self.model.server_finished(expDoneList)
		self.try_sync()

	#connect to server with ip and port specified
	def connect_to_server(self):
		self.ip=self.edit_ip.text()
		self.port=int(self.edit_port.text())
		self.sendsMessage.emit("Attempt to connect with ip: "+self.ip+" and port: "+str(self.port))
		self.tcpSocket.abort()
		self.tcpSocket.connectToHost(QtNetwork.QHostAddress(self.ip),self.port)
		
	def on_state_change(self,intState):
		if intState==0:
			self.button_connectServer.setEnabled(True)
			self.sendsMessage.emit("Socket unconnected")
		elif intState==1:
			self.button_connectServer.setEnabled(False)
			self.sendsMessage.emit("Socket state: Host Look up...")
		elif intState==2:
			self.button_connectServer.setEnabled(False)
			self.sendsMessage.emit("Socket state: Connecting...")
		elif intState==3:
			self.sendsMessage.emit("Socket state: Connected")
			self.on_connection()

	def on_connection(self):
		if self.tcpSocket.isValid():
			self.sendsMessage.emit("Connected to server (ip="+self.ip+", port="+str(self.port)+")")
			self.update_Layout(connected=True)
		else:
			self.sendsMessage.emit("Socket is not valid")
			
	def on_disconnection(self):
		self.update_Layout(connected=False)
		self.sendsMessage.emit("Socket was disconnected")
		self.model.server_close()
		
	def display_error(self,socketError):
		if socketError == QtNetwork.QAbstractSocket.RemoteHostClosedError:
			self.sendsMessage.emit("Host closed connection")
		elif socketError == QtNetwork.QAbstractSocket.HostNotFoundError:
			self.sendsMessage.emit("The host was not found. Please check the host name and port settings.")
		elif socketError == QtNetwork.QAbstractSocket.ConnectionRefusedError:
			self.sendsMessage.emit("The connection was refused by the peer or time out. Please check the host name and port settings")
		else:
			self.sendsMessage.emit("The following error occurred: %s." % self.tcpSocket.errorString())
		self.tcpSocket.abort()
		
	def send_protocol(self,instruction,List=[]):
		block=QtCore.QByteArray()
		out=QtCore.QDataStream(block,QtCore.QIODevice.WriteOnly)
		out.setVersion(QtCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		
		instr=bytes(instruction,encoding="ascii")
		out.writeString(instr)
		if instruction=="processList" and len(List)!=0:
			out.writeQStringList(List)
			print("send",List)
		else:
			print("send_protocol : instruction not known")
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block

	#receive instruction from server
	def read(self):
		while self.tcpSocket.bytesAvailable():
			#read size of block
			if self.tcpSocket.bytesAvailable() < 2:
				print("client: bytes inf 2")
				return 0
			self.blockSize = self.dataStream.readUInt16()

			#check if all data is available
			if self.tcpSocket.bytesAvailable() < self.blockSize:
				print("client :bytes inf block size")
				return 0
			
			#read instruction
			instr=self.dataStream.readString()
			instruction=str(instr,encoding='ascii')
			
			if instruction=="updateState":
				stateList=self.dataStream.readQStringList()
				print("receive state",stateList)
				self.model.server_update_state(stateList)
				
			elif instruction=="expDone":
				expDoneList=self.dataStream.readQStringList()
				print("receive expDone",expDoneList)
				self.server_send_finished(expDoneList)
			else:
				print("received unknown instruction:",instruction)

#-----------------------------------------------------------------
	def close(self):
		pass
		#if not self.process.waitForFinished(1):
			#if self.model.kill_current():
				#self.process.kill()
				#self.wasKill=True
				#self.process.waitForFinished(1)
			#else:
				#return
		#if not self.processSync.waitForFinished(1):
			#if self.model.kill_current_sync():
				#self.processSync.kill()
				#self.processSync.waitForFinished(1)
			#else:
				#return
		#self.tcpSocket.disconnectFromHost()
		#del self.model


#---------------------------------------------------------------------------------------------------------
#  If launch alone (not up to date)
#---------------------------------------------------------------------------------------------------------
#if __name__=='__main__':
	#QtGui.QApplication.setStyle("cleanlooks")
	#app=QtGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	#signal.signal(signal.SIGINT, signal.SIG_DFL)

	
	#win=ProcessManager()

	#win.setMinimumSize(1000,600)

	#win.show()

	#sys.exit(app.exec_())
