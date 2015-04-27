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
class Experiment(PCore.QObject):
	changeState=PCore.Signal(object)
	
	def __init__(self,name,pathNAS):
		super(Experiment,self).__init__()
		
		#where to find the prmFile
		self.name=name
		self.pathNAS=pathNAS
		
		#where to find folder
		self.folderName=pathNAS.split('/')[-2]
		self.folderPathNAS='/'.join(pathNAS.split('/')[:-1])

		#where to put on the server
		self.folderPathServer=SERVER_PATH+'/'+self.folderName
		self.pathServer=SERVER_PATH+'/'+self.folderName+'/'+self.name

		#where is the processing
		self.state="Found in NAS"
		self.isTransfered=False
		self.isRunning=False
		self.isDone=False


	def copy_fromNAS_toServer(self):
		if not self.isTransfered:
			try:
				#to improve: move file by file
				os.system('cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/')
				print('cp -r '+self.folderPathNAS+' '+SERVER_PATH+'/')
				self.state="transfered to server"
				self.isTransfered=True
			except Exception,e:
				print "exception:",e
				self.state="could not transfer to server"
			self.changeState.emit(self.name)
		
	def run_klusta(self,process):
		process.setWorkingDirectory(SERVER_PATH+'/'+self.folderName)
		process.start(PROGRAM,[self.name]+ARGUMENTS)
		self.state="Klusta running"
		self.isRunning=True
		self.changeState.emit(self.name)
		
	def is_done(self,exitcode):
		if exitcode!=0:
			self.state="klusta crashed"
			print "exitcode", exitcode
		else:
			self.state="Processing done (klusta ran)"
		self.isDone=True
		self.isRunning=False
		self.changeState.emit(self.name)




#-------------------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py  ---- other data on client
#-------------------------------------------------------------------------------------------------------------------
class Client(PCore.QObject):
	hasUpdate=PCore.Signal()
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
		print "Do: processList"
		#read list
		self.prmFileList+=self.dataStream.readQStringList()
		#check it
		for prmFile in self.prmFileList:
			self.check_file(prmFile)
		self.prmFileList=[]
		#send change to client
		self.send_process_state()
		#Signal server
		self.hasUpdate.emit()
	
		#client is waiting since this moment
		self.waitingSince=time.time()
		
		#transfer correct file from NAS to Server
		for name,experiment in self.experimentDict.items():
			if not experiment.isTransfered:
				experiment.copy_fromNAS_toServer()
		#signal server that new files arrived (maybe)
		self.hasNewExperiment.emit()


	def on_experiment_change_state(self):
		#send change to client
		self.send_process_state()
		#Signal server
		self.hasUpdate.emit()
		

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
				self.experimentDict[name]=Experiment(name,pathNAS=prmFileNAS)
				self.experimentDict[name].changeState.connect(self.on_experiment_change_state)
				found=True
				break
		if not found:
			self.impossibleList+=[name,"not find in NAS"]


	def send_process_state(self):
		#Send state to client
		listToSend=[]
		for name,experiment in self.experimentDict.items():
			listToSend+=[name,experiment.state]
		listToSend+=self.impossibleList
		block=self.send_protocol("updateDict",listToSend)
		self.tcpSocket.write(block)
		print "Send updateDict to client",self.ip
		print "list=",listToSend
		
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
		self.hasUpdate.emit()


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
# Display console output
#--------------------------------------------------------------------------------------------------------
class ConsoleView(PGui.QGroupBox):
	def __init__(self):
		super(ConsoleView,self).__init__()
		self.setTitle("Console Output")
		
		self.output=PGui.QTextEdit()
		self.output.setReadOnly(True)
		
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.output)
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
		self.process=PCore.QProcess()
		self.process.finished.connect(self.go_to_next)
		self.process.setProcessChannelMode(PCore.QProcess.MergedChannels)
		self.process.readyRead.connect(self.display_output)
		self.isRunning=False
		self.currentExperiment=None
		
		#console output
		self.console=ConsoleView()

	def display_output(self):
		lines=str(self.process.readAll())
		self.console.output.append(lines)
		
	def separator(self):
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b>'+str(self.currentExperiment.name)+'</b> \n'
		sep2='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.console.output.append(sep)
		self.console.output.append(sep1)
		self.console.output.append(sep2)

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
				self.clientDict[ip].hasUpdate.connect(self.update_table)
				self.clientDict[ip].hasNewExperiment.connect(self.try_launch_process)


	def try_launch_process(self):
		if not self.isRunning:
			if self.find_file_to_process():
				self.isRunning=True
				self.separator()
				self.currentExperiment.run_klusta(self.process)
			else:
				print "no file to process"
		else:
			print "already running"

	def find_file_to_process(self):
		for ip,client in self.clientDict.items():
			for name,experiment in client.experimentDict.items():
				if experiment.isTransfered and not experiment.isDone:
					self.currentExperiment=experiment
					return True
		self.currentExperiment=None
		return False

	def go_to_next(self,exitcode):
		self.currentExperiment.is_done(exitcode)
		if self.find_file_to_process():
			self.separator()
			self.currentExperiment.run_klusta(self.process)
		else:
			self.isRunning=False
		
			
		




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
		
		#Layout
		self._layout()
		
	def _layout(self):
		WIDTH=800
		HEIGHT=600
		
		self.processView.console.setMinimumSize(WIDTH/2 -20,HEIGHT*0.75)
		self.processView.table.setMinimumSize(WIDTH/2 -20,HEIGHT -20)
		
		group=PGui.QWidget()
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.serverView)
		vbox.addWidget(self.processView.console)
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
			self.processView.server.close()
			print "Server close: not accepting new clients"
			

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

