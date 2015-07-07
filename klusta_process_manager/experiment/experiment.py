import sys
import signal
import time
 
#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
import PyQt4.QtCore as QtCore

from .klustaFolder import KlustaFolder
from config import *

#----------------------------------------------------------------------------------------------
# Experiment (=one folder)
#----------------------------------------------------------------------------------------------
class Experiment(QtCore.QObject):
	
	#Init an experiment from a dictionnary (result of a database query)
	def __init__(self,expInfoDict,parent=None):
		super(Experiment,self).__init__(parent)
		self.state="--"
		
		#Database related
		self.hasChange=False  # True = have to be update in database
		
		#Information contained in database
		self.folderName=expInfoDict["folderName"]
		icon=expInfoDict["icon"]
		self.pathBackUP=expInfoDict["pathBackUP"]
		self.pathLocal=QtCore.QFileInfo(expInfoDict["pathLocal"]).absoluteFilePath()
		self.animalID=expInfoDict["animalID"]
		self.dateTime=None
		self.yearMonth=None
		self.dayTime=None
		
		#Check if date is correct
		#Should be already checked in database
		self.isValid=self.string_to_date(expInfoDict["dateTime"])
		if not self.isValid:
			self.state="Date not valid"
			return
		
		#Local folder
		self.folder=KlustaFolder(self.pathLocal,icon)
		if not self.folder.exists():
			self.state="could not find folder %s"%self.pathLocal
			self.isValid=False
			return
		
		#BackUP folder
		self.backUPFolder=KlustaFolder(self.pathBackUP)
		if not self.backUPFolder.exists():
			if self.find_path_backUP():
				self.backUPFolder=KlustaFolder(self.pathBackUP)
			else:
				self.state="Could not find folder %s in BACK_UP"%self.folderName
				self.pathBackUP=None


	#comparison between object (lt=less than)
	def __lt__(self,other):
		return self.dateTime<other.dateTime
		
    #----------------------------------------------------------------------------------------------
	# Convert a string into several date objects
	# Mostly use to display date in FileBrowser
	def string_to_date(self,date):
		self.dateTime=QtCore.QDateTime().fromString(date,DATE_TIME_FORMAT)
		if not self.dateTime.isValid():
			return False
		self.yearMonth=self.dateTime.toString(" MMM \n yyyy ")
		self.day=self.dateTime.toString(" ddd dd ")
		self.time=self.dateTime.toString(" hh:mm ")
		return True

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
			
		
	#------------------------------------------------------------------------------------------------------
	#find path in backUP
	def find_path_backUP(self):
		if QtCore.QDir(BACK_UP+"/"+self.animalID).exists():
			pathBackUP=BACK_UP+"/"+self.animalID+EXP_PATH+"/"+self.folderName
			if QtCore.QDir(pathBackUP).exists():
				self.pathBackUP=pathBackUP
				self.hasChange=True
				return True
		else:
			return False

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
