#Class to process a list of experiment in klusta
#Buttons to launch klusta on list
#View progress

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import sys
import signal

#is start alone, will process LIST
LIST=["/home/david/Documents/app_1.0/testRatfolder/testRatfolder.prm","/home/david/Documents/app_1.0/testRatfolder/testRatfolder.prm"]


class ProcessManager(PGui.QGroupBox):

	def __init__(self):
		super(ProcessManager,self).__init__()
		
		self.setTitle("Process Manager")
		
		self.program="klusta"
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.process=PCore.QProcess()
		
		self._buttons()
		self._labels()
		self._layout()
		
		self.process.finished.connect(self.go_to_next)
		self.process.readyReadStandardOutput.connect(self.display_output)
		
	def _buttons(self):
		self.button_processList=PGui.QPushButton("Process list here \n")
		self.button_processList.setEnabled(False)
		self.button_processListRemote=PGui.QPushButton("Process list \n on remote computer")
		self.button_processListRemote.setEnabled(False)
		
	def _labels(self):
		self.label_general=PGui.QLabel("Nothing running")
		self.label_currentProcess=PGui.QLabel("")
		self.label_warning=PGui.QLabel("")
		
	def _layout(self):
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0)
		grid.addWidget(self.button_processListRemote,0,1)
		grid.addWidget(self.label_general,1,0,1,2)
		grid.addWidget(self.label_currentProcess,2,0,2,2)
		grid.addWidget(self.label_warning,3,0,2,2)
		self.setLayout(grid)
		
	def feed_list(self,prmFileList):
		self.prmFileList=prmFileList
		self.nbFile=len(prmFileList)
		self.label_general.setText("Start processing list ("+str(self.nbFile)+" files)")
		self.run_one(prmFileList[0])
		
	def run_one(self,prmFile):
		print "ProcessManager: dealing with prmFile",prmFile
		arguments=[prmFile,"--overwrite","--detect-only"]
		path='/'.join(prmFile.split('/')[:-1])
		
		#dealing with the klusta environment
		env = PCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)

		self.process.setEnvironment(env)
		self.process.setWorkingDirectory(path)
		self.process.start(self.program,arguments)
		
		self.label_general.setText("Processing file "+str(self.nbFileDone+1)+"/"+str(self.nbFile))

	def go_to_next(self,exitcode):
		if exitcode!=0:
			print "ProcessManager: exitcode",exitcode
			self.label_warning.setText("Could not process correctly file: \n"+str(self.prmFileList[self.nbFileDone]))
		
		self.nbFileDone+=1
		
		if self.nbFile==self.nbFileDone:
			print "ProcessManager: every file was processed"
			self.label_general.setText("List done")
			self.label_currentProcess.setText("")
			self.clear()
		else:
			self.run_one(self.prmFileList[self.nbFileDone])
			
	def display_output(self):
		line=self.process.readLine(1024)
		self.label_currentProcess.setText(str(line))
		
	def clear(self):
		self.prmFileList=[]
		self.nbFile=0
		self.nbFileDone=0
		self.process.close()
		#self.process=PCore.QProcess()


if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=ProcessManager()
	win.setMinimumSize(600,200)
	win.feed_list(LIST)
	win.show()

	sys.exit(app.exec_())
