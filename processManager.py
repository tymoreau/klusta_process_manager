#Class to process a list of experiment in klusta
#Buttons to launch klusta on list
#View progress

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import sys
import signal

#is start alone, will process LIST
LIST=["/home/david/dataRat/Rat034_shank0/Rat034_shank0.prm"]

SEPARATOR='---'*15


class ProcessManager(PGui.QGroupBox):

	def __init__(self):
		super(ProcessManager,self).__init__()
		
		self.setTitle("Process Manager")
		
		self.program="klusta"
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.errorsList=[]
		self.sucessList=[]
		self.currentOutput=["\n","\n","\n"]
		self.currentName=""
		
		self._buttons()
		self._labels()
		self._layout()
		
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
	
	def _buttons(self):
		self.button_processList=PGui.QPushButton("Process list \n on this computer")
		self.button_processList.setEnabled(False)
		self.button_processListRemote=PGui.QPushButton("Process list \n on remote computer")
		self.button_processListRemote.setEnabled(False)
		
	def _labels(self):
		self.label_general=PGui.QLabel("Nothing running")
		self.label_warning=PGui.QLabel("")
		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		self.console_output.setAlignment(PCore.Qt.AlignLeft)
		
	def _layout(self):
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0)
		grid.addWidget(self.button_processListRemote,0,1)
		grid.addWidget(self.console_output,0,2,10,2)
		
		grid.addWidget(self.label_general,1,0,1,2)
		grid.addWidget(self.label_warning,3,0,3,2)
		self.setLayout(grid)
		
	def feed_list(self,prmFileList):
		self.prmFileList=prmFileList
		self.nbFile=len(prmFileList)
		self.label_general.setText("Start processing list ("+str(self.nbFile)+" files)")
		
		self.run_one(prmFileList[0])
		
	def run_one(self,prmFile):
		print "ProcessManager: dealing with prmFile",prmFile
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
			print "ProcessManager: exitcode",exitcode
			self.errorsList.append(self.currentName)
			warningList='\n'.join(self.errorsList)
			self.label_warning.setText("Klusta crashed with file(s): \n"+warningList)
		else:
			self.sucessList.append(self.currentName)
		
		self.nbFileDone+=1
		
		if self.nbFile==self.nbFileDone:
			print "ProcessManager: every file was processed"
			self.label_general.setText("List done")
			self.clear()
		else:
			print "ProcessManager: move to next file"
			self.run_one(self.prmFileList[self.nbFileDone])
			
	def display_output(self):
		lines=str(self.process.readAll())
		self.console_output.append(lines)
		
	def clear(self):
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.process.close()


if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	
	win=ProcessManager()
	win.setMinimumSize(1000,200)
	win.feed_list(LIST)
	win.show()

	sys.exit(app.exec_())
