import sys
import signal
 
#Remove Qvariant and all from PyQt (for python2 compatibility)
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
 
#import QT
from PyQt4 import QtCore,QtGui,QtSql

#Import views
from processManager import ProcessManager
from filebrowser import FileBrowser
from database import Database
from experiment import Experiment

#Import parameter
from parameter import *

#-------------------------------------------------------------------------------------------------------------------
# Receive message an print them 
# Keep only 3 lines
class LogView(QtGui.QWidget):
	
	def __init__(self,parent=None):
		super(LogView,self).__init__(parent)
		self.label=QtGui.QLabel()
		self.listMessage=[" "," "," "]
		self.label.setText("\n".join(self.listMessage))
	
	def add_message(self,message):
		msgList=message.split("\n")
		for msg in msgList:
			self.listMessage.append(msg)
		self.listMessage=self.listMessage[-3:]
		self.label.setText("\n".join(self.listMessage))

#-------------------------------------------------------------------------------------------------------------------
class MainWindow(QtGui.QWidget):
	sendsMessage=QtCore.pyqtSignal(object)
	
	def __init__(self,database):
		super(MainWindow,self).__init__()
		#database
		self.database=database
		
		#dictionnary of experiment
		self.experimentDict={}
		
		#watch for change in file system
		self.watcher=QtCore.QFileSystemWatcher(self)
		self.watcher.addPath(ROOT)
		self.watcher.directoryChanged.connect(self.on_directory_change)
		self.watchList=[]
		
		#FileBrowser
		self.animalFolderList=self.database.get_animalID_list(notEmpty=True)
		self.fileBrowser=FileBrowser()
		self.fileBrowser.animalComboBox.currentIndexChanged.connect(self.on_animal_change)
		self.fileBrowser.set_animalComboBox(self.animalFolderList)
		
		self.processManager=ProcessManager(BACK_UP)
		self.logView=LogView(self)

		#Connect views
		self.fileBrowser.button_add.clicked.connect(self.add_to_process_manager)

		#Connect message to log
		self.processManager.sendsMessage.connect(self.logView.add_message)
		self.sendsMessage.connect(self.logView.add_message)

		#Layout
		splitterVertical=QtGui.QSplitter(QtCore.Qt.Vertical)
		splitterVertical.addWidget(self.fileBrowser)
		splitterVertical.addWidget(self.processManager)
		splitterVertical.setChildrenCollapsible(False)
		
		self.fileBrowser.setMinimumSize(MIN_WIDTH-20,int(MIN_HEIGHT/2)-20)
		self.processManager.setMinimumSize(MIN_WIDTH-20,int(MIN_HEIGHT/2)-20)
		
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(splitterVertical)
		vbox.addWidget(self.logView.label)
		
		self.setLayout(vbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle(TITLE)
		
	#TODO
	def on_directory_change(self,path):
		if path==ROOT:
			print(ROOT, "has changed")
			#check for new/deleted animal (database + list)
		else:
			folderName=QtCore.QFileInfo(path).fileName()
			if folderName in self.experimentDict:
				self.experimentDict[folderName].reset_folder_icon()
				self.fileBrowser.model.update_exp(self.experimentDict[folderName])
			elif folderName in self.animalFolderList:
				print(folderName,"has changed")
				#add/remove exp (database+dict)
		
	def on_animal_change(self,index):
		animalID=self.fileBrowser.animalComboBox.itemText(index)
		experimentInfoList=self.database.get_experimentInfo_list(animal=animalID)
		if self.watchList:
			self.watcher.removePaths(self.watchList)
		self.watchList=[]
		expList=[]
		for expInfoDict in experimentInfoList:
			folderName=expInfoDict["folderName"]
			if folderName not in self.experimentDict:
				self.experimentDict[folderName]=Experiment(expInfoDict,parent=self)
			expList.append(self.experimentDict[folderName])
			self.watchList.append(self.experimentDict[folderName].pathLocal)
		self.watcher.addPaths(self.watchList)
		self.fileBrowser.reset_experimentList(expList)

	#Button_add (green arrow): connect FileBrowser to processManager
	def add_to_process_manager(self):
		selection=self.fileBrowser.get_experiment_selection()
		expList=[]
		for item in selection:
			exp=self.experimentDict[item.data()]
			expList.append(exp)
		self.processManager.add_experiments(expList)

	def closeEvent(self,event):
		expList=self.experimentDict.values()
		self.fileBrowser.model.worker.abort()
		self.database.reverbate_change(expList)
		self.database.close()
		self.processManager.close()
		self.close()

#-------------------------------------------------------------------------------------------------------------------
# MAIN
#-------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
	QtGui.QApplication.setStyle("plastique")
	app = QtGui.QApplication(sys.argv)
	
	backUP=QtCore.QDir(BACK_UP)
	root=QtCore.QDir(ROOT)
	
	if not backUP.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("BACK_UP do not refers to a folder: "+str(BACK_UP))
		msgBox.exec_()
	elif not root.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("ROOT do not refers to a folder: "+str(ROOT))
		msgBox.exec_()
	else:
		#to be able to close wth ctrl+c
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		
		#Create database class
		dbName="database_loc-"+ROOT.split('/')[-1]+"_backUP-"+BACK_UP.split('/')[-1]+".db"
		database=Database(dbName,ROOT,BACK_UP,EXP_PATH,DEFAULT_ICON,DATE_TIME_FORMAT,LENGTH_ID)

		if database._open():
			#Update/create database
			database.update_tables()
			#Open application
			win=MainWindow(database)
			win.setAttribute(QtCore.Qt.WA_DeleteOnClose)
			win.show()
			sys.exit(app.exec_())
		else:
			msgBox=QtGui.QMessageBox()
			msgBox.setText("Could not open database %s"%dbName)
			msgBox.exec_()
