#Remove Qvariant and all from PyQt (for python2 compatibility)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

#import QT
from PyQt4 import QtCore,QtGui

class ServerModel(QtCore.QAbstractTableModel):
	def __init__(self,parent=None):
		super(ServerModel,self).__init__(parent)
		
		self.experimentList=[]

		self.toProcess=[]
		self.futureToProcess=[]
		self.toBackUP=[]
		self.toSyncFromBackUP=[]
		self.futureToSendClient=[]
		self.toSendClient=[]
		
		self.expProcessing=None
		self.expSyncing=None
		
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
		self.experimentList.sort()
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
				#print(self.experimentList[row].name, self.experimentList[row].state)
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

	def update_exp(self,exp):
		if exp in self.isCheckable:
			row=self.experimentList.index(exp)
			index=self.index(row,1)
			exp.refresh_state()
			self.dataChanged.emit(index,index)

	def clear(self):
		self.beginResetModel()
		for exp in self.isCheckable:
			self.experimentList.remove(exp)
		nb=len(self.isCheckable)
		self.isCheckable=[]
		self.checkList=[]
		self.endResetModel()
		return nb
