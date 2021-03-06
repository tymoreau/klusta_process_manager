import sys
import signal
import os
 
#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtSql

#Import views
from klusta_process_manager.processManager import ProcessManager
from klusta_process_manager.fileBrowser import FileBrowser
from klusta_process_manager.experiment import Experiment

#Import parameter
from klusta_process_manager.config import TITLE, get_user_folder_path, read_user_config_file

#----------------------------------------------------------------------------------------------------------
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

#----------------------------------------------------------------------------------------------------------
class MainWindow(QtGui.QWidget):
	sendsMessage=QtCore.pyqtSignal(object)
	
	def __init__(self,database,ROOT,BACK_UP, IP_SERVER, PORT_SERVER):
		super(MainWindow,self).__init__()
		self.rootPath=ROOT
		self.backUPPath=BACK_UP

		WIDTH=800
		HEIGHT=600
		param=read_user_config_file()
		if param is not None:
			try:
				HEIGHT=param["window_pixel_height"]
				WIDTH=param["window_pixel_width"]
			except KeyError:
				pass

		#error handler
		self.err_box=None
		
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
		self.fileBrowser=FileBrowser(ROOT,self)
		self.fileBrowser.animalComboBox.currentIndexChanged.connect(self.on_animal_change)
		self.fileBrowser.set_animalComboBox(self.animalFolderList)
		
		self.processManager=ProcessManager(BACK_UP,IP_SERVER,PORT_SERVER,BACK_UP, self)
		self.logView=LogView(self)

		#Connect views
		self.fileBrowser.button_add.clicked.connect(self.add_to_process_manager)

		#Connect message to log
		self.processManager.sendsMessage.connect(self.logView.add_message)
		self.sendsMessage.connect(self.logView.add_message)

		#read save
		self.add_to_process_manager_from_save()

		#Layout
		splitterVertical=QtGui.QSplitter(QtCore.Qt.Vertical)
		splitterVertical.addWidget(self.fileBrowser)
		splitterVertical.addWidget(self.processManager)
		splitterVertical.setChildrenCollapsible(False)
		splitterVertical.setStretchFactor(0,2)
		
		self.fileBrowser.setMinimumSize(WIDTH-20,int(HEIGHT/2)-20)
		self.processManager.setMinimumSize(WIDTH-20,int(HEIGHT/2)-20)
		
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(splitterVertical)
		vbox.addWidget(self.logView.label)
		
		self.setLayout(vbox)
		self.setMinimumSize(WIDTH,HEIGHT)
		self.setWindowTitle(TITLE)

	def std_err_post(self, msg):
		'''
		This method receives stderr text strings as a pyqtSlot. 
		http://stackoverflow.com/a/28505463/4720935
		'''
		if self.err_box is None:
			self.err_box = QtGui.QMessageBox()
			self.err_box.finished.connect(self.clear)
		self.err_box.setText(self.err_box.text() + msg)
		self.err_box.show()

	def clear(self):
		self.err_box.setText('')

	#TODO
	def on_directory_change(self,path):
		if path==self.rootPath:
			print(self.rootPath, "has changed")
			#check for new/deleted animal (database + list)
		else:
			folderName=QtCore.QFileInfo(path).fileName()
			if folderName in self.experimentDict:
				self.experimentDict[folderName].reset_folder_icon()
				self.fileBrowser.model.update_exp(self.experimentDict[folderName])
				self.processManager.model.update_exp(self.experimentDict[folderName])
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
				exp=Experiment(expInfoDict,parent=self)
				if exp.isValid:
					self.experimentDict[folderName]=exp
			try:
				expList.append(self.experimentDict[folderName])
				self.watchList.append(self.experimentDict[folderName].pathLocal)
			except KeyError:
				pass
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

	def add_to_process_manager_from_save(self):
		userPath=get_user_folder_path()
		filePath=os.path.join(userPath,"experimentListServer.save")
		expList=[]
		if not os.path.exists(filePath):
			return
		with open(filePath,"r") as f:
			for folderName in f:
				folderName=folderName.strip()
				if folderName not in self.experimentDict:
					expInfoDict=self.database.get_experimentDict(folderName)
					if expInfoDict is None:
						print("not ok")
						continue
					exp=Experiment(expInfoDict,parent=self)
					self.experimentDict[folderName]=exp
				expList.append(self.experimentDict[folderName])
		if expList:
			self.processManager.add_experiments_on_server(expList)
				

	def closeEvent(self,event):
		expList=self.experimentDict.values()
		if self.processManager.on_close():
			self.fileBrowser.on_close()
			self.database.reverbate_change(expList)
			self.database.close()
			event.accept()
			return
		event.ignore()
