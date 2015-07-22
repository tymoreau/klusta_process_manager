import sys
import signal
import os

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtSql

from klusta_process_manager.general import MainWindow 
from klusta_process_manager.database import Database
import config

def main():
	QtGui.QApplication.setStyle("plastique")
	app = QtGui.QApplication(sys.argv)

	#user config file
	userConfigDict=config.read_user_config_file()
	if userConfigDict is None:
		msgBox=QtGui.QMessageBox()
		msgBox.setText("Could not open user config file %s"%(config.get_user_config_path()))
		msgBox.exec_()
		return
	else:
		BACK_UP=userConfigDict["path_to_back_up"]
		ROOT=userConfigDict["path_to_data"]
		IP_SERVER=userConfigDict["default_ip_for_server"]
		PORT_SERVER=userConfigDict["default_port_for_server"]
		LENGTH_ID=userConfigDict["length_id"]
		DATE_TIME_FORMAT=userConfigDict["dateTime_format"]
		EXP_PATH=userConfigDict["path_from_animal_to_exp"]
		
	backUP=QtCore.QDir(BACK_UP)
	root=QtCore.QDir(ROOT)

	#Check if backUP path and root path exist
	if not backUP.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("BACK_UP do not refers to a folder: "+str(BACK_UP))
		msgBox.exec_()
		return
	if not root.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("ROOT do not refers to a folder: "+str(ROOT))
		msgBox.exec_()
		return
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)

	#Create database class
	dbName="database_loc-"+ROOT.split('/')[-1]+"_backUP-"+BACK_UP.split('/')[-1]+".db"
	dbPath=os.path.join(config.get_user_folder_path(),dbName)
	database=Database(dbPath,ROOT,BACK_UP,EXP_PATH,config.DEFAULT_ICON,DATE_TIME_FORMAT,LENGTH_ID)
	print("done")
	print(type(database))

	if database._open():
		#Update/create database
		database.update_tables()
		#Open application
		win=MainWindow(database,ROOT,BACK_UP,IP_SERVER, PORT_SERVER)
		win.setAttribute(QtCore.Qt.WA_DeleteOnClose)
		win.show()
		sys.exit(app.exec_())
	else:
		msgBox=QtGui.QMessageBox()
		msgBox.setText("Could not open database %s"%dbPath)
		msgBox.exec_()

if __name__=='__main__':
	main()
