import sys
import signal

#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui,QtSql

from klusta_process_manager.server import ServerTCP 
from config import *

def main():
	QtGui.QApplication.setStyle("cleanlooks")
	app = QtGui.QApplication(sys.argv)
	
	nas=QtCore.QDir(BACK_UP_PATH)
	server=QtCore.QDir(SERVER_PATH)
	if not nas.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("BACK_UP_PATH do not refers to a folder: "+str(BACK_UP_PATH))
		msgBox.exec_()
	elif not server.exists():
		msgBox=QtGui.QMessageBox()
		msgBox.setText("SERVER_PATH do not refers to a folder: "+str(SERVER_PATH))
		msgBox.exec_()
	else:
		#to be able to close wth ctrl+c
		signal.signal(signal.SIGINT, signal.SIG_DFL)
		
		win=ServerTCP()

		sys.exit(app.exec_())

if __name__=='__main__':
	main()

