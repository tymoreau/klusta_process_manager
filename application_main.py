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
ROOT='/home/david/dataRat'

#Property of the window
WIDTH=1200
HEIGHT=1000
MIN_WIDTH=int(WIDTH*0.75)
MIN_HEIGHT=int(HEIGHT*0.75)
TITLE="Process Manager"


class LogView(PGui.QGroupBox):
	
	def __init__(self):
		super(LogView,self).__init__()
		
		self.setTitle("Log")
		self.label=PGui.QLabel("")
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(self.label)
		self.setLayout(hbox)


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
		#self.processManager.tabHere.button_processList.clicked.connect(self.process_list_here)
		#self.listToProcess.becomesEmpty.connect(lambda: self.processManager.tabHere.button_processList.setEnabled(False))
		#self.listToProcess.becomesFill.connect(lambda: self.processManager.tabHere.button_processList.setEnabled(True))
		
		#Connect message to log
		#self.listToProcess.sendsMessage.connect(self.logView.label.setText)
		self.fileBrowser.sendsMessage.connect(self.logView.label.setText)
		self.sendsMessage.connect(self.logView.label.setText)

		#Layout
		self._layout()
		
	def _layout(self):

		#Create Top splitter
		splitterTop=PGui.QSplitter(PCore.Qt.Horizontal)
		splitterTop.setMinimumSize(WIDTH/2,HEIGHT)
		splitterTop.setChildrenCollapsible(False)
		
		#Add the treeview and the selection list
		splitterTop.addWidget(self.fileBrowser)
		#splitterTop.addWidget(self.logView)
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
		pass
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

