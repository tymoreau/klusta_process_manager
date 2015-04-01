import sys
import os
import subprocess
import datetime as d



def run(input_name):
	#Open file with list of parameter files in full path
	input=input_name
	list_parameterFiles=open(input,"r")
	print "Open file",input

	#Create log file
	log=open("run_klusta.log","w")
	log.write("List of parameters files: "+input+"\n")

	#Activate klusta environment - don't work
	#os.system("/bin/bash --rcfile klusta/bin/activate")

	#launch klusta one folder at a time
	for prmFile in list_parameterFiles:
		prmFile=prmFile.rstrip('\n')
		
		print "Launch klusta for parameter file:",prmFile
		log.write("Launch klusta for parameter file: "+prmFile+"\n")
		
		time_start=d.datetime.now()
		log.write("time: "+str(time_start)+"\n")

		#set working directory to where the files are (or troubles)
		path='/'.join(prmFile.split('/')[:-1])
		os.chdir(path)
		
		returncode=subprocess.call(["klusta",prmFile,"--overwrite"])

		time_end=d.datetime.now()
		print "Finish parameter file:",prmFile
		log.write("Finish parameter file: "+prmFile+"\n")
		log.write("time: "+str(d.datetime.now())+"\n")
		log.write("running time: "+str(time_end-time_start)+"\n")
		
		print returncode
		if returncode!=0:
			print "There was an error, returncode:",returncode
			log.write("There was an error, returncode:"+str(returncode)+"\n")
		log.write("----------------------------------------------------\n")

if __name__ == '__main__':
	run(sys.argv[1])

