import sys
import signal
import time
 
#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
import PyQt4.QtCore as QtCore

from .klustaFolder import KlustaFolder
from klusta_process_manager.config import RSYNC_ARG_TO_BACKUP, RSYNC_ARG_FROM_BACKUP

#----------------------------------------------------------------------------------------------
# Experiment (=one folder)
#----------------------------------------------------------------------------------------------
class Experiment(QtCore.QObject):
	
	#Init an experiment from a dictionnary (result of a database query)
	def __init__(self,expInfoDict, parent=None):
		super(Experiment,self).__init__(parent)
		self.state="--"
		self.isValid=True
		
		#Database related
		self.hasChange=False  # True = have to be update in database
		
		#Information contained in database
		self.folderName=expInfoDict["folderName"]
		icon=expInfoDict["icon"]
		self.pathBackUP=expInfoDict["pathBackUP"]
		self.pathLocal=QtCore.QFileInfo(expInfoDict["pathLocal"]).absoluteFilePath()
		self.animalID=expInfoDict["animalID"]
		try:
			self.yearMonth=expInfoDict["yearMonth"]
			self.day=expInfoDict["day"]
			self.time=expInfoDict["time"]
		except KeyError: #server side
			self.yearMonth="--"
			self.day="--"
			self.time="--"

		#retrieve date for sorting purpose
		dateString=self.yearMonth+self.day+self.time
		self.dateTime=QtCore.QDateTime().fromString(dateString," MMM \n yyyy  ddd dd  hh:mm ")
			
		#Local folder
		if not QtCore.QDir(self.pathLocal).exists():
			self.state="Could not find folder %s"%self.pathLocal
			self.isValid=False
			return
		self.folder=KlustaFolder(self.pathLocal,icon)

		if QtCore.QDir(self.pathBackUP).exists():
			self.backUPFolder=KlustaFolder(self.pathBackUP)
		else:
			self.state="Could not find folder %s in back up" %(self.pathBackUP)
			self.pathBackUP=None
			return

	#comparison between object (lt=less than)
	def __lt__(self,other):
		return self.dateTime<other.dateTime

	#Automaticaly find a icon for the folder
	def reset_folder_icon(self):
		previousIcon=self.folder.icon
		self.folder.reset_icon()
		if self.folder.icon!=previousIcon:
			self.hasChange=True

	def refresh_state(self):
		if not self.backUPFolder.exists():
			self.state="Could not find folder %s in BACK_UP"%self.folderName
		elif not self.folder.exists():
			self.state="Could not find folder at %s"%self.pathLocal
		elif self.folder.has_kwik():
			self.state="Done (kwik file)"
		elif self.backUPFolder.has_kwik():
			self.state="Done (kwik file on back up)"
		elif self.folder.can_be_process():
			self.state="ready to be processed"
		else:
			self.state=self.folder.state
			if not self.folder.has_rawData():
				if self.backUPFolder.has_rawData():
					self.state="raw data on back up"

	def create_files(self,prmModel,prbModel):
		if self.folder.has_rawData():
			self.folder.create_files(prmModel=prmModel,prbModel=prbModel)
		elif self.backUPFolder.has_rawData():
			rawData=self.backUPFolder.rawData.fileName()
			self.folder.create_files(prmModel=prmModel,prbModel=prbModel,rawData=rawData)
		else:
			self.state="raw data not found"

	def is_done_and_backUP(self):
		return self.backUPFolder.has_kwik()

	#------------------------------------------------------------------------------------------------------
	#Processs local
	def can_be_process(self):
		if not self.backUPFolder.exists():
			self.state="Could not find folder %s in BACK_UP"%self.folderName
			return False
		elif not self.folder.can_be_process():
			self.state=self.folder.state
			return False
		elif self.backUPFolder.has_kwik():
			self.state="Done (kwik file on back up)"
			return False
		return True

	def can_be_process_on_server(self):
		if self.can_be_process():
			return True
		elif self.backUPFolder.can_be_process():
			return True
		#dat on BackUP, prm and prb on local
		elif self.backUPFolder.has_rawData():
			if self.folder.prm.exists() and self.folder.prb.exists():
				return True
		return False

	def run_process(self,process):
		res=self.folder.run_process(process)
		self.state=self.folder.state
		return res

	def process_is_done(self,exitcode):
		res=self.folder.is_done(exitcode)
		self.state=self.folder.state
		return res
	
	#------------------------------------------------------------------------------------------------------
	# Sync (one at a time)
	def sync_to_backUP(self,process):
		if self.folder.exists():
			if self.backUPFolder.exists():
				process.start("rsync",RSYNC_ARG_TO_BACKUP+[self.pathLocal+"/",self.pathBackUP])
				self.state="Sync Local->BackUP"
				return True
			self.state="No folder in backUP"
		else:
			self.state="No folder in local"
		return False
		
	def sync_from_backUP(self,process,arg=RSYNC_ARG_FROM_BACKUP):
		if self.folder.exists():
			if self.backUPFolder.exists():
				process.start("rsync",arg+[self.pathBackUP+"/",self.pathLocal])
				print("rsync",arg+[self.pathBackUP+"/",self.pathLocal])
				self.state="Sync BackUP->Local"
				return True
			self.state="No folder in backUP"
		else:
			self.state="No folder in local"
		return False
	
	def sync_done(self,exitcode):
		self.folder.refresh()
		if exitcode!=0:
			self.state+=": FAIL, exitcode=%i"%exitcode
			return False
		else:
			self.state+=": Done"
			return True
