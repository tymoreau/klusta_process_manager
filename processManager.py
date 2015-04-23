#Process Manager
#Holds two tab: process here or process on server (=remote)

import PySide.QtCore as PCore
import PySide.QtGui as PGui
import PySide.QtNetwork as PNet
import sys
import signal

#import tab
from tabHere import TabHere
from tabRemote import TabRemote



#if start alone, will process LIST
LIST=["/home/david/dataRat/Rat034_small/Rat034_small2.pr","/home/david/dataRat/Rat034_small/DoNotExist.prm","/home/david/dataRat/Rat034_small/Rat034_small.prm"]


class ProcessManager(PGui.QTabWidget):

	def __init__(self):
		super(ProcessManager,self).__init__()
		self.tabHere=TabHere()
		self.tabRemote=TabRemote()
		self.addTab(self.tabHere, "Process Here")
		self.addTab(self.tabRemote,"Process on Server")


if __name__=='__main__':
	PGui.QApplication.setStyle("cleanlooks")
	app=PGui.QApplication(sys.argv)
	
	#to be able to close wth ctrl+c
	signal.signal(signal.SIGINT, signal.SIG_DFL)
	
	win=ProcessManager()
	win.setMinimumSize(900,600)
	
	def processListRemote():
		win.tabRemote.feed_list_remote(LIST)
	win.tabRemote.button_processList.setEnabled(True)
	win.tabRemote.button_processList.clicked.connect(processListRemote)

	
	
	def processListHere():
		win.tabHere.feed_list(LIST)
	win.tabHere.button_processList.setEnabled(True)
	win.tabHere.button_processList.clicked.connect(processListHere)
	

	win.show()

	sys.exit(app.exec_())
