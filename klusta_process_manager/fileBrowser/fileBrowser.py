import os

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui

from .tableDelegate import TableDelegate
from .folderView import FolderView

#------------------------------------------------------------------------------------------------------------
# Worker: Runs continuously in a separate thread
# Can do differents method / method can be interrupt by new method call
#------------------------------------------------------------------------------------------------------------
class Worker(QtCore.QObject):
	valueChanged=QtCore.pyqtSignal(int)
	folderDone=QtCore.pyqtSignal(int)
	finished=QtCore.pyqtSignal()
	
	def __init__(self):
		super(Worker,self).__init__()
		self._abort=False
		self._interrupt=False
		self._method="none"
		self.mutex=QtCore.QMutex()
		self.condition=QtCore.QWaitCondition()
		
	def mainLoop(self):
		while 1:
			self.mutex.lock()
			if not self._interrupt and not self._abort:
				self.condition.wait(self.mutex)
			self._interrupt=False
			if self._abort:
				self.finished.emit()
				return
			method=self._method
			self.mutex.unlock()
			if method=="icon_folder":
				self.doMethod_icon_folder()
	
	def requestMethod(self,method,arg=None):
		locker=QtCore.QMutexLocker(self.mutex)
		self._interrupt=True
		self._method=method
		self._arg=arg
		self.condition.wakeOne()

	def doMethod_icon_folder(self):
		expList=self._arg
		i=0
		s=len(expList)
		for exp in expList:
			self.mutex.lock()
			abort=self._abort
			interrupt=self._interrupt
			self.mutex.unlock()
			if abort or interrupt:
				self.valueChanged.emit(100)
				break
			exp.reset_folder_icon()
			self.folderDone.emit(i)
			i+=1
			self.valueChanged.emit(i*100.0/s)

	def abort(self):
		locker=QtCore.QMutexLocker(self.mutex)
		self._abort=True
		self.condition.wakeOne()
	
#------------------------------------------------------------------------------------------------------------
# Model
#------------------------------------------------------------------------------------------------------------
class Model(QtCore.QAbstractTableModel):

	def __init__(self,delegate=None,parent=None):
		super(Model,self).__init__(parent)
		
		#thread
		self.working=False
		self.thread=QtCore.QThread()
		self.worker=Worker()
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.mainLoop)
		self.thread.finished.connect(self.deleteLater)
		self.thread.start()
		self.worker.folderDone.connect(self.icon_done)
		self.worker.finished.connect(self.thread.quit)
		
		#list of current experiments to display
		self.experimentList=[]
		
		#Delegate
		self.delegate=delegate

	def rowCount(self,QModelIndex):
		return len(self.experimentList)
	
	def columnCount(self,QModelIndex):
		return 4

	def icon_done(self,row):
		idx=self.index(row,3)
		self.dataChanged.emit(idx,idx)

	def reset_list(self,expList):
		self.beginResetModel()
		expList.sort()
		self.experimentList=expList[:]
		self.reset_horizontal_lines()
		self.worker.requestMethod("icon_folder",self.experimentList)
		self.endResetModel()

	#To draw horizontal line according to date
	def reset_horizontal_lines(self):
		listDate=[exp.dateTime for exp in self.experimentList]
		self.delegate.reset_horizontal_lines(listDate)

	def clear(self):
		self.beginResetModel()
		self.experimentList=[]
		self.endResetModel()

	def data(self,index,role):
		col=index.column()
		row=index.row()
		if role==QtCore.Qt.DisplayRole:
			if col==0:
				return self.experimentList[row].yearMonth
			if col==1:
				return self.experimentList[row].day
			if col==2:
				return self.experimentList[row].time
			if col==3:
				return self.experimentList[row].folderName
		if role==QtCore.Qt.DecorationRole:
			if col==3:
				path=os.path.join(os.path.dirname(os.path.realpath(__file__)), '../icons/')
				path=os.path.realpath(path)+"/"
				return QtGui.QIcon(path+self.experimentList[row].folder.icon)

	def flags(self,index):
		if index.column()==3:
			return QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
		return QtCore.Qt.NoItemFlags
	
	def pathLocal_from_index(self,index):
		exp=self.experimentList[index.row()]
		return exp.pathLocal
	
	def createFiles_onSelection(self,selection,prmModel,prbModel):
		for index in selection:
			self.experimentList[index.row()].create_files(prmModel=prmModel,prbModel=prbModel)
			self.experimentList[index.row()].reset_folder_icon()
		self.dataChanged.emit(selection[0],selection[-1])

	def update_exp(self,exp):
		if exp in self.experimentList:
			row=self.experimentList.index(exp)
			index=self.index(row,3)
			self.dataChanged.emit(index,index)

#--------------------------------------------------------------------------------------------------------------
# FileBrowser Widget
#--------------------------------------------------------------------------------------------------------------
class FileBrowser(QtGui.QWidget):
	
	def __init__(self,ROOT,parent=None):
		super(FileBrowser,self).__init__(parent)

		#Combo Box
		self.animalComboBox=QtGui.QComboBox()

		#model/view
		self.delegate=TableDelegate(self)
		self.model=Model(self.delegate,self)
		self.view=FolderView(self.model,self)
		self.model.worker.valueChanged.connect(self.display_load)
		self.view.table.setItemDelegate(self.delegate)
		
		#button
		pathIcon=os.path.join(os.path.dirname(os.path.realpath(__file__)), '../icons/downarrow.png')
		pathIcon=os.path.realpath(pathIcon)
		self.button_add=QtGui.QPushButton(QtGui.QIcon(pathIcon)," ")
		self.button_createFiles=QtGui.QPushButton("Create prm/prb")
		self.button_createFiles.clicked.connect(self.createFiles)
		self.button_createFiles.setEnabled(False)
		self.button_loadModels=QtGui.QPushButton("Load models")
		self.button_loadModels.clicked.connect(self.loadModels)
		
		#label
		self.label_path=QtGui.QLabel(ROOT+os.sep)
		self.label_load=QtGui.QLabel('          ')
		self.label_prmModel=QtGui.QLabel('no prm model')
		self.label_prbModel=QtGui.QLabel('no prb model')
		
		self.prmModel=QtCore.QFileInfo()
		self.prbModel=QtCore.QFileInfo()
		
		#Layout
		hboxT=QtGui.QHBoxLayout()
		hboxT.addWidget(self.label_path)
		hboxT.addWidget(self.animalComboBox)
		hboxT.addStretch()

		vboxP=QtGui.QVBoxLayout()
		vboxP.addWidget(self.label_prmModel)
		vboxP.addWidget(self.label_prbModel)

		hboxB=QtGui.QHBoxLayout()
		hboxB.addWidget(self.button_add)
		hboxB.addWidget(self.button_loadModels)
		hboxB.addLayout(vboxP)
		hboxB.addWidget(self.button_createFiles)
		hboxB.addWidget(self.label_load)
		
		vbox=QtGui.QVBoxLayout()
		vbox.addLayout(hboxT)
		vbox.addWidget(self.view)
		vbox.addLayout(hboxB)
		self.setLayout(vbox)
		
	def set_animalComboBox(self,animalList):
		for animalID in animalList:
			self.animalComboBox.addItem(animalID)
		
	def get_experiment_selection(self):
		return self.view.table.selectedIndexes()
		
	def createFiles(self):
		if self.prmModel.exists() and self.prbModel.exists():
			selection=self.get_experiment_selection()
			self.model.createFiles_onSelection(selection,prmModel=self.prmModel,prbModel=self.prbModel)
		self.view.refresh()
	
	def loadModels(self):
		filebox=QtGui.QFileDialog(self,"Load model for PRB and PRM files")
		filebox.setFileMode(QtGui.QFileDialog.ExistingFiles)
		filebox.setNameFilters(["PRB/PRM (*.prm *.prb)"])
		filebox.setOptions(QtGui.QFileDialog.DontUseNativeDialog)
		if filebox.exec_():
			for selectedFile in filebox.selectedFiles():
				if selectedFile.endswith(".prm"):
					self.prmModel.setFile(selectedFile)
					self.label_prmModel.setText(self.prmModel.fileName())
				elif selectedFile.endswith(".prb"):
					self.prbModel.setFile(selectedFile)
					self.label_prbModel.setText(self.prbModel.fileName())
					
		if self.prmModel.exists() and self.prbModel.exists():
			self.button_createFiles.setEnabled(True)

	def display_load(self,i):
		percentage=str(i)+'%'
		if i==100:
			self.label_load.setText("")
		else:
			self.label_load.setText("Loading icons: "+percentage)

	def reset_experimentList(self,experimentInfoList):
		self.model.reset_list(experimentInfoList)
		self.view.reset_view()

	def on_close(self):
		self.model.worker.abort()
		#self.model.thread.wait()

