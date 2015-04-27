# Import Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

#Connection to remote computer
IP="10.51.101.29"
HOST=PNet.QHostAddress(IP) 
PORT=8000

class TabRemote(PGui.QStackedWidget):

	def __init__(self):
		super(TabRemote,self).__init__()

		self._buttons()
		self._labels()
		
		self.viewConnect=PGui.QWidget()
		self.viewConnect.setLayout(self.layoutConnect())
		
		self.viewServer=PGui.QWidget()
		self.viewServer.setLayout(self.layoutServer())
		
		self.addWidget(self.viewConnect)
		self.addWidget(self.viewServer)
		self.setCurrentIndex(0)
		
		self.tcpSocket=PNet.QTcpSocket(self)
		self.tcpSocket.error.connect(self.display_error)
		self.tcpSocket.stateChanged.connect(self.on_state_change)
		self.tcpSocket.disconnected.connect(self.on_disconnection)
		self.tcpSocket.readyRead.connect(self.display_output_from_remote)
		
		self.blockSize=0
		self.ip=IP
		self.port=PORT
		

	def _buttons(self):
		self.button_connect=PGui.QPushButton("\n Connect to server \n")
		self.button_connect.clicked.connect(self.connect_to_server)
		
		self.button_processList=PGui.QPushButton("Process list")
		self.button_processList.setEnabled(False)
		
		self.button_clear=PGui.QPushButton("Clear output")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_output)

	def _labels(self):
		self.label_general=PGui.QLabel("Nothing running")
		self.label_errors=PGui.QLabel("")
		self.label_success=PGui.QLabel("")
		self.label_connect=PGui.QLabel("")

	def layoutConnect(self):
		self.edit_ip=PGui.QLineEdit(IP)
		self.edit_port=PGui.QLineEdit(str(PORT))
		self.edit_port.setValidator(PGui.QIntValidator(1,65535,self))
		
		self.label_state=PGui.QLabel("")
		self.label_connectionErrors=PGui.QLabel("")
		
		formLayout=PGui.QFormLayout()
		formLayout.addRow("Server IP: ",self.edit_ip)
		formLayout.addRow("Port: ",self.edit_port)
		
		vbox=PGui.QVBoxLayout()
		vbox.addStretch()
		vbox.addLayout(formLayout)
		vbox.addWidget(self.button_connect)
		vbox.addWidget(self.label_state)
		vbox.addWidget(self.label_connectionErrors)
		vbox.addStretch()
		
		hbox=PGui.QHBoxLayout()
		hbox.addStretch()
		hbox.addLayout(vbox)
		hbox.addStretch()
		return hbox

	def layoutServer(self):
		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		self.console_output.setAlignment(PCore.Qt.AlignLeft)
		
		grid=PGui.QGridLayout()
		grid.addWidget(self.label_connect,0,0,1,2)
		grid.addWidget(self.button_processList,1,0,1,1)
		grid.addWidget(self.button_clear,1,1,1,1)
		grid.addWidget(self.label_general,2,0,1,2)
		grid.addWidget(self.label_success,3,0,1,2)
		grid.addWidget(self.label_errors,4,0,1,2)
		grid.addWidget(self.console_output,0,2,5,3)
		return grid
		
	def connect_to_server(self):
		self.ip=self.edit_ip.text()
		self.port=int(self.edit_port.text())
		self.label_connectionErrors.setText("Attempt to connect with ip: "+self.ip+" and port: "+str(self.port))
		self.tcpSocket.abort()
		self.tcpSocket.connectToHost(PNet.QHostAddress(self.ip),self.port)


	def on_state_change(self,fullState):
		state=str(fullState).split('.')[-1][:-5]
		print "Socket state: ",state
		self.label_state.setText("Socket state: "+state)
		
		if state=='HostLookup':
			self.button_connect.setEnabled(False)
			
		elif state=='Connecting':
			self.button_connect.setEnabled(False)
			
		elif state=="Unconnected":
			self.button_connect.setEnabled(True)
			
		elif state=='Connected':
			self.on_connection()
			

	def on_connection(self):
		if self.tcpSocket.isValid():
			print "Connected to server"
			self.setCurrentIndex(1)
			self.label_connect.setText("Connected to server (ip="+self.ip+", port="+str(self.port)+")")
		else:
			print "Socket is not valid"

	def on_disconnection(self):
		print "Disconnection"
		self.setCurrentIndex(0)
		self.label_state.setText("Socket was disconnected")


	def send_protocol(self,instruction,List=[]):
		block=PCore.QByteArray()
		out=PCore.QDataStream(block,PCore.QIODevice.WriteOnly)
		out.setVersion(PCore.QDataStream.Qt_4_0)
		out.writeUInt16(0)
		out.writeString(instruction)
		if instruction=="processList" and len(List)!=0:
			out.writeQStringList(List)
		elif instruction=="stopProcess":
			pass
		elif instruction=="myProcessState":
			pass
		else:
			print "send_protocol : instruction not known"
			return 0
		out.device().seek(0)
		out.writeUInt16(block.size()-2)
		return block

	def feed_list_remote(self,prmFileList):
		block=self.send_protocol("processList",prmFileList)
		if block:
			self.tcpSocket.write(block)
			print "send list to server"
		else:
			print "could not send list to server"


	def display_error(self,socketError):
		if socketError == PNet.QAbstractSocket.RemoteHostClosedError:
			self.label_connectionErrors.setText("Host closed connection")
		elif socketError == PNet.QAbstractSocket.HostNotFoundError:
			self.label_connectionErrors.setText("The host was not found. Please check the host name and port settings.")
		elif socketError == PNet.QAbstractSocket.ConnectionRefusedError:
			self.label_connectionErrors.setText("The connection was refused by the peer or time out. Please check the host name and port settings")
		else:
			self.label_connectionErrors.setText("The following error occurred: %s." % self.tcpSocket.errorString())
		self.tcpSocket.abort()

	def display_output_from_remote(self):
		instr=PCore.QDataStream(self.tcpSocket)
		instr.setVersion(PCore.QDataStream.Qt_4_0)
		
		if self.blockSize == 0:
			if self.tcpSocket.bytesAvailable() < 2:
				print "client: bytes inf 2"
				return 0
			self.blockSize = instr.readUInt16()

		if self.tcpSocket.bytesAvailable() < self.blockSize:
			print "client :bytes inf block size"
			return 0
		
		print "message received:", instr.readString()

	def clear_output():
		self.label_general.setText("Nothing running")
		self.errorsList=[]
		self.successList=[]
		self.label_errors.setText("")
		self.label_success.setText("")
		self.console_output.clear()
		self.button_clear.setEnabled(False)