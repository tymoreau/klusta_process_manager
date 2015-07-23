import os
from six import exec_

def create_user_config_file(override=False):
	dirPath=get_user_folder_path()
	if not os.path.exists(dirPath):
		print("Creating",dirPath)
		os.mkdir(dirPath)

	userPath=os.path.join(dirPath,"userConfig.py")
	if not override:
		if os.path.exists(userPath):
			return
	print("Writing",userPath)
	with open(userPath, "w") as f:
		f.write("path_to_data='/data'\n")
		f.write("path_to_back_up='/NAS02'\n")
		f.write("\n")
		f.write("default_ip_for_server='10.51.25.1'\n")
		f.write("default_port_for_server='1234'\n")
		f.write("\n")
		f.write("length_id=3\n")
		f.write("dateTime_format=['yyyy_MM_dd_HH_mm']\n")
		f.write("path_from_animal_to_exp='/Experiments'\n")
		

def get_user_folder_path():
	homePath=os.path.expanduser("~")
	dirPath=os.path.join(homePath,"processManager")
	return dirPath

def get_user_config_path():
	dirPath=get_user_folder_path()
	userPath=os.path.join(dirPath,"userConfig.py")
	return userPath

def read_user_config_file():
	userPath=get_user_config_path()
	if not os.path.exists(userPath):
		return None
	else:
		with open(userPath,'r') as f:
			contents = f.read()
			metadata = {}
			exec_(contents, {}, metadata)
			metadata = {k: v for (k, v) in metadata.items()}
		return metadata

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
			return None

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



