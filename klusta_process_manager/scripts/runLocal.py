import sys
import signal

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtSql

from klusta_process_manager.general import MainWindow 
from klusta_process_manager.database import Database
from config import *

def main():
	QtGui.QApplication.setStyle("cleanlooks")
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

if __name__=='__main__':
	main()
