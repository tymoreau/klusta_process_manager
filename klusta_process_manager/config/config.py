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
			answer=input("Configuration file %s already exist, override ([Y]/N) ?"%configPath)
			if str(answer).lower() in ["n","no"]:
				return

	print("Creating configuration file ",configPath)
	parameters= {"path_to_data":"/data",
				 "path_to_back_up":"/NAS02",
				 "length_ID":3,
				 "dateTime_formats":["_yyyy_MM_dd_HH_mm"],
				 "default_ip_for_server":"10.51.25.1",
				 "default_port_for_server":"1234",
				 "rsync_arg_local_to_backup":["-rlzutO"],
				 "rsync_arg_backup_to_local":["-rlzutO","--exclude=*.dat"],
				 "window_pixel_width":1000,
				 "window_pixel_height":1000,
				 }
	
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
	miniconda=os.path.join(homePath,"miniconda/envs/klusta/bin/klusta")
	if os.path.exists(miniconda):
		return miniconda
	anaconda3=os.path.join(homePath,"anaconda3/envs/klusta/bin/klusta")
	if os.path.exists(anaconda3):
		return anaconda3
	miniconda3=os.path.join(homePath,"miniconda3/envs/klusta/bin/klusta")
	if os.path.exists(miniconda3):
		return miniconda3
	return "klusta"


#------------------------------------------------------------------------------------------
#    Main Window   
#------------------------------------------------------------------------------------------
TITLE="Klusta Process Manager"

#------------------------------------------------------------------------------------------
#    Database
#------------------------------------------------------------------------------------------
DEFAULT_ICON="folder-grey.png"

#------------------------------------------------------------------------------------------
# Server
#------------------------------------------------------------------------------------------
RSYNC_ARG_FROM_BACKUP_TO_SERVER=["-rlzutO","--prune-empty-dirs","--include","*/","--include=*.prm","--include=*.prb","--include=*.dat","--exclude=*"]

SERVER_PATH="/home/david/Code/application/test/dataServer"
BACK_UP_PATH='/home/david/Code/application/test/fakeNAS'
PORT=1234



