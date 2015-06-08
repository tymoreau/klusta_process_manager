import sys
import time
import signal

import PyQt4.QtCore as PCore
import PyQt4.QtGui as PGui

ROOT="/home/david/NAS02"

#animalID_year_month_day_hour_min
DATE_TIME_FORMAT="yyyy_MM_dd_HH_mm"
#length_ID "RAT034"->3   "Mou01"->2
LENGTH_ID=2

#-----------------------------------------------------------------------------------------------------------------------
# QDate.toString("yyyy MMM")   #MM=01 MMM=Jan
# QDate.toString("dd")   "01" or ddd "Mon"
# QTime.toString("hh:mm")
#-----------------------------------------------------------------------------------------------------------------------


#-----------------------------------------------------------------------------------------------------------------------
# Model
#-----------------------------------------------------------------------------------------------------------------------
class Experiment(PCore.QObject):
	
	def __init__(self,name,path):
		super(Experiment,self).__init__()
		self.name=name
		self.path=path
		self.folder=PCore.QDir(path+'/'+name)
		
		self.image="images/folder-grey.png"
		
		self.animalID=None
		self.dateTime=None
		self.date=None
		self.dayTime=None
		
	def is_valid(self):
		if self.folder.exists():
			if self.extract_from_name():
				return True
		return False
		
	def reset_folder_image(self):
		if len(self.folder.entryList())==0:
			self.image="images/folder-grey.png"
			return
		if len(self.folder.entryList(['*.kwik']))>0:
			self.image="images/folder-violet.png"
			return
		if len(self.folder.entryList(['*.dat','*.raw.kwd']))>0:
			self.image="images/folder-green.png"
			return
		self.image="images/folder-blue.png"
		
		
	def extract_from_name(self):
		#check name if correct format
		t=self.name.split("_")
		if len(t)!=6:
			return False
		#animalID
		self.animalID=t[0]
		self.ID=self.animalID[-LENGTH_ID:]
		#date
		date="_".join(t[1:])
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
	finished=PCore.pyqtSignal()
	finished_color_folder=PCore.pyqtSignal(str)
	
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
			i+=1
			self.valueChanged.emit(i*100.0/s)
		if i==s:
			self.finished_color_folder.emit(expList[0].animalID)

	def abort(self):
		locker=PCore.QMutexLocker(self.mutex)
		self._abort=True
		self.condition.wakeOne()
	

class Model(PCore.QAbstractTableModel):

	def __init__(self,parent=None):
		super(Model,self).__init__(parent)
		
		self.animalList={}
		self.animalList['None']=[[],True]
		self.currentAnimal='None'
		
		
		
		#thread
		self.working=False
		self.thread=PCore.QThread()
		self.worker=Worker()
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.mainLoop)
		self.worker.finished.connect(self.thread.quit)
		self.thread.start()
		self.worker.finished_color_folder.connect(self.color_done)
		
	
	def color_done(self,animalID):
		self.animalList[animalID][1]=True
		self.endResetModel()
		
	def reset_animal(self,animalID):
		self.beginResetModel()
		self.currentAnimal=animalID
		
		if animalID in self.animalList.keys():
			if self.animalList[animalID][1]==True:
				self.endResetModel()
				return

		self.animalList[animalID]=[[],False]
		animal=PCore.QDir(ROOT+"/"+animalID+"/Experiments")
		path=ROOT+"/"+animalID+"/Experiments"
		listFolder=[]
		for folderName in animal.entryList(PCore.QDir.Dirs|PCore.QDir.NoDotAndDotDot):
			exp=Experiment(folderName,path)
			if exp.is_valid():
				listFolder.append(exp)
		if len(listFolder)>0:
			listFolder.sort()
			self.animalList[animalID][0]=listFolder
			self.endResetModel()
			self.reset_folders_colors()
		else:
			self.endResetModel()
				
	def get_dateList(self):
		return [exp.dateTime for exp in self.animalList[self.currentAnimal][0]]

		
	def reset_folders_colors(self):
		self.beginResetModel()
		self.working=True
		self.worker.requestMethod("color_folder",self.animalList[self.currentAnimal][0])
		
	#def clear(self):
		#self.beginResetModel()
		#self.animalList[self.currentAnimal]
		#self.endResetModel()

	def data(self,index,role):
		col=index.column()
		row=index.row()
		if role==PCore.Qt.DisplayRole:
			if col==0:
				return self.animalList[self.currentAnimal][0][row].date
			if col==1:
				return self.animalList[self.currentAnimal][0][row].day
			if col==2:
				return self.animalList[self.currentAnimal][0][row].time
			if col==3:
				return self.animalList[self.currentAnimal][0][row].name
		if role==PCore.Qt.DecorationRole:
			if col==3:
				return PGui.QIcon(self.animalList[self.currentAnimal][0][row].image)

	def flags(self,index):
		if index.column()==3:
			return PCore.Qt.ItemIsEnabled|PCore.Qt.ItemIsSelectable
		return PCore.Qt.NoItemFlags
		


	def rowCount(self,parent=PCore.QModelIndex()):
		return len(self.animalList[self.currentAnimal][0])
	
	def columnCount(self,parent=PCore.QModelIndex()):
		return 4
	
	#def headerData(self,section,orientation,role):
		#if role==PCore.Qt.DisplayRole:
			#if orientation==PCore.Qt.Horizontal:
				#if section==0:
					#return "Month/Year"
				#elif section==1:
					#return "Day/Hour"
				#elif section==2:

	
	



#-----------------------------------------------------------------------------------------------------------------------
# View
#-----------------------------------------------------------------------------------------------------------------------
class CustomDelegate(PGui.QStyledItemDelegate):
	#colors=PGui.QColor.colorNames()
	
	def __init__(self,view):
		super(CustomDelegate,self).__init__()
		self.view=view
		self.header=self.view.horizontalHeader()


	def paint(self,painter,option,index):
		
		row=index.row()
		col=index.column()
		
		painter.setPen(PCore.Qt.gray)
		
		#Month/Year
		if col==0:
			p1=option.rect.bottomLeft()
			length=self.header.length()
			p2=PCore.QPoint(length,p1.y())
			line=PCore.QLine(p1,p2)
			painter.drawLine(line)
			
			painter.setPen(PCore.Qt.black)
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())
			return
		
		#Day
		elif col==1:
			painter.setPen(PGui.QPen(PGui.QBrush(PCore.Qt.gray),1,PCore.Qt.DotLine))
			p1=option.rect.bottomLeft()
			length=self.header.length()
			p2=PCore.QPoint(length,p1.y())
			line=PCore.QLine(p1,p2)
			painter.drawLine(line)
			
			painter.setPen(PGui.QPen(PCore.Qt.black))
			painter.drawText(option.rect,PCore.Qt.AlignVCenter,index.data())
			return 
			
		#FodlerName
		elif col==2:
			#line to the left
			painter.setPen(PCore.Qt.gray)
			p1=option.rect.topRight()
			p2=option.rect.bottomRight()
			line=PCore.QLine(p1,p2)
			painter.drawLine(line)
		
		return super(CustomDelegate,self).paint(painter,option,index)


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
		
		
		
		
		#self.table.setHorizontalScrollBarPolicy()
		
		#self.setAlternatingRowColors(True)
		delegate=CustomDelegate(view=self.table)
		self.table.setItemDelegate(delegate)
		self.table.setModel(model)
		self.table.connect(self.table.selectionModel(),PCore.SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),self.on_selection_change)
		

		self.listFile=PGui.QTreeView(self)
		self.listFile.header().setResizeMode(PGui.QHeaderView.ResizeToContents)
		self.listFile.header().setStretchLastSection(True)
		self.folderModel=PGui.QFileSystemModel()
		
		hbox=PGui.QHBoxLayout()
		hbox.addWidget(vbar)
		hbox.addWidget(self.table)
		hbox.addWidget(self.listFile)
		self.setLayout(hbox)
		

	def on_selection_change(self,selected,deselected):
		lastIndex=selected.indexes()[-1]
		foldername=lastIndex.data()
		animal=foldername.split('_')[0]
		path=ROOT+"/"+animal+"/Experiments/"+foldername
		self.folderModel.setRootPath(path)
		self.listFile.setModel(self.folderModel)
		self.listFile.setRootIndex(self.folderModel.index(path))
		#self.listFile.resizeColumnsToContents()
		
		
	#Merge cells according to date
	def reset_date(self,listDate):
		self.table.reset()
		self.table.clearSpans()
		self.folderModel.reset()
		self.listFile.reset()
		self.table.resizeColumnsToContents()
		self.table.setMaximumWidth(self.table.width()+10)
		
		
		startRow=0
		row=0
		nbRowSpan=1
		previousMonth=0
		previousWeek=0
		
		#Merge per month then week
		for date in listDate:
			month=date.date().month()
			week=date.date().weekNumber()[0]
			if month==previousMonth and week==previousWeek:     #same week
				nbRowSpan+=1
			else:
				if nbRowSpan>1:
					self.table.setSpan(startRow,0,nbRowSpan,1)
					nbRowSpan=1
				previousMonth=month
				previousWeek=week
				startRow=row
			row+=1
		if nbRowSpan>1:
			self.table.setSpan(startRow,0,nbRowSpan,1)
			
		#Merge per day
		startRow=0
		row=0
		nbRowSpan=1
		previousDay=0
		for date in listDate:
			day=date.date().day()
			if day==previousDay:
				nbRowSpan+=1
			else:
				if nbRowSpan>1:
					self.table.setSpan(startRow,1,nbRowSpan,1)
					nbRowSpan=1
				previousDay=day
				startRow=row
			row+=1
		if nbRowSpan>1:
			self.table.setSpan(startRow,1,nbRowSpan,1)


#-----------------------------------------------------------------------------------------------------------------------
# Widget
#-----------------------------------------------------------------------------------------------------------------------
class FileBrowser(PGui.QWidget):
	
	def __init__(self,parent=None):
		super(FileBrowser,self).__init__(parent)

		#fileWatcher

		#animal list
		self.animalComboBox=PGui.QComboBox()
		self.animalComboBox.addItem("None")
		self.root=PCore.QDir(ROOT)
		animalFolderList=self.root.entryList(PCore.QDir.Dirs|PCore.QDir.NoDotAndDotDot)
		for animalID in animalFolderList:
			self.animalComboBox.addItem(animalID)
			
		self.animalComboBox.currentIndexChanged.connect(self.on_animal_change)



		self.label_load=PGui.QLabel('')

		#model/view1
		self.model=Model()
		self.view=View_Folders(self.model)

		self.model.worker.valueChanged.connect(self.display_load)

		
		#Layout
		vbox=PGui.QVBoxLayout()
		vbox.addWidget(self.animalComboBox)
		vbox.addWidget(self.view)
		vbox.addWidget(self.label_load)
		self.setLayout(vbox)
		
	def display_load(self,i):
		percentage=str(i)+'%'
		if i==100:
			self.label_load.setText("")
		else:
			self.label_load.setText("Loading colors: "+percentage)
		
		
	def on_animal_change(self,index):
		time.sleep(0.1)
		animalID=self.animalComboBox.itemText(index)
		self.model.reset_animal(animalID)
		self.view.reset_date(self.model.get_dateList())


	def closeEvent(self,event):
		self.model.worker.abort()
		event.accept()



# TEST
if __name__=='__main__':
	PGui.QApplication.setStyle("plastique")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	win=FileBrowser()
	win.setAttribute(PCore.Qt.WA_DeleteOnClose)
	win.setMinimumSize(800,600)

	win.show()

	sys.exit(app.exec_())
