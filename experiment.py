import sys
import os 
import signal
import time
 
import PySide.QtCore as PCore

#PROGRAM="klusta"
PROGRAM="/home/david/anaconda/envs/klusta/bin/klusta"

#Rsync arguments | -a=archive (recursive,update permission and timestamp,keep symlink...) -u=update (do not downgrade files)
RSYNC_ARG="-au"

#----------------------------------------------------------------------------------------------------------------------
#Folder meant to be process with klusta 
#  For correct behaviour, every file inside should have as basename the name of the folder
#----------------------------------------------------------------------------------------------------------------------
class KlustaFolder(PCore.QDir):
	
	def __init__(self,path):
		self.path=str(path)
		super(KlustaFolder,self).__init__(self.path)
		
		#QFileInfo: system independant file information (path, name,...)
		self.prm=PCore.QFileInfo() 
		self.rawData=PCore.QFileInfo()
		self.prb=PCore.QFileInfo()
		
		self.state=""
		self.name=self.dirName()
		
		
	def set_files(self,prmName,rawDataName,prbName):
		if self.exist(prmName) and self.exist(rawDataName) and self.exist(prbName):
			self.prm.setFile(self.filePath(prmName))
			self.rawData.setFile(self.filePath(rawDataName))
			self.prb.setFile(self.filePath(prbName))
			return True
		else:
			return False
			
		
	#look for prm file in folder, get rawData and prb name, look for them in folder
	def fetch_files(self):
		if self.exists():
			self.refresh()
			#look for prm file
			listPrm=self.entryList(["*.prm"])
			if len(listPrm)>0:
				self.prm.setFile(self.filePath(listPrm[0]))
				#look for rawData and prb in prm file, check if they exist
				if self.extract_info_from_prm():
					if self.rawData.exists():
						if self.prb.exists():
							self.state="ready to be processed"
							return True
						else:
							self.state="prb file not found"
					else:
						self.state="raw data not found"
				else:
					self.state="prm file incorrect"
			else:
				self.state="prm file not found"
		else:
			self.state="no folder found"
		return False
		
	#look for experiment_name, raw_data_files and prb_files in the parameter file (.prm)
	# This function execute the prm file as a python script: it's not safe if user mess with prm file
	def extract_info_from_prm(self):
		prmPath=self.prm.filePath()
		with open(prmPath) as f:
			try:
				code=compile(f.read(),prmPath,'exec')
				exec(code,globals(),locals())
				#if 'experiment_name' in locals():
					#self.name=experiment_name
				#else:
					#return False
				if 'raw_data_files' in locals():
					self.rawData.setFile(self.filePath(raw_data_files))
				else:
					return False
				if 'prb_file' in locals():
					self.prb.setFile(self.filePath(prb_file))
				else:
					return False
				return True
			except:
				return False
			
	#check if rawdata, prb and prm files are still in the folder
	def can_be_process(self):
		if self.exists():
			self.refresh()
			if self.prm.exists() and self.prb.exists() and self.rawData.exists():
				self.state="ready to be processed"
				return True
		return self.fetch_files()
	
	#check if kwik file in folder
	def has_kwik(self):
		self.refresh()
		if self.exists(self.name+".kwik"):
			self.state="found kwik file"
			return True
		return False
	
	#check if .dat or .raw.kwd file in folder
	def has_rawData(self):
		self.refresh()
		if self.rawData.exists():
			self.state=str(self.rawData.completeSuffix())
			return True
		elif self.exists(self.name+".dat"):
			self.rawData.setFile(self.filePath(self.name+".dat"))
			self.state=".dat"
			return True
		elif self.exists(self.name+".raw.kwd"):
			self.rawData.setFile(self.filePath(self.name+".raw.kwd"))
			self.state=".raw.kwd"
			return True
		
	def extension_list(self):
		extList=[]
		for fileName in self.entryList(PCore.QDir.Files):
			extList.append(str(fileName.completeSuffix()))
		return extList
	
	def subfolder_list(self):
		subList=[]
		for folderName in self.entryList(PCore.QDir.Dirs|PCore.QDir.NoDotAndDotDot):
			subList.append(str(folderName))
		return subList
		


#----------------------------------------------------------------------------------------------------------
# Experiment to be process with klusta
#----------------------------------------------------------------------------------------------------------
class Experiment(PCore.QObject):
	
	def __init__(self,folderPath,NASroot):
		#self.isOK=False
		self.state="error in experiment.py"
		self.name=folderPath
		self.path=folderPath
		self.NASroot=NASroot
		
		#display related
		self.isChecked=True
		self.state="--"
		
		#Processing
		self.toProcess=False
		self.isRunning=False
		self.program=PROGRAM
		self.arguments=[]
		
		#General state
		self.onServer=False #True: local experiment being process/transfer on server  (/!\ do not put to True on server side)
		self.isDone=False   #True: has a kwik file
		self.finish=False   #nothing more to do on the experiment    (useful ?)
		
		#transfer
		self.toSync=False
		self.isSyncing=False
		self.localToNAS=True
		self.toSend=False #send it's name to the server (once everything is back up on nas)
		
		self._set(folderPath,NASroot)
		
		
	def _set(self,folderPath,NASroot):
		#folder on local computer
		self.folder=KlustaFolder(folderPath)
		if not self.folder.exists():
			self.state="no folder found"
			self.finish=True
			return
		self.name=self.folder.name
		
		#folder on NAS
		self.NASFolderPath=None
		if self.look_for_NAS_subfolder():
			self.NASFolder=KlustaFolder(self.NASFolderPath)
		else:
			self.finish=True
			return
		
		self.refresh_state()
		
	def refresh_state(self):
		self.toProcess=False
		self.isRunning=False
		self.arguments=[]
		self.isDone=False
		self.toSync=False
		self.isSyncing=False
		self.localToNAS=True
		self.toSend=False
		
		if not self.folder.exists():
			self.state="no folder found"
			self.finish=True
			return
		if not self.NASFolder.exists():
			self.state="no folder found on NAS"
			self.finish=True
			return 
	
		#check for raw data (.dat or .raw.kwd)
		#has to be on NAS
		if self.NASFolder.has_rawData():
			self.state="raw data on NAS"
		else:
			self.state="no raw data on NAS"
			self.finish=True
			return
		
		#check for kwik files
		if self.NASFolder.has_kwik():
			self.state="done (kwik file on NAS)"
			self.isDone=True
		elif self.folder.has_kwik():
			self.state="done (kwik file) - not backup"
			self.isDone=True
		else:
			#no kwik file, check for prm,prb,rawData
			if self.folder.can_be_process():
				self.arguments=[self.folder.prm.fileName()]
			self.state=self.folder.state



	#STATE
	#---------------------------------------------------------------------------------------------
	def can_be_process_here(self):
		if self.isRunning or self.onServer or self.toSync or self.isDone:
			return False
		if self.folder.has_kwik():
			self.state='Already done (kwik file)'
			return False
		if self.NASFolder.has_kwik():
			self.state='Already done (kwik file on NAS)'
			return False
		if self.folder.can_be_process():
			self.arguments=[self.folder.prm.fileName()]
			self.state="waiting to be processed"
			self.toProcess=True
			return True
		else:
			self.state=self.folder.state
			return False
		
	def can_be_process_server(self):
		if self.isRunning or self.onServer or self.toSync or self.isDone:
			return False
		if self.folder.has_kwik():
			self.state='Already done (kwik file)'
			return False
		if self.NASFolder.has_kwik():
			self.state='Kwik file on NAS - waiting to be sync'
			self.toSync=True
			self.localToNAS=False
			return False
		if self.folder.can_be_process():
			self.toSync=True
			self.localToNAS=True
			self.state="waiting to be sync (local->NAS)"
			self.toSend=True
			self.onServer=True
			return True
		else:
			self.state=self.folder.state
			return False
		
	def cancel(self):
		if self.isSyncing or self.isRunning or self.onServer:
			return False
		if self.toProcess or self.toSync:
			self.toProcess=False
			self.toSync=False
			self.state="--(cancel)"
			return True
		return False
	
	def can_be_remove(self):
		if self.isSyncing or self.isRunning or self.onServer or self.toProcess or self.toSync:
			return False
		return True


	# TRANSFER
	#---------------------------------------------------------------------------------------------
	# For experiment "animalID_date" look for subfolder animalID in the NAS
	# if found, look inside for subfolder animalID_date
	def look_for_NAS_subfolder(self):
		NAS=PCore.QDir(self.NASroot)
		if NAS.exists():
			animalID=self.name.split("_")[0]
			#quick look for regular case ("/NAS/animalID/Experiments/animalID_date")
			if NAS.exists(animalID+"/Experiments/"+self.name):
				self.NASFolderPath=self.NASroot+"/"+animalID+"/Experiments/"+self.name
				return True
			#quick look for common case  ("/NAS/animalID/animalID_date")
			if NAS.exists(animalID+"/"+self.name):
				self.NASFolderPath=self.NASroot+"/"+animalID+"/"+self.name
				return True
			#quick look for other common case  (no s: "/NAS/animalID/Experiment/animalID_date")
			if NAS.exists(animalID+"/Experiment/"+self.name):
				self.NASFolderPath=self.NASroot+"/"+animalID+"/Experiment/"+self.name
				return True
			
			#not common case: look for subfolder animalID - case insensitive 
			found=False
			for subfolder in NAS.entryList(PCore.QDir.Dirs|PCore.QDir.NoDotAndDotDot):
				if str(subfolder).lower()==animalID.lower():
					animalID=str(subfolder)
					found=True
					break
			#if found, look inside
			if found:
				#quick look for regular case ("/NAS/animalID/Experiments/animalID_date")
				if NAS.exists(animalID+"/Experiments/"+self.name):
					self.NASFolderPath=self.NASroot+"/"+animalID+"/Experiments/"+self.name
					return True
				#quick look for common case  ("/NAS/animalID/animalID_date")
				if NAS.exists(animalID+"/"+self.name):
					self.NASFolderPath=self.NASroot+"/"+animalID+"/"+self.name
					return True
				
				#not common case: iterate through all subfolders
				iterFolder=PCore.QDirIterator(self.NASroot+"/"+animalID,["noFile"],PCore.QDir.AllDirs|PCore.QDir.NoDotAndDotDot,PCore.QDirIterator.Subdirectories)
				while iterFolder.hasNext():
					iterFolder.next()
					if iterFolder.fileName()==self.name:
						self.NASFolderPath=iterFolder.filePath()
						return True
				
				#if still not found
				self.state="could not find folder %s in NAS"%self.name
				self.finish=True
				return False
				
			#if not found -> error (would be possible to create folder)
			else:
				self.state="could not find folder %s in NAS (case insensitive)"%animalID
				self.finish=True
				return False
		else:
			self.state="could not find: %s"%self.NASroot
			self.finish=True
			return False
	
	
	#Update folders, from local to NAS or from NAS to local, using rsync
	def rsync(self,process):
		if not self.toSync:
			return False
		if process.state()==PCore.QProcess.Running:
			return False
		self.toSync=False
		if self.folder.exists() and self.NASFolder.exists():
			if self.localToNAS:
				sourcePath=self.folder.absolutePath()+"/"
				destinationPath=self.NASFolder.absolutePath()
				self.state="rsync %s local -> NAS"%RSYNC_ARG
			else:
				sourcePath=self.NASFolder.absolutePath()+"/"
				destinationPath=self.folder.absolutePath()
				self.state="rsync %s NAS -> local"%RSYNC_ARG
				
			arguments=[RSYNC_ARG,sourcePath,destinationPath]
			process.start("rsync",arguments)
			
			process.waitForStarted()
			if process.state()==PCore.QProcess.Running:
				self.isSyncing=True
				return True
			else:
				self.state="failed to start rsync"
				process.kill()
				return False
		else:
			self.finish=True
			self.state="missing a folder"
			return False


	def sync_done(self,exitcode):
		if not self.isSyncing:
			return
		self.isSyncing=False
		if exitcode!=0:
			self.state+="(fail,exitcode=%i)"%exitcode
		else:
			self.state+="(done)"
		


	# KLUSTA
	#---------------------------------------------------------------------------------------------
	def run_klusta(self,process):
		if not self.toProcess:
			return False
		if process.state()==PCore.QProcess.Running:
			return False
		self.toProcess=False
		if self.folder.can_be_process():
			self.state="try to launch klusta"
			process.setWorkingDirectory(self.folder.absolutePath())
			process.start(self.program,self.arguments)
			process.waitForStarted()
			if process.state()==PCore.QProcess.Running:
				self.isRunning=True
				self.state="klusta running"
				return True
			else: #if process.error()==PCore.QProcess.FailedToStart:
				self.state="failed to start process: "+PROGRAM
				process.kill()
		else:
			self.state=self.folder.state
		return False
	
	
	def is_done(self,exitcode):
		if self.onServer or self.isDone:
			return
		self.isRunning=False
		if exitcode==42:
			self.state="Killed by user"
			name="kill_"+time.strftime('%Y_%m_%d_%H_%M')
		elif exitcode!=0:
			self.state="Klusta crashed"
			name="crash_"+time.strftime('%Y_%m_%d_%H_%M')
		else:
			self.state="Done (Klusta ran) - waiting to be sync (local->NAS)"
			self.isDone=True
			self.toSync=True
			self.localToNAS=True
			self.finish=True
			return

		if exitcode!=0:
			self.folder.mkdir(name)
			extension_list=["*.high.kwd","*.kwik","*.kwx","*.log","*.low.kwd","*.prb","*.prm"]
			if self.folder.rawData.fileName().endswith(".dat"):
				self.folder.remove(self.name+".raw.kwd")
			for fileName in self.folder.entryList(extension_list,PCore.QDir.Files):
				self.folder.rename(fileName,name+"/"+fileName)
			self.finish=True
			self.toSync=False
	





