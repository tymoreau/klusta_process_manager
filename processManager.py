#Process Manager

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet

import sys
import signal

#Model
from experimentModel import ExperimentModel,Experiment

SEPARATOR='---'*15

#Command to perform on list
PROGRAM="klusta"
ARGUMENTS=["--overwrite"]

#Connection to remote computer
IP="10.51.101.29"
HOST=PNet.QHostAddress(IP) 
PORT=8000


class ProcessManager(PGui.QWidget):

	def __init__(self):
		super(ProcessManager,self).__init__()
		
		#experimentModel
		self.model=ExperimentModel()
		self.tableView=PGui.QTableView()
		self.tableView.setModel(self.model)
		self.tableView.horizontalHeader().setResizeMode(PGui.QHeaderView.Stretch)
		
		#console output
		self.console=PGui.QTextEdit()
		self.console.setReadOnly(True)
		
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
		self.process.setEnvironment(env)
		
		#Layout
		self._edits()
		self._buttons()
		self._layout()
		
		
	def _edits(self):
		self.label_ip=PGui.QLabel("IP")
		self.edit_ip=PGui.QLineEdit(IP)
		
		self.label_port=PGui.QLabel("Port")
		self.edit_port=PGui.QLineEdit(str(PORT))
		self.edit_port.setValidator(PGui.QIntValidator(1,65535,self))
		

	def _buttons(self):
		#process here
		self.button_processHere=PGui.QPushButton("\nProcess here\n")
		self.button_processHere.clicked.connect(self.process_here)
		
		#process on server
		self.button_connectServer=PGui.QPushButton("\nConnect to server\n")
		self.button_processServer=PGui.QPushButton("\nProcess on server\n")
		
		#on a selection
		self.button_cancel=PGui.QPushButton("Cancel")
		self.button_cancel.clicked.connect(self.cancel)
		self.button_remove=PGui.QPushButton("Remove/Kill")
		self.button_remove.clicked.connect(self.remove)
		self.button_restart=PGui.QPushButton("Restart")
		
		#on everything
		self.button_clear=PGui.QPushButton("Clear")
		self.button_save=PGui.QPushButton("Save list")
		self.button_load=PGui.QPushButton("Load list")

	def _layout(self):
		frame_selection=PGui.QGroupBox("On selection")
		vbox_selection=PGui.QVBoxLayout()
		
		vbox_selection.addWidget(self.button_processHere)
		
		vbox_selection.addWidget(self.button_cancel)
		vbox_selection.addWidget(self.button_remove)
		vbox_selection.addWidget(self.button_restart)
		frame_selection.setLayout(vbox_selection)
		
		frame_server=PGui.QGroupBox("Server")
		vbox_server=PGui.QVBoxLayout()
		vbox_server.addWidget(self.label_ip)
		vbox_server.addWidget(self.edit_ip)
		vbox_server.addWidget(self.label_port)
		vbox_server.addWidget(self.edit_port)
		vbox_server.addWidget(self.button_connectServer)
		frame_server.setLayout(vbox_server)
		
		hbox_everything=PGui.QHBoxLayout()
		hbox_everything.addWidget(self.button_clear)
		hbox_everything.addWidget(self.button_save)
		hbox_everything.addWidget(self.button_load)
		
		vbox1=PGui.QVBoxLayout()
		vbox1.addWidget(self.tableView)
		vbox1.addLayout(hbox_everything)
		
		vbox2=PGui.QVBoxLayout()
		vbox2.addWidget(frame_server)
		vbox2.addWidget(frame_selection,2)
	
		hbox=PGui.QHBoxLayout()
		hbox.addLayout(vbox1,2)
		hbox.addLayout(vbox2)
		hbox.addWidget(self.console,2)
		self.setLayout(hbox)
		
		
	def add_experiment(self,experiment):
		self.model.add_experiment(experiment)
		
		
	#user click on Process Here: 
	# -update status of experiments "ready to be process" -> "waiting to be process"
	# -if klusta not already running, starts klusta
	def process_here(self):
		self.model.selectionUpdate_process_here()
		if not self.isRunning:
			if self.model.get_first_to_process():
				self.run_one()
				
	#user click cancel: 
	#"waiting to be process" -> None
	def cancel(self):
		self.model.selectionUpdate_cancel()
		
	def remove(self):
		self.model.selectionUpdate_remove()
			
	#run klusta on one experiment
	def run_one(self):
		if self.model.currentExperiment!=None:
			path_prmFile=self.model.currentExperiment.prmFile
			name_prmFile=path_prmFile.split('/')[-1]
			path_folder=self.model.currentExperiment.folder
			arguments=[name_prmFile]+ARGUMENTS
		
			print "Working directory:",path_folder
			print "Do: ",PROGRAM," ".join(arguments)
		
			self.separator()
			self.process.setWorkingDirectory(path_folder)
			self.process.start(PROGRAM,arguments)
		
	#when the current process finish, this function is activate
	#process an other experiment or stop
	def go_to_next(self,exitcode):
		#update experiment
		self.model.currentExperiment_done(exitcode)
		
		#find another experiment to process
		if self.model.get_first_to_process():
			self.run_one()
		#or stop
		else:
			self.process.close()

	#print a separator on the console view
	def separator(self):
		currentName=self.model.currentExperiment.name
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b> Experiment: '+str(currentName)+'</b> \n'
		sep2='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.console.append(sep)
		self.console.append(sep1)
		self.console.append(sep2)

	#print output of the console in the console view
	def display_output(self):
		lines=str(self.process.readAll())
		self.console.append(lines)



if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	
	#Test Experiments
	exp1=Experiment("Rat034_small",prmFile="/home/david/dataRat/Rat034_small/Rat034_small.prm")
	exp2=Experiment("Rat034_small_number2",prmFile="/home/david/dataRat/Rat034_small_number2/Rat034_small_number2.prm")
	
	
	win=ProcessManager()
	
	win.model.add_experiment(exp1)
	win.model.add_experiment(exp2)
	
	
	win.setMinimumSize(900,600)

	win.show()

	sys.exit(app.exec_())
