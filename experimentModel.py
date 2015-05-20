import sys
import os 
import signal

import PySide.QtCore as PCore
import PySide.QtGui as PGui

from experiment import Experiment, ExperimentOnServer
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
		self.currentExperiment=None
		self.nbChecked=0
		self.NASPath=NASPath

	#-----------------------------------------------------------------------------------------------------
	# Processing
	#-----------------------------------------------------------------------------------------------------
	#look in experimentList for the first experiment ready to be process
	#return True in one experiment is found (one at least)
	def get_first_to_process(self):
		for experiment in self.experimentList:
			if experiment.toProcess:
				self.beginResetModel()
				experiment.toProcess=False
				experiment.isRunning=True
				self.currentExperiment=experiment
				self.endResetModel()
				return True
		self.currentExperiment=None
		return False
	
	def currentExperiment_isDone(self,exitcode):
		self.beginResetModel()
		self.currentExperiment.is_done(exitcode)
		self.endResetModel()


	#Transfer
	def get_first_to_transfer(self):
		for experiment in self.experimentList:
			if experiment.toTransfer:
				self.beginResetModel()
				experiment.state="being transfered "+experiment.state_transfer()
				self.currentExperimentTransfer=experiment
				self.endResetModel()
				return True
		self.currentExperimentTransfer=None
		return False


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
#       ExperimentModelServer (list of ExperimentOnServer)
#------------------------------------------------------------------------------------------------------------------
class ExperimentModelServer(ExperimentModelBase):
	
	# add an experiment if not already in model
	def add_experiment(self,nameLocal,serverPath,NASPath):
		nameLocal=str(nameLocal)
		print "self.names:",self.names
		if nameLocal in self.names:
			for experiment in self.experimentList:
				if experiment.nameLocal==nameLocal:
					if experiment.serverFinished:
						self.beginResetModel()
						experiment.reset(serverPath,NASPath)
						self.endResetModel()
					return experiment.state
					
			return "error on server add_experiment"
		else:
			experiment=ExperimentOnServer(nameLocal,serverPath,NASPath)
			self.beginResetModel()
			row=len(self.experimentList)
			self.beginInsertRows(PCore.QModelIndex(),row,row)
			self.experimentList.append(experiment)
			self.endInsertRows()
			self.names.append(str(nameLocal))
			self.endResetModel()
			return experiment.state
		

#------------------------------------------------------------------------------------------------------------------
#       ExperimentModel (list of Experiment)
#------------------------------------------------------------------------------------------------------------------
# Model to use with QTableView
# Checkbox in the first column (next to the text)
# Checked lines are colored in grey
# Default : everything is checked

class ExperimentModel(ExperimentModelBase):

	# add an experiment if not already in model
	def add_experiment(self,folderPath):
		self.beginResetModel()
		if folderPath in self.names:
			return "already in list"
		else:
			experiment=Experiment(folderPath,self.NASPath)
			if experiment.isOK:
				row=len(self.experimentList)
				self.beginInsertRows(PCore.QModelIndex(),row,row)
				self.experimentList.append(experiment)
				self.nbChecked+=1
				self.changeChecked.emit(self.nbChecked)
				self.endInsertRows()
				self.names.append(folderPath)
				self.endResetModel()
			else:
				print "exp not ok:",experiment.name
			return experiment.state

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
				if experiment.folder.dirName()==name:
					experiment.onServer=False
					if doneOnServer=="True":
						if experiment.check_remote_folder_done(experiment.NASfolder):
							experiment.isBackup=True
							experiment.state="results waiting to be transfered (NAS->local)"
							experiment.toTransfer=True
							experiment.localToNAS=False
						else:
							experiment.state="server finished job, but no kwik file on NAS"
					else:
						experiment.isBackup=False
			i+=2
		self.endResetModel()
		
		
	def update_state(self,stateList):
		self.beginResetModel()
		i=0
		while (i+1)<len(stateList):
			name=stateList[i]
			state=stateList[i+1]
			for experiment in self.experimentList:
				if experiment.folder.dirName()==name:
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
		
	#Clear the list : keep only experiment being/waiting to be process
	#return number of experiment removed
	def clear(self):
		self.beginResetModel()
		indexToRemove=[]
		for index,experiment in enumerate(self.experimentList):
			if not experiment.toProcess and not experiment.isRunning:
				if experiment.folder.absolutePath() in self.names:
					self.names.remove(experiment.folder.absolutePath())
				if experiment.isChecked:
					self.nbChecked-=1
				indexToRemove.append(index)
		self.changeChecked.emit(self.nbChecked)
		self.experimentList=[exp for index,exp in enumerate(self.experimentList) if index not in indexToRemove]
		self.endResetModel()
		return len(indexToRemove)
	
	#-----------------------------------------------------------------------------------------------------
	# On the selection (isChecked==True)
	#-----------------------------------------------------------------------------------------------------
	#user click on "process here": update state and boolean of selection
	def selectionUpdate_process_here(self):
		self.beginResetModel()
		nbFound=0
		for experiment in self.experimentList:
			if experiment.isChecked and (not experiment.isRunning) and (not experiment.onServer) and (not experiment.isDone):
				if experiment.check_if_done():
					self.isDone=True
					self.state="Already done (found a kwik file)"
				elif experiment.check_files_exist():
					experiment.state="waiting to be process"
					experiment.toProcess=True
					nbFound+=1
		self.endResetModel()
		return nbFound
	
	#user click on "process on server"
	def selectionUpdate_process_server(self):
		self.beginResetModel()
		nbFound=0
		print self.experimentList
		for experiment in self.experimentList:
			print "exp:",experiment.name, experiment.rawOnNAS, experiment.onServer,experiment.toTransfer
			if experiment.isChecked and (not experiment.isRunning) and (not experiment.onServer) and (not experiment.isDone):
				if experiment.check_if_done():
					experiment.isDone=True
					experiment.state="Already done (found a kwik file)"
				elif experiment.check_remote_folder_done(experiment.NASfolder):
					experiment.isDone=True
					experiment.state="Already done (found a kwik file on NAS)"
					if experiment.check_remote_folder_raw(experiment.NASfolder):
						experiment.isBackup=True
						experiment.rawOnNAS=True
						experiment.state="Already done and backup"
					else:
						experiment.state="Weird: kwik file on NAS but no raw data"
				else:
					if experiment.check_remote_folder_raw(experiment.NASfolder):
						experiment.state="sending request to server"
						experiment.toSend=True
						experiment.onServer=True
						experiment.rawOnNAS=True
						nbFound+=1
					else:
						experiment.rawOnNAS=False
						experiment.state="waiting to be transfered (local->NAS)"
						experiment.toTransfer=True
						experiment.localToNAS=True
						experiment.onServer=True
						nbFound+=1
			print "exp done:",experiment.name, experiment.rawOnNAS, experiment.onServer,experiment.toTransfer
		self.endResetModel()
		return nbFound
		
	#user click on "cancel": update state and boolean of selection
	def selectionUpdate_cancel(self):
		self.beginResetModel()
		nbFound=0
		for experiment in self.experimentList:
			if experiment.isChecked and experiment.toProcess and (not experiment.onServer):
				experiment.state="-- (cancel)"
				experiment.toProcess=False
				nbFound+=1
			if experiment.isChecked and experiment.toTransfer and (not experiment.onServer):
				experiment.state="-- (cancel)"
				experiment.toTransfer=False
				nbFound+=1
		self.endResetModel()
		return nbFound
		
	##user click on "restart": update state and boolean of selection
	#def selectionUpdate_restart(self):
		#self.beginResetModel()
		#nbFound=0
		#for experiment in self.experimentList:
			#if experiment.isChecked and not experiment.onServer:
				#experiment.state="waiting to be process (overwrite)"
				#experiment.toProcess=True
				#experiment.crashed=False
				#experiment.isDone=False
				#experiment.arguments.append("--overwrite")
				#nbFound+=1
		#self.endResetModel()
		#return nbFound

	#user click on "remove"
	def selectionUpdate_remove(self):
		self.beginResetModel()
		indexToRemove=[]
		killCurrent=False
		for index,experiment in enumerate(self.experimentList):
			if experiment.isChecked:
				if experiment.isRunning:
					#warning message
					msgBox = PGui.QMessageBox(PGui.QMessageBox.Warning,"Remove/Kill on selection","Kill the current process ("+experiment.name+") ?", PGui.QMessageBox.Yes | PGui.QMessageBox.No)
					msgBox.setDefaultButton(PGui.QMessageBox.No)
					answer = msgBox.exec_()
					#if yes, kill process (if it is still the current Experiment)
					if answer==PGui.QMessageBox.Yes and experiment.isRunning:
						killCurrent=True
						experiment.isRunning=False
						experiment.toProcess=False
						experiment.crashed=True
				elif not experiment.onServer:
					#remove experiment
					self.names.remove(experiment.folder.absolutePath())
					indexToRemove.append(index)
					self.nbChecked-=1
		self.changeChecked.emit(self.nbChecked)
		self.experimentList=[exp for index,exp in enumerate(self.experimentList) if index not in indexToRemove]
		self.endResetModel()
		return killCurrent,len(indexToRemove)
