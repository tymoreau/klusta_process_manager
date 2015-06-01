
import sys
import signal
 
# Import the core and GUI elements of Qt
import PyQt4.QtCore as PCore
import PyQt4.QtGui as PGui

#Import views
from processManager import ProcessManager
from fileBrowser import FileBrowser

#import parameter
from parameter import *

#Property of the window
WIDTH=1200
HEIGHT=1000
MIN_WIDTH=int(WIDTH*0.75)
MIN_HEIGHT=int(HEIGHT*0.75)
TITLE="FileBrowser + Process Manager"


# Receive message an print them 
class LogView(PGui.QGroupBox):
	
	def __init__(self,parent=None):
		super(LogView,self).__init__(parent)
		
		self.setTitle("Log")
		self.view=PGui.QTextEdit()
		self.view.setReadOnly(True)
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(self.view)
		self.setLayout(hbox)
	
	def add_message(self,message):
		self.view.append(message)



class MainWindow(PGui.QWidget):
	sendsMessage=PCore.pyqtSignal(object)
	
	def __init__(self):
		super(MainWindow,self).__init__()
		
		#Views
		self.fileBrowser=FileBrowser(ROOT)
		self.processManager=ProcessManager(NAS_PATH)
		self.logView=LogView(self)

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


#-------------------------------------------------------------------------------------------------------------------
	#Button_add (green arrow)
	#for each item selected in the treeview, check if it's a folder and add it to the processManager
	def add_to_process_manager(self):
		selection=sorted(self.fileBrowser.tree.selectedIndexes())
		self.sendsMessage.emit("\n******** add to list ")
		for item in selection:
			if item.column()==0:
				name=item.data()
				type=self.fileBrowser.model.type(item)
				if type=='Folder':
					path_folder=self.fileBrowser.model.filePath(item)
					state=self.processManager.add_experiment(path_folder)
					self.sendsMessage.emit("*** "+str(name)+": "+state)
				else:
					self.sendsMessage.emit("*** "+str(name)+": not a folder")
		self.sendsMessage.emit("\n")

#-------------------------------------------------------------------------------------------------------------------


	def closeEvent(self,event):
		self.processManager.close()
		self.close()
		
		#check if is running
		#if self.processManager.isRunning:
			#msgBox = PGui.QMessageBox()
			#msgBox.setText("Closing the app")
			#msgBox.setInformativeText("A process is running, are you sure you want to quit ? The process will be killed")
			#msgBox.setStandardButtons(PGui.QMessageBox.Yes | PGui.QMessageBox.Cancel)
			#msgBox.setDefaultButton(PGui.QMessageBox.Cancel)
			#answer = msgBox.exec_()
			#if answer==PGui.QMessageBox.Cancel:
				#event.ignore()
				#return
		#self.processManager.process.kill()
		#event.accept()


if __name__ == '__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app = PGui.QApplication(sys.argv)
	
	nas=PCore.QDir(NAS_PATH)
	if not nas.exists():
		msgBox=PGui.QMessageBox()
		msgBox.setText("NAS_PATH do not refers to a folder: "+str(NAS_PATH))
		msgBox.exec_()
	else:
		#to be able to close wth ctrl+c
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		
		win=MainWindow()
		win.show()

		sys.exit(app.exec_())

