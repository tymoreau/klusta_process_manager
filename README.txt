16/04/2015
What's new:
	- Log view on the middle right, tells you what you just did
	- don't need to activate klusta environment
	- "Process Here" tab on the bottom, display general progress on the left and display console output of klusta on the right


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
	The app will launch in the application's folder, where you can use "testFile_smallDat" to test klusta (it should run in a few seconds)
	
	Example of test to do (in this order):
	 -load prm and prb model (provided in the folder)
	 -select a file, click "Create prm and prb files in selected folders"  -> nothing happen
	 -select the folder "testFile_smallDat", click "Create prm etc"  -> prb and prm are created
	 -select .prm file or test folder, add to list  -> full path added to list
	 -select other type of file, add to list -> nothing is add
	 -save list, load list
	 -click on "Process list"  (with the file testFile_smallDat.prm in the list)  -> klusta runs, everything is display on the bottom pannel
	 -click on "Clear ouput" -> the bottom pannel only display "Nothing running"

2) change the path in application_main.py 
	open with Kwrite 
	line 15, ROOT='.'  to replace with ROOT=myPath  ('/home/data' or '/data', etc)
	
	
-----------------
	LAUNCH
-----------------
1) Open a terminal
2) Go in the folder of the application
3) type "python application_main.py"

you should not need to do "source activate klusta" anymore (yeah !)


-----------------
	USE
-----------------
-> if you close the terminal, the application is closed (if klusta was running, it crash)

-> experiment are processed with "klusta --overwrite" : if it was already processed, it will start again overwritting the old files

-> some informations/warning are printed in the terminal, but most are now display in the Log view (on middle-right of the window) or in the bottom pannel ("Process here" tab)

-> "Process on remote Computer" is not implemented for now

-> "Create PRM and PRB files" will overwrite files if they already exist


