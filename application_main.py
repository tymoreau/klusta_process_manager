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
		
		#Views
		self.fileBrowser=FileBrowser(database)
		self.processManager=ProcessManager(BACK_UP)
		self.logView=LogView(self)

		#Connect views
		self.fileBrowser.button_add.clicked.connect(self.add_to_process_manager)

		#Connect message to log
		self.processManager.sendsMessage.connect(self.logView.add_message)
		self.sendsMessage.connect(self.logView.add_message)
		
		#database
		self.database=database

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

	#Button_add (green arrow): connect FileBrowser to processManager
	def add_to_process_manager(self):
		selection=self.fileBrowser.get_experiment_selection()
		for item in selection:
			folderName=item.data()
			animal=folderName.split('_')[0]
			path=ROOT+"/"+animal+"/Experiments/"+folderName
			state=self.processManager.add_experiment(path)
		self.sendsMessage.emit("Added experiments to list")

	def closeEvent(self,event):
		self.fileBrowser.close()
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
		database=Database(dbName,ROOT,BACK_UP,EXP_PATH,DEFAULT_IMAGE,DATE_TIME_FORMAT,LENGTH_ID)

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
