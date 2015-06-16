import sys
import signal
import time

#Remove Qvariant and all from PyQt (for python2 compatibility)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

#import QT
from PyQt4 import QtCore,QtGui

#Import parameter
from parameter import *

#-----------------------------------------------------------------------------------------------------------------------
#  Experiment
#-----------------------------------------------------------------------------------------------------------------------
class Experiment(QtCore.QObject):
	
	def __init__(self,expInfoDict,parent=None):
		super(Experiment,self).__init__(parent)
		self.folderName=expInfoDict["folderName"]
		self.image=expInfoDict["image"]
		self.pathBackUP=expInfoDict["pathBackUP"]
		self.pathLocal=expInfoDict["pathLocal"]
		self.folder=QtCore.QDir(self.pathLocal)
		self.dateTime=None
		self.date=None
		self.dayTime=None
		self.string_to_date(expInfoDict["dateTime"])
		
		#view/database related
		self.hasChange=False
		self.colorDone=False
		
	def reset_folder_image(self):
		previousImage=self.image
		if len(self.folder.entryList())==0:
			self.image="images/folder-grey.png"
		elif len(self.folder.entryList(['*.kwik']))>0:
			self.image="images/folder-violet.png"
		elif len(self.folder.entryList(['*.dat','*.raw.kwd']))>0:
			self.image="images/folder-green.png"
		else:
			self.image="images/folder-blue.png"
		if self.image!=previousImage:
			self.hasChange=True
		self.colorDone=True
		
	def string_to_date(self,date):
		self.dateTime=QtCore.QDateTime().fromString(date,DATE_TIME_FORMAT)
		if not self.dateTime.isValid():
			return False
		self.date=self.dateTime.toString(" MMM \n yyyy ")
		self.day=self.dateTime.toString(" ddd dd ")
		self.time=self.dateTime.toString(" hh:mm ")
		return True
	
	#comparison between object (lt=less than)
	def __lt__(self,other):
		return self.dateTime<other.dateTime

#-----------------------------------------------------------------------------------------------------------------------
# Worker: Runs continuously in a separate thread
# Can do differents method / method can be interrupt by new method call
#-----------------------------------------------------------------------------------------------------------------------
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
			if method=="color_folder":
				self.doMethod_color_folder()
	
	def requestMethod(self,method,arg=None):
		locker=QtCore.QMutexLocker(self.mutex)
		self._interrupt=True
		self._method=method
		self._arg=arg
		self.condition.wakeOne()

	def doMethod_color_folder(self):
		expList=self._arg
		expList=[exp for exp in expList if not exp.colorDone]
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
			exp.reset_folder_image()
			self.folderDone.emit(i)
			i+=1
			self.valueChanged.emit(i*100.0/s)

	def abort(self):
		locker=QtCore.QMutexLocker(self.mutex)
		self._abort=True
		self.condition.wakeOne()
	
#-----------------------------------------------------------------------------------------------------------------------
# Model
#-----------------------------------------------------------------------------------------------------------------------
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
		self.worker.folderDone.connect(self.color_done)
		self.worker.finished.connect(self.thread.quit)
		
		#list of current experiments to display
		self.experimentList=[]
		
		#dictionnary of experiment
		self.experimentDict={}
		
		#Delegate
		self.delegate=delegate

	def rowCount(self,parent=QtCore.QModelIndex()):
		return len(self.experimentList)
	
	def columnCount(self,parent=QtCore.QModelIndex()):
		return 4

	def color_done(self,row):
		idx=self.index(row,3)
		self.dataChanged.emit(idx,idx)
		
	def reset_list(self,experimentInfoList):
		self.beginResetModel()
		self.experimentList=[]
		for expInfoDict in experimentInfoList:
			folderName=expInfoDict["folderName"]
			if folderName not in self.experimentDict.keys():
				self.experimentDict[folderName]=Experiment(expInfoDict,parent=self)
			self.experimentList.append(self.experimentDict[folderName])
		self.experimentList.sort()
		self.reset_horizontal_lines()
		self.endResetModel()
		self.worker.requestMethod("color_folder",self.experimentList)
		
	#To draw horizontal line according to date
	def reset_horizontal_lines(self):
		listDate=[exp.dateTime for exp in self.experimentList]
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
		
		self.delegate.weekLines=weekLines
		self.delegate.dayLines=dayLines
		
		week2=[-1]+weekLines[:-1]
		middleWeek=[ (a+b+1) for a,b in zip(weekLines,week2)]
		self.delegate.middleWeek=[ int(summ/2) for summ in middleWeek if summ%2==0]
		self.delegate.middleWeekOdd=[ int(summ/2) for summ in middleWeek if summ%2!=0]
		dayLines=dayLines+weekLines
		dayLines.sort()
		day2=[-1]+dayLines[:-1]
		middleDay=[(a+b+1) for a,b in zip(dayLines,day2)]
		self.delegate.middleDay=[ int(summ/2) for summ in middleDay if summ%2==0]
		self.delegate.middleDayOdd=[ int(summ/2) for summ in middleDay if summ%2!=0]


	def clear(self):
		self.beginResetModel()
		self.experimentList=[]
		self.endResetModel()

	def data(self,index,role):
		col=index.column()
		row=index.row()
		if role==QtCore.Qt.DisplayRole:
			if col==0:
				return self.experimentList[row].date
			if col==1:
				return self.experimentList[row].day
			if col==2:
				return self.experimentList[row].time
			if col==3:
				return self.experimentList[row].folderName
		if role==QtCore.Qt.DecorationRole:
			if col==3:
				return QtGui.QIcon(self.experimentList[row].image)

	def flags(self,index):
		if index.column()==3:
			return QtCore.Qt.ItemIsEnabled|QtCore.Qt.ItemIsSelectable
		return QtCore.Qt.NoItemFlags
	
	def get_expList(self):
		return self.experimentDict.values()
	
	def pathLocal_from_index(self,index):
		exp=self.experimentList[index.row()]
		return exp.pathLocal

	def close(self):
		self.worker.abort()
		return self.experimentDict.values()

#-----------------------------------------------------------------------------------------------------------------------
# Delegate
#-----------------------------------------------------------------------------------------------------------------------
class TableDelegate(QtGui.QStyledItemDelegate):
	#colors=QtGui.QColor.colorNames()
	
	def __init__(self,parent=None):
		super(TableDelegate,self).__init__(parent)
		self.weekLines=[]
		self.dayLines=[]
		self.middleWeek=[]
		self.middleWeekOdd=[]
		self.middleDay=[]
		self.middleDayOdd=[]

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

#-----------------------------------------------------------------------------------------------------------------------
# View
#-----------------------------------------------------------------------------------------------------------------------
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
		self.table.connect(self.table.selectionModel(),QtCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)

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
		

	#User clicked on one folder
	def on_selection_change(self,selected,deselected):
		if len(selected.indexes())==0:
			self.listFile.hide()
			self.space.show()
			return
		self.listFile.show()
		self.space.hide()
		#Set ListFile to display folder's content
		lastIndex=selected.indexes()[-1]
		path=lastIndex.model().pathLocal_from_index(lastIndex)
		self.folderModel.setRootPath(path)
		self.listFile.setModel(self.folderModel)
		self.listFile.setRootIndex(self.folderModel.index(path))
		
	#user changed animal
	def reset_view(self):
		self.table.reset()
		self.folderModel.reset()
		self.listFile.hide()
		self.space.show()
		self.table.resizeColumnsToContents()
		he=self.table.horizontalHeader()
		length=he.sectionSize(0)+he.sectionSize(1)+he.sectionSize(2)+he.sectionSize(3)
		self.table.setMaximumWidth(length+10)

#-----------------------------------------------------------------------------------------------------------------------
# FileBrowser Widget
#-----------------------------------------------------------------------------------------------------------------------
class FileBrowser(QtGui.QWidget):
	
	def __init__(self,database,parent=None):
		super(FileBrowser,self).__init__(parent)

		#Combo Box
		self.animalComboBox=QtGui.QComboBox()
		self.animalComboBox.currentIndexChanged.connect(self.on_animal_change)

		#progress label
		self.label_load=QtGui.QLabel('')

		#model/view
		self.delegate=TableDelegate(self)
		self.model=Model(self.delegate,self)
		self.view=View_Folders(self.model,self)
		self.model.worker.valueChanged.connect(self.display_load)
		self.view.table.setItemDelegate(self.delegate)
		
		#Database
		self.database=database
		animalFolderList=self.database.get_animalID_list(notEmpty=True)
		for animalID in animalFolderList:
			self.animalComboBox.addItem(animalID)
		
		#button 
		self.button_add=QtGui.QPushButton(QtGui.QIcon("images/downarrow.png")," ")
		
		#Layout
		hbox=QtGui.QHBoxLayout()
		hbox.addWidget(self.button_add)
		hbox.addWidget(self.label_load)
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(self.animalComboBox)
		vbox.addWidget(self.view)
		vbox.addLayout(hbox)
		self.setLayout(vbox)

	def display_load(self,i):
		percentage=str(i)+'%'
		if i==100:
			self.label_load.setText("")
		else:
			self.label_load.setText("Loading colors: "+percentage)

	def on_animal_change(self,index):
		animalID=self.animalComboBox.itemText(index)
		experimentInfoList=self.database.get_experimentInfo_list(animal=animalID)
		self.model.reset_list(experimentInfoList)
		self.view.reset_view()

	def closeEvent(self,event):
		expList=self.model.close()
		self.database.reverbate_change(expList)
		self.database.close()

#-----------------------------------------------------------------------------------------------------------------------
if __name__=='__main__':
	
	from database import Database
	app=QtGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	if QtCore.QDir(ROOT).exists() and QtCore.QDir(BACK_UP).exists():
		dbName="database_loc-"+ROOT.split('/')[-1]+"_backUP-"+BACK_UP.split('/')[-1]+".db"
		database=Database(dbName,ROOT,BACK_UP,EXP_PATH,DEFAULT_IMAGE,DATE_TIME_FORMAT,LENGTH_ID)
	else:
		print("ROOT or BACK_UP folders not found")
	if database._open():
		database.update_tables()
	else:
		print("could not open database")

	win=FileBrowser(database)
	win.setMinimumSize(1000,600)
	
	#app.aboutToQuit.connect(win.close)

	win.show()

	sys.exit(app.exec_())
