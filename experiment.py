import sys
import os 
import signal
import time
 
import PySide.QtCore as PCore

#Command to perform on list
PROGRAM="klusta"

#------------------------------------------------------------------------------------------------------------------
#       Experiment (on the local computer)
#------------------------------------------------------------------------------------------------------------------
class Experiment(PCore.QObject):
	
	def __init__(self,folderPath,NASPath):
		self.folder=PCore.QDir(str(folderPath))
		self.name=folderPath
		
		self.isOK=False
		
		#QFileInfo: system independant file information (path, name,...)
		self.prm=PCore.QFileInfo() 
		self.rawData=PCore.QFileInfo()
		self.prb=PCore.QFileInfo()
		
		#display related
		self.isChecked=True
		self.state="--"
		
		#Processing
		self.toProcess=False
		self.isRunning=False
		self.crashed=False
		self.arguments=[]
		
		#General state
		self.onServer=False #True: experiment being process/transfer on server
		self.isBackup=False #True: results are on NAS
		self.rawOnNAS=False #True: raw data are on NAS (raw data,prb,prm)
		self.isDone=False   #done on local computer
		
		#transfer
		self.toTransfer=False
		self.localToNAS=True
		self.toSend=False #send it's name to the server (raw data is on nas)
		
		self.nas=PCore.QDir(NASPath)
		self.reset(NASPath)
		
	def reset(self,NASPath):
		#check if folder exist
		if not self.folder.exists():
			self.state="folder not found"
			self.isOK=False
			self.name=folderPath
			return

		self.name=self.folder.dirName()
			
		#Look for the name, raw data and prb in the prm file, check if everything exist
		self.isOK=self.check_files_exist()
		if not self.isOK:
			return
		
		#Warning: check if folder name match experiment_name
		if self.folder.dirName()!=self.name:
			print("Warning: experiment_name differs from folder name, could be trouble ('%s' and '%s')"%(self.folder,self.name))
		
		self.arguments=[self.prm.fileName()]
		
		self.check_if_done()
		
		#NAS
		self.NASfolder=self.look_for_subfolder(self.name,NASPath)
		#if no folder, create one
		if self.NASfolder==None:
			self.nas.mkdir(self.name)
			self.NASfolder=PCore.QDir(self.nas.filePath(self.name))
		#else check what is inside
		else:
			if self.check_remote_folder_raw(self.NASfolder):
				self.rawOnNAS=True
				self.state= "raw data on NAS"
				if self.check_remote_folder_done(self.NASfolder):
					self.isBackup=True
					self.state="results on NAS"
				
		if self.isDone and not self.isBackup:
			self.state="Done (found kwik file) - not back up"
			self.toTransfer=True
			self.localToNAS=True
		if self.isDone and self.isBackup:
			self.state="Done and back up (kwik file)"
		if not self.isDone and self.isBackup:
			self.isDone=True
			self.state="Done (kwik file on NAS, not on local computer)"
			self.localToNAS=False
				
		
	
		
	#----------------------------------------------------------------------------------------------------------
	#Transfer
	#----------------------------------------------------------------------------------------------------------
	def look_for_subfolder(self,folderName,root):
		iterFolder=PCore.QDirIterator("./test/fakeNAS",["noFile"],PCore.QDir.AllDirs|PCore.QDir.NoDotAndDotDot,PCore.QDirIterator.Subdirectories)
		while iterFolder.hasNext():
			iterFolder.next()
			if iterFolder.fileName()==folderName:
				return PCore.QDir(iterFolder.filePath())
		return None
	
	def transfer(self):
		if self.toTransfer:
			self.toTransfer=False
			if self.localToNAS:
				return self.copy_fromLocal_toNAS()
			else:
				return self.copy_fromNAS_toLocal()
			
	def state_transfer(self):
		if self.localToNAS:
			return "(Local->NAS)"
		else:
			return "(NAS->Local)"
	
	def copy_fromLocal_toNAS(self):
		if not self.folder.exists():
			self.state="No folder in local computer"
			return
		self.isOK=self.check_files_exist()
		if not self.isOK:
			return
		if not self.NASfolder.exists():
			self.nas.mkdir(self.folder.dirName())
			self.NASfolder=PCore.QDir(self.nas.filePath(self.name))
			
		#copy recursively
		self.copy_recursive(self.folder,self.NASfolder)
		self.NASfolder.refresh()
		if self.check_remote_folder_raw(self.NASfolder):
			self.state="local files transfered to NAS"
			self.rawOnNAS=True
			if self.check_remote_folder_done(self.NASfolder):
				self.isBackup=True
				self.state="results backup on NAS"
			else:
				if self.onServer:
					self.toSend=True
		else:
			self.state="problem during transfer local->NAS"
			
		
		
	def copy_fromNAS_toLocal(self):
		if not self.folder.exists():
			self.state="No folder in local computer - files on NAS"
		if not self.NASfolder.exists():
			self.state="No folder found on NAS"
		else:
			self.isOK=self.check_files_exist()
			if not self.isOK:
				self.state=self.state+" (on NAS)"
				return
			#copy recursively
			self.copy_recursive(self.NASfolder,self.folder)
			self.folder.refresh()
			self.state="NAS files transfered to local computer"
			if self.check_if_done():
				self.state="Done and back up"
		

	def copy_recursive(self,folder,destinationFolder):
		folder.refresh()
		folder.setFilter(PCore.QDir.AllEntries|PCore.QDir.NoDotAndDotDot)
		for fileInfo in folder.entryInfoList():
				if fileInfo.isDir():
					name=fileInfo.fileName()
					#create folder on destination
					destinationFolder.mkdir(name)
					#call recursively
					subfolder=PCore.QDir(fileInfo.absoluteFilePath())
					destinationSubFolder=PCore.QDir(destinationFolder.absoluteFilePath(name))
					self.copy_recursive(subfolder,destinationSubFolder)
				else:
					Qfile=PCore.QFile(fileInfo.absoluteFilePath())
					Qfile.copy(destinationFolder.filePath(fileInfo.fileName()))

		

	#----------------------------------------------------------------------------------------------------------
	#Processing
	#----------------------------------------------------------------------------------------------------------
	def run_klusta(self,process):
		process.setWorkingDirectory(self.folder.absolutePath())
		process.start(PROGRAM,self.arguments)
		self.state="Klusta running"
		self.isRunning=True
		self.toProcess=False
		
	def is_done(self,exitcode):
		self.isRunning=False
		self.isDone=True
		if self.crashed:
			self.state="Killed by user"
			name="kill_"+time.strftime('%Y_%m_%d_%H_%M')
		elif exitcode!=0:
			self.crashed=True
			self.state="Klusta crashed"
			name="crash_"+time.strftime('%Y_%m_%d_%H_%M')
		else:
			self.state="Done (Klusta ran)"

		if self.crashed:
			self.folder.mkdir(name)
			self.folder.setFilter(PCore.QDir.Files)
			for fileName in self.folder.entryList():
				if not (fileName.endswith(".raw.kwd") or fileName.endswith(".dat")):
					if not (fileName.startswith("crash") or fileName.startswith("kill")):
						self.folder.rename(fileName,name+"/"+fileName)
			self.serverFinished=True
			self.folder.setFilter(PCore.QDir.AllEntries|PCore.QDir.NoDotAndDotDot)
			self.crashed=False
			self.isDone=False
			
	#----------------------------------------------------------------------------------------------------------
	# Check files
	#----------------------------------------------------------------------------------------------------------
	def check_if_done(self):
		#Look for a kwik file
		if self.folder.exists(self.name+".kwik"):
			self.folder.refresh()
			self.isDone=True
			self.state="Done (found kwik file)"
			return True
		return False
		
	#check if files exist in current folder, and set them
	def check_files_exist(self):
		#check if folder exist
		if not self.folder.exists():
			self.state="folder not found"
			return False
		self.folder.refresh()
		#find prm file
		listPrm=self.folder.entryList(["*.prm"])
		if len(listPrm)>0:
			self.prm.setFile(self.folder.absoluteFilePath(listPrm[0]))
			#look for rawData and prb in prm file, check if they exist
			if self.check_prm():
				if self.rawData.exists():
					if self.prb.exists():
						return True
					else:
						self.state="prb file not found"
				else:
					self.state="raw data not found"
			else:
				self.state="prm file incorrect"
		else:
			self.state="prm file not found"
		return False
	
	
	#check if raw files exist in a remote folder (prb,prm,rawData)
	def check_remote_folder_raw(self,folder):
		#check if folder exist
		if folder.exists():
			folder.refresh()
			listFile=folder.entryList()
			if self.prm.fileName() in listFile:
				if self.prb.fileName() in listFile:
					if self.rawData.fileName() in listFile:
						return True
		return False
	
	def check_remote_folder_done(self,folder):
		if folder.exists():
			folder.refresh()
			if self.name+".kwik" in folder.entryList():
				return True
		return False

	#look for experiment_name, raw_data_files and prb_files in the parameter file
	def check_prm(self):
		prmPath=self.prm.absoluteFilePath()
		with open(prmPath) as f:
			try:
				code=compile(f.read(),prmPath,'exec')
				exec(code,globals(),locals())
				if 'experiment_name' in locals():
					self.name=experiment_name
				else:
					return False
				if 'raw_data_files' in locals():
					self.rawData.setFile(self.folder.absoluteFilePath(raw_data_files))
				else:
					return False
				if 'prb_file' in locals():
					self.prb.setFile(self.folder.absoluteFilePath(prb_file))
				else:
					return False
				return True
			except:
				return False


#------------------------------------------------------------------------------------------------------------------
#       Experiment on the server (duplicate of an experiment in a local computer)
# 
#------------------------------------------------------------------------------------------------------------------
class ExperimentOnServer(Experiment):
	
	def __init__(self,nameLocal,ServerPath,NASPath):
		#name of the folder in the local computer
		self.nameLocal=nameLocal

		#QFileInfo: system independant file information (path, name,...)
		self.prm=PCore.QFileInfo() 
		self.rawData=PCore.QFileInfo()
		self.prb=PCore.QFileInfo()
		
		self.reset(ServerPath,NASPath)
		
	def reset(self,ServerPath,NASPath):
		#processing/transfer
		self.toProcess=False
		self.isRunning=False
		self.isDone=False
		self.crashed=False  
		
		#transfer
		self.toTransfer=False
		self.isBackup=False   #isDone and result are on NAS (client can retrieve the result)
		self.NasToServer=True #if False, transfer will be Server->NAS
		self.transferCrash=False
		
		self.isOK=False
		self.serverFinished=False
		
		#view related
		self.isChecked=True
		self.state=""
		
		#root for the server and the nas
		self.server=PCore.QDir(ServerPath)
		self.NAS=PCore.QDir(NASPath)
		
		#look for the folder in the server and in the NAS
		self.serverFolder=self.look_for_subfolder(folderName=self.nameLocal,root=ServerPath)
		self.NASFolder=self.look_for_subfolder(folderName=self.nameLocal,root=NASPath)
		
		#case 1: no folder at all
		if self.serverFolder==None and self.NASFolder==None:
			self.isOK=False
			self.state="folder not found in NAS (neither on server)"
			self.serverFinished=True
			return
		
		#case 2: no folder on nas, a folder on server
		if self.NASFolder==None:
			#create folder on NAS
			self.NAS.mkdir(self.nameLocal)
			self.NASFolder=PCore.QDir(self.NAS.filePath(self.nameLocal))
		
			self.folder=self.serverFolder
			serverRaw=self.check_files_exist()
			serverDone=self.check_if_done()
			
			#2a: done on server, to do= back up on NAS
			if serverDone:
				self.toTransfer=True
				self.NasToServer=False
				self.state="Already Done (kwik file on server)- Waiting to be transfered (Server -> NAS)"
				return
			
			#2b: raw data on server, to do= process on server
			if serverRaw:
				self.arguments=[self.prm.fileName()]
				self.toProcess=True
				self.state="waiting to be process (server)"
				return
			
			#2c: empty folder
			self.isOK=False
			self.state="files not found in NAS (neither on server)"
			self.serverFinished=True
			return
			
		#case 3: no folder on server, a folder on NAS
		if self.serverFolder==None:
			self.folder=self.NASFolder
			NASRaw=self.check_files_exist()
			NASDone=self.check_if_done()
			#3a: no raw data on nas
			if not NASRaw:
				self.isOK=False
				self.state="raw Data not found in NAS (neither on server)"
				self.serverFinished=True
				return
			#3b: raw data and done on NAS 
			if NASDone:
				self.state="Already done (kwik file found on NAS)"
				self.isBackup=True
				self.serverFinished=True
				return
			#3c: raw data on NAS, to do=transfer
			self.state="waiting to be transfered (NAS->server)"
			self.waitingSince=time.time()
			self.toTransfer=True
			self.NasToServer=True
			#create folder on server
			self.server.mkdir(self.nameLocal)
			self.serverFolder=PCore.QDir(self.server.filePath(self.nameLocal))
			return
			
		#case 4:folders on both side
		self.folder=self.NASFolder
		NASRaw=self.check_files_exist()
		NASDone=self.check_if_done()
		self.folder=self.serverFolder
		serverRaw=self.check_files_exist()
		serverDone=self.check_if_done()
		#4a: everything is on NAS
		if NASRaw and NASDone:
			self.state="Already done (kwik file found on NAS)"
			self.isBackup=True
			self.serverFinished=True
			return
		#4b: no raw data anywhere
		if not NASRaw and not serverRaw:
			self.isOK=False
			self.state="raw Data not found in NAS (neither on server)"
			self.serverFinished=True
			return
		#4c: raw data somewhere, done on server-> transfer everything from server to NAS
		if serverDone:
			self.toTransfer=True
			self.NasToServer=False
			self.state="Already Done (kwik file on server)- Waiting to be transfered (Server -> NAS)"
			return
		#4d: done on nas but no raw data, raw data on server (weird)
		if NASDone and serverRaw:
			self.toTransfer=True
			self.NasToServer=False
			self.state="Weird: kwik file on NAS and raw Data on server -- transfer Server->NAS"
			return
		#4e: raw data on server
		if serverRaw:
			self.folder=self.serverFolder
			self.check_files_exist()
			self.arguments=[self.prm.fileName()]
			self.toProcess=True
			self.state="waiting to be process (server)"
			return
		#4f: raw data on NAS
		if NASRaw:
			self.folder=self.NASFolder
			self.check_files_exist()
			self.state="waiting to be transfered (NAS->server)"
			self.toTransfer=True
			self.NasToServer=True

	#----------------------------------------------------------------------------------------------------------
	#Processing
	#----------------------------------------------------------------------------------------------------------
	def run_klusta(self,process):
		process.setWorkingDirectory(self.folder.absolutePath())
		process.start(PROGRAM,self.arguments)
		self.state="Klusta running (on server)"
		self.isRunning=True
		self.toProcess=False
		
		
	def is_done(self,exitcode):
		self.isDone=True
		self.isRunning=False
		if self.crashed:
			self.state="Killed by user (on server)"
			name="kill_"+time.strftime('%Y_%m_%d_%H_%M')
		elif exitcode!=0:
			self.crashed=True
			self.state="Klusta crashed (on server)"
			name="crash_"+time.strftime('%Y_%m_%d_%H_%M')
		else:
			self.state="Done (Klusta ran) - Waiting to be transfered (Server->NAS)"
			self.toTransfer=True
			self.NasToServer=False
			
		if self.crashed:
			self.folder.mkdir(name)
			self.folder.setFilter(PCore.QDir.Files)
			for fileName in self.folder.entryList():
				if not (fileName.endswith(".raw.kwd") or fileName.endswith(".dat")):
					if not (fileName.startswith("crash") or fileName.startswith("kill")):
						self.folder.rename(fileName,name+"/"+fileName)
			self.serverFinished=True
			self.folder.setFilter(PCore.QDir.AllEntries|PCore.QDir.NoDotAndDotDot)
			self.crashed=False
			self.isDone=False
	
	#----------------------------------------------------------------------------------------------------------
	# transfer -- if file alredy exist, copy() function will not overwrite but do nothing
	#----------------------------------------------------------------------------------------------------------
	def transfer(self):
		if self.toTransfer:
			self.toTransfer=False
			if self.NasToServer:
				return self.copy_fromNAS_toServer()
			else:
				return self.copy_fromServer_toNAS()
			
	def state_transfer(self):
		if self.NasToServer:
			return "(NAS->Server)"
		else:
			return "(Server->NAS)"
	
	def copy_fromNAS_toServer(self):
		self.folder=self.NASFolder
		
		#check if files are still on NAS
		if not (self.prm.exists() and self.prb.exists() and self.rawData.exists()):
			self.isOK=self.check_files_exist()
			if not self.isOK:
				self.state=self.state+" (on NAS)"
				return False
		
		#if no folder on server, define one
		if not self.serverFolder.exists():
			self.server.mkdir(self.nameLocal)
			self.serverFolder=PCore.QDir(self.server.filePath(self.nameLocal))

		#move prm file (no overwrite)
		NASprm=PCore.QFile(self.prm.filePath())  						#file on nas
		prmPathServer=self.serverFolder.filePath(self.prm.fileName()) 	#file on server (path)
		NASprm.copy(prmPathServer) 										#copy NAS -> Server
		self.prm.setFile(prmPathServer)									#set new File
		if not self.prm.exists():										#chek if copy successful
			self.state="could not copy prm file (NAS->server)"
			return False
		self.arguments=[self.prm.fileName()]
		
		#move prb file (no overwrite)
		NASprb=PCore.QFile(self.prb.filePath())
		prbPathServer=self.serverFolder.filePath(self.prb.fileName())
		NASprb.copy(prbPathServer)
		if not self.prb.exists():
			self.state="could not copy prb file (NAS->server)"
			return False
			
		#move rawData (no overwrite)
		NASdata=PCore.QFile(self.rawData.filePath())
		dataPathServer=self.serverFolder.filePath(self.rawData.fileName())
		NASdata.copy(dataPathServer)
		if not self.rawData.exists():
			self.state="could not copy raw data (NAS->server)"
			return False

		self.folder=self.serverFolder
		self.folder.refresh()
		self.check_files_exist()  #to set the correct names
		self.toProcess=True
		self.state="waiting to be process (on server)"
		return True

	def copy_fromServer_toNAS(self):
		if self.isDone and not self.crashed and not self.isBackup:
			self.folder=self.serverFolder
			#check if files are still on server
			if not (self.prm.exists() and self.prb.exists() and self.rawData.exists()):
				self.isOK=self.check_files_exist()
				if not self.isOK:
					self.state=self.state+" (on server)"
					return False
			
			self.toTransfer=False
			
			#if no folder on nas, define one
			if not self.NASFolder.exists():
				self.NAS.mkdir(self.nameLocal)
				self.NASFolder=PCore.QDir(self.NAS.filePath(self.nameLocal))
			
			#copy recursively
			self.copy_recursive(self.folder,self.NASFolder)
			self.NASFolder.refresh()
			self.state="server results transfered to NAS"
			self.isBackup=True
			self.serverFinished=True