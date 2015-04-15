import sys
import os 
import signal
 
# Import the core and GUI elements of Qt
import PySide.QtCore as PCore
import PySide.QtGui as PGui

#Import views
from processManager import ProcessManager
from fileBrowser import FileBrowser
from listToProcess import ListToProcess

#Path to your data folder
ROOT='/home/david/dataRat'

#Property of the window
WIDTH=1200
HEIGHT=1000
TITLE="Process Manager"

class MainWindow(PGui.QWidget):
	
	def __init__(self):
		super(MainWindow,self).__init__()
		
		#Views
		self.fileBrowser=FileBrowser(ROOT)
		self.listToProcess=ListToProcess()
		self.processManager=ProcessManager()

		#Connect views
		self.fileBrowser.button_add.clicked.connect(self.add_to_selection)
		self.processManager.button_processList.clicked.connect(self.process_list)
		self.listToProcess.becomesEmpty.connect(lambda: self.processManager.button_processList.setEnabled(False))
		self.listToProcess.becomesFill.connect(lambda: self.processManager.button_processList.setEnabled(True))

		self._layout()
		
	def _layout(self):

		#Create Top splitter
		splitterTop=PGui.QSplitter(PCore.Qt.Horizontal)
		splitterTop.setMinimumSize(WIDTH/2,HEIGHT)
		splitterTop.setChildrenCollapsible(False)
		
		#Add the treeview and the selection list
		splitterTop.addWidget(self.fileBrowser)
		splitterTop.addWidget(self.listToProcess)
		splitterTop.setMinimumSize(WIDTH,HEIGHT/2)

		#Add buttons in the handle of the top splitter
		#splitterTop.setHandleWidth(50)
		#vboxButton=QVBoxLayout()
		#splitterTop.handle(1).setLayout(vboxButton)
		
		#Create Vertical Splitter, with the top splitter and bottom pannel
		splitterVertical=PGui.QSplitter(PCore.Qt.Vertical)
		splitterVertical.addWidget(splitterTop)
		splitterVertical.addWidget(self.processManager)
		splitterVertical.setChildrenCollapsible(False)
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(splitterVertical)
		
		self.setLayout(hbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle(TITLE)

	def add_to_selection(self):
		string_toAdd=[]
		selection=sorted(self.fileBrowser.tree.selectedIndexes())
		for item in selection:
			if item.column()==0:
				name=item.data()
				#size=item.sibling(item.row(),1).data()
				#type=item.sibling(item.row(),2).data()
				type=self.fileBrowser.model.type(item)
				if type=='Folder':
					path=self.fileBrowser.model.filePath(item)
					for filename in os.listdir(path):
						if filename.endswith('.prm'):
							string_toAdd.append(path+'/'+filename)
							break
				elif name.endswith(".prm"):
					path=self.fileBrowser.model.filePath(item)
					string_toAdd.append(path)
			
		newString=list(set(self.listToProcess.model.stringList()).union(set(string_toAdd)))
		newString=sorted(newString, key=lambda s: s.lower())
		self.listToProcess.model.setStringList(newString)
		#self.fileBrowser.tree.clearSelection()
		if len(newString)!=0:
			self.listToProcess.button_save_txt.setEnabled(True)
			self.listToProcess.button_clear.setEnabled(True)
			self.processManager.button_processList.setEnabled(True)

	def process_list(self):
		list=self.listToProcess.model.stringList()
		self.processManager.feed_list(list)


if __name__ == '__main__':
	PGui.QApplication.setStyle("cleanlooks")
	
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()
	win.show()

	sys.exit(app.exec_())

