import sys
import signal

#Remove Qvariant and all from PyQt (for python2 compatibility)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

#import QT
from PyQt4 import QtCore,QtGui

#-------------------------------------------------------------------------------------------------------------
# Custom Header
#-------------------------------------------------------------------------------------------------------------
class CheckBoxHeader(QtGui.QHeaderView):
	clicked=QtCore.pyqtSignal(bool)
	_x_offset = 3
	_y_offset = 0 #value calculated later
	_width = 20
	_height = 20
	
	def __init__(self,orientation=QtCore.Qt.Horizontal,parent=None):
		super(CheckBoxHeader,self).__init__(orientation,parent)
		self.setResizeMode(QtGui.QHeaderView.Stretch)
		self.resizeSection(0,20)
		self.isChecked=0
		
	def paintSection(self,painter,rect,logicalIndex):
		painter.save()
		super(CheckBoxHeader,self).paintSection(painter,rect,logicalIndex)
		painter.restore()
		if logicalIndex==0:
			self._y_offset=int((rect.height()-self._width)/2)
			option=QtGui.QStyleOptionButton()
			option.rect= QtCore.QRect(rect.x()+self._x_offset,rect.y()+self._y_offset, self._width,self._height)
			option.state=QtGui.QStyle.State_Enabled | QtGui.QStyle.State_Active
			if self.isChecked==2:
				option.state|=QtGui.QStyle.State_NoChange
			elif self.isChecked==1:
				option.state|=QtGui.QStyle.State_On
			else:
				option.state|=QtGui.QStyle.State_Off
				
			self.style().drawControl(QtGui.QStyle.CE_CheckBox,option,painter)
			
	def updateCheckState(self,state):
		self.isChecked=state
		self.viewport().update()
		
	def mousePressEvent(self,event):
		index=self.logicalIndexAt(event.pos())
		if 0<=index<self.count():
			x = self.sectionPosition(index)
			condX=x + self._x_offset < event.pos().x() < x + self._x_offset + self._width
			condY=self._y_offset < event.pos().y() < self._y_offset + self._height
			if condX and condY:
				if self.isChecked:
					self.isChecked=False
				else:
					self.isChecked=True
				self.clicked.emit(self.isChecked)
				self.viewport().update()
				return
		super(CheckBoxHeader, self).mousePressEvent(event)
		
#-------------------------------------------------------------------------------------------------------------
# Process List Model
#-------------------------------------------------------------------------------------------------------------
class ProcessListModel(QtCore.QAbstractTableModel):
	changeChecked=QtCore.pyqtSignal(int)
	
	def __init__(self,parent=None):
		super(ProcessListModel,self).__init__(parent)
		self.header=CheckBoxHeader()
		self.header.clicked.connect(self.headerClick)
		
		self.experimentList=[]
		self.checkList=[]
		
		self.toProcess=[]
		self.futureToProcess=[]
		self.toBackUP=[]
		self.toSyncFromBackUP=[]
		self.futureToSendServer=[]
		self.toSendServer=[]
		
		self.isCheckable=[]
		
		self.expProcessing=None
		self.expSyncing=None
		
		self.indexProcess=None
		self.indexSync=None
		
	def rowCount(self,QModelIndex):
		return len(self.experimentList)
		
	def columnCount(self,QModelIndex):
		return 2
		
	def add_experiments(self,expList):
		self.beginResetModel()
		for exp in expList:
			if exp not in self.experimentList:
				row=len(self.experimentList)
				self.beginInsertRows(QtCore.QModelIndex(),row,row)
				self.experimentList.append(exp)
				self.checkList.append(exp)
				self.isCheckable.append(exp)
				self.endInsertRows()
			if exp in self.isCheckable:
				exp.refresh_state()
		self.updateCheck()
		self.endResetModel()

	def updateCheck(self):
		nbChecked=len(self.checkList)
		self.updateHeader(nbChecked)
		self.changeChecked.emit(nbChecked)

	#-----------------------------------------------------------------------------------------------------
	# View and checkbox related
	#-----------------------------------------------------------------------------------------------------
	def data(self,index,role):
		row=index.row()
		col=index.column()
		if role==QtCore.Qt.DisplayRole:
			if col==0:
				#print(self.experimentList[row].name, self.experimentList[row].state)        #display name,state to debug
				return self.experimentList[row].folderName
			if col==1:
				return self.experimentList[row].state
		elif role==QtCore.Qt.CheckStateRole:
			if col==0:
				exp= self.experimentList[row]
				if exp in self.checkList:
					return QtCore.Qt.Checked
				elif exp in self.isCheckable:
					return QtCore.Qt.Unchecked
		#Color in grey if checked
		elif role==QtCore.Qt.BackgroundRole:
			exp=self.experimentList[row]
			if exp in self.checkList:
				color=QtGui.QBrush(QtCore.Qt.lightGray)
				return color
			elif exp not in self.isCheckable:
				color=QtGui.QBrush(QtCore.Qt.yellow)
				return color

	def setData(self,index,value,role):
		row=index.row()
		col=index.column()
		if role==QtCore.Qt.CheckStateRole and col==0:
			exp=self.experimentList[row]
			if exp in self.checkList:
				self.checkList.remove(exp)
			elif exp in self.isCheckable:
				self.checkList.append(exp)
			else:
				return True
			#we changed the color of the whole line, not just this cell
			lastIndex=self.index(row,col+1)
			self.dataChanged.emit(index,lastIndex)  
			#number of row checked
			nbChecked=len(self.checkList)
			self.changeChecked.emit(nbChecked)
			self.updateHeader(nbChecked)
		return True
	
	def updateHeader(self,nbChecked):
		if nbChecked==0:
			self.header.updateCheckState(0)
		elif nbChecked==len(self.isCheckable):
			self.header.updateCheckState(1)
		else:
			self.header.updateCheckState(2)
	
	#Check/UnCheck all experiment
	def headerClick(self,isChecked):
		self.beginResetModel()
		if isChecked:
			self.checkList=self.experimentList[:]
		else:
			self.checkList=[]
		self.changeChecked.emit(len(self.checkList))
		self.endResetModel()

	def flags(self,index):
		if index.column()==0:
			if self.experimentList[index.row()] in self.isCheckable:
				return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable
		return QtCore.Qt.ItemIsEnabled

	def headerData(self,section,orientation,role):
		if role==QtCore.Qt.DisplayRole:
			if orientation==QtCore.Qt.Horizontal:
				if section==0:
					return "Experiment"
				elif section==1:
					return "State"

	#-----------------------------------------------------------------------------------------------------
	# Processing (Local)
	#-----------------------------------------------------------------------------------------------------
	#user click on "process here"
	def selection_process_local(self):
		self.beginResetModel()
		for exp in self.checkList:
			if exp.can_be_process():
				if not exp.backUPFolder.has_rawData():
					self.toBackUP.append(exp)
					self.futureToProcess.append(exp)
					exp.state="waiting to be backed up"
				else:
					self.toProcess.append(exp)
					exp.state="waiting to be processed"
				self.isCheckable.remove(exp)
		self.checkList=[]
		self.updateCheck()
		self.endResetModel()

	def has_exp_to_process(self):
		if len(self.toProcess)>0:
			return True
		return False

	def process_one_experiment(self,process):
		if self.expProcessing is None:
			if len(self.toProcess)>0:
				self.expProcessing=self.toProcess.pop(0)
				hasStart=self.expProcessing.run_process(process)
				if hasStart:
					self.processing=True
					return True
		return False
				
	def process_is_done(self,exitcode):
		if self.expProcessing is not None:
			self.beginResetModel()
			if self.expProcessing.process_is_done(exitcode):
				self.toBackUP.append(self.expProcessing)
				self.expProcessing.state="Done - waiting to be backed up"
			self.isCheckable.append(self.expProcessing)
			self.expProcessing=None
			self.endResetModel()
			return True
		return False

	#-----------------------------------------------------------------------------------------------------
	# Sync (Local <--> BackUP)
	#-----------------------------------------------------------------------------------------------------
	#user click on "back up"
	def selection_backUP(self):
		self.beginResetModel()
		self.toBackUP=self.checkList[:]
		for exp in self.toBackUP:
			exp.state="waiting to be backed up"
			self.isCheckable.remove(exp)
		self.checkList=[]
		self.updateCheck()
		self.endResetModel()

	def selection_sync_from_backUP(self):
		self.beginResetModel()
		self.toSyncFromBackUP=self.checkList[:]
		for exp in self.toSyncFromBackUP:
			exp.state="waiting to be sync from back up"
			self.isCheckable.remove(exp)
		self.checkList=[]
		self.updateCheck()
		self.endResetModel()

	def has_exp_to_sync(self):
		if len(self.toBackUP)>0:
			return True
		if len(self.toSyncFromBackUP)>0:
			return True
		return False
	
	def sync_one_experiment(self,process):
		if self.expSyncing is None:
			if len(self.toBackUP)>0:
				self.expSyncing=self.toBackUP.pop(0)
				self.expSyncing.sync_to_backUP(process)
				return True
			elif len(self.toSyncFromBackUP)>0:
				self.expSyncing=self.toSyncFromBackUP.pop(0)
				self.expSyncing.sync_from_backUP(process)
				return True
			else:
				return False
			
	def sync_done(self,exitcode):
		if self.expSyncing is not None:
			self.beginResetModel()
			if self.expSyncing.sync_done(exitcode):
				if self.expSyncing in self.futureToProcess:
					self.futureToProcess.remove(self.expSyncing)
					self.toProcess.append(self.expSyncing)
					self.expSyncing.state="waiting to be processed"
				if self.expSyncing in self.futureToSendServer:
					self.futureToSendServer.remove(self.expSyncing)
					self.toSendServer.append(self.expSyncing)
					self.expSyncing.state="waiting to be send to server"
				else:
					self.isCheckable.append(self.expSyncing)
			else:
				self.isCheckable.append(self.expSyncing)
			self.expSyncing=None
			self.endResetModel()

	#-----------------------------------------------------------------------------------------------------
	# Server
	#-----------------------------------------------------------------------------------------------------
	def selection_process_server(self):
		self.beginResetModel()
		for exp in self.checkList:
			if exp.can_be_process():
				self.toBackUP.append(exp)
				self.futureToSendServer.append(exp)
				self.isCheckable.remove(exp)
				exp.state="waiting to be backed up"
		self.checkList=[]
		self.updateCheck()
		self.endResetModel()

	def list_to_send_server(self):
		l=[str(exp.pathBackUP) for exp in self.toSendServer]
		self.onServer=self.toSendServer[:]
		self.toSendServer=[]
		return l

	def server_finished(pathList,success):
		expList=[exp for exp in self.onServer if exp.pathBackUP in pathList]
		if success:
			pass
		else:
			pass

	def server_unreachable(pathList):
		expList=[exp for exp in self.onServer if exp.pathBackUP in pathList]
		for exp in expList:
			self.onServer.remove(exp)
			exp.state="Could not send data to server"
			self.isCheckable.append(exp)
			

	

		

##list of NAS path, to process on server
	#def list_to_send(self):
		#l=[]
		#for experiment in self.experimentList:
			#if experiment.onServer and experiment.toSend:
				#if not experiment.toSync and not experiment.isSyncing:
					#experiment.toSend=False
					#experiment.state="waiting for server response"
					#fullpath=experiment.NASFolder.absolutePath()    #/NAS/animalID/Experiments/animalID_date1
					#root=experiment.NASroot                         #/NAS
					#pathFromRoot=fullpath.replace(root,"")          #/animalID/Experiments/animalID_date1
					#l.append(pathFromRoot)
		#return l

	#def server_close(self):
		#self.beginResetModel()
		#for experiment in self.experimentList:
			#if experiment.onServer:
				#experiment.state+=" ? /!\ server was closed"
		#self.endResetModel()
		
	##at least one experiment is done for the server
	#def server_finished(self,expDone):
		#self.beginResetModel()
		#i=0
		#while (i+1)<len(expDone):
			#name=expDone[i]
			#doneOnServer=expDone[i+1]
			#for experiment in self.experimentList:
				#if experiment.name==name:
					#experiment.onServer=False
					#if doneOnServer=="True":
						#experiment.toSync=True
						#experiment.localToNAS=False
						#experiment.state="results waiting to be sync (NAS->local)"
						#experiment.isDone=True
			#i+=2
		#self.endResetModel()
	



	#def kill_current(self):
		##check if something to kill
		#if self.indexProcess==None:
			#return False
		##warning message
		#index=self.indexProcess
		#msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"Kill process ?","Kill the current process (%s) ?"%self.experimentList[index].name, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		#msgBox.setDefaultButton(QtGui.QMessageBox.No)
		#answer = msgBox.exec_()
		##if yes, kill process (if it is still the current Experiment)
		#if answer==QtGui.QMessageBox.Yes:
			#if self.experimentList[index].isRunning:
				#return True
		#return False
	
	##-----------------------------------------------------------------------------------------------------
	## Transfer / Sync
	##-----------------------------------------------------------------------------------------------------
	#def kill_current_sync(self):
		##check if something to kill
		#if self.indexSync==None:
			#return False
		##warning message
		#index=self.indexSync
		#msgBox = QtGui.QMessageBox(QtGui.QMessageBox.Warning,"Kill sync ?","Kill the current sync (%s) ?"%self.experimentList[index].name, QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
		#msgBox.setDefaultButton(QtGui.QMessageBox.No)
		#answer = msgBox.exec_()
		##if yes, kill process (if it is still the current Experiment)
		#if answer==QtGui.QMessageBox.Yes:
			#if self.experimentList[index].isSyncing:
				#return True
		#return False

	
	##-----------------------------------------------------------------------------------------------------
	## Server
	##-----------------------------------------------------------------------------------------------------

		
		
	#def update_state(self,stateList):
		#self.beginResetModel()
		#i=0
		#while (i+1)<len(stateList):
			#name=stateList[i]
			#state=stateList[i+1]
			#state=state.replace("local","server")
			#for experiment in self.experimentList:
				#if experiment.name==name:
					#experiment.state=state
			#i+=2
		#self.endResetModel()

	##-----------------------------------------------------------------------------------------------------
	## On the whole list
	##-----------------------------------------------------------------------------------------------------

		
	##-----------------------------------------------------------------------------------------------------
	## On the selection (isChecked==True)
	##-----------------------------------------------------------------------------------------------------

	
	##user click on "process on server"
	#def selectionUpdate_process_server(self):
		#self.beginResetModel()
		#nbFound=0
		#for experiment in self.experimentList:
			#if experiment.isChecked and not experiment.finish:
				#if experiment.can_be_process_server():
					#nbFound+=1
		#self.endResetModel()
		#return nbFound
		
	##user click on "cancel": update state and boolean of selection
	#def selectionUpdate_cancel(self):
		#self.beginResetModel()
		#nbFound=0
		#for experiment in self.experimentList:
			#if experiment.isChecked:
				#if experiment.cancel():
					#nbFound+=1
		#self.endResetModel()
		#return nbFound

	##user click on "remove"
	#def selectionUpdate_remove(self):
		#self.beginResetModel()
		#indexToRemove=[]
		#for index,experiment in enumerate(self.experimentList):
			#if experiment.isChecked:
				#if experiment.can_be_remove():
					#self.names.remove(experiment.path)
					#indexToRemove.append(index)
					#self.nbChecked-=1
		#self.changeChecked.emit(self.nbChecked)
		#self.experimentList=[exp for index,exp in enumerate(self.experimentList) if index not in indexToRemove]
		#self.endResetModel()
		#return len(indexToRemove)
