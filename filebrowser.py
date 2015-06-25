import sys
import signal

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui

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
				return QtGui.QIcon(self.experimentList[row].folder.icon)

	def flags(self,index):
		if index.column()==3:
			return QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
		return QtCore.Qt.NoItemFlags
	
	def pathLocal_from_index(self,index):
		exp=self.experimentList[index.row()]
		return exp.pathLocal
	
	def createFiles_onSelection(self,selection,prmModel,prbModel):
		for index in selection:
			self.experimentList[index.row()].folder.create_files(prmModel=prmModel,prbModel=prbModel)
			self.experimentList[index.row()].reset_folder_icon()
		self.dataChanged.emit(selection[0],selection[-1])

	def update_exp(self,exp):
		if exp in self.experimentList:
			row=self.experimentList.index(exp)
			index=self.index(row,3)
			self.dataChanged.emit(index,index)
			
		
#---------------------------------------------------------------------------------------------------
# Delegate
#---------------------------------------------------------------------------------------------------
class TableDelegate(QtGui.QStyledItemDelegate):
	#icons=QtGui.QIcon.iconNames()
	
	def __init__(self,parent=None):
		super(TableDelegate,self).__init__(parent)
		self.weekLines=[]
		self.dayLines=[]
		self.middleWeek=[]
		self.middleWeekOdd=[]
		self.middleDay=[]
		self.middleDayOdd=[]
		
	def reset_horizontal_lines(self,listDate):
		previousMonth=listDate[0].date().month()
		previousWeek=listDate[0].date().weekNumber()[0]
		previousDay=listDate[0].date().day()
		weekLines=[]
		dayLines=[]
		
		for row,date in enumerate(listDate):
			month=date.date().month()
			week=date.date().weekNumber()[0]
			day=date.date().day()
			if month==previousMonth and week==previousWeek:     #same week
				if day!=previousDay:
					dayLines.append(row-1)
			else:
				weekLines.append(row-1)
			previousMonth=month
			previousWeek=week
			previousDay=day
		weekLines.append(len(listDate)-1)
		
		self.weekLines=weekLines
		self.dayLines=dayLines
		
		week2=[-1]+weekLines[:-1]
		middleWeek=[ (a+b+1) for a,b in zip(weekLines,week2)]
		self.middleWeek=[ int(summ/2) for summ in middleWeek if summ%2==0]
		self.middleWeekOdd=[ int(summ/2) for summ in middleWeek if summ%2!=0]
		dayLines=dayLines+weekLines
		dayLines.sort()
		day2=[-1]+dayLines[:-1]
		middleDay=[(a+b+1) for a,b in zip(dayLines,day2)]
		self.middleDay=[ int(summ/2) for summ in middleDay if summ%2==0]
		self.middleDayOdd=[ int(summ/2) for summ in middleDay if summ%2!=0]

	def paint(self,painter,option,index):
		row=index.row()
		col=index.column()
		#Vertical Lines
		if col==2:
			p1=option.rect.topRight()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.setPen(QtCore.Qt.black)
			painter.drawLine(line)
		#Horizontal Lines---------------------------------
		#Month/Year/Week
		if row in self.weekLines:
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.setPen(QtCore.Qt.black)
			painter.drawLine(line)
		#Day
		elif col!=0 and (row in self.dayLines):
			painter.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.gray),1.5,QtCore.Qt.DotLine))
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.drawLine(line)
		#Draw Text
		painter.setPen(QtCore.Qt.black)
		if col==3:
			return super(TableDelegate,self).paint(painter,option,index)
		elif col==0 and (row in self.middleWeek):
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif col==0 and (row in self.middleWeekOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +5
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif (col==1 or col==2) and (row in self.middleDay):
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif (col==1 or col==2) and (row in self.middleDayOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +7
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())

#-----------------------------------------------------------------------------------------------
# View (+fileSystemModel)
#----------------------------------------------------------------------------------------------
class View_Folders(QtGui.QWidget):

	def __init__(self,model,parent=None):
		super(View_Folders,self).__init__(parent)
		
		#Table (list of experiment)
		self.table=QtGui.QTableView(self)
		self.table.horizontalHeader().setVisible(False)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
		self.table.setShowGrid(False)
		vbar=self.table.verticalScrollBar()
		self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.table.setModel(model)
		self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

		#ListFile (contents of one experiment folder)
		self.listFile=QtGui.QTreeView(self)
		self.listFile.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
		self.listFile.header().setStretchLastSection(True)
	
		#FileSytemModel linked to listFile
		self.folderModel=QtGui.QFileSystemModel(self)
		
		#Layout
		self.space=QtGui.QWidget()
		hbox=QtGui.QHBoxLayout()
		hbox.addWidget(vbar)
		hbox.addWidget(self.table)
		hbox.addWidget(self.space)
		hbox.addWidget(self.listFile)
		self.setLayout(hbox)
		self.listFile.hide()
		self.space.show()
		
	def refresh(self):
		self.listFile.update()
		
	#User clicked on one folder
	def on_selection_changed(self,selected,deselected):
		if len(selected.indexes())==0:
			if len(self.table.selectedIndexes())==0:
				self.listFile.hide()
				self.space.show()
				return
			else:
				lastIndex=self.table.selectedIndexes()[-1]
		else:
			lastIndex=selected.indexes()[-1]
		self.listFile.show()
		self.space.hide()
		#Set ListFile to display folder's content
		path=lastIndex.model().pathLocal_from_index(lastIndex)
		self.folderModel.setRootPath(path)
		self.listFile.setModel(self.folderModel)
		self.listFile.setRootIndex(self.folderModel.index(path))
		self.listFile.clearSelection()
		
	#user changed animal
	def reset_view(self):
		self.table.reset()
		self.table.clearSelection()
		self.folderModel.reset()
		self.listFile.hide()
		self.listFile.clearSelection()
		self.space.show()
		self.table.resizeColumnsToContents()
		he=self.table.horizontalHeader()
		length=he.sectionSize(0)+he.sectionSize(1)+he.sectionSize(2)+he.sectionSize(3)
		self.table.setMaximumWidth(length+10)

#--------------------------------------------------------------------------------------------------------------
# FileBrowser Widget
#--------------------------------------------------------------------------------------------------------------
class FileBrowser(QtGui.QWidget):
	
	def __init__(self,parent=None):
		super(FileBrowser,self).__init__(parent)

		#Combo Box
		self.animalComboBox=QtGui.QComboBox()

		#model/view
		self.delegate=TableDelegate(self)
		self.model=Model(self.delegate,self)
		self.view=View_Folders(self.model,self)
		self.model.worker.valueChanged.connect(self.display_load)
		self.view.table.setItemDelegate(self.delegate)
		
		#button 
		self.button_add=QtGui.QPushButton(QtGui.QIcon("icons/downarrow.png")," ")
		self.button_createFiles=QtGui.QPushButton("Create prm/prb")
		self.button_createFiles.clicked.connect(self.createFiles)
		self.button_createFiles.setEnabled(False)
		self.button_loadModels=QtGui.QPushButton("Load models")
		self.button_loadModels.clicked.connect(self.loadModels)
		
		#label
		self.label_load=QtGui.QLabel('')
		self.label_prmModel=QtGui.QLabel('no prm model')
		self.label_prbModel=QtGui.QLabel('no prb model')
		
		self.prmModel=QtCore.QFileInfo()
		self.prbModel=QtCore.QFileInfo()
		
		#Layout
		grid=QtGui.QGridLayout()
		grid.addWidget(self.button_loadModels,0,0,2,1)
		grid.addWidget(self.label_prmModel,0,1)
		grid.addWidget(self.label_prbModel,1,1)
		grid.addWidget(self.button_createFiles,0,2,2,1)
		hbox=QtGui.QHBoxLayout()
		hbox.addWidget(self.button_add)
		hbox.addLayout(grid)
		hbox.addWidget(self.label_load)
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(self.animalComboBox)
		vbox.addWidget(self.view)
		vbox.addLayout(hbox)
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


