import sys
import os 
import signal
 
# Import the core and GUI elements of Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui

#Import views
from processManager import ProcessManager
from fileBrowser import FileBrowser
from experimentModel import ExperimentModel, Experiment

#Path to your data folder
ROOT='./test'

#Property of the window
WIDTH=1200
HEIGHT=1000
MIN_WIDTH=int(WIDTH*0.75)
MIN_HEIGHT=int(HEIGHT*0.75)
TITLE="FileBrowser + Process Manager"


class LogView(PGui.QGroupBox):
	
	def __init__(self):
		super(LogView,self).__init__()
		
		self.setTitle("Log")
		self.view=PGui.QTextEdit()
		self.view.setReadOnly(True)
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(self.view)
		self.setLayout(hbox)
	
	def add_message(self,message):
		self.view.append(message)


class MainWindow(PGui.QWidget):
	sendsMessage=PCore.Signal(object)
	
	def __init__(self):
		super(MainWindow,self).__init__()
		
		#Views
		self.fileBrowser=FileBrowser(ROOT)
		self.processManager=ProcessManager()
		self.logView=LogView()

		#Connect views
		self.fileBrowser.button_add.clicked.connect(self.add_to_process_manager)

		#Connect message to log
		self.fileBrowser.sendsMessage.connect(self.logView.add_message)
		self.processManager.sendsMessage.connect(self.logView.add_message)
		self.sendsMessage.connect(self.logView.add_message)

		#Layout
		self._layout()
		
	def _layout(self):

		#Create Top splitter
		splitterTop=PGui.QSplitter(PCore.Qt.Horizontal)
		splitterTop.setMinimumSize(WIDTH/2,HEIGHT)
		splitterTop.setChildrenCollapsible(False)
		
		#Add the treeview and the selection list
		splitterTop.addWidget(self.fileBrowser)
		splitterTop.addWidget(self.logView)
		splitterTop.setMinimumSize(MIN_WIDTH,int(MIN_HEIGHT/2))

		#Add buttons in the handle of the top splitter
		#splitterTop.setHandleWidth(50)
		#vboxButton=QVBoxLayout()
		#splitterTop.handle(1).setLayout(vboxButton)
		
		#Create Vertical Splitter, with the top splitter and bottom pannel
		splitterVertical=PGui.QSplitter(PCore.Qt.Vertical)
		splitterVertical.addWidget(splitterTop)
		splitterVertical.addWidget(self.processManager)
		splitterVertical.setChildrenCollapsible(False)
		self.processManager.setMinimumSize(MIN_WIDTH,int(MIN_HEIGHT/2))
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(splitterVertical)
		
		self.setLayout(hbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle(TITLE)


	#Convert selection of tree view into Experiment object to add to experimentModel
	def add_to_process_manager(self):
		selection=sorted(self.fileBrowser.tree.selectedIndexes())
		self.sendsMessage.emit("\n******** add to list ")
		for item in selection:
			if item.column()==0:
				name=item.data()
				type=self.fileBrowser.model.type(item)
				if type=='Folder':
					path_folder=self.fileBrowser.model.filePath(item)
					name_prmFile=""
					for filename in os.listdir(path_folder):
						if filename.endswith('.prm'):
							name_prmFile=filename
							self.check_prm_file(path_folder,name_prmFile,name)
							break
					if name_prmFile=="":
						self.sendsMessage.emit("*** "+str(name)+": do not have a prm file")
				else:
					self.sendsMessage.emit("*** "+str(name)+": not a folder")


	#Check if we should be able to process the prmfile
	def check_prm_file(self,path_folder,name_prmFile,name):
		path_prmFile=path_folder+"/"+name_prmFile
		with open(path_prmFile,'r') as fPRM:
			nbFound=0
			for line in fPRM.readlines():
				if line.startswith("experiment_name"):
					experiment_name=line.split("=")[-1].strip()[1:-1]
					nbFound+=1
				elif line.startswith("raw_data_files"):
					data_name=line.split("=")[-1].strip()[1:-1]
					nbFound+=1
				elif line.startswith("prb_file"):
					prb_name=line.split("=")[-1].strip()[1:-1]
					nbFound+=1
				if nbFound>=3:
					break
			#check if we found everything
			if nbFound<3:
				self.sendsMessage.emit("*** "+str(name)+": prmFile is incorrect")
				return False
			#experiment name has to match folder name
			if experiment_name!=name:
				self.sendsMessage.emit("*** "+str(name)+": experiment name don't match folder name")
				return False
			#check if the raw data and prb file are in the folder
			listFile=os.listdir(path_folder)
			if (data_name not in listFile) or (prb_name not in listFile):
				self.sendsMessage.emit("*** "+str(name)+": could not find raw data or PRB file in folder")
				return False
			
			#if everything is ok
			experiment=Experiment(name=experiment_name,prmFile=path_prmFile,rawData=data_name,prb=prb_name)
			if not self.processManager.add_experiment(experiment):
				self.sendsMessage.emit("*** "+str(name)+": already in list")
				del experiment
				return False
			else:
				self.sendsMessage.emit("*** "+str(name)+": added to list")
				return True
			

						
				
		#string_toAdd=[]
		#selection=sorted(self.fileBrowser.tree.selectedIndexes())
		#for item in selection:
			#if item.column()==0:
				#name=item.data()
				##size=item.sibling(item.row(),1).data()
				##type=item.sibling(item.row(),2).data()
				#type=self.fileBrowser.model.type(item)
				#if type=='Folder':
					#path=self.fileBrowser.model.filePath(item)
					#for filename in os.listdir(path):
						#if filename.endswith('.prm'):
							#string_toAdd.append(path+'/'+filename)
							#break
				#elif name.endswith(".prm"):
					#path=self.fileBrowser.model.filePath(item)
					#string_toAdd.append(path)
			
		#if string_toAdd:
			#currentString=self.listToProcess.model.stringList()
			#newString=list(set(currentString).union(set(string_toAdd)))
			#newFiles=len(newString)-len(currentString)
			#if newFiles!=0:
				#newString=sorted(newString, key=lambda s: s.lower())
				#self.listToProcess.model.setStringList(newString)
				#self.listToProcess.button_save_txt.setEnabled(True)
				#self.listToProcess.button_clear.setEnabled(True)
				#self.listToProcess.becomesFill.emit()
				#self.sendsMessage.emit("Added "+str(newFiles)+" file(s)")
			#else:
				#self.sendsMessage.emit("Nothing new to add")
		#else:
			#self.sendsMessage.emit("No PRM files to add")
				


if __name__ == '__main__':
	PGui.QApplication.setStyle("cleanlooks")
	
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()
	win.show()

	sys.exit(app.exec_())

