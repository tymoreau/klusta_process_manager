#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)

from PyQt4 import QtCore,QtGui
from klusta_process_manager.config import get_klusta_path

class FolderView(QtGui.QWidget):

	def __init__(self,model,parent=None):
		super(FolderView,self).__init__(parent)
		
		#Table (list of experiment)
		self.table=QtGui.QTableView(self)
		self.table.horizontalHeader().setVisible(False)
		self.table.verticalHeader().setVisible(False)
		self.table.horizontalHeader().setResizeMode(QtGui.QHeaderView.ResizeToContents)
		self.table.setShowGrid(False)
		vbar=self.table.verticalScrollBar()
		self.table.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
		self.table.setModel(model)
		self.table.selectionModel().selectionChanged.connect(self.on_selection_changed)

		#ListFile (contents of one experiment folder)
		self.listFile=QtGui.QTreeView(self)
		self.listFile.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
		self.listFile.header().setStretchLastSection(True)
		self.listFile.doubleClicked.connect(self.open_selected_file)
	
		#FileSytemModel linked to listFile
		self.folderModel=QtGui.QFileSystemModel(self)

		#open klustaviewa
		self.processViewa=QtCore.QProcess()
		#dealing with the klusta environment (not perfect)
		env = QtCore.QProcess.systemEnvironment()
		itemToReplace=[item for item in env if item.startswith('PATH=')]
		for item in itemToReplace:
			newitem=item.replace('/anaconda/bin:','/anaconda/envs/klusta/bin:')
			newitem=newitem.replace('/miniconda/bin:','/miniconda/envs/klusta/bin:')
			env.remove(item)
			env.append(newitem)
		env.append("CONDA_DEFAULT_ENV=klusta")
		self.processViewa.setEnvironment(env)
		
		#Layout
		self.space=QtGui.QWidget()
		hbox=QtGui.QHBoxLayout()
		hbox.addWidget(vbar)
		hbox.addWidget(self.table)
		hbox.addWidget(self.space)
		hbox.addWidget(self.listFile)
		self.setLayout(hbox)
		self.listFile.hide()
		self.space.show()
		
	def refresh(self):
		self.listFile.update()
		
	#User clicked on one folder
	def on_selection_changed(self,selected,deselected):
		if len(selected.indexes())==0:
			if len(self.table.selectedIndexes())==0:
				self.listFile.hide()
				self.space.show()
				return
			else:
				lastIndex=self.table.selectedIndexes()[-1]
		else:
			lastIndex=selected.indexes()[-1]
		self.listFile.show()
		self.space.hide()
		#Set ListFile to display folder's content
		path=lastIndex.model().pathLocal_from_index(lastIndex)
		self.folderModel.setRootPath(path)
		self.listFile.setModel(self.folderModel)
		self.listFile.setRootIndex(self.folderModel.index(path))
		self.listFile.clearSelection()
		
	#user changed animal
	def reset_view(self):
		self.table.reset()
		self.table.clearSelection()
		self.folderModel.reset()
		self.listFile.hide()
		self.listFile.clearSelection()
		self.space.show()
		self.table.resizeColumnsToContents()
		he=self.table.horizontalHeader()
		length=he.sectionSize(0)+he.sectionSize(1)+he.sectionSize(2)+he.sectionSize(3)
		self.table.setMaximumWidth(length+10)

	#double click on a file
	def open_selected_file(self,index):
		if self.folderModel.isDir(index):
			return
		path=self.folderModel.filePath(index)
		if path.endswith(".kwik"):
			self.open_klustaviewa(path)
		else:
			QtGui.QDesktopServices.openUrl(QtCore.QUrl(path))

	def open_klustaviewa(self,path):
		pathKlustaviewa=get_klusta_path()+"viewa"
		isOpen=self.processViewa.startDetached(pathKlustaviewa,[path])
		if not isOpen:
			QtGui.QMessageBox.warning(self,"error",
									  "Could not open Klustaviewa (path=%s)"%pathKlustaviewa,
									  QtGui.QMessageBox.Ok)

