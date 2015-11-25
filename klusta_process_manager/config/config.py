from __future__ import print_function
import os
import json

# Create a folder in the user's root with a config file, scripts and prm/prb models
def create_user_config_file(override=False):
	dirPath=get_user_folder_path()
	if not os.path.exists(dirPath):
		print("Creating",dirPath)
		os.mkdir(dirPath)

	scriptFolder=os.path.join(dirPath,"scripts")
	if not os.path.exists(scriptFolder):
		os.mkdir(scriptFolder)

	configPath=os.path.join(dirPath,"userConfig.json")
	if not override:
		if os.path.exists(configPath):
			return

	print("Creating configuration file ",configPath)
	parameters= {"path_to_data":"/data",
				 "path_to_back_up":"/NAS02",
				 "length_ID":3,
				 "dateTime_formats":["_yyyy_MM_dd_HH_mm"],
				 "default_ip_for_server":"10.52.25.1",
				 "default_port_for_server":"1234"}
	
	with open(configPath, "w") as f:
		json.dump(parameters,f,sort_keys=True,indent=4)

# Get path to user's root
def get_user_folder_path():
	homePath=os.path.expanduser("~")
	dirPath=os.path.join(homePath,"processManager")
	return dirPath

#Get path to user's config file
def get_user_config_path():
	dirPath=get_user_folder_path()
	configPath=os.path.join(dirPath,"userConfig.json")
	return configPath

#Get path the user's scripts folder
def get_user_script_path():
	dirPath=get_user_folder_path()
	scriptPath=os.path.join(dirPath,"scripts")
	return scriptPath

#Read the json configuration file, return dictionnary
def read_user_config_file():
	configPath=get_user_config_path()
	if not os.path.exists(configPath):
		return None
	else:
		with open(configPath,'r') as f:
			parameters=json.load(f)
		return parameters
	
def get_klusta_path():
	homePath=os.path.expanduser("~")
	anaconda=os.path.join(homePath,"anaconda/envs/klusta/bin/klusta")
	if os.path.exists(anaconda):
		return anaconda
	else:
		miniconda=os.path.join(homePath,"miniconda/envs/klusta/bin/klusta")
		if os.path.exists(miniconda):
			return miniconda
		else:
			return "klusta"


#------------------------------------------------------------------------------------------
#    Main Window   
#------------------------------------------------------------------------------------------
WIDTH=1000
HEIGHT=1000
MIN_WIDTH=int(WIDTH*0.75)
MIN_HEIGHT=int(HEIGHT*0.75)
TITLE="Klusta Process Manager"

#------------------------------------------------------------------------------------------
#    Database
#------------------------------------------------------------------------------------------
DEFAULT_ICON="folder-grey.png"

#------------------------------------------------------------------------------------------
#    Transfer:  > rsync RSYNC_ARG /source/ /destination     
#------------------------------------------------------------------------------------------
#Rsync arguments
# -r: recursive
# -l: keep symlink
# -z: compress (faster if slow network)
# -u: update (keep the last modified file)
# -t: update the timestamps (important for -u to work correctly)
# -O: don't update the timestamps on directories (rsync fail (error 23) on some filesystem)

#Do not put extra quotes (Wrong: --include='*.prm' | Right: --include=*.prm)

RSYNC_ARG_TO_BACKUP=["-rlzutO"]
RSYNC_ARG_FROM_BACKUP=["-rlzutO","--exclude=*.dat"]

RSYNC_ARG_FROM_BACKUP_TO_SERVER=["-rlzutO","--prune-empty-dirs","--include","*/","--include=*.prm","--include=*.prb","--include=*.dat","--exclude=*"]

#------------------------------------------------------------------------------------------
# Server
#------------------------------------------------------------------------------------------
SERVER_PATH="../test/dataServer"
BACK_UP_PATH='../test/fakeNAS'
PORT=1234



