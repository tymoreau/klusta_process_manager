#Process Manager

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

import sys
import signal

#Model
from experimentModel import ExperimentModel


SEPARATOR='---'*15

#Command to perform on list
PROGRAM="/home/david/anaconda/envs/klusta/bin/klusta"   #experiment.py !
NAS_PATH="/home/david/NAS02"

#Connection to remote computer
IP="10.51.101.29"
PORT=8000


#---------------------------------------------------------------------------------------------------------
# console output
#---------------------------------------------------------------------------------------------------------
class ConsoleView(PGui.QWidget):
	
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
# Thread to transfer NAS -- Local
#------------------------------------------------------------------------------
class Worker(PCore.QObject):
	finished=PCore.Signal()
	workRequested=PCore.Signal()
	
	def __init__(self):
		super(Worker,self).__init__()
		self.isWorking=False
		
	def requestTransfer(self,model):
		if not self.isWorking:
			self.model=model
			self.workRequested.emit()
	
	def doWork(self):
		if not self.isWorking:
			self.isWorking=True
			self.model.beginResetModel()
			self.model.currentExperimentTransfer.transfer()
			self.model.endResetModel()
			self.isWorking=False
			self.finished.emit()




#---------------------------------------------------------------------------------------------------------
# Process Manager
#---------------------------------------------------------------------------------------------------------
class ProcessManager(PGui.QWidget):
	sendsMessage=PCore.Signal(object)

	def __init__(self,NASPath):
		super(ProcessManager,self).__init__()
		
		#experimentModel
		self.model=ExperimentModel(NASPath)
		self.model.changeChecked.connect(self.update_buttons)
		
		#table View
		self.tableView=PGui.QTableView()
		self.tableView.setModel(self.model)
		self.tableView.horizontalHeader().setResizeMode(PGui.QHeaderView.Stretch)
		
		#console
		self.console=ConsoleView()
		
		#server
		self.tcpSocket=PNet.QTcpSocket(self)
		self.tcpSocket.error.connect(self.display_error)
		self.tcpSocket.stateChanged.connect(self.on_state_change)
		self.tcpSocket.disconnected.connect(self.on_disconnection)
		self.tcpSocket.readyRead.connect(self.read)
		#Reading data
		self.blockSize=0
		self.dataStream=PCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(PCore.QDataStream.Qt_4_0)
		
		#Transfer
		self.thread=PCore.QThread()
		self.worker=Worker()
		self.worker.moveToThread(self.thread)
		self.worker.workRequested.connect(self.thread.start)
		self.thread.started.connect(self.worker.doWork)
		self.worker.finished.connect(self.thread.quit)
		self.thread.finished.connect(self.find_file_to_transfer)
		
		#process Here
		self.process=PCore.QProcess()
		self.process.finished.connect(self.go_to_next)
		self.process.readyRead.connect(self.display_output)
		self.process.setProcessChannelMode(PCore.QProcess.MergedChannels)
		
		self.isRunning=False
		
		#dealing with the klusta environment
		env = PCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		env.append(unicode("CONDA_DEFAULT_ENV=klusta"))
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
		self.button_processHere=PGui.QPushButton("\nProcess here\n (klusta) \n")
		self.button_processHere.clicked.connect(self.process_here)
		self.button_processHere.setToolTip("On this computer, process the selected experiments (if they were not already process)")
		
		#process on server
		self.button_connectServer=PGui.QPushButton("\nConnect to server\n")
		self.button_connectServer.clicked.connect(self.connect_to_server)
	
		self.button_processServer=PGui.QPushButton("\nProcess on server\n (klusta) \n")
		self.button_processServer.clicked.connect(self.process_server)

		#on a selection
		self.button_cancel=PGui.QPushButton("Cancel")
		self.button_cancel.clicked.connect(self.cancel)
		self.button_cancel.setToolTip("The selected experiments waiting to be processed will not be processed")
		self.button_remove=PGui.QPushButton("Remove/Kill")
		self.button_remove.clicked.connect(self.remove)
		self.button_remove.setToolTip("The selected experiments will be removed from the list.\n Waiting experiment will not be processed.\n Running experiments will be killed after a warning message")
		
		
		#on everything
		self.button_clear=PGui.QPushButton("Clear")
		self.button_clear.clicked.connect(self.clear_list)
		self.button_clear.setToolTip("Keeps only experiments being or waiting to be processed")
		self.button_selectAll=PGui.QPushButton("Select All")
		self.button_selectAll.clicked.connect(self.model.selectAll)
		self.button_selectNone=PGui.QPushButton("Select None")
		self.button_selectNone.clicked.connect(self.model.selectNone)

	def update_buttons(self,nbChecked):
		if nbChecked>0:
			boolean=True
		else:
			boolean=False
		self.button_processHere.setEnabled(boolean)
		self.button_processServer.setEnabled(boolean)
		self.button_cancel.setEnabled(boolean)
		self.button_remove.setEnabled(boolean)
		
	def _edits(self):
		self.label_ip=PGui.QLabel("IP")
		self.edit_ip=PGui.QLineEdit(IP)
		
		self.label_port=PGui.QLabel("Port")
		self.edit_port=PGui.QLineEdit(str(PORT))
		self.edit_port.setValidator(PGui.QIntValidator(1,65535,self))
		
	def _frames(self):
		#server frame (not connected)
		grid=PGui.QGridLayout()
		grid.addWidget(self.label_ip,0,0)
		grid.addWidget(self.edit_ip,0,1)
		grid.addWidget(self.label_port,1,0)
		grid.addWidget(self.edit_port,1,1)
		grid.addWidget(self.button_connectServer,2,0,1,2)
		self.frameServer=PGui.QGroupBox("Server")
		self.frameServer.setLayout(grid)
		
		#"on selection" frame
		self.vboxSelection=PGui.QVBoxLayout()
		self.vboxSelection.addWidget(self.button_processHere)
		self.vboxSelection.addWidget(self.button_processServer)
		self.vboxSelection.addWidget(self.button_cancel)
		self.vboxSelection.addWidget(self.button_remove)
		frameSelection=PGui.QGroupBox("On Selection")
		frameSelection.setLayout(self.vboxSelection)
		self.button_processServer.hide()
		
		#Middle pannel 
		self.vboxFrame=PGui.QVBoxLayout()
		self.vboxFrame.addWidget(self.frameServer)
		self.vboxFrame.addWidget(frameSelection,1)
		self.middlePannel=PGui.QWidget()
		self.middlePannel.setLayout(self.vboxFrame)
		

	def _layout(self):
		hbox_everything=PGui.QHBoxLayout()
		hbox_everything.addWidget(self.button_clear)
		hbox_everything.addWidget(self.button_selectAll)
		hbox_everything.addWidget(self.button_selectNone)

		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.tableView)
		vbox.addLayout(hbox_everything)
		
		hbox=PGui.QHBoxLayout()
		hbox.addLayout(vbox,2)
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
	#Server related
#---------------------------------------------------------------------------------------------------------
	#connect to server with ip and port specified
	def connect_to_server(self):
		self.ip=self.edit_ip.text()
		self.port=int(self.edit_port.text())
		self.sendsMessage.emit("Attempt to connect with ip: "+self.ip+" and port: "+str(self.port))
		self.tcpSocket.abort()
		self.tcpSocket.connectToHost(PNet.QHostAddress(self.ip),self.port)
		
	def on_state_change(self,fullState):
		state=str(fullState).split('.')[-1][:-5]
		self.sendsMessage.emit("Socket state: "+state)
		if state=='HostLookup':
			self.button_connectServer.setEnabled(False)
		elif state=='Connecting':
			self.button_connectServer.setEnabled(False)
		elif state=="Unconnected":
			self.button_connectServer.setEnabled(True)
		elif state=='Connected':
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
		if socketError == PNet.QAbstractSocket.RemoteHostClosedError:
			self.sendsMessage.emit("Host closed connection")
		elif socketError == PNet.QAbstractSocket.HostNotFoundError:
			self.sendsMessage.emit("The host was not found. Please check the host name and port settings.")
		elif socketError == PNet.QAbstractSocket.ConnectionRefusedError:
			self.sendsMessage.emit("The connection was refused by the peer or time out. Please check the host name and port settings")
		else:
			self.sendsMessage.emit("The following error occurred: %s." % self.tcpSocket.errorString())
		self.tcpSocket.abort()
		
	def send_protocol(self,instruction,List=[]):
		block=PCore.QByteArray()
		out=PCore.QDataStream(block,PCore.QIODevice.WriteOnly)
		out.setVersion(PCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		out.writeString(instruction)
		if instruction=="processList" and len(List)!=0:
			out.writeQStringList(List)
		else:
			print "send_protocol : instruction not known"
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block
	
	def process_server(self):
		self.model.selectionUpdate_process_server()
		self.find_file_to_transfer()
		self.send_list_to_process()
		
	def send_list_to_process(self):
		nameList=[]
		self.model.beginResetModel()
		for experiment in self.model.experimentList:
			if experiment.onServer and experiment.rawOnNAS and experiment.toSend:
				nameList.append(experiment.folder.dirName())
				experiment.toSend=False
				experiment.state="waiting for server response"
		self.model.endResetModel()
		if len(nameList)>0:
			block=self.send_protocol("processList",List=nameList)
			if block!=0:
				self.tcpSocket.write(block)


#---------------------------------------------------------------------------------------------------------
	# receive instruction from server
#---------------------------------------------------------------------------------------------------------
	def read(self):
		while self.tcpSocket.bytesAvailable():
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
			if instruction=="updateState":
				stateList=self.dataStream.readQStringList()
				self.model.update_state(stateList)
				
			elif instruction=="expDone":
				expDone=self.dataStream.readQStringList()
				self.model.server_finished(expDone)
				self.find_file_to_transfer()
			else:
				print "received unknown instruction:",instruction
			


#---------------------------------------------------------------------------------------------------------
	#Transfer
#---------------------------------------------------------------------------------------------------------
	#Transfer a file if possible 
	def find_file_to_transfer(self):
		self.send_list_to_process()
		#if there is not already a transfer running
		if not self.thread.isRunning():
			if self.model.get_first_to_transfer():
				#do the transfer in another thread
				self.worker.requestTransfer(self.model)
				return
	
#---------------------------------------------------------------------------------------------------------
	#List
#---------------------------------------------------------------------------------------------------------
		
	#Return false if experiment already in list
	def add_experiment(self,folderPath):
		return self.model.add_experiment(folderPath)

	def clear_list(self):
		nbRemove=self.model.clear()
		self.sendsMessage.emit("Clear: removed %i experiment(s)" %nbRemove)
		
	#user click cancel: 
	#"waiting to be process" -> None
	def cancel(self):
		nbFound=self.model.selectionUpdate_cancel()
		self.sendsMessage.emit("Canceled %i experiment(s)" %nbFound)
	
	#remove selection from the list
	#if current process in the list, kill it
	def remove(self):
		killCurrent,nbFound=self.model.selectionUpdate_remove()
		self.sendsMessage.emit("Removed %i experiment(s)" %nbFound)
		if killCurrent:
			self.process.kill()
			self.sendsMessage.emit("Killed 1 experiment")
			
			


#---------------------------------------------------------------------------------------------------------
	#Process Here
#---------------------------------------------------------------------------------------------------------
	#user click on Process Here: 
	# -update status of experiments "ready to be process" -> "waiting to be process"
	# -if klusta not already running, starts klusta
	def process_here(self):
		nbFound=self.model.selectionUpdate_process_here()
		self.sendsMessage.emit("Process Here: found %i experiment(s) to process" %nbFound)
		if not self.isRunning and nbFound>0:
			if self.model.get_first_to_process():
				if not self.run_one():
					self.isRunning=False

	#run klusta on one experiment
	def run_one(self):
		if self.model.currentExperiment!=None:
			self.isRunning=True
			self.console.separator(self.model.currentExperiment)
			self.model.currentExperiment.run_klusta(self.process)
		
	#when the current process finish, this function is activate
	#process an other experiment or stop
	def go_to_next(self,exitcode):
		#update experiment
		self.model.currentExperiment_isDone(exitcode)
		
		#find another experiment to process
		if self.model.get_first_to_process():
			self.run_one()
		#or stop
		else:
			self.process.close()
			self.isRunning=False


#---------------------------------------------------------------------------------------------------------
	#Display
#---------------------------------------------------------------------------------------------------------
	#print output of the console in the console view
	def display_output(self):
		lines=str(self.process.readAll())
		self.console.display(lines)


#---------------------------------------------------------------------------------------------------------
#  If launch alone
#---------------------------------------------------------------------------------------------------------
if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	
	win=ProcessManager()

	win.setMinimumSize(1000,600)

	win.show()

	sys.exit(app.exec_())
