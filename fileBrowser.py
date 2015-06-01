import PyQt4.QtCore as PCore
import PyQt4.QtGui as PGui

import sys
import signal
import os

class FileBrowser(PGui.QGroupBox):
	sendsMessage=PCore.pyqtSignal(object)
	
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
		self.button_prm=PGui.QPushButton("\n Create prm and prb files \n")
		self.button_prm.clicked.connect(self.create_prm_prb)
		self.button_prm.setEnabled(False)
		
		self.button_load=PGui.QPushButton("\n Load PRB/PRM model \n")
		self.button_load.clicked.connect(self.load)
		self.label_PRB=PGui.QLabel("No PRB model")
		self.label_PRM=PGui.QLabel("No PRM model")
		
		#self.button_add=PGui.QToolButton()
		#self.button_add.setArrowType(PCore.Qt.DownArrow)
		self.button_add=PGui.QPushButton(PGui.QIcon("images/downarrow.png")," ")
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
		grid.addWidget(self.button_load,0,0,2,1)
		grid.addWidget(self.label_PRM,0,1)
		grid.addWidget(self.label_PRB,1,1)
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(self.button_add)
		hbox.addStretch(1)
		hbox.addWidget(self.button_prm)
		hbox.addLayout(grid)
		hbox.addStretch(1)
		
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.tree)
		vbox.addLayout(hbox)
		self.setLayout(vbox)
		
	def load(self):
		filebox=PGui.QFileDialog(self,"Load model for PRB file")
		filebox.setFileMode(PGui.QFileDialog.ExistingFiles)
		filebox.setNameFilters(["PRB/PRM (*.prm *.prb)"])
		filebox.setOptions(PGui.QFileDialog.DontUseNativeDialog)
		if filebox.exec_():
			for selectedFile in filebox.selectedFiles():
				if selectedFile.endswith(".prm"):
					self.prmModel=selectedFile
					namePRM=selectedFile.split("/")[-1]
					self.label_PRM.setText(namePRM)
					self.sendsMessage.emit("Set parameter Model: "+namePRM)
				elif selectedFile.endswith(".prb"):
					self.prbModel=selectedFile
					namePRB=selectedFile.split("/")[-1]
					self.label_PRB.setText(namePRB)
					self.sendsMessage.emit("Set probe Model: "+namePRB)

			if len(self.tree.selectedIndexes())!=0 and self.prbModel!=0 and self.prmModel!=0:
				self.button_prm.setEnabled(True)

	def create_prm_prb(self):
		if self.prbModel==0 or self.prmModel==0:
			self.sendsMessage.emit("Can't do : missing a PRB or PRM model")
		else:
			self.sendsMessage.emit("\n******** create prm and prb")
			selection=self.tree.selectedIndexes()
			for item in selection:
				if item.column()==0 and self.model.type(item)=="Folder":
					path=self.model.filePath(item)
					baseName=item.data()
					prbName=baseName+".prb"
					prmName=baseName+".prm"
					dataName=baseName+".raw.kwd"
					
					if dataName not in os.listdir(path):
						dataName=baseName+'.dat'
						if dataName not in os.listdir(path):
							self.sendsMessage.emit("*** "+baseName+": no raw data")
							continue #to the next item in selection

					os.system('cp '+self.prbModel+" "+path+"/"+prbName)
					os.system('cp '+self.prmModel+" "+path+"/"+prmName)
				
					with open(path+"/"+prmName,"r+") as fPRM:
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
						self.sendsMessage.emit("*** "+baseName+": ok")


	def on_selection_change(self,selected,deselected):
		if len(self.tree.selectedIndexes())!=0:
			self.button_add.setEnabled(True)
			if self.prmModel!=0 and self.prbModel!=0:
				self.button_prm.setEnabled(True)
		else:
			self.button_prm.setEnabled(False)
			self.button_add.setEnabled(False)
			

if __name__=='__main__':
	
	ROOT='/home/david/Documents/app_1.0'
	
	PGui.QApplication.setStyle("cleanlooks")
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=FileBrowser(ROOT)
	win.show()

	sys.exit(app.exec_())
	
	