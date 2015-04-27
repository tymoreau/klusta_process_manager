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
		self.experimentList=[]
		self.stopNext=False
		self.nbCurrent=0
		
		self.isRunning=False
		
		#Process
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
		
		#table
		self.table=PGui.QTableWidget(0,2)
		self.table.setHorizontalHeaderLabels(["File","State"])
		self.table.horizontalHeader().setResizeMode(PGui.QHeaderView.Stretch)
		self.table.setEditTriggers(PGui.QAbstractItemView.NoEditTriggers)
		
		#console
		self.console_output=PGui.QTextEdit()
		self.console_output.setReadOnly(True)
		
		#Layout
		self._buttons()
		self._labels()
		self._layout()


	def _buttons(self):
		self.button_processList=PGui.QPushButton("\n Process list \n")
		self.button_processList.setEnabled(False)
		#connect in application_main.py
		
		self.button_clear=PGui.QPushButton("Clear output")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_output)
		
		self.button_stopNext=PGui.QPushButton("Stop after current file")
		self.button_stopNext.clicked.connect(self.stop_next)
		self.button_stopNext.setEnabled(False)
		
	def _labels(self):
		self.label_command=PGui.QLabel("<b>Command:</b> "+PROGRAM+" "+" ".join(ARGUMENTS))

	def _layout(self):
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_processList,0,0,1,2)
		grid.addWidget(self.button_clear,1,0,1,1)
		grid.addWidget(self.button_stopNext,1,1,1,1)
		grid.addWidget(self.label_command,2,0,1,2)
		grid.addWidget(self.table,3,0,6,2)
		grid.addWidget(self.console_output,0,2,9,2)
		self.setLayout(grid)
		
	def update_table(self):
		self.table.clear()
		self.table.setRowCount(0)
		self.table.setHorizontalHeaderLabels(["File","State"])
		for row in range(len(self.experimentList)):
			self.table.insertRow(row)
			itemFile=PGui.QTableWidgetItem(self.experimentList[row][0])
			itemState=PGui.QTableWidgetItem(self.experimentList[row][2])
			self.table.setItem(row,0,itemFile)
			self.table.setItem(row,1,itemState)
		
		
		
	def feed_list(self,prmFileList):
		for prmFilePath in prmFileList:
			name=prmFilePath.split('/')[-1]
			self.experimentList.append([name,prmFilePath,"to be process"])
			
		if not self.isRunning:
			self.run_one(self.experimentList[self.nbCurrent])
			self.button_stopNext.setEnabled(True)
			
		self.update_table()
		

	def run_one(self,experiment):
		prmFile=experiment[1]
		print "ProcessManager Here: dealing with prmFile",prmFile
		arguments=[prmFile] + ARGUMENTS
		folderPath='/'.join(prmFile.split('/')[:-1])
		self.separator()
		self.process.setWorkingDirectory(folderPath)
		self.process.start(self.program,arguments)
		
		experiment[2]="running"
		self.update_table()

	def separator(self):
		currentName=self.experimentList[self.nbCurrent][0]
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b>'+str(currentName)+'</b> \n'
		sep2='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.console_output.append(sep)
		self.console_output.append(sep1)
		self.console_output.append(sep2)

	def stop_next(self):
		self.stopNext=True
		i=self.nbCurrent+1
		while i<len(self.experimentList):
			self.experimentList[i][2]="(Stop) to be process"
			i+=1
		self.update_table()

	def go_to_next(self,exitcode):
		if exitcode!=0:
			print "ProcessManager Here: exitcode",exitcode
			self.experimentList[self.nbCurrent][2]="klusta crashed"
		else:
			self.experimentList[self.nbCurrent][2]="Done (klusta ran)"
		self.update_table()
		self.nbCurrent+=1
		
		#Go to next
		if not self.stopNext and not self.nbCurrent==len(self.experimentList):
			print "ProcessManager Here: move to next file"
			self.run_one(self.experimentList[self.nbCurrent])
			return
		
		#Or stop
		if self.nbCurrent==len(self.experimentList):
			print "ProcessManager Here: every file was processed"

		if self.stopNext:
			print "ProcessManager: stop next"
			self.stopNext=False

		self.process.close()
		self.button_stopNext.setEnabled(False)
		self.button_clear.setEnabled(True)


	def display_output(self):
		lines=str(self.process.readAll())
		self.console_output.append(lines)
		

	def clear_output(self):
		self.console_output.clear()
		self.button_clear.setEnabled(False)
		self.nbCurrent=0
		self.experimentList=[]
		self.update_table()