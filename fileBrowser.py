import PySide.QtCore as PCore
import PySide.QtGui as PGui
import sys
import signal
import os

class FileBrowser(PGui.QGroupBox):
	sendsMessage=PCore.Signal(object)
	
	def __init__(self,root):
		super(FileBrowser,self).__init__()
		
		self.root=root
		self.setTitle(self.root)
		
		self.prbModel=0
		self.prmModel=0
		
		self._model()
		self._tree()
		self._buttons()
		self._layout()
		
		self.tree.connect(self.tree.selectionModel(),PCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)
		
	def _buttons(self):
		self.button_prm=PGui.QPushButton("Create prm and prb files \n in selected folders")
		self.button_prm.clicked.connect(self.create_prm_prb)
		self.button_prm.setEnabled(False)
		
		self.button_loadPRB=PGui.QPushButton("Load PRB model")
		self.button_loadPRB.clicked.connect(self.load_PRB)
		self.label_PRB=PGui.QLabel("No PRB model                                    ")
		
		self.button_loadPRM=PGui.QPushButton("Load PRM model")
		self.button_loadPRM.clicked.connect(self.load_PRM)
		self.label_PRM=PGui.QLabel("No PRM model")
		
		self.button_add=PGui.QPushButton("Add selection \n to list")
		self.button_add.setEnabled(False)
		
	def _model(self):
		self.model=PGui.QFileSystemModel(self)
		self.model.setRootPath(self.root)
		
	def _tree(self):
		self.tree=PGui.QTreeView(self)
		self.tree.setModel(self.model)
		self.tree.setRootIndex(self.model.index(self.root))

		self.tree.setHeader(self.tree.header().setResizeMode(0,PGui.QHeaderView.ResizeToContents))
		self.tree.setSelectionMode(PGui.QAbstractItemView.ExtendedSelection)
		self.tree.setSelectionBehavior(PGui.QAbstractItemView.SelectRows)
		
	def _layout(self):
		grid=PGui.QGridLayout()
		grid.addWidget(self.button_loadPRM,0,0)
		grid.addWidget(self.label_PRM,0,1)
		grid.addWidget(self.button_loadPRB,1,0)
		grid.addWidget(self.label_PRB,1,1)
		
		hbox=PGui.QHBoxLayout()
		hbox.addLayout(grid)
		hbox.addWidget(self.button_prm)
		hbox.addWidget(self.button_add)
		
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.tree)
		vbox.addLayout(hbox)
		self.setLayout(vbox)
	
	def load_PRB(self):
		filebox=PGui.QFileDialog(self,"Load model for PRB file")
		filebox.setFileMode(PGui.QFileDialog.AnyFile)
		filebox.setNameFilter("PRB (*.prb)")
		filebox.setOptions(PGui.QFileDialog.DontUseNativeDialog)
		if filebox.exec_():
			self.prbModel=filebox.selectedFiles()[0]
			self.label_PRB.setText(self.prbModel)
			if len(self.tree.selectedIndexes())!=0 and self.prmModel!=0:
				self.button_prm.setEnabled(True)
			
	def load_PRM(self):
		filebox=PGui.QFileDialog(self,"Load model for PRM file")
		filebox.setFileMode(PGui.QFileDialog.AnyFile)
		filebox.setNameFilter("PRM (*.prm)")
		filebox.setOptions(PGui.QFileDialog.DontUseNativeDialog)
		if filebox.exec_():
			self.prmModel=filebox.selectedFiles()[0]
			self.label_PRM.setText(self.prmModel)
			if len(self.tree.selectedIndexes())!=0 and self.prbModel!=0:
				self.button_prm.setEnabled(True)

	def create_prm_prb(self):
		if self.prmModel==0 or self.prbModel==0:
			msgbox=PGui.QMessageBox()
			msgbox.setText("Can't do : missing a PRB or PRM model")
			msgbox.exec_()
		else:
			nbSuccess=0
			nbError=0
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
							nbError+=1
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
					nbSuccess+=1
					
				if nbSuccess+nbError==0:
					self.sendsMessage.emit("no folder in selection")
				else:
					msg="Created PRM/PRB - Success:"+str(nbSuccess)+" Fail:"+str(nbError)
					self.sendsMessage.emit(msg)


	def on_selection_change(self,selected,deselected):
		if len(self.tree.selectedIndexes())!=0:
			self.button_add.setEnabled(True)
			if self.prmModel!=0 and self.prbModel!=0:
				self.button_prm.setEnabled(True)
		else:
			self.button_prm.setEnabled(False)
			

if __name__=='__main__':
	
	ROOT='/home/david/Documents/app_1.0'
	
	PGui.QApplication.setStyle("cleanlooks")
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=FileBrowser(ROOT)
	win.show()

	sys.exit(app.exec_())
	
	