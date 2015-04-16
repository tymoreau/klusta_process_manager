#Class to process a list of experiment in klusta
#Buttons to launch klusta on list
#View progress

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet
import sys
import signal


#Connection to remote computer
IP="10.51.101.164"
HOST=PNet.QHostAddress(IP) 
PORT=8000

#if start alone, will process LIST
LIST=["/home/david/dataRat/Rat034_small/Rat034_small.prm","/home/david/dataRat/Rat034_small/Rat034_smal.prm"]

SEPARATOR='---'*15


class TabHere(PGui.QWidget):
	
	def __init__(self):
		super(TabHere,self).__init__()
		
		self.program="klusta"
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.errorsList=[]
		self.successList=[]
		self.currentName=""
		
		self._buttons()
		self._labels()
		self._layout()

	def _buttons(self):
		self.button_processList=PGui.QPushButton("Process list")
		self.button_processList.setEnabled(False)
		
		self.button_clear=PGui.QPushButton("Clear output")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_output)

		
	def _labels(self):
		self.label_general=PGui.QLabel("Nothing running")
		self.label_errors=PGui.QLabel("")
		self.label_success=PGui.QLabel("")

	def _layout(self):
		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		self.console_output.setAlignment(PCore.Qt.AlignLeft)
		
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0,1,1)
		grid.addWidget(self.button_clear,0,1,1,1)
		grid.addWidget(self.label_general,1,0,1,2)
		grid.addWidget(self.label_success,2,0,1,2)
		grid.addWidget(self.label_errors,3,0,1,2)
		grid.addWidget(self.console_output,0,2,4,3)
		self.setLayout(grid)
		
	def feed_list(self,prmFileList):
		self.prmFileList=prmFileList
		self.nbFile=len(prmFileList)
		self.nbFileDone=0
		self.currentName=""
		self.label_general.setText("Start processing list ("+str(self.nbFile)+" files)")
		
		self.process=PCore.QProcess()
		
		#dealing with the klusta environment
		env = PCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		self.process.setEnvironment(env)

		self.process.finished.connect(self.go_to_next)
		self.process.readyRead.connect(self.display_output)
		self.process.setProcessChannelMode(PCore.QProcess.MergedChannels)
		
		self.run_one(prmFileList[0])

	def run_one(self,prmFile):
		print "ProcessManager Here: dealing with prmFile",prmFile
		arguments=[prmFile,"--cluster-only"]
		path='/'.join(prmFile.split('/')[:-1])
		self.currentName=prmFile.split('/')[-1]
		self.separator()
		self.process.setWorkingDirectory(path)
		self.process.start(self.program,arguments)
		self.label_general.setText("Processing file "+str(self.nbFileDone+1)+"/"+str(self.nbFile)+": "+str(self.currentName))

	def separator(self):
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b>'+str(self.currentName)+'</b> \n'
		sep2='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.console_output.append(sep)
		self.console_output.append(sep1)
		self.console_output.append(sep2)

	def go_to_next(self,exitcode):
		if exitcode!=0:
			print "ProcessManager Here: exitcode",exitcode
			self.errorsList.append(self.currentName)
			self.label_errors.setText("Klusta crashed with file(s): \n"+'\n'.join(self.errorsList))
		else:
			self.successList.append(self.currentName)
			self.label_success.setText("Klusta ran with file(s): \n"+'\n'.join(self.successList))
			
		
		self.nbFileDone+=1
		
		if self.nbFile==self.nbFileDone:
			print "ProcessManager Here: every file was processed"
			self.label_general.setText("List done")
			self.button_clear.setEnabled(True)
			self.prmFileList=[]
			self.nbFile=0
			self.nbFileDone=0
			self.currentName=""
			self.process.close()
		else:
			print "ProcessManager Here: move to next file"
			self.run_one(self.prmFileList[self.nbFileDone])

	def display_output(self):
		lines=str(self.process.readAll())
		self.console_output.append(lines)
		
	def clear_output(self):
		self.label_general.setText("Nothing running")
		self.errorsList=[]
		self.successList=[]
		self.label_errors.setText("")
		self.label_success.setText("")
		self.console_output.clear()
		self.button_clear.setEnabled(False)



class TabRemote(PGui.QWidget):

	def __init__(self):
		super(TabRemote,self).__init__()
		self.button_processList=PGui.QPushButton("Process list Remote computer")
		self.button_processList.setEnabled(False)
		self.label_general=PGui.QLabel("Nothing running")
		self.label_warning=PGui.QLabel("")

		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		self.console_output.setAlignment(PCore.Qt.AlignLeft)
		
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0)
		grid.addWidget(self.label_general,1,0,1,2)
		grid.addWidget(self.label_warning,2,0,4,2)
		
		grid.addWidget(self.console_output,0,1,10,2)
		self.setLayout(grid)

	#def feed_list_remote(self,prmFileList,IP,PORT):
		#self.tcpSocket=PNet.QTcpSocket(self)
		#self.tcpSocket.readyRead.connect(self.display_output)
		#self.tcpSocket.error.connect(self.displayError)
		#self.blockSize=0
		#self.tcpSocket.abort()
		
		#HOST=PNet.QHostAddress(IP) 
		#if self.tcpSocket.connectToHost(HOST,PORT):
			#print "connect done"
		
			#block=PCore.QByteArray()
			#out=PCore.QDataStream(block,PCore.QIODevice.WriteOnly)
			#out.writeUInt16(0)
			#out.writeQStringList(prmFileList)
			#out.device().seek(0)
			#out.writeUInt16(block.size()-2)
			#print "out done"
			#self.tcpSocket.write(block)
			#print "write done"


	#def displayError(self,socketError):
		#if socketError == PNet.QAbstractSocket.RemoteHostClosedError:
			#print "Host closed connection"
		#elif socketError == PNet.QAbstractSocket.HostNotFoundError:
			#PGui.QMessageBox.information(self, "Client","The host was not found. Please check the host name and port settings.")
		#elif socketError == PNet.QAbstractSocket.ConnectionRefusedError:
			#PGui.QMessageBox.information(self, "Client","The connection was refused by the peer. Check the host name and port settings")
		#else:
			#PGui.QMessageBox.information(self, "Client","The following error occurred: %s." % self.tcpSocket.errorString())
	


class ProcessManager(PGui.QTabWidget):

	def __init__(self):
		super(ProcessManager,self).__init__()
		self.tabHere=TabHere()
		self.tabRemote=TabRemote()
		self.addTab(self.tabHere, "Process Here")
		self.addTab(self.tabRemote,"Process on Remote computer")



if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	
	win=ProcessManager()
	win.setMinimumSize(1000,200)
	
	def processListHere():
		win.tabHere.feed_list(LIST)
	win.tabHere.button_processList.setEnabled(True)
	win.tabHere.button_processList.clicked.connect(processListHere)

	win.show()

	sys.exit(app.exec_())
