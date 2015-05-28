import sys
import os 
import signal

import PySide.QtCore as PCore
import PySide.QtGui as PGui

from experiment import Experiment
#to do : check remove row/inser row, avoid reset model ?

#------------------------------------------------------------------------------------------------------------------
#       ExperimentModelBase: visualize experiment object
#------------------------------------------------------------------------------------------------------------------
class ExperimentModelBase(PCore.QAbstractTableModel):
	changeChecked=PCore.Signal(object)
	
	def __init__(self,NASPath):
		super(ExperimentModelBase,self).__init__()
		
		self.experimentList=[]
		self.names=[]
		self.indexProcess=None
		self.indexSync=None
		self.nbChecked=0
		self.NASPath=NASPath
		
	def add_experiment(self,folderPath):
		if folderPath in self.names:
			for experiment in self.experimentList:
				if experiment.path==folderPath:
					if experiment.remove():    #=if nothing running/waiting and if not on server
						self.beginResetModel()
						experiment.refresh_state()
						self.endResetModel()
				return experiment.state
			return 'error in add_experiment'
		else:
			experiment=Experiment(folderPath,self.NASPath)
			row=len(self.experimentList)
			self.beginInsertRows(PCore.QModelIndex(),row,row)
			self.experimentList.append(experiment)
			self.nbChecked+=1
			self.changeChecked.emit(self.nbChecked)
			self.endInsertRows()
			self.names.append(folderPath)
			return experiment.state
		

	#-----------------------------------------------------------------------------------------------------
	# On the whole list
	#-----------------------------------------------------------------------------------------------------
	def clear(self):
		self.beginResetModel()
		indexToRemove=[]
		for index,experiment in enumerate(self.experimentList):
			if experiment.remove():
				if experiment.isChecked:
					self.nbChecked-=1
				indexToRemove.append(index)
				self.names.remove(experiment.path)
		self.changeChecked.emit(self.nbChecked)
		self.experimentList=[exp for index,exp in enumerate(self.experimentList) if index not in indexToRemove]
		self.endResetModel()
		return len(indexToRemove)
	


	#-----------------------------------------------------------------------------------------------------
	# Processing
	#-----------------------------------------------------------------------------------------------------
	
	def has_exp_to_process(self):
		for experiment in self.experimentList:
			if experiment.toProcess and not experiment.toSync:
				return True
		return False
			
	def process_one_experiment(self,process):
		for index,experiment in enumerate(self.experimentList):
			if experiment.toProcess and not experiment.toSync:
				self.beginResetModel()
				experiment.run_klusta(process)
				self.endResetModel()
				self.indexProcess=index
				return True
		self.indexProcess=None
		return False
				
	def process_done(self,exitcode):
		if self.indexProcess==None:
			return
		self.beginResetModel()
		self.experimentList[self.indexProcess].is_done(exitcode)
		self.indexProcess=None
		self.endResetModel()
		
	def kill_current(self):
		#check if something to kill
		if self.indexProcess==None:
			return False
		#warning message
		index=self.indexProcess
		msgBox = PGui.QMessageBox(PGui.QMessageBox.Warning,"Kill process ?","Kill the current process (%s) ?"%self.experimentList[index].name, PGui.QMessageBox.Yes | PGui.QMessageBox.No)
		msgBox.setDefaultButton(PGui.QMessageBox.No)
		answer = msgBox.exec_()
		#if yes, kill process (if it is still the current Experiment)
		if answer==PGui.QMessageBox.Yes:
			if self.experimentList[index].isRunning:
				self.experimentList[index].is_done(exitcode=42)
				return True
		return False



	#-----------------------------------------------------------------------------------------------------
	# Transfer / Sync
	#-----------------------------------------------------------------------------------------------------
	
	def has_exp_to_sync(self):
		for experiment in self.experimentList:
			if experiment.toSync:
				return True
		return False
	
	def sync_one_experiment(self,process):
		for index,experiment in enumerate(self.experimentList):
			if experiment.toSync:
				self.beginResetModel()
				experiment.rsync(process)
				self.endResetModel()
				self.indexSync=index
				return True
		self.indexSync=None
		return False

	def sync_done(self,exitcode):
		if self.indexSync==None:
			return
		self.beginResetModel()
		self.experimentList[self.indexSync].sync_done(exitcode)
		self.indexSync=None
		self.endResetModel()


	#----------------------------------------------------------------------------------------
	# Overrided function related to view
	#----------------------------------------------------------------------------------------
	def rowCount(self,QModelIndex):
		return int(len(self.experimentList))
		
	def columnCount(self,QModelIndex):
		return int(2)
	
	def data(self,index,role):
		row=index.row()
		col=index.column()
		if role==PCore.Qt.DisplayRole:
			if col==0:
				#print self.experimentList[row].name, self.experimentList[row].state             #display name,state to debug
				return str( self.experimentList[row].name )
			if col==1:
				return str( self.experimentList[row].state )
		elif role==PCore.Qt.CheckStateRole:
			if col==0:
				if  self.experimentList[row].isChecked:
					return PCore.Qt.Checked
				else:
					return PCore.Qt.Unchecked
		#Color in grey if checked
		elif role==PCore.Qt.BackgroundRole:
			if self.experimentList[row].isChecked:
				color=PGui.QBrush(PCore.Qt.lightGray)
				return color

	def setData(self,index,value,role):
		row=index.row()
		col=index.column()
		if role==PCore.Qt.CheckStateRole and col==0:
			if  self.experimentList[row].isChecked:
				self.experimentList[row].isChecked=False
				self.nbChecked-=1
			else:
				self.experimentList[row].isChecked=True
				self.nbChecked+=1
			#we changed the color of the whole line, not just this cell
			lastIndex=self.index(row,col+1)
			self.dataChanged.emit(index,lastIndex)  
			self.changeChecked.emit(self.nbChecked)
		return True

	def flags(self,index):
		if index.column()==0:
			return PCore.Qt.ItemIsEnabled | PCore.Qt.ItemIsUserCheckable
		return PCore.Qt.ItemIsEnabled

	def headerData(self,section,orientation,role):
		if role==PCore.Qt.DisplayRole:
			if orientation==PCore.Qt.Horizontal:
				if section==0:
					return str("Experiment")
				elif section==1:
					return str("State")




#------------------------------------------------------------------------------------------------------------------
#       ExperimentModel (list of Experiment) on local computer, possible to communicate with server
#------------------------------------------------------------------------------------------------------------------
# Model to use with QTableView
# Checkbox in the first column (next to the text)
# Checked lines are colored in grey
# Default : everything is checked

class ExperimentModel(ExperimentModelBase):

	#-----------------------------------------------------------------------------------------------------
	# Server
	#-----------------------------------------------------------------------------------------------------

	def server_close(self):
		self.beginResetModel()
		for experiment in self.experimentList:
			if experiment.onServer:
				experiment.state+=" ? /!\ server was closed"
		self.endResetModel()
		
	#at least one experiment is done for the server
	def server_finished(self,expDone):
		self.beginResetModel()
		i=0
		while (i+1)<len(expDone):
			name=expDone[i]
			doneOnServer=expDone[i+1]
			for experiment in self.experimentList:
				if experiment.name==name:
					experiment.onServer=False
					if doneOnServer=="True":
						experiment.toSync=True
						experiment.localToNAS=False
						experiment.state="results waiting to be sync (NAS->local)"
						experiment.isDone=True
			i+=2
		self.endResetModel()
		
		
	def update_state(self,stateList):
		self.beginResetModel()
		i=0
		while (i+1)<len(stateList):
			name=stateList[i]
			state=stateList[i+1]
			for experiment in self.experimentList:
				if experiment.name==name:
					experiment.state=state
			i+=2
		self.endResetModel()

	#-----------------------------------------------------------------------------------------------------
	# On the whole list
	#-----------------------------------------------------------------------------------------------------
	#Check all experiments
	def selectAll(self):
		self.beginResetModel()
		self.nbChecked=len(self.experimentList)
		self.changeChecked.emit(self.nbChecked)
		for experiment in self.experimentList:
			experiment.isChecked=True
		self.endResetModel()
			
	#Uncheck all experiments
	def selectNone(self):
		self.beginResetModel()
		for experiment in self.experimentList:
			experiment.isChecked=False
		self.nbChecked=0
		self.changeChecked.emit(self.nbChecked)
		self.endResetModel()
		
	#-----------------------------------------------------------------------------------------------------
	# On the selection (isChecked==True)
	#-----------------------------------------------------------------------------------------------------
	#user click on "process here": update state and boolean of selection
	def selectionUpdate_process_here(self):
		self.beginResetModel()
		nbFound=0
		for experiment in self.experimentList:
			if experiment.isChecked:
				if experiment.can_be_process_here():
					nbFound+=1
		self.endResetModel()
		return nbFound
	
	#user click on "process on server"
	def selectionUpdate_process_server(self):
		self.beginResetModel()
		nbFound=0
		for experiment in self.experimentList:
			if experiment.isChecked:
				if experiment.can_be_process_server():
					nbFound+=1
		self.endResetModel()
		return nbFound
		
	#user click on "cancel": update state and boolean of selection
	def selectionUpdate_cancel(self):
		self.beginResetModel()
		nbFound=0
		for experiment in self.experimentList:
			if experiment.isChecked:
				if experiment.cancel():
					nbFound+=1
		self.endResetModel()
		return nbFound

	#user click on "remove"
	def selectionUpdate_remove(self):
		self.beginResetModel()
		indexToRemove=[]
		for index,experiment in enumerate(self.experimentList):
			if experiment.isChecked:
				if experiment.remove():
					self.names.remove(experiment.path)
					indexToRemove.append(index)
					self.nbChecked-=1
		self.changeChecked.emit(self.nbChecked)
		self.experimentList=[exp for index,exp in enumerate(self.experimentList) if index not in indexToRemove]
		self.endResetModel()
		return len(indexToRemove)
