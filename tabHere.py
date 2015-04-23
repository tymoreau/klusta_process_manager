# Import Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

SEPARATOR='---'*15

#Command to perform on list
PROGRAM="klusta"
ARGUMENTS=["--overwrite"]


class TabHere(PGui.QWidget):
	
	def __init__(self):
		super(TabHere,self).__init__()
		
		self.program=PROGRAM
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.errorsList=[]
		self.successList=[]
		self.currentName=""
		self.stopNext=False
		
		self._buttons()
		self._labels()
		self._layout()

	def _buttons(self):
		self.button_processList=PGui.QPushButton("Process list")
		self.button_processList.setEnabled(False)
		
		self.button_clear=PGui.QPushButton("Clear output")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_output)
		
		self.button_stopNext=PGui.QPushButton("Stop after current process")
		self.button_stopNext.clicked.connect(self.stop_next)
		self.button_stopNext.setEnabled(False)
		
	def _labels(self):
		self.label_command=PGui.QLabel("<b>Command:</b> "+PROGRAM+" "+" ".join(ARGUMENTS))
		self.label_general=PGui.QLabel("<b>Nothing running</b>")
		self.label_errors=PGui.QLabel("")
		self.label_success=PGui.QLabel("")

	def _layout(self):
		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		self.console_output.setAlignment(PCore.Qt.AlignLeft)
		
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0,1,1)
		grid.addWidget(self.button_clear,0,1,1,1)
		grid.addWidget(self.button_stopNext,1,0,1,1)
		grid.addWidget(self.label_command,2,0,1,2)
		grid.addWidget(self.label_general,3,0,1,2)
		grid.addWidget(self.label_success,4,0,1,2)
		grid.addWidget(self.label_errors,5,0,1,2)
		grid.addWidget(self.console_output,0,2,6,3)
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
		
		self.button_stopNext.setEnabled(True)
		
		self.run_one(prmFileList[0])

	def run_one(self,prmFile):
		print "ProcessManager Here: dealing with prmFile",prmFile
		arguments=[prmFile] + ARGUMENTS
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

	def stop_next(self):
		self.stopNext=True
		self.label_general.setText("<b>Processing file "+str(self.nbFileDone+1)+"/"+str(self.nbFile)+": "+str(self.currentName)+"\n This will be the last file processed </b>")

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
			self.label_general.setText("<b>List done</b>")
			self.button_clear.setEnabled(True)
			self.prmFileList=[]
			self.nbFile=0
			self.nbFileDone=0
			self.currentName=""
			self.process.close()
			self.button_stopNext.setEnabled(False)
		elif self.stopNext:
			print "ProcessManager: stop next"
			self.label_general.setText("<b>List done partially:</b> "+str(self.nbFileDone)+"/"+str(self.nbFile))
			self.button_clear.setEnabled(True)
			self.prmFileList=[]
			self.nbFile=0
			self.nbFileDone=0
			self.currentName=""
			self.process.close()
			self.button_stopNext.setEnabled(False)
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