#import QT
import sip

sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtSql

class Database(object):
	def __init__(self,name,localPath,backUPPath,expPath,defaultIcon,dateTimeFormats,lengthID):
		
		self.db=QtSql.QSqlDatabase.addDatabase("QSQLITE","SQLITE")
		self.db.setDatabaseName(name)

		self.localPath=localPath
		self.backUPPath=backUPPath
		self.expPath=expPath.strip(QtCore.QDir.separator())
		self.defaultIcon=defaultIcon
		self.dateTimeFormats=dateTimeFormats
		self.lengthID=lengthID
		
	def _open(self):
		return self.db.open()

	def close(self):
		return self.db.close()

	#Create/Update tables "Animal" and "Experiment"
	def update_tables(self):
		tables=self.db.tables()
		if sorted(tables)!=['Experiment','Animal']:
			#delete previous tables
			for table in tables:
				self.db.exec_("Drop table %s"%table)
			#Create tables
			sqlAnimal=("CREATE table Animal"
					   "(animalID TEXT PRIMARY KEY UNIQUE,"
					   "pathLocal TEXT UNIQUE,"
					   "pathBackUP TEXT)")
			self.db.exec_(sqlAnimal)

			sqlExperiment=("CREATE table Experiment"
						   "(folderName TEXT PRIMARY KEY UNIQUE,"
						   "yearMonth TEXT,"
						   "day TEXT,"
						   "time TEXT,"
						   "animalID TEXT,"
						   "icon TEXT,"
						   "pathLocal TEXT UNIQUE,"
						   "pathBackUP TEXT,"
						   "FOREIGN KEY(animalID) REFERENCES Animal(animalID))")
			self.db.exec_(sqlExperiment)

		self.db.transaction()
		#Update table animal
		self.update_animals_from_root(self.localPath)
		#Update table experiment
		self.update_experiments()
		self.db.commit()

#---------------------------------------------------------------------------------------------------------
# Animal table - update functions
#--------------------------------------------------------------------------------------------------------- 
	#Update table Animal to match content of root folder
	def update_animals_from_root(self,root):
		rootFolder=QtCore.QDir(root)
		animalList=self.get_animalID_list()

		# Add new folders
		for folder in rootFolder.entryList(["no file"],QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot):
			if str(folder[-self.lengthID:]).isdigit():
				if folder in animalList:
					animalList.remove(folder)
				else:
					animalPathLocal=rootFolder.filePath(folder)
					self.add_animal(folder,animalPathLocal)

		#Remove deleted folders
		if len(animalList)>0:
			for animal in animalList:
				self.delete_animal(animal)

	#Add an entry to table Animal
	def add_animal(self,folderName,animalPathLocal):
		query=QtSql.QSqlQuery(self.db)
		animalPathBackUP=QtCore.QDir(self.backUPPath).filePath(folderName)
		if not QtCore.QDir(animalPathBackUP).exists():
			animalPathBackUP="unknown"

		sqlAdd=("INSERT INTO Animal"
				"(animalID,pathLocal,pathBackUP)"
				"VALUES (:animalID, :pathLocal, :pathBackUP)")
		query.prepare(sqlAdd)
		query.bindValue(":animalID",folderName)
		query.bindValue(":pathLocal",animalPathLocal)
		query.bindValue(":pathBackUP",animalPathBackUP)
		query.exec_()

	#Delete an entry of table Animal, and the corresponding experiments of table Experiment
	def delete_animal(self,animalID):
		self.db.exec_("Delete From Animal Where animalID='%s'"%animalID)
		self.db.exec_("Delete From Experiment Where animalID='%s'"%animalID)

#---------------------------------------------------------------------------------------------------------
# Get lists
#--------------------------------------------------------------------------------------------------------- 
	def get_animalID_list(self,notEmpty=False):
		query=QtSql.QSqlQuery(self.db)
		if notEmpty:
			#multiline in inner select = query return False
			sqlCount=("SELECT animalID FROM Animal WHERE"
					  "(SELECT COUNT(folderName) FROM Experiment WHERE Experiment.animalID=Animal.animalID)>0")
			query.exec_(sqlCount)
		else:
			query.exec_("Select animalID from Animal")
		l=[]
		while query.next():
			l.append(query.value(0))
		return l

	def get_experiment_list(self,animal=None):
		query=QtSql.QSqlQuery(self.db)
		if animal is None:
			query.exec_("Select folderName from Experiment")
		else:
			query.exec_("Select folderName from Experiment Where animalID='%s'"%animal)
		l=[]
		while query.next():
			l.append(query.value(0))
		return l

	def get_experimentInfo_list(self,animal=None):
		query=QtSql.QSqlQuery(self.db)
		if animal is None:
			query.exec_("Select * from Experiment")
		else:
			query.exec_("Select * from Experiment Where animalID='%s'"%animal)
		l=[]
		while query.next():
			l.append({"folderName":query.value(0),
					  "yearMonth":query.value(1),
					  "day":query.value(2),
					  "time":query.value(3),
					  "animalID":query.value(4),
					  "icon":query.value(5),
					  "pathLocal":query.value(6),
					  "pathBackUP":query.value(7)})
		return l

	def get_experimentDict(self,folderName):
		query=QtSql.QSqlQuery(self.db)
		query.exec_("Select * from Experiment Where folderName='%s'"%folderName)
		while(query.next()):
			expDict={"folderName":query.value(0),
					 "yearMonth":query.value(1),
					 "day":query.value(2),
					 "time":query.value(3),
					 "animalID":query.value(4),
					 "icon":query.value(5),
					 "pathLocal":query.value(6),
					 "pathBackUP":query.value(7)}
			return expDict
		return None

#--------------------------------------------------------------------------------------------------------- 
# Experiment table - update functions
#---------------------------------------------------------------------------------------------------------
	def update_experiments(self):
		expList=self.get_experiment_list()
		query=QtSql.QSqlQuery(self.db)
		
		#For each animal, get folder "Experiments" (self.expPath)
		query.exec_("Select pathLocal,animalID,pathBackUP from Animal")
		
		#add new folders
		while query.next():
			pathLocalExp=QtCore.QDir(query.value(0)).filePath(self.expPath)  #ex: ../Rat034/Experiments
			animalID=query.value(1)
			pathBackUPExp=QtCore.QDir(query.value(2)).filePath(self.expPath)
			
			animalExp=QtCore.QDir(pathLocalExp)

			for folder in animalExp.entryList(["no file"],QtCore.QDir.AllDirs|QtCore.QDir.NoDotAndDotDot):
				if folder in expList:
					expList.remove(folder)
				elif folder.startswith(animalID):
					expPathLocal=animalExp.filePath(folder)
					if pathBackUPExp.startswith("unknown"):
						expPathBackUP="unknown"
					else:
						expPathBackUP=QtCore.QDir(pathBackUPExp).filePath(folder)
					self.add_experiment(folder,animalID,expPathLocal,expPathBackUP)
					
		#remove deleted folders
		if len(expList)>0:
			for exp in expList:
				self.delete_exp(exp)

	# Convert a string into several date objects
	# Use to check folder validity and to display date in FileBrowser
	def folderName_to_date(self,folderName,animalID):
		dateString=folderName.replace(animalID,"")
		valid=False
		for dateFormat in self.dateTimeFormats:
			self.dateTime=QtCore.QDateTime().fromString(dateString,dateFormat)
			if self.dateTime.isValid():
				valid=True
				break
		if not valid:
			return None
		else:
			yearMonth=self.dateTime.toString(" MMM \n yyyy ")
			day=self.dateTime.toString(" ddd dd ")
			time=self.dateTime.toString(" hh:mm ")
			return yearMonth,day,time

	def add_experiment(self,folder,animalID,expPathLocal,expPathBackUP):
		result=self.folderName_to_date(folder,animalID)
		if result is None:
			return  #date not valid
		else:
			yearMonth,day,time=result
		
		query=QtSql.QSqlQuery(self.db)
		sqlAdd=("INSERT INTO Experiment"
				"(folderName, yearMonth, day, time, animalID, icon, pathLocal, pathBackUP)"
				"Values (:folderName, :yearMonth, :day, :time, :animalID, :icon, :pathLocal, :pathBackUP)")
		query.prepare(sqlAdd)
		query.bindValue(":folderName",folder)
		query.bindValue(":yearMonth",yearMonth)
		query.bindValue(":day",day)
		query.bindValue(":time",time)
		query.bindValue(":animalID",animalID)
		query.bindValue(":icon",self.defaultIcon)
		query.bindValue(":pathLocal",expPathLocal)
		query.bindValue(":pathBackUP",expPathBackUP)
		query.exec_()

	def delete_exp(self,exp):
		self.db.exec_("Delete From Experiment Where folderName='%s'"%exp)

	#From model (list of experiment object) to database
	def reverbate_change(self,expList):
		self.db.transaction()
		for exp in expList:
			if exp.hasChange:
				self.db.exec_("Update Experiment SET icon='%s' Where folderName='%s'"%(exp.folder.icon,exp.folderName))
				self.db.exec_("Update Experiment SET pathBackUP='%s' Where folderName='%s'"%(exp.pathBackUP,exp.folderName))
		self.db.commit()

#---------------------------------------------------------------------------------------------------------
if __name__=='__main__':
	from PyQt4 import QtGui
	import sys
	
	QtGui.QApplication.setStyle("plastique")
	app=QtGui.QApplication(sys.argv)
	
	localPath="/data"
	backUPPath="/NAS02"
	expPath="/Experiments"
	defaultIcon="folder-grey.png"
	dateTimeFormat="yyyy_MM_dd_HH_mm"
	lengthID=3

	if QtCore.QDir(localPath).exists() and QtCore.QDir(backUPPath).exists():
		name="database_loc-"+localPath.split('/')[-1]+"_backUP-"+backUPPath.split('/')[-1]+".db"
		print("name=",name)
		database=Database(name,localPath,backUPPath,expPath,defaultIcon,dateTimeFormat,lengthID)
		
		if database._open():
			database.update_tables()
			database.close()
		else:
			print("could not open database")
	else:
		print("path not found")
