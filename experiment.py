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
	
	def __init__(self,folderPath):
		#check if folder exist
		self.folder=PCore.QDir(str(folderPath))
		if not self.folder.exists():
			self.state="folder not found"
			self.isOK=False
			return

		self.name=self.folder.dirName()
			
		#QFileInfo: system independant file information (path, name,...)
		self.prm=PCore.QFileInfo() 
		self.rawData=PCore.QFileInfo()
		self.prb=PCore.QFileInfo()
		
		#Look for the name, raw data and prb in the prm file, check if everything exist
		self.isOK=self.check_files_exist()
		if not self.isOK:
			return
		
		#Warning: check if folder name match experiment_name
		if self.folder.dirName()!=self.name:
			print("Warning: experiment_name differs from folder name, could be trouble ('%s' and '%s')"%(self.folder,self.name))
			
		#Display related: line is checked by default
		self.isChecked=True

		#Processing
		self.toProcess=False
		self.isRunning=False
		self.isDone=False
		self.crashed=False
		self.arguments=[self.prm.fileName()]
		self.onServer=False
		
		self.check_if_done()
		
		

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
		elif exitcode!=0:
			self.crashed=True
			self.state="Klusta crashed"
		else:
			self.state="Done (Klusta ran)"

	#----------------------------------------------------------------------------------------------------------
	# Check files
	#----------------------------------------------------------------------------------------------------------
	def check_if_done(self):
		#Look for a kwik file
		if self.folder.exists(self.name+".kwik"):
			self.isDone=True
			self.state="Done (found a kwik file)"
			return True
		return False
		
	def check_files_exist(self):
		#find prm file
		listPrm=self.folder.entryList(["*.prm"])
		if len(listPrm)>0:
			self.prm.setFile(self.folder.absoluteFilePath(listPrm[0]))
			#look for rawData and prb in prm file, check if they exist
			if self.check_prm():
				if self.rawData.exists():
					if self.prb.exists():
						self.state="--"
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
#------------------------------------------------------------------------------------------------------------------
class ExperimentOnServer(Experiment):
	
	def __init__(self,nameLocal,ServerPath,NASPath):
		
		#name of the folder in the local computer
		self.nameLocal=nameLocal
		
		#root for the server and the nas
		self.server=PCore.QDir(ServerPath)
		self.NAS=PCore.QDir(NASPath)
		
		#QFileInfo: system independant file information (path, name,...)
		self.prm=PCore.QFileInfo() 
		self.rawData=PCore.QFileInfo()
		self.prb=PCore.QFileInfo()
		
		#processing/transfer
		self.toTransfer=False
		self.toProcess=False
		self.isRunning=False
		self.isDone=False
		self.crashed=False
		
		self.isBackup=False
		
		self.isChecked=True
		
		#look for the folder in the server
		iterFolder=PCore.QDirIterator(ServerPath,PCore.QDir.Dirs|PCore.QDir.NoSymLinks|PCore.QDir.NoDotAndDotDot, PCore.QDirIterator.Subdirectories)
		self.folder=None
		while iterFolder.hasNext():
			if iterFolder.fileName()==self.nameLocal:
				self.folder=PCore.QDir(iterFolder.filePath())
				break
			iterFolder.next()
			
		#if the folder and the files are found in the server, experiment is ready to be processed
		if self.folder!=None:
			self.isOK=self.check_files_exist()
			if self.isOK:
				if not self.check_if_done():
					self.arguments=[self.prm.fileName()]
					self.toProcess=True
					self.state="waiting to be process (server)"
				else:
					#experiment is done on the server
					#look for kwik file and all in nas, if not there copy
					# --> test if backup, if not put self.toTransfer=True 
					pass
				return

		#if not in server, look in NAS
		iterFolder=PCore.QDirIterator(NASPath,PCore.QDir.Dirs|PCore.QDir.NoSymLinks|PCore.QDir.NoDotAndDotDot, PCore.QDirIterator.Subdirectories)
		self.folder=None
		while iterFolder.hasNext():
			if iterFolder.fileName()==self.nameLocal:
				self.folder=PCore.QDir(iterFolder.filePath())
				break
			iterFolder.next()
		
		if self.folder!=None:
			self.isOK=self.check_files_exist()
			if not self.isOK:
				self.state=self.state+"(on NAS)"
			else:
				if not self.check_if_done():
					self.state="waiting to be transfered (NAS->server)"
					self.waitingSince=time.time()
					self.toTransfer=True
					self.arguments=[self.prm.fileName()]
					return
				else:
					self.state="Done (found kwik file in NAS)"
		else:
			self.isOK=False
			self.state="folder not found in NAS (neither on server)"

	
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
		self.isRunning=False
		self.isDone=True
		if self.crashed:
			self.state="Killed by user (on server)"
		elif exitcode!=0:
			self.crashed=True
			self.state="Klusta crashed (on server)"
		else:
			self.state="Done (Klusta ran, on server)"
	
	#----------------------------------------------------------------------------------------------------------
	# transfer  if file alredy exist, copy() function will not overwrite but do nothing
	#----------------------------------------------------------------------------------------------------------
	def transfer(self):
		if self.isOK:
			if self.toTransfer:
				self.toTransfer=False
				#toTransfer, not isDone
				if not self.isDone:
					return self.copy_fromNAS_toServer()
				#toTransfer, isDone, not crashed, not backUp
				elif (not self.crashed and not self.isBackUp):
					return self.copy_fromNAS_toServer()
			self.state="error: transfer called but impossible"
			return False
		else:
			self.state="not ok"
			return False
	
	def copy_fromNAS_toServer(self):
		#self.prm, self.folder should be the one found in NAS

		#check if files are still on NAS
		if not (self.prm.exists() and self.prb.exists() and self.rawData.exists()):
			self.isOK=self.check_files_exist()
			if not self.isOK:
				self.state=self.state+" (on NAS)"
				return False
		
		#create folder on server
		self.server.mkdir(self.folder.dirName())
		folderPathServer=self.server.absoluteFilePath(self.folder.dirName())
		self.folder.setPath(folderPathServer)

		#move prm file
		NASprm=PCore.QFile(self.prm.absoluteFilePath())  		#file on nas
		prmPathServer=folderPathServer+"/"+self.prm.fileName() 	#file on server (path)
		NASprm.copy(prmPathServer) 								#copy NAS-> Server
		self.prm.setFile(prmPathServer)							#set new File
		if not self.prm.exists():								#chek if copy successful
			self.state="could not copy prm file (NAS->server)"
			return False
		
		#move prb file
		NASprb=PCore.QFile(self.prb.absoluteFilePath())
		prbPathServer=folderPathServer+"/"+self.prb.fileName()
		NASprb.copy(prbPathServer)
		if not self.prb.exists():
			self.state="could not copy prb file (NAS->server)"
			return False
			
		#move rawData
		NASdata=PCore.QFile(self.rawData.absoluteFilePath())
		dataPathServer=folderPathServer+"/"+self.rawData.fileName()
		NASdata.copy(dataPathServer)
		if not self.rawData.exists():
			self.state="could not copy raw data (NAS->server)"
			return False

		self.toProcess=True
		self.state="waiting to be process (on server)"
		return True
		
		
	def look_for_result_files(self):
		
		
		
	def copy_fromServer_toNAS(self):
		if self.isDone and not self.isCrashed and not self.isBackup:
			self.toTransfer=False



			#if not (self.prm.exists() and self.prb.exists() and self.rawData.exists()):
				#self.isOK=self.check_files_exist()
				#if not self.isOK:
					#self.state=self.state+" - files not found on server"
					#return False
			#else:
				##look for folder in NAS
				#iterFolder=PCore.QDirIterator(NASPath,PCore.QDir.Dirs|PCore.QDir.NoSymLinks|PCore.QDir.NoDotAndDotDot, PCore.QDirIterator.Subdirectories)
				#ffolderPathNAS=None
				#while iterFolder.hasNext():
					#if iterFolder.fileName()==self.nameLocal:
						#folderPathNAS=iterFolder.filePath()
						#break
					#iterFolder.next()
				##if not found, create a folder
				#if folderPathNAS==None:
					#self.NAS.mkdir(self.folder.dirName())
					#folderPathNAS=self.NAS.absoluteFilePath(self.folder.dirName())
				
				##move prm file
				#Serverprm=PCore.QFile(self.prm.absoluteFilePath())  	#file on server
				#prmPathNAS=folderPathNAS+"/"+self.prm.fileName() 		#file on nas (path)
				#Serverprm.copy(prmPathNAS) 								#copy server -> NAS
				#self.prm.setFile(prmPathNAS)							#set new File
				#if not self.prm.exists():								#chek if copy successful
					#self.state=self.state+" - could not copy prm file (server -> Nas)"
					#return False
				
				##move prb file
				#Serverprb=PCore.QFile(self.prb.absoluteFilePath())
				#prbPathNAS=folderPathNAS+"/"+self.prb.fileName()
				#Serverprb.copy(prbPathNAS)
				#if not self.prb.exists():
					#self.state=self.state+" - could not copy prb file (Server->NAS)"
					#return False
				
				##move rawData
				#Serverdata=PCore.QFile(self.rawData.absoluteFilePath())
				#dataPathNAS=folderPathNAS+"/"+self.rawData.fileName()
				#Serverdata.copy(dataPathNAS)
				#if not self.rawData.exists():
					#self.state=self.state+" - could not copy raw data (Server->NAS)"
					#return False
				
				#self.isBackup=True
				#self.state=self.state+" - files backup in NAS"
				#return True
