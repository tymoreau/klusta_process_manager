#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui

from config import SERVER_PATH, RSYNC_ARG_FROM_BACKUP_TO_SERVER

class ExperimentModelServer(QtCore.QAbstractTableModel):
	expStateChanged=QtCore.pyqtSignal(str) #clientIP
	expDone=QtCore.pyqtSignal(str,str,str) #clientIP, folderName, pathBackUP
	expFail=QtCore.pyqtSignal(str,str) #clientIP, folderName
	
	def __init__(self,parent=None):
		super(ExperimentModelServer,self).__init__(parent)
		
		self.experimentList=[]
		self.toProcess=[]
		self.futureToProcess=[]
		self.toBackUP=[]
		self.toSyncFromBackUP=[]
		
		self.expProcessing=None
		self.expSyncing=None

		self.nameToClient={}

		self.processDel=QtCore.QProcess()
		self.processDel.setWorkingDirectory(SERVER_PATH)

	def rowCount(self,QModelIndex):
		return len(self.experimentList)

	def columnCount(self,QModelIndex):
		return 3

	def add_experiments(self,expList,clientIP):
		self.beginResetModel()
		for exp in expList:
			if exp in self.experimentList:
				c1=exp in self.toProcess
				c2=exp in self.futureToProcess
				c3=exp in self.toBackUP
				c4=exp in self.toSyncFromBackUP
				if c1 or c2 or c3 or c4 or (exp==self.expProcessing) or (exp==self.expSyncing):
					print(exp.folderName,"already being process/sync/waiting")
					return
			else:
				self.nameToClient[exp.folderName]=clientIP
				row=len(self.experimentList)
				self.beginInsertRows(QtCore.QModelIndex(),row,row)
				self.experimentList.append(exp)
				self.endInsertRows()
			if exp.folder.has_kwik():
				self.toBackUP.append(exp)
				exp.state="Kwik file on server, waiting to be backed up"
			else:
				self.toSyncFromBackUP.append(exp)
				exp.state="Waiting to be sync (back up -> server)"
				self.futureToProcess.append(exp)
		self.endResetModel()

	#-----------------------------------------------------------------------------------------------------
	# View related
	#-----------------------------------------------------------------------------------------------------
	def data(self,index,role):
		row=index.row()
		col=index.column()
		if role==QtCore.Qt.DisplayRole:
			if col==0:
				return self.nameToClient[self.experimentList[row].folderName]
			elif col==1:
				return self.experimentList[row].folderName
			elif col==2:
				return self.experimentList[row].state

	def flags(self,index):
		return QtCore.Qt.ItemIsEnabled

	def headerData(self,section,orientation,role):
		if role==QtCore.Qt.DisplayRole:
			if orientation==QtCore.Qt.Horizontal:
				if section==0:
					return "Client"
				elif section==1:
					return "Experiment"
				elif section==2:
					return "State"

	def sync_one_experiment(self,process):
		if self.expSyncing is None:
			if len(self.toBackUP)>0:
				self.expSyncing=self.toBackUP.pop(0)
				self.expSyncing.sync_to_backUP(process)
				self.expStateChanged.emit(self.nameToClient[self.expSyncing.folderName])
				return True
			elif len(self.toSyncFromBackUP)>0:
				self.expSyncing=self.toSyncFromBackUP.pop(0)
				self.expSyncing.sync_from_backUP(process,arg=RSYNC_ARG_FROM_BACKUP_TO_SERVER)
				self.expStateChanged.emit(self.nameToClient[self.expSyncing.folderName])
				return True
			else:
				return False

	def sync_done(self,exitcode):
		toContinue=False
		if self.expSyncing is not None:
			self.beginResetModel()
			if self.expSyncing.sync_done(exitcode):
				if self.expSyncing in self.futureToProcess:
					self.futureToProcess.remove(self.expSyncing)
					self.toProcess.append(self.expSyncing)
					self.expSyncing.state="waiting to be processed"
					toContinue=True
					self.expStateChanged.emit(self.nameToClient[self.expSyncing.folderName])
				else:
					folderName=self.expSyncing.folderName
					pathBackUP=self.expSyncing.pathBackUP
					self.expDone.emit(self.nameToClient[folderName],folderName,pathBackUP)
					self.delete(self.expSyncing)
			else:
				self.expFail.emit(self.nameToClient[self.expSyncing.folderName],self.expSyncing.folderName)
			self.expSyncing=None
			self.endResetModel()
		return toContinue

	def process_one_experiment(self,process):
		if self.expProcessing is None:
			if len(self.toProcess)>0:
				self.expProcessing=self.toProcess.pop(0)
				hasStart=self.expProcessing.run_process(process)
				if hasStart:
					self.processing=True
					self.expStateChanged.emit(self.nameToClient[self.expProcessing.folderName])
					return True
				else:
					process.kill()
					folderName=self.expProcessing.folderName
					self.expFail.emit(self.nameToClient[folderName],folderName)
					self.expProcessing=None
		return False
	
	def process_is_done(self,exitcode):
		success=False
		if self.expProcessing is not None:
			self.beginResetModel()
			if self.expProcessing.process_is_done(exitcode):
				self.toBackUP.append(self.expProcessing)
				self.expProcessing.state="Done - waiting to be backed up"
				success=True
				self.expStateChanged.emit(self.nameToClient[self.expProcessing.folderName])
			else:
				folderName=self.expProcessing.folderName
				self.expFail.emit(self.nameToClient[folderName],folderName)
			self.expProcessing=None
			self.endResetModel()
		return success

	def delete(self,exp):
		self.beginResetModel()
		if not exp.is_done_and_backUP():
			if exp.folder.has_kwik():
				exp.state="/!\ not correctly backed up ?"
				print(exp.folderName,"not deleted, because no kwik file on backUP")
				return
		self.processDel.start("rm",["-r",exp.folderName])
		self.processDel.waitForFinished()
		self.experimentList.remove(exp)
		del self.nameToClient[exp.folderName]
		self.endResetModel()
