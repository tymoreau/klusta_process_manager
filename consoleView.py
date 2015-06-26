import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtGui

PROGRAM="klusta"
SEPARATOR="---"*10

#-------------------------------------------------------------------------------------------------------
# console output
#--------------------------------------------------------------------------------------------------------
class ConsoleView(QtGui.QGroupBox):
	def __init__(self,parent=None):
		super(ConsoleView,self).__init__(parent)
		
		#output
		self.output=QtGui.QTextEdit()
		self.output.setReadOnly(True)

		#buttons
		self.button_clear=QtGui.QPushButton("Clear output")
		self.button_clear.clicked.connect(self.output.clear)
		
		#Layout
		vbox=QtGui.QVBoxLayout()
		vbox.addWidget(self.output)
		vbox.addWidget(self.button_clear)
		self.setLayout(vbox)
		
	def display(self,lines):
		self.output.append(lines)
		
	def separator(self,experiment):
		sep='<b>'+SEPARATOR+SEPARATOR+'</b> \n'
		sep1='<b> Experiment: </b> \n'
		sep2='Working directory: \n'
		sep3='Do: %s %s \n'%(PROGRAM)
		sep4='<b>'+SEPARATOR+SEPARATOR+'</b>'
		self.output.append(sep)
		self.output.append(sep1)
		self.output.append(sep2)
		self.output.append(sep3)
		self.output.append(sep4)
