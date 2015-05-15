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
			self.name=folderPath
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
		
		self.onServer=False #True: experiment being process/transfer on server
		
		#transfer
		self.isBackup=False #True: experiment is on NAS
		self.toTransfer=False
		self.localToNAS=True
		
		self.check_if_done()
		
	#----------------------------------------------------------------------------------------------------------
	#Transfer
	#----------------------------------------------------------------------------------------------------------
	def copy_fromLocal_toNAS(self,NASPath,folderNASPath=None):
		self.toTransfer=False
		
		if folderNASPath==None:
			NAS=PCore.QDir(NASPath)
			self.NAS.mkdir(self.folder.dirName())
			folderNASPath=NASPath+'/'+self.folder.dirName()
			
		#copy recursively
		self.copy_recursive(self.folder,PCore.QDir(folderNASPath))
		self.state="local files transfered to NAS"
		self.isBackup=True
		
	def copy_fromNAS_toLocal(self,folderNASPath):
		self.toTransfer=False
		
		#copy recursively
		self.copy_recursive(PCore.QDir(folderNASPath),self.folder)
		self.state="NAS files transfered to local computer"
		

	def copy_recursive(self,folder,destinationFolder):
		for fileInfo in folder.entryInfoList():
				if fileInfo.isDir():
					if fileInfo.fileName()!='.' and fileInfo.fileName()!='..':
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
		#check if folder exist
		if not self.folder.exists():
			self.state="folder not found"
			return False
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
# to do: self.folderServerPath should be QDir/QFileInfo ? (cross platform) 
#------------------------------------------------------------------------------------------------------------------
class ExperimentOnServer(Experiment):
	
	def __init__(self,nameLocal,ServerPath,NASPath):
		self.reset(nameLocal,ServerPath,NASPath)
		
		
	def reset(self,nameLocal,ServerPath,NASPath):
		#------------------------------------------------------------------------------
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
		self.toProcess=False
		self.isRunning=False
		self.isDone=False
		self.crashed=False   #klusta did not ran properly: tu re-run, need to use overwrite
		
		#transfer
		self.toTransfer=False
		self.isBackup=False   #isDone and result are on NAS (client can retrieve the result)
		self.NasToServer=True #if False, transfer will be Server->NAS
		self.transferCrash=False
		
		self.isOK=False
		self.serverFinished=False
		
		#table view related
		self.isChecked=True
		
		#------------------------------------------------------------------------------
		
		#look for the folder in the server and in the NAS
		self.folderServerPath=self.look_for_subfolder(folderName=self.nameLocal,root=ServerPath)
		self.folderNASPath=self.look_for_subfolder(folderName=self.nameLocal,root=NASPath)
		
		print "folder server",self.folderServerPath
		print "folder nas",self.folderNASPath
		
		doneOnServer=False
		self.name=nameLocal
		
		#if there is a folder on the server
		if self.folderServerPath!=None:
			self.folder=PCore.QDir(self.folderServerPath)
			self.isOK=self.check_files_exist()
			#if rawData, prb and prm are in the folder
			if self.isOK:
				#if experiment is done (crashed or not)
				if self.check_if_done():
					doneOnServer=True
				#if experiment is not done, it is ready to be process, return
				else:
					self.arguments=[self.prm.fileName()]
					self.toProcess=True
					self.state="waiting to be process (server)"
					return

		#COMMON CASE: not ready to be process on server but there is a folder on NAS
		if self.folderNASPath!=None:
			self.folder=PCore.QDir(self.folderNASPath)
			self.isOK=self.check_files_exist()
			#if rawData, prb and prm are in the folder
			if self.isOK:
				#if experiment is done (crashed or not)
				if self.check_if_done():
					self.state="Already done (kwik file found on NAS)"
					self.isBackup=True
					self.serverFinished=True
					return
				#if experiment is not done on NAS but done on Server, transfer Server->NAS 
				elif doneOnServer:
					self.toTransfer=True
					self.NasToServer=False
					self.state="Done (kwik file on server)- Waiting to be transfered (Server -> NAS)"
					return
				#COMMON CASE: experiment not done, neither on server or on NAS
				else:
					self.state="waiting to be transfered (NAS->server)"
					self.waitingSince=time.time()
					self.arguments=[self.prm.fileName()]
					self.toTransfer=True
					self.NasToServer=True
					return
			#if something is wrong with rawData, prb or prm on NAS
			else:
				self.state=self.state+"(on NAS)"
				return
				
		#Weird case: experiment done on server but no folder found on NAS
		if doneOnServer and self.folderNASPath==None:
			#create folder on NAS
			self.NAS.mkdir(self.nameLocal)
			self.folderNASPath=NASPath+"/"+self.nameLocal
			#ready to transder
			self.toTransfer=True
			self.NasToServer=False
			self.state="Already Done (kwik file on server)- Waiting to be transfered (Server -> NAS)"
			return
	
		#Folder not in Nas, not in Server
		if self.folderNASPath==None and self.folderServerPath==None:
			self.isOK=False
			self.state="folder not found in NAS (neither on server)"
			self.serverFinished=True
			return
		
		#if none of the cases above
		self.state="error: experimentOnServer.__init__ no case match"
		self.serverFinished=True

	def look_for_subfolder(self,folderName,root):
		iterFolder=PCore.QDirIterator(root)
		while True:
			if iterFolder.fileName()==folderName:
				return iterFolder.filePath()
			if iterFolder.hasNext():
				iterFolder.next()
			else:
				break
		return None

	
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
			self.state="Done (Klusta ran) - Waiting to be transfered (Server->NAS)"
			self.toTransfer=True
			self.NasToServer=False
	
	#----------------------------------------------------------------------------------------------------------
	# transfer  if file alredy exist, copy() function will not overwrite but do nothing
	#----------------------------------------------------------------------------------------------------------
	#to put in model ?
	def transfer(self):
		if self.toTransfer:
			self.toTransfer=False
			if self.NasToServer:
				return self.copy_fromNAS_toServer()
			else:
				return self.copy_fromServer_toNAS()
	
	def copy_fromNAS_toServer(self):
		#self.prm, self.folder should be the one found in NAS
		self.folder=PCore.QDir(self.folderNASPath)

		#self.folderServerPath=self.look_for_subfolder(folderName=self.nameLocal,root=ServerPath)
		#self.folderNASPath=self.look_for_subfolder(folderName=self.nameLocal,root=NASPath)

		#check if files are still on NAS
		if not (self.prm.exists() and self.prb.exists() and self.rawData.exists()):
			self.isOK=self.check_files_exist()
			if not self.isOK:
				self.state=self.state+" (on NAS)"
				return False
		
		#if no folder on server, define one
		if self.folderServerPath==None:
			self.folderServerPath=self.server.absoluteFilePath(self.folder.dirName())
		#create folder on server (mkpath do nothing if folder already there)
		self.server.mkpath(self.folderServerPath)
		#set folder to new location
		self.folder.setPath(self.folderServerPath)

		#move prm file (no overwrite)
		NASprm=PCore.QFile(self.prm.absoluteFilePath())  			#file on nas
		prmPathServer=self.folderServerPath+"/"+self.prm.fileName() #file on server (path)
		NASprm.copy(prmPathServer) 									#copy NAS-> Server
		self.prm.setFile(prmPathServer)								#set new File
		if not self.prm.exists():									#chek if copy successful
			self.state="could not copy prm file (NAS->server)"
			return False
		
		#move prb file (no overwrite)
		NASprb=PCore.QFile(self.prb.absoluteFilePath())
		prbPathServer=self.folderServerPath+"/"+self.prb.fileName()
		NASprb.copy(prbPathServer)
		if not self.prb.exists():
			self.state="could not copy prb file (NAS->server)"
			return False
			
		#move rawData (no overwrite)
		NASdata=PCore.QFile(self.rawData.absoluteFilePath())
		dataPathServer=self.folderServerPath+"/"+self.rawData.fileName()
		NASdata.copy(dataPathServer)
		if not self.rawData.exists():
			self.state="could not copy raw data (NAS->server)"
			return False

		self.toProcess=True
		self.state="waiting to be process (on server)"
		return True

	def copy_fromServer_toNAS(self):
		if self.isDone and not self.crashed and not self.isBackup:
			self.folder=PCore.QDir(self.folderServerPath)
			self.toTransfer=False
			
			if self.folderNASPath==None:
				self.state="error: folderNASPath=None"
				return
			
			#in case NAS folder was erase (will do nothing if not)
			self.NAS.mkdir(self.folderNASPath)
			
			#copy recursively
			self.copy_recursive(self.folder,PCore.QDir(self.folderNASPath))
			self.state="server results transfered to NAS"
			self.isBackup=True
			self.serverFinished=True
			
	def copy_recursive(self,folder,destinationFolder):
		for fileInfo in folder.entryInfoList():
				if fileInfo.isDir():
					if fileInfo.fileName()!='.' and fileInfo.fileName()!='..':
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