import time
#QT
import PyQt4.QtCore as QtCore

from config import PROGRAM

#------------------------------------------------------------------------------------------------------------
#  Folder meant to be process with klusta 
#  For correct behaviour, every file inside should have the same basename (and it should be the folder's name)
#------------------------------------------------------------------------------------------------------------
class KlustaFolder(QtCore.QDir):
	
	def __init__(self,path,icon=None):
		self.path=str(path)
		super(KlustaFolder,self).__init__(self.path)
		self.state="--"
		self.name=self.dirName()
		
		#QFileInfo: system independant file information (path, name,...)
		self.prm=QtCore.QFileInfo() 
		self.rawData=QtCore.QFileInfo()
		self.prb=QtCore.QFileInfo()
		
		self.icon=icon
		self.program=PROGRAM
		
	def reset_icon(self):
		if len(self.entryList())==0:
			self.icon="folder-grey.png"
		elif len(self.entryList(['*.kwik']))>0:
			self.icon="folder-violet.png"
		elif len(self.entryList(['*.dat','*.raw.kwd']))>0:
			self.icon="folder-green.png"
			if self.exists(self.name+".prm") and self.exists(self.name+".prb"):
				self.icon="folder-green-star.png"
		elif self.exists(self.name+".prm") and self.exists(self.name+".prb"):
			self.icon="folder-blue-star.png"
		else:
			self.icon="folder-blue.png"
		
	#not use
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
			if self.exists(self.name+".prm"):
				self.prm.setFile(self.filePath(self.name+".prm"))
			else:
				listPrm=self.entryList(["*.prm"])
				if len(listPrm)>0:
					self.prm.setFile(self.filePath(listPrm[0]))
				else:
					self.state="prm file not found"
					return False
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
			self.state="Folder %s not found"%self.name
		return False
		
	#look for experiment_name, raw_data_files and prb_files in the parameter file (.prm)
	# This function execute the prm file as a python script: it's not safe if user mess with prm file
	def extract_info_from_prm(self):
		prmPath=self.prm.filePath()
		with open(prmPath) as f:
			try:
				code=compile(f.read(),prmPath,'exec')
				exec(code,globals(),locals())
				if 'raw_data_files' in locals():
					self.rawData.setFile(self.filePath(locals()['raw_data_files']))
				else:
					return False
				if 'prb_file' in locals():
					self.prb.setFile(self.filePath(locals()['prb_file']))
				else:
					return False
				return True
			except:
				print("Error in extract_info_frm_prm:",str(IOError))
				return False
			
	#check if rawdata, prb and prm files are still in the folder
	def can_be_process(self):
		if self.exists():
			self.refresh()
			if self.has_kwik():
				return False
			self.prm.refresh()
			self.prb.refresh()
			self.rawData.refresh()
			if self.prm.exists() and self.prb.exists() and self.rawData.exists():
				self.state="ready to be processed"
				return True
		return self.fetch_files()
	
	#check if kwik file in folder
	def has_kwik(self):
		self.refresh()
		if self.exists(self.name+".kwik"):
			self.state="Done (kwik file)"
			return True
		return False
	
	#check if .dat or .raw.kwd file in folder
	def has_rawData(self):
		self.refresh()
		self.rawData.refresh()
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
		return False
		
	def extension_list(self):
		extList=[]
		for fileName in self.entryList(QtCore.QDir.Files):
			extList.append(str(fileName.completeSuffix()))
		return extList
	
	def subfolder_list(self):
		subList=[]
		for folderName in self.entryList(QtCore.QDir.Dirs|QtCore.QDir.NoDotAndDotDot):
			subList.append(str(folderName))
		return subList
	
	#---------------------------------------------------------------------------------------------
	#create prm and prb file from models
	def create_files(self,prmModel,prbModel,rawData=None):
		#look for raw data
		if not self.has_rawData() and rawData is None:
			self.state="raw data not found"
			return False
		#prm and prb files
		prmPath=self.filePath(self.name+'.prm')
		prbPath=self.filePath(self.name+'.prb')
		#Delete existing file
		if QtCore.QFile.exists(prmPath):
			QtCore.QFile.remove(prmPath)
		if QtCore.QFile.exists(prbPath):
			QtCore.QFile.remove(prbPath)
		#Copy file
		res1=QtCore.QFile.copy(prmModel.filePath(),prmPath)
		res2=QtCore.QFile.copy(prbModel.filePath(),prbPath)
		if not (res1 and res2):
			print("could not copy prm or prb model")
			return False
		#Modify prm
		output=[]
		with open(prmPath,"r+") as prm:
			find=0
			for line in prm:
				if line.startswith("experiment_name"):
					line="experiment_name = '%s' \n"%self.name
					find+=1
				elif line.startswith("raw_data_files"):
					if rawData is None:
						line="raw_data_files = '%s' \n"%self.rawData.fileName()
					else:
						line="raw_data_files = '%s' \n"%rawData
					find+=1
				elif line.startswith("prb_file"):
					line="prb_file = '%s.prb' \n"%self.name
					find+=1
				output.append(line)
			if find!=3:
				print("prm Model incorrect")
				QtCore.QFile.remove(prmPath)
				return False
			prm.seek(0)
			prm.write(''.join(output))
			prm.truncate()
		self.prm.setFile(prmPath)
		self.prb.setFile(prbPath)
		return True
	
	#---------------------------------------------------------------------------------------------
	# Run Klusta
	def run_process(self,process):
		if self.can_be_process():
			arguments=[self.prm.fileName()]
			self.state="try to launch klusta"
			process.setWorkingDirectory(self.path)
			print(self.program,arguments)
			process.start(self.program,arguments)
			process.waitForStarted()
			if process.state()==QtCore.QProcess.Running:
				self.state="klusta running"
				return True
				#self.icon= ? + send message to fileBrowser
			else: #if process.error()==QtCore.QProcess.FailedToStart:
				self.state="failed to start program:%s"%PROGRAM
				print(process.error())
		return False
	
	def is_done(self,exitcode):
		self.refresh()
		if exitcode==42:
			self.state="Killed by user"
			name="kill_"+time.strftime('%Y_%m_%d_%H_%M')
		elif exitcode!=0:
			self.state="Klusta crashed"
			name="crash_"+time.strftime('%Y_%m_%d_%H_%M')
		else:
			self.state="Done (Klusta ran)"
			return True
		#if crash/kill, put files in a subfolder
		if exitcode!=0:
			self.mkdir(name)
			extension_list=["*.high.kwd","*.kwik","*.kwx","*.log","*.low.kwd","*.prb","*.prm"]
			if self.rawData.fileName().endswith(".dat"):
				self.remove(self.name+".raw.kwd")
			for fileName in self.entryList(extension_list,QtCore.QDir.Files):
				self.rename(fileName,name+"/"+fileName)
			self.refresh()
		return False
	
	
	
	
	
