#QT
import sip
sip.setapi('QVariant',2)
sip.setapi('QString',2)
from PyQt4 import QtCore,QtGui

class TableDelegate(QtGui.QStyledItemDelegate):
	def __init__(self,parent=None):
		super(TableDelegate,self).__init__(parent)
		self.weekLines=[]
		self.dayLines=[]
		self.middleWeek=[]
		self.middleWeekOdd=[]
		self.middleDay=[]
		self.middleDayOdd=[]
		
	def reset_horizontal_lines(self,listDate):
		previousMonth=listDate[0].date().month()
		previousWeek=listDate[0].date().weekNumber()[0]
		previousDay=listDate[0].date().day()
		weekLines=[]
		dayLines=[]
		
		for row,date in enumerate(listDate):
			month=date.date().month()
			week=date.date().weekNumber()[0]
			day=date.date().day()
			if month==previousMonth and week==previousWeek:     #same week
				if day!=previousDay:
					dayLines.append(row-1)
			else:
				weekLines.append(row-1)
			previousMonth=month
			previousWeek=week
			previousDay=day
		weekLines.append(len(listDate)-1)
		
		self.weekLines=weekLines
		self.dayLines=dayLines
		
		week2=[-1]+weekLines[:-1]
		middleWeek=[ (a+b+1) for a,b in zip(weekLines,week2)]
		self.middleWeek=[ int(summ/2) for summ in middleWeek if summ%2==0]
		self.middleWeekOdd=[ int(summ/2) for summ in middleWeek if summ%2!=0]
		dayLines=dayLines+weekLines
		dayLines.sort()
		day2=[-1]+dayLines[:-1]
		middleDay=[(a+b+1) for a,b in zip(dayLines,day2)]
		self.middleDay=[ int(summ/2) for summ in middleDay if summ%2==0]
		self.middleDayOdd=[ int(summ/2) for summ in middleDay if summ%2!=0]

	def paint(self,painter,option,index):
		row=index.row()
		col=index.column()
		#Vertical Lines
		if col==2:
			p1=option.rect.topRight()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.setPen(QtCore.Qt.black)
			painter.drawLine(line)
		#Horizontal Lines---------------------------------
		#Month/Year/Week
		if row in self.weekLines:
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.setPen(QtCore.Qt.black)
			painter.drawLine(line)
		#Day
		elif col!=0 and (row in self.dayLines):
			painter.setPen(QtGui.QPen(QtGui.QBrush(QtCore.Qt.gray),1.5,QtCore.Qt.DotLine))
			p1=option.rect.bottomLeft()
			p2=option.rect.bottomRight()
			line=QtCore.QLine(p1,p2)
			painter.drawLine(line)
		#Draw Text
		painter.setPen(QtCore.Qt.black)
		if col==3 or col==2:
			return super(TableDelegate,self).paint(painter,option,index)
		elif col==0 and (row in self.middleWeek):
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif col==0 and (row in self.middleWeekOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +5
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif col==1  and (row in self.middleDay):
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
		elif col==1  and (row in self.middleDayOdd):
			rowHeight=self.sizeHint(option,index).height()//2 +7
			option.rect.translate(0,rowHeight)
			painter.drawText(option.rect,QtCore.Qt.AlignVCenter,index.data())
