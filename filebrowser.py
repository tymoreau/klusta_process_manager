import sys
import signal

#Remove Qvariant and all from PyQt (was not done for python2)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

import PyQt4.QtCore as PCore
import PyQt4.QtGui as PGui
import PyQt4.QtSql as PSql

from database import Database

from parameter import *

#TO DO
# filewatcher to check if color change
# check if folder root empty


#-----------------------------------------------------------------------------------------------------------------------
#  Experiment
#-----------------------------------------------------------------------------------------------------------------------
class Experiment(PCore.QObject):
	
	def __init__(self,expInfoDict,parent=None):
		super(Experiment,self).__init__(parent)
		self.folderName=expInfoDict["folderName"]
		self.image=expInfoDict["image"]
		self.pathBackUP=expInfoDict["pathBackUP"]
		self.pathLocal=expInfoDict["pathLocal"]
		self.folder=PCore.QDir(self.pathLocal)
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
		self.dateTime=PCore.QDateTime().fromString(date,DATE_TIME_FORMAT)
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
# Worker
#-----------------------------------------------------------------------------------------------------------------------
class Worker(PCore.QObject):
	valueChanged=PCore.pyqtSignal(int)
	folderDone=PCore.pyqtSignal(int)
	finished=PCore.pyqtSignal()
	
	def __init__(self):
		super(Worker,self).__init__()
		self._abort=False
		self._interrupt=False
		self._method="none"
		self.mutex=PCore.QMutex()
		self.condition=PCore.QWaitCondition()
		
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
		locker=PCore.QMutexLocker(self.mutex)
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
		locker=PCore.QMutexLocker(self.mutex)
		self._abort=True
		self.condition.wakeOne()
	
#-----------------------------------------------------------------------------------------------------------------------
# Model
#-----------------------------------------------------------------------------------------------------------------------
class Model(PCore.QAbstractTableModel):

	def __init__(self,delegate=None,parent=None):
		super(Model,self).__init__(parent)
		
		#thread
		self.working=False
		self.thread=PCore.QThread()
		self.worker=Worker()
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.mainLoop)
		self.thread.start()
		self.worker.finished.connect(self.thread.quit)
		self.worker.folderDone.connect(self.color_done)
		
		#list of current experiment to display
		self.experimentList=[]
		
		#dictionnary of experiment
		self.experimentDict={}
		
		#Delegate
		self.delegate=delegate

	def rowCount(self,parent=PCore.QModelIndex()):
		return len(self.experimentList)
	
	def columnCount(self,parent=PCore.QModelIndex()):
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
		previousMonth=0
		previousWeek=0
		previousDay=0
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
		self.delegate.middleWeek=[ summ/2 for summ in middleWeek if summ%2==0]
		self.delegate.middleWeekOdd=[ summ//2 for summ in middleWeek if summ%2!=0]
		
		dayLines=dayLines+weekLines
		dayLines.sort()
		day2=[-1]+dayLines[:-1]
		middleDay=[(a+b+1) for a,b in zip(dayLines,day2)]
		self.delegate.middleDay=[ summ/2 for summ in middleDay if summ%2==0]
		self.delegate.middleDayOdd=[ summ//2 for summ in middleDay if summ%2!=0]

	def clear(self):
		self.beginResetModel()
		self.experimentList=[]
		self.endResetModel()

	def data(self,index,role):
		col=index.column()
		row=index.row()
		if role==PCore.Qt.DisplayRole:
			if col==0:
				return self.experimentList[row].date
			if col==1:
				return self.experimentList[row].day
			if col==2:
				return self.experimentList[row].time
			if col==3:
				return self.experimentList[row].folderName
		if role==PCore.Qt.DecorationRole:
			if col==3:
				return PGui.QIcon(self.experimentList[row].image)

	def flags(self,index):
		if index.column()==3:
			return PCore.Qt.ItemIsEnabled|PCore.Qt.ItemIsSelectable
		return PCore.Qt.NoItemFlags
	
	def get_expList(self):
		return self.experimentDict.values()

	def close(self):
		self.worker.abort()
		return self.get_expList()


#-----------------------------------------------------------------------------------------------------------------------
# Delegate
#-----------------------------------------------------------------------------------------------------------------------
class TableDelegate(PGui.QStyledItemDelegate):
	#colors=PGui.QColor.colorNames()
	
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
			line=PCore.QLine(p1,p2)
			
			painter.setPen(PCore.Qt.black)
			painter.drawLine(line)
		
		#Horizontal Lines---------------------------------
		#Month/Year/Week
		if row in self.weekLines:
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=PCore.QLine(p1,p2)
			
			painter.setPen(PCore.Qt.black)
			painter.drawLine(line)
		#Day
		elif col!=0 and (row in self.dayLines):
			painter.setPen(PGui.QPen(PGui.QBrush(PCore.Qt.gray),1.5,PCore.Qt.DotLine))
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=PCore.QLine(p1,p2)
			painter.drawLine(line)
			
		#Draw Text
		painter.setPen(PCore.Qt.black)
		if col==3:
			return super(TableDelegate,self).paint(painter,option,index)
		elif col==0 and (row in self.middleWeek):
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())
		elif col==0 and (row in self.middleWeekOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +5
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())
		elif (col==1 or col==2) and (row in self.middleDay):
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())
		elif (col==1 or col==2) and (row in self.middleDayOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +7
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())

#-----------------------------------------------------------------------------------------------------------------------
# View
#-----------------------------------------------------------------------------------------------------------------------
class View_Folders(PGui.QWidget):

	def __init__(self,model,parent=None):
		super(View_Folders,self).__init__(parent)
		
		self.table=PGui.QTableView(self)
		self.table.horizontalHeader().setVisible(False)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setResizeMode(PGui.QHeaderView.ResizeToContents)
		self.table.setShowGrid(False)
		
		vbar=self.table.verticalScrollBar()
		self.table.setVerticalScrollBarPolicy(PCore.Qt.ScrollBarAlwaysOff)
		
		self.table.setModel(model)
		self.table.connect(self.table.selectionModel(),PCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)


		self.listFile=PGui.QTreeView(self)
		self.listFile.header().setResizeMode(PGui.QHeaderView.ResizeToContents)
		self.listFile.header().setStretchLastSection(True)
		
		self.folderModel=PGui.QFileSystemModel(self)

		self.space=PGui.QWidget()
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(vbar)
		hbox.addWidget(self.table)
		hbox.addWidget(self.space)
		hbox.addWidget(self.listFile)
		self.setLayout(hbox)
		
		self.listFile.hide()
		self.space.show()
		

	def on_selection_change(self,selected,deselected):
		if len(selected.indexes())==0:
			self.listFile.hide()
			self.space.show()
			return
		self.listFile.show()
		self.space.hide()
		lastIndex=selected.indexes()[-1]
		foldername=lastIndex.data()
		animal=foldername.split('_')[0]
		path=ROOT+"/"+animal+"/Experiments/"+foldername
		self.folderModel.setRootPath(path)
		self.listFile.setModel(self.folderModel)
		self.listFile.setRootIndex(self.folderModel.index(path))
		
	#Merge cells according to date
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
# Widget
#-----------------------------------------------------------------------------------------------------------------------
class FileBrowser(PGui.QWidget):
	
	def __init__(self,database,parent=None):
		super(FileBrowser,self).__init__(parent)

		#Combo Box
		self.animalComboBox=PGui.QComboBox()
		self.animalComboBox.currentIndexChanged.connect(self.on_animal_change)

		#progress label
		self.label_load=PGui.QLabel('')

		#model/view
		self.delegate=TableDelegate(self)
		self.model=Model(self.delegate,self)
		self.view=View_Folders(self.model,self)
		self.model.worker.valueChanged.connect(self.display_load)
		self.view.table.setItemDelegate(self.delegate)
		
		#button 
		self.button_add=PGui.QPushButton(PGui.QIcon("images/downarrow.png")," ")
		
		#Layout
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.animalComboBox)
		vbox.addWidget(self.view)
		vbox.addWidget(self.label_load)
		vbox.addWidget(self.button_add)
		self.setLayout(vbox)

		self.database=database
		animalFolderList=self.database.get_animalID_list(notEmpty=True)
		for animalID in animalFolderList:
			self.animalComboBox.addItem(animalID)
		
		
		
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
		event.accept()
		
	

# TEST
if __name__=='__main__':
	PGui.QApplication.setStyle("plastique")
	#PGui.QApplication.addLibraryPath(".\\plugins")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	if PCore.QDir(ROOT).exists() and PCore.QDir(BACK_UP).exists():
		dbName="database_loc-"+ROOT.split('/')[-1]+"_backUP-"+BACK_UP.split('/')[-1]+".db"
		print("Creating/Updating database %s..."%dbName)
		database=Database(dbName,ROOT,BACK_UP,EXP_PATH,DEFAULT_IMAGE,DATE_TIME_FORMAT,LENGTH_ID)
	else:
		print("ROOT or BACK_UP folders not found")

	
	if database._open():
		database.update_tables()
	else:
		print("could not open database")


	win=FileBrowser(database)
	
	#win.setAttribute(PCore.Qt.WA_DeleteOnClose)
	win.setMinimumSize(1000,600)

	win.show()

	sys.exit(app.exec_())
