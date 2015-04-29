29/04/2015
What's new:
	- New display: browse your files on top and manage the processing on the bottom
	- More buttons to manage processing (cancel, remove/kill, restart..)
	- Log view on the top right
	- "Add to list" button replace by a green arrow (on the left)

-----------------
	Requirements
-----------------

- Python 2.7 with the library PySide
	with anaconda installed, type in a terminal "conda install pyside"
	
- Klusta v0.3.0

-----------------
	SET UP
-----------------

1) copy paste the whole folder on your computer, change the name of the folder if you want

2) Launch (see below) and test if everything is working, play around with buttons
  klusta should run in a few seconds on the test data
	
	Example of test to do (in this order):
	 -load prm and prb model (provided in the folder)
	 -select a file, click "Create prm and prb files"  -> nothing happen
	 -select a folder , click "Create prm and prb files"  -> prb and prm are created
	 -select folder, click on green arrow -> appears on the bottom left list
	 -select other type of file, add to list -> nothing is add
	 -click on "Process list"  (with the file testFile_smallDat.prm in the list)  -> klusta runs, everything is display on the bottom right pannel


2) change the path in application_main.py 
	open with Kwrite 
	line 15, ROOT='.'  to replace with ROOT=myPath  ('/home/data' or '/data', etc)
	
	
-----------------
	LAUNCH
-----------------
1) Open a terminal
2) Go in the folder of the application
3) type "python application_main.py"

-----------------
	USE
-----------------
-> if you close the terminal, the application is closed (if klusta was running, it crash)

-> "Connect to server" is not implemented for now

-> "Create PRM and PRB files" will overwrite files if they already exist


