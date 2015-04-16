import PySide.QtCore as PCore
import PySide.QtGui as PGui
import sys
import signal

class ListToProcess(PGui.QGroupBox):
	becomesEmpty=PCore.Signal()
	becomesFill=PCore.Signal()
	sendsMessage=PCore.Signal(object)
	
	def __init__(self):
		super(ListToProcess,self).__init__()
		
		self.setTitle("List of parameter files")
		self._model()
		self._view()
		self._buttons()
		self._layout()
		
		self.view.connect(self.view.selectionModel(),PCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)
		self.view.selectionModel
	
	def _model(self):
		self.model=PGui.QStringListModel(self)

	def _view(self):
		self.view=PGui.QListView(self)
		self.view.setModel(self.model)
		self.view.setSelectionMode(PGui.QAbstractItemView.ExtendedSelection)
		self.view.setEditTriggers(PGui.QAbstractItemView.NoEditTriggers)
		
	def _buttons(self):
		self.button_remove=PGui.QPushButton("Remove from list")
		self.button_remove.setEnabled(False)
		self.button_remove.clicked.connect(self.remove_from_selection)
		
		self.button_clear=PGui.QPushButton("Clear list")
		self.button_clear.setEnabled(False)
		self.button_clear.clicked.connect(self.clear_list)
		
		self.button_save_txt=PGui.QPushButton("Save list")
		self.button_save_txt.setEnabled(False)
		self.button_save_txt.clicked.connect(self.save_txt)
		
		self.button_load_txt=PGui.QPushButton("Load list")
		self.button_load_txt.clicked.connect(self.load_txt)

	def _layout(self):
		hboxButton=PGui.QHBoxLayout()
		hboxButton.addWidget(self.button_remove)
		hboxButton.addWidget(self.button_clear)
		hboxButton.addWidget(self.button_save_txt)
		hboxButton.addWidget(self.button_load_txt)
		
		vbox=PGui.QVBoxLayout()
		vbox.addLayout(hboxButton)
		vbox.addWidget(self.view)
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
			self.becomesEmpty.emit()
			
		msg="Removed "+str(len(string_toRemove))+" file(s)"
		self.sendsMessage.emit(msg)

	def clear_list(self):
		self.model.setStringList([])
		self.view.clearSelection()
		self.button_remove.setEnabled(False)
		self.button_save_txt.setEnabled(False)
		self.button_clear.setEnabled(False)
		self.becomesEmpty.emit()
		
		self.sendsMessage.emit("Clear list")
		
	def save_txt(self):
		list=self.model.stringList()
		if len(list)!=0:
			filebox=PGui.QFileDialog(self,"Save list")
			filebox.setFileMode(PGui.QFileDialog.AnyFile)
			filebox.setNameFilter("Text (*.txt)")
			filebox.setAcceptMode(PGui.QFileDialog.AcceptSave)
			if filebox.exec_():
				outputname=filebox.selectedFiles()[0]
				output=open(outputname,"w")
				for line in list:
					output.write(line+"\n")
				output.close()
				msg="Save list at "+str(outputname)
				self.sendsMessage.emit(msg)
		else:
			msg="The list is empty, nothing to save"
			self.sendsMessage.emit(msg)

	def load_txt(self):
		filebox=PGui.QFileDialog(self,"Load list of parameter files")
		filebox.setFileMode(PGui.QFileDialog.AnyFile)
		filebox.setNameFilter("Text (*.txt)")
		if filebox.exec_():
			name=filebox.selectedFiles()[0]
			newList=open(name).readlines()
			self.model.setStringList([line.rstrip() for line in newList])
			self.button_clear.setEnabled(True)
			self.button_save_txt.setEnabled(True)
			self.becomesFill.emit()
			msg="Load list: "+str(name)
			self.sendsMessage.emit(msg)

if __name__=='__main__':
	
	ROOT='/home/david/Documents/app_1.0'
	
	PGui.QApplication.setStyle("cleanlooks")
	app = PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=ListToProcess()
	win.show()

	sys.exit(app.exec_())