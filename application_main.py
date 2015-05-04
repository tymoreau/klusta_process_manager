#! /home/david/anaconda/bin/python
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
ROOT='/home/david/dataRat/'

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
		
		#read save
		self.read_save()
		
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


#-------------------------------------------------------------------------------------------------------------------
	#for each item selected in the treeview, check if it's a folder name
	def add_to_process_manager(self):
		selection=sorted(self.fileBrowser.tree.selectedIndexes())
		self.sendsMessage.emit("\n******** add to list ")
		for item in selection:
			if item.column()==0:
				name=item.data()
				type=self.fileBrowser.model.type(item)
				if type=='Folder':
					path_folder=self.fileBrowser.model.filePath(item)
					self.look_for_prm(path_folder,name)
				else:
					self.sendsMessage.emit("*** "+str(name)+": not a folder")
					
	#look for a prm file and try to add the experiment to processManager
	def look_for_prm(self,path_folder,name):
		for filename in os.listdir(path_folder):
			if filename.endswith('.prm'):
				if self.processManager.add_experiment(path_folder+'/'+filename):
					self.sendsMessage.emit("*** "+str(name)+": added")
				else:
					self.sendsMessage.emit("*** "+str(name)+": already in list")
				return
		self.sendsMessage.emit("*** "+str(name)+": do not have a prm file")
#-------------------------------------------------------------------------------------------------------------------


			

	def closeEvent(self,event):
		#check if is running
		if self.processManager.isRunning:
			msgBox = PGui.QMessageBox()
			msgBox.setText("Closing the app")
			msgBox.setInformativeText("A process is running, are you sure you want to quit ? The process will be killed")
			msgBox.setStandardButtons(PGui.QMessageBox.Yes | PGui.QMessageBox.Cancel)
			msgBox.setDefaultButton(PGui.QMessageBox.Cancel)
			answer = msgBox.exec_()
			if answer==PGui.QMessageBox.Cancel:
				event.ignore()
				return
		self.save()
		event.accept()
				
	def save(self):
		with open("save.txt","w") as f:
			self.processManager.save(f)
			
	
	def read_save(self):
		try :
			f=open("save.txt","r")
			self.processManager.read_save(f)
			f.close()
		except IOError:
			pass
			
		


if __name__ == '__main__':
	PGui.QApplication.setStyle("cleanlooks")
	
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()
	win.show()

	sys.exit(app.exec_())

