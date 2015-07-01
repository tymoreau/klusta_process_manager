#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui

class ExperimentModelServer(QtCore.QAbstractTableModel):
	expStateChanged=QtCore.pyqtSignal(str)
	expDone=QtCore.pyqtSignal(str,str)
	expFail=QtCore.pyqtSignal(str,str)
	
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
		
	def rowCount(self,QModelIndex):
		return len(self.experimentList)
		
	def columnCount(self,QModelIndex):
		return 3
		
	def add_experiments(self,expList,clientIP):
		self.beginResetModel()
		for exp in expList:
			if exp not in self.experimentList:
				self.nameToClient[exp.folderName]=clientIP
				row=len(self.experimentList)
				self.beginInsertRows(QtCore.QModelIndex(),row,row)
				self.experimentList.append(exp)
				if exp.folder.has_kwik():
					self.toBackUP.append(exp)
					exp.state="Kwik file on server, waiting to be backed up"
				else:
					self.toSyncFromBackUP.append(exp)
					exp.state="Waiting to be sync (back up -> server)"
					self.futureToProcess.append(exp)
				self.endInsertRows()
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

	def update_exp(self,exp):
		pass

	def clear(self):
		pass

	def sync_one_experiment(self,process):
		if self.expSyncing is None:
			if len(self.toBackUP)>0:
				self.expSyncing=self.toBackUP.pop(0)
				self.expSyncing.sync_to_backUP(process)
				self.expStateChanged.emit(self.nameToClient[self.expSyncing.folderName])
				return True
			elif len(self.toSyncFromBackUP)>0:
				self.expSyncing=self.toSyncFromBackUP.pop(0)
				self.expSyncing.sync_from_backUP(process)
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
					self.expDone.emit(self.nameToClient[self.expSyncing.folderName],self.expSyncing.folderName)
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
				self.expFail.emit(self.nameToClient[self.expProcessing.folderName],self.expProcessing.folderName)
			self.expProcessing=None
			self.endResetModel()
		return success
