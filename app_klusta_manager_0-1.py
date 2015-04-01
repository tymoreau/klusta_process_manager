# Allow access to command-line arguments
import sys
import os 
import signal
import IPython
import run_klusta_batch as run
 
# Import the core and GUI elements of Qt
from PySide.QtCore import *
from PySide.QtGui import *

TXTname="list_prm_file.txt"

class SelectionView():
	
	def __init__(self,parent):
		#super(SelectionView,self).__init__()
		
		self.root='/home/david/dataRat'
		
		self._tree(parent)
		self._list(parent)
		
		self.button_add=QPushButton("Add to \n list",parent)
		self.button_add.clicked.connect(self.add_to_selection)
		
	def _tree(self,parent):
		self.model=QFileSystemModel(parent)
		self.model.setRootPath(self.root)
		
		self.tree=QTreeView(parent)
		self.tree.setModel(self.model)
		self.tree.setRootIndex(self.model.index(self.root))

		self.tree.setHeader(self.tree.header().setResizeMode(0,QHeaderView.ResizeToContents))
		self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
		
		self.button_prm=QPushButton("Create prm and prb files",parent)
		#self.button_prm.clicked.connect(self.)

	def _list(self,parent):
		self.selectionModel=QStringListModel(parent)
		self.selectionList=QListView(parent)
		self.selectionList.setModel(self.selectionModel)
		self.selectionList.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.selectionList.setEditTriggers(QAbstractItemView.NoEditTriggers)
		
		self.button_remove=QPushButton("Remove from list",parent)
		self.button_remove.clicked.connect(self.remove_from_selection)
		
		self.button_clear=QPushButton("Clear list",parent)
		self.button_clear.clicked.connect(self.clear_list)
		
		self.button_createTxt=QPushButton("Create txt",parent)
		self.button_createTxt.clicked.connect(self.create_txt)
		
	def add_to_selection(self):
		string_toAdd=[]
		
		selection=sorted(self.tree.selectedIndexes()) #ordered by row then column
		for i in range(0,len(selection),4):
			name=selection[i].data()
			size=selection[i+1].data()
			type=selection[i+2].data()
			if type=='folder':
				pass #search for prm
			elif name.endswith(".prm"):
				path=self.model.filePath(selection[i])
				string_toAdd.append(path)
			
		newString=list(set(self.selectionModel.stringList()).union(set(string_toAdd)))
		newString=sorted(newString, key=lambda s: s.lower())
		self.selectionModel.setStringList(newString)
		self.tree.clearSelection()
		
	def remove_from_selection(self):
		selection=self.selectionList.selectedIndexes()
		string_toRemove=[]
		for item in selection:
			string_toRemove.append(item.data())
			
		newString=list(set(self.selectionModel.stringList())-set(string_toRemove))
		newString=sorted(newString, key=lambda s: s.lower())
		self.selectionModel.setStringList(newString)
		self.selectionList.clearSelection()

	def clear_list(self):
		self.selectionModel.setStringList([])
		self.selectionList.clearSelection()
		
	def create_txt(self):
		list=self.selectionModel.stringList()
		msgbox=QMessageBox()
		if len(list)!=0:
			output=open(TXTname,"w")
			for line in list:
				output.write(line+"\n")
			output.close()
			msgbox.setText("List has been saved under the name "+TXTname)
		else:
			msgbox.setText("The list is empty, nothing saved")
		msgbox.exec_()


class MainWindow(QWidget):
	
	def __init__(self):
		super(MainWindow,self).__init__()
		width=800
		height=600
		
		self.selectionview=SelectionView(self)
		self.selectionview.tree.setMinimumSize(width/3,height/2)
		self.selectionview.selectionList.setMinimumSize(width/3,height/2)

		self.logview=QFrame(self)
		button_klusta=QPushButton("Run Klusta on txt")
		button_klusta.clicked.connect(self.run_klusta)
		hboxButton=QHBoxLayout()
		hboxButton.addWidget(button_klusta)
		self.logview.setLayout(hboxButton)

		#Create Top splitter
		splitterTop=QSplitter(Qt.Horizontal)
		splitterTop.setMinimumSize(width/2,height)
		splitterTop.setChildrenCollapsible(False)
		
		#Add the treeview and the selection list with their corresponding buttons
		splitterTop.addWidget(self.frame_treeview())
		splitterTop.addWidget(self.frame_selectionList())

		#Add buttons in the handle of the top splitter
		splitterTop.setHandleWidth(100)
		vboxButton=QVBoxLayout()
		vboxButton.addWidget(self.selectionview.button_add)
		splitterTop.handle(1).setLayout(vboxButton)
		
		#Create Vertical Splitter, with the top splitter inside
		splitterVertical=QSplitter(Qt.Vertical)
		splitterVertical.addWidget(splitterTop)
		splitterVertical.addWidget(self.logview)
		splitterVertical.setChildrenCollapsible(False)
		
		hbox=QHBoxLayout()
		hbox.addWidget(splitterVertical)
		
		self.setLayout(hbox)
		self.setMinimumSize(width,height)
		self.setWindowTitle("Klusta Selection Manager")
		self.show()
		
	def frame_selectionList(self):
		frame=QFrame()
		hboxButton=QHBoxLayout()
		hboxButton.addWidget(self.selectionview.button_remove)
		hboxButton.addWidget(self.selectionview.button_clear)
		hboxButton.addWidget(self.selectionview.button_createTxt)
		vbox=QVBoxLayout()
		vbox.addWidget(self.selectionview.selectionList)
		vbox.addLayout(hboxButton)
		frame.setLayout(vbox)
		return frame
	
	def frame_treeview(self):
		frame=QFrame()
		hboxButton=QHBoxLayout()
		hboxButton.addWidget(self.selectionview.button_prm)
		vbox=QVBoxLayout()
		vbox.addWidget(self.selectionview.tree)
		vbox.addLayout(hboxButton)
		frame.setLayout(vbox)
		return frame

	def run_klusta(self):
		run.run(TXTname)
		



if __name__ == '__main__':
	QApplication.setStyle("cleanlooks")
	app = QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()

	sys.exit(app.exec_())

