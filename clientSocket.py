#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtNetwork

#parameters
SERVER_PATH="./test/dataServer"
BACK_UP_PATH="./test/fakeNAS"  #need
PROGRAM="klusta"
PORT=8000
SEPARATOR="---"*10
IP="127.0.0.1"

#--------------------------------------------------------------------------------------------------------
#  CLIENT: tcpSocket to communicate with the tcpSocket of ProcessManager.py
#---------------------------------------------------------------------------------------------------------
class Client(QtCore.QObject):
	hasNewPaths=QtCore.pyqtSignal(str)

	def __init__(self,socket):
		super(Client,self).__init__()
		
		#TCP socket
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		
		#Reading data
		self.blockSize=0
		self.dataStream=QtCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(QtCore.QDataStream.Qt_4_0)
		
		#Client infos
		self.ip=self.tcpSocket.peerAddress().toString()
		self.connected=True

		#Experiment
		self.pathToState={}
		self.newPaths=[]
		self.expDoneList=[]
		self.expFailList=[]

	#client reconnected to server
	def update_socket(self,socket):
		self.tcpSocket=socket
		self.tcpSocket.disconnected.connect(self.on_disconnect)
		self.tcpSocket.readyRead.connect(self.read)
		#Reading data
		self.blockSize=0
		self.dataStream=QtCore.QDataStream(self.tcpSocket)
		self.dataStream.setVersion(QtCore.QDataStream.Qt_4_0)
		self.connected=True
		
	#client disconnected
	def on_disconnect(self):
		try:
			self.tcpSocket.deleteLater()
		except RuntimeError:
			pass
		self.connected=False

	#Experiments
	def get_new_paths(self):
		new=self.newPaths[:]
		self.newPaths=[]
		return new

	def update_experiments_state(self,expList):
		for exp in expList:
			self.pathToState[exp.folderName]=exp
		self.send_pathToState()

	def unvalid_experiments(self,expFailList):
		self.expFailList+=expFailList
		self.send_expFail()

	def send_expDone(self):
		if self.connected:
			if self.expDoneList:
				print("send",self.expDoneList)
				block=self.send_protocol("expDone",List=self.expDoneList)
				if block!=0:
					self.tcpSocket.write(block)
					self.expDoneList=[]

	def send_expFail(self):
		if self.connected:
			if self.expFailList:
				print("send",self.expFailList)
				block=self.send_protocol("expFail",List=self.expFailList)
				if block!=0:
					self.tcpSocket.write(block)
					self.expFailList=[]

	def send_pathToState(self):
		if self.connected:
			stateList=[]
			for path in self.pathToState:
				stateList.append(path)
				stateList.append(self.pathToState[path].state)
			if stateList:
				print("send",stateList)
				block=self.send_protocol("updateState",List=stateList)
				if block!=0:
					self.tcpSocket.write(block)

	# Receive instruction
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

	#Received a list of pathBackUP, replace root
	def instruction_process_list(self):
		#read list
		pathList=self.dataStream.readQStringList()
		rootClient=pathList.pop(0)
		for path in pathList:
			path=path.replace(rootClient,BACK_UP_PATH)
		self.newPaths+=pathList
		if self.newPaths:
			self.hasNewPaths.emit(self.ip)

	def send_protocol(self,instruction,List=[]):
		block=QtCore.QByteArray()
		out=QtCore.QDataStream(block,QtCore.QIODevice.WriteOnly)
		out.setVersion(QtCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		instr=bytes(instruction,encoding="ascii")
		out.writeString(instr)
		if instruction in ["updateState","expDone","expFail"]:
			out.writeQStringList(List)
		else:
			print("send_protocol : instruction not known")
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block

