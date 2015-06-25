#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtNetwork

#parameters
SERVER_PATH="./test/dataServer"
NAS_PATH="./test/fakeNAS"
PROGRAM="klusta"
PORT=8000
SEPARATOR="---"*10
IP="127.0.0.1"

#--------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py
#---------------------------------------------------------------------------------------------------------
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

