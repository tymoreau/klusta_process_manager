# Allow access to command-line arguments
import sys
import os 
import signal
import IPython
import run_klusta_batch as run
 
# Import the core and GUI elements of Qt
from PySide.QtCore import *
from PySide.QtGui import *

ROOT='/home/david/dataRat'

class FileBrowser(QGroupBox):
	
	def __init__(self):
		super(FileBrowser,self).__init__()
		
		self.root=ROOT
		self.setTitle(self.root)
		
		self.prbModel=0
		self.prmModel=0
		
		self._model()
		self._tree()
		self._buttons()
		self._layout()
		
		self.tree.connect(self.tree.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)
		
	def _buttons(self):
		self.button_prm=QPushButton("Create prm and prb files \n in selected folders")
		self.button_prm.clicked.connect(self.create_prm_prb)
		self.button_prm.setEnabled(False)
		
		self.button_loadPRB=QPushButton("Load PRB model")
		self.button_loadPRB.clicked.connect(self.load_PRB)
		self.label_PRB=QLabel("No PRB model                                    ")
		
		self.button_loadPRM=QPushButton("Load PRM model")
		self.button_loadPRM.clicked.connect(self.load_PRM)
		self.label_PRM=QLabel("No PRM model")
		
		self.button_add=QPushButton("Add selection \n to list")
		self.button_add.setEnabled(False)
		
	def _model(self):
		self.model=QFileSystemModel(self)
		self.model.setRootPath(self.root)
		
	def _tree(self):
		self.tree=QTreeView(self)
		self.tree.setModel(self.model)
		self.tree.setRootIndex(self.model.index(self.root))

		self.tree.setHeader(self.tree.header().setResizeMode(0,QHeaderView.ResizeToContents))
		self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)
		
	def _layout(self):
		grid=QGridLayout()
		grid.addWidget(self.button_loadPRM,0,0)
		grid.addWidget(self.label_PRM,0,1)
		grid.addWidget(self.button_loadPRB,1,0)
		grid.addWidget(self.label_PRB,1,1)
		
		hbox=QHBoxLayout()
		hbox.addLayout(grid)
		hbox.addWidget(self.button_prm)
		hbox.addWidget(self.button_add)
		
		vbox=QVBoxLayout()
		vbox.addWidget(self.tree)
		vbox.addLayout(hbox)
		self.setLayout(vbox)
	
	def load_PRB(self):
		filebox=QFileDialog(self,"Load model for PRB file")
		filebox.setFileMode(QFileDialog.AnyFile)
		filebox.setNameFilter("PRB (*.prb)")
		if filebox.exec_():
			self.prbModel=filebox.selectedFiles()[0]
			self.label_PRB.setText(self.prbModel)
			if len(self.tree.selectedIndexes())!=0 and self.prmModel!=0:
				self.button_prm.setEnabled(True)
			
	def load_PRM(self):
		filebox=QFileDialog(self,"Load model for PRM file")
		filebox.setFileMode(QFileDialog.AnyFile)
		filebox.setNameFilter("PRM (*.prm)")
		if filebox.exec_():
			self.prmModel=filebox.selectedFiles()[0]
			self.label_PRM.setText(self.prmModel)
			if len(self.tree.selectedIndexes())!=0 and self.prbModel!=0:
				self.button_prm.setEnabled(True)

	def create_prm_prb(self):
		if self.prmModel==0 or self.prbModel==0:
			msgbox=QMessageBox()
			msgbox.setText("Can't do : missing a PRB or PRM model")
			msgbox.exec_()
		else:
			selection=self.tree.selectedIndexes()
			for item in selection:
				if item.column()==0 and item.sibling(item.row(),2).data()=='Folder':
					path=self.model.filePath(item)
					baseName=item.data()
					prbName=path+"/"+baseName+".prb"
					prmName=path+"/"+baseName+".prm"
					dataName=baseName+".raw.kwd"
					
					if dataName not in os.listdir(path):
						dataName=baseName+'.dat'
						if dataName not in os.listdir(path):
							print "no raw data for folder",baseName
							continue #to the next item in selection
					dataName=path+"/"+dataName

					os.system('cp '+self.prbModel+" "+prbName)
					os.system('cp '+self.prmModel+" "+prmName)
				
					with open(prmName,"r+") as fPRM:
						outputPRM=[]
						for line in fPRM.readlines():
							if line.startswith("experiment_name"):
								line="experiment_name = '"+baseName+"'"
							elif line.startswith("raw_data_files"):
								line="raw_data_files = '"+dataName+"'"
							elif line.startswith("prb_file"):
								line="prb_file = '"+prbName+"'"
							outputPRM.append(line)
						fPRM.seek(0)
						fPRM.write(''.join(outputPRM))
						fPRM.truncate()

	def on_selection_change(self,selected,deselected):
		if len(self.tree.selectedIndexes())!=0:
			self.button_add.setEnabled(True)
			if self.prmModel!=0 and self.prbModel!=0:
				self.button_prm.setEnabled(True)
		else:
			self.button_prm.setEnabled(False)

class ListToProcess(QGroupBox):
	
	def __init__(self):
		super(ListToProcess,self).__init__()
		
		self.setTitle("List of parameter files")
		self._model()
		self._view()
		self._buttons()
		self._layout()
		
		self.view.connect(self.view.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)
		
	def _model(self):
		self.model=QStringListModel(self)

	def _view(self):
		self.view=QListView(self)
		self.view.setModel(self.model)
		self.view.setSelectionMode(QAbstractItemView.ExtendedSelection)
		self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
		
	def _buttons(self):
		self.button_remove=QPushButton("Remove from list")
		self.button_remove.setEnabled(False)
		self.button_remove.clicked.connect(self.remove_from_selection)
		
		self.button_clear=QPushButton("Clear list")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_list)
		
		self.button_save_txt=QPushButton("Save list")
		self.button_save_txt.setEnabled(False)
		self.button_save_txt.clicked.connect(self.save_txt)
		
		self.button_klusta=QPushButton("Run Klusta on list above")
		self.button_klusta.setEnabled(False)
		self.button_klusta.clicked.connect(self.run_klusta)
		self.label_klusta=QLabel("Nothing running ")
		
		self.button_load_txt=QPushButton("Load list")
		self.button_load_txt.clicked.connect(self.load_txt)
		self.label_txt=QLabel("No list")

	def _layout(self):
		hboxButton=QHBoxLayout()
		hboxButton.addWidget(self.button_remove)
		hboxButton.addWidget(self.button_clear)
		hboxButton.addWidget(self.button_save_txt)
		hboxButton.addWidget(self.button_load_txt)
		
		vbox=QVBoxLayout()
		vbox.addLayout(hboxButton)
		vbox.addWidget(self.view)
		vbox.addWidget(self.button_klusta)
		vbox.addWidget(self.label_klusta)
		self.setLayout(vbox)

	def on_selection_change(self,selected,deselected):
		if len(self.view.selectedIndexes())!=0:
			self.button_remove.setEnabled(True)
		else:
			self.button_remove.setEnabled(False)

	def remove_from_selection(self):
		selection=self.view.selectedIndexes()
		string_toRemove=[]
		for item in selection:
			string_toRemove.append(item.data())
		newString=list(set(self.model.stringList())-set(string_toRemove))
		newString=sorted(newString, key=lambda s: s.lower())
		self.model.setStringList(newString)
		self.view.clearSelection()
		self.button_remove.setEnabled(False)
		if len(newString)==0:
			self.button_save_txt.setEnabled(False)
			self.button_clear.setEnabled(False)

	def clear_list(self):
		self.model.setStringList([])
		self.view.clearSelection()
		self.button_remove.setEnabled(False)
		self.button_save_txt.setEnabled(False)
		self.button_clear.setEnabled(False)
		
	def save_txt(self):
		list=self.model.stringList()
		if len(list)!=0:
			filebox=QFileDialog(self,"Save list")
			filebox.setFileMode(QFileDialog.AnyFile)
			filebox.setNameFilter("Text (*.txt)")
			filebox.setAcceptMode(QFileDialog.AcceptSave)
			if filebox.exec_():
				outputname=filebox.selectedFiles()[0]
				output=open(outputname,"w")
				for line in list:
					output.write(line+"\n")
				output.close()
		else:
			msgbox=QMessageBox()
			msgbox.setText("The list is empty, nothing to save")
			msgbox.exec_()

	def run_klusta(self):
		reply = QMessageBox.question(self,'Message','Did you activate the klusta environment ? ', QMessageBox.Yes| QMessageBox.No)
		
		if reply==QMessageBox.Yes:
			list=self.model.stringList()
			self.label_klusta.setText("Start processing")
			self.label_klusta.repaint()
			
			for prmFile in list:
				self.label_klusta.setText("Processing "+prmFile)
				self.label_klusta.repaint()
				QApplication.processEvents()
				run.run_one_file(prmFile)
			self.label_klusta.setText("List has been processed")
		else:
			msgbox=QMessageBox()
			msgbox.setText("Quit the app, do 'source activate klusta' and restart. \n You can save your list before")
			msgbox.exec_()

		
	def load_txt(self):
		filebox=QFileDialog(self,"Load list of parameter files")
		filebox.setFileMode(QFileDialog.AnyFile)
		filebox.setNameFilter("Text (*.txt)")
		if filebox.exec_():
			newList=open(filebox.selectedFiles()[0]).readlines()
			self.model.setStringList([line.rstrip() for line in newList])
			self.button_klusta.setEnabled(True)
			self.button_clear.setEnabled(True)
			self.button_save_txt.setEnabled(True)


class MainWindow(QWidget):
	
	def __init__(self):
		super(MainWindow,self).__init__()
		width=1200
		height=1000
		
		self.fileBrowser=FileBrowser()
		self.listToProcess=ListToProcess()

		#add button
		self.fileBrowser.button_add.clicked.connect(self.add_to_selection)
		
		#Bottom pannel
		self.logview=QFrame(self)
		hboxButton=QHBoxLayout()
		self.logview.setLayout(hboxButton)

		#Create Top splitter
		splitterTop=QSplitter(Qt.Horizontal)
		splitterTop.setMinimumSize(width/2,height)
		splitterTop.setChildrenCollapsible(False)
		
		#Add the treeview and the selection list with their corresponding buttons
		splitterTop.addWidget(self.fileBrowser)
		splitterTop.addWidget(self.listToProcess)
		splitterTop.setMinimumSize(width,height/2)

		#Add buttons in the handle of the top splitter
		#splitterTop.setHandleWidth(50)
		#vboxButton=QVBoxLayout()
		#splitterTop.handle(1).setLayout(vboxButton)
		
		#Create Vertical Splitter, with the top splitter and bottom pannel
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
			self.listToProcess.button_klusta.setEnabled(True)
	


if __name__ == '__main__':
	QApplication.setStyle("cleanlooks")
	app = QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=MainWindow()

	sys.exit(app.exec_())

