import sys
import signal
import time
 
#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
import PyQt4.QtCore as QtCore

from klustaFolder import KlustaFolder
from parameter import BACK_UP, EXP_PATH, DATE_TIME_FORMAT, PROGRAM,RSYNC_ARG_TO_BACKUP,RSYNC_ARG_FROM_BACKUP

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
		image=expInfoDict["image"]
		self.pathBackUP=expInfoDict["pathBackUP"]
		self.pathLocal=expInfoDict["pathLocal"]
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
		self.folder=KlustaFolder(self.pathLocal,image)
		if not self.folder.exists():
			self.state="could not find folder %s"%self.pathLocal
			self.isValid=False
			return
		
		#FileBrowser related
		self.colorDone=False  # True = no need to recompute color
		
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

	#Automaticaly find a color for the folder
	def reset_folder_image(self):
		previousImage=self.folder.image
		self.folder.reset_image()
		if self.folder.image!=previousImage:
			self.hasChange=True
		self.colorDone=True

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
				process.start("rsync",[RSYNC_ARG_TO_BACKUP,self.pathLocal+"/",self.pathBackUP])
				self.state="Sync Local->BackUP"
				return True
			self.state="No folder in backUP"
		else:
			self.state="No folder in local"
		return False
		
	def sync_from_backUP(self,process):
		if self.folder.exists():
			if self.backUPFolder.exists():
				process.start("rsync",[RSYNC_ARG_FROM_BACKUP,self.pathBackUP+"/",self.pathLocal])
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




		
	#def refresh_state(self):
		#self.finish=False 
		#self.toProcess=False
		#self.isRunning=False
		#self.isDone=False
		#self.toSync=False
		#self.isSyncing=False
		#self.localTobackUP=True
		#self.toSend=False
		#self.state="unknown"
		
		#if not self.folder.exists():
			#self.state="no folder found"
			#self.finish=True
			#return
		
		#if self.backUPFolder==None or not self.backUPFolder.exists():
			#if self.look_for_backUP_subfolder():
				#self.backUPFolder=KlustaFolder(self.backUPFolderPath)
				#self.state="folder on backUP"
			#else:
				#self.state="no folder found on backUP"
				#self.finish=True
				#return 
	
		##check for raw data (.dat or .raw.kwd)
		##has to be on backUP
		#if self.backUPFolder.has_rawData():
			#self.state="raw data on backUP"
		#else:
			#self.state="no raw data on backUP"
			#self.finish=True
			#return
		
		##check for kwik files
		#if self.backUPFolder.has_kwik():
			#self.state="done (kwik file on backUP)"
			#self.isDone=True
			#self.finish=True
		#elif self.folder.has_kwik():
			#self.state="done (kwik file) - waiting to be sync"
			#self.finish=True
			#self.isDone=True
			#self.toSync=True
			#self.localTobackUP=True
		#else:
			##no kwik file, check for prm,prb,rawData
			#if self.folder.can_be_process():
				#self.arguments=[self.folder.prm.fileName()]
			#self.state=self.folder.state

			
			
	
	##For experiment on server
	##---------------------------------------------------------------------------------------------
	#def try_process_on_server(self):
		#if self.finish or self.isDone:
			#return
		#if self.folder.can_be_process():
			#self.toProcess=True
			#self.arguments=[self.folder.prm.fileName()]
			#self.state="waiting to be processed"
		#elif self.backUPFolder.can_be_process():
			#self.toSync=True
			#self.toProcess=True
			#self.localTobackUP=False
			#self.state="waiting to be sync backUP->Server"
		#else:
			#self.finish=True
			#self.state=self.backUPFolder.state



	##STATE
	##---------------------------------------------------------------------------------------------
	#def can_be_process_here(self):
		#if self.isRunning or self.onServer or self.toSync or self.isDone:
			#return False
		#if self.folder.has_kwik():
			#self.state='Already done (kwik file)'
			#return False
		#if self.backUPFolder.has_kwik():
			#self.state='Kwik file on backUP - waiting to be sync'
			#self.toSync=True
			#self.localTobackUP=False
			#return False
		#if self.folder.can_be_process():
			#self.arguments=[self.folder.prm.fileName()]
			#self.state="waiting to be processed"
			#self.toProcess=True
			#return True
		#else:
			#self.state=self.folder.state
			#return False
		
	#def can_be_process_server(self):
		#if self.isRunning or self.onServer or self.toSync or self.isDone:
			#return False
		#if self.folder.has_kwik():
			#self.state='Already done (kwik file)'
			#return False
		#if self.backUPFolder.has_kwik():
			#self.state='Kwik file on backUP - waiting to be sync'
			#self.toSync=True
			#self.localTobackUP=False
			#return False
		#if self.folder.can_be_process():
			#self.toSync=True
			#self.localTobackUP=True
			#self.state="waiting to be sync (local->backUP)"
			#self.toSend=True
			#self.onServer=True
			#return True
		#else:
			#self.state=self.folder.state
			#return False

		
	#def cancel(self):
		#if self.isSyncing or self.isRunning or self.onServer:
			#return False
		#if self.toProcess or self.toSync:
			#self.toProcess=False
			#self.toSync=False
			#self.state="--(cancel)"
			#return True
		#return False
	
	#def can_be_remove(self):
		#if self.isSyncing or self.isRunning or self.onServer or self.toProcess or self.toSync:
			#return False
		#return True


	## TRANSFER
	##---------------------------------------------------------------------------------------------
	## For experiment "animalID_date" look for subfolder animalID in the backUP
	## if found, look inside for subfolder animalID_date
	## do not look for backUP/animalID_date, should ?
	#def look_for_backUP_subfolder(self):
		#backUP=QtCore.QDir(self.backUProot)
		#if backUP.exists():
			#animalID=self.name.split("_")[0]
			##quick look for regular case ("/backUP/animalID/Experiments/animalID_date")
			#if backUP.exists(animalID+"/Experiments/"+self.name):
				#self.backUPFolderPath=self.backUProot+"/"+animalID+"/Experiments/"+self.name
				#return True
			##quick look for common case  ("/backUP/animalID/animalID_date")
			#if backUP.exists(animalID+"/"+self.name):
				#self.backUPFolderPath=self.backUProot+"/"+animalID+"/"+self.name
				#return True
			##quick look for other common case  (no s: "/backUP/animalID/Experiment/animalID_date")
			#if backUP.exists(animalID+"/Experiment/"+self.name):
				#self.backUPFolderPath=self.backUProot+"/"+animalID+"/Experiment/"+self.name
				#return True
			
			##not common case: look for subfolder animalID - case insensitive 
			#found=False
			#for subfolder in backUP.entryList(QtCore.QDir.Dirs|QtCore.QDir.NoDotAndDotDot):
				#if str(subfolder).lower()==animalID.lower():
					#animalID=str(subfolder)
					#found=True
					#break
			##if found, look inside
			#if found:
				##quick look for regular case ("/backUP/animalID/Experiments/animalID_date")
				#if backUP.exists(animalID+"/Experiments/"+self.name):
					#self.backUPFolderPath=self.backUProot+"/"+animalID+"/Experiments/"+self.name
					#return True
				##quick look for common case  ("/backUP/animalID/animalID_date")
				#if backUP.exists(animalID+"/"+self.name):
					#self.backUPFolderPath=self.backUProot+"/"+animalID+"/"+self.name
					#return True
				
				##not common case: iterate through all subfolders
				#iterFolder=QtCore.QDirIterator(self.backUProot+"/"+animalID,["noFile"],QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot,QtCore.QDirIterator.Subdirectories)
				#while iterFolder.hasNext():
					#iterFolder.next()
					#if iterFolder.fileName().lower()==self.name.lower():
						#self.backUPFolderPath=iterFolder.filePath()
						#return True
				
				##if still not found
				#self.state="could not find folder %s in backUP"%self.name
				#return False
				
			##if not found -> error (would be possible to create folder)
			#else:
				#self.state="could not find folder %s in backUP (case insensitive)"%animalID
				#return False
		#else:
			#self.state="could not find: %s"%self.backUProot
			#return False
	
	
	##Update folders, from local to backUP or from backUP to local, using rsync
	#def rsync(self,process):
		#if not self.toSync:
			#return False
		#if process.state()==QtCore.QProcess.Running:
			#return False
		#self.toSync=False
		#if self.folder.exists() and self.backUPFolder.exists():
			#if self.localTobackUP:
				#sourcePath=self.folder.absolutePath()+"/"
				#destinationPath=self.backUPFolder.absolutePath()
				#self.state="rsync local -> backUP"
			#else:
				#sourcePath=self.backUPFolder.absolutePath()+"/"
				#destinationPath=self.folder.absolutePath()
				#self.state="rsync backUP -> local"
				
			#arguments=[RSYNC_ARG,sourcePath,destinationPath]
			#process.start("rsync",arguments)
			
			#process.waitForStarted()
			#if process.state()==QtCore.QProcess.Running:
				#self.isSyncing=True
				#return True
			#else:
				#self.state="failed to start rsync"
				#process.kill()
				#return False
		#else:
			#self.finish=True
			#self.state="missing a folder"
			#return False


	#def sync_done(self,exitcode):
		#if not self.isSyncing:
			#return
		#self.isSyncing=False
		#if exitcode!=0:
			#self.state+=" (fail,exitcode=%i)"%exitcode
		#else:
			#self.state+=" (done)"
		#self.folder.refresh()


	## KLUSTA
	##---------------------------------------------------------------------------------------------
	#def run_klusta(self,process):
		#if not self.toProcess:
			#return False
		#if process.state()==QtCore.QProcess.Running:
			#return False
		#self.toProcess=False
		#if self.folder.can_be_process():
			#self.arguments=[self.folder.prm.fileName()]
			#self.state="try to launch klusta"
			#process.setWorkingDirectory(self.folder.absolutePath())
			#process.start(self.program,self.arguments)
			#process.waitForStarted()
			#if process.state()==QtCore.QProcess.Running:
				#self.isRunning=True
				#self.state="klusta running"
				#return True
			#else: #if process.error()==QtCore.QProcess.FailedToStart:
				#self.state="failed to start process: "+PROGRAM
				#process.kill()
		#else:
			#self.state=self.folder.state
		#return False
	
	


	





