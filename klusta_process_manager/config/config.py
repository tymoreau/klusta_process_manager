from __future__ import print_function
import os
import json

def create_user_config_file(override=False):
    """Create a folder in the user's root with a config file"""

    dirPath = get_user_folder_path()
    if not os.path.exists(dirPath):
        print("Creating", dirPath)
        os.mkdir(dirPath)

    configPath = os.path.join(dirPath, "userConfig.json")
    if not override:
        if os.path.exists(configPath):
            answer = input("Configuration file %s already exist, override ([y]/n) ?"%configPath)
            if str(answer).lower() in ["n", "no"]:
                return

    print("Creating configuration file ", configPath)
    parameters= {"path_to_data": "/data",
                 "path_to_back_up": "/NAS02",
                 "length_ID": 3,
                 "dateTime_formats": ["_yyyy_MM_dd_HH_mm"],
                 "default_ip_for_server": "10.51.25.1",
                 "default_port_for_server": "1234",
                 "rsync_arg_local_to_backup": ["-rlzutO"],
                 "rsync_arg_backup_to_local": ["-rlzutO","--exclude=*.dat"],
                 "window_pixel_width": 1000,
                 "window_pixel_height": 1000,
                 }
    
    with open(configPath, "w") as f:
        json.dump(parameters, f, sort_keys=True, indent=4)

def get_user_folder_path():
    """Get path to user's root"""
    
    homePath = os.path.expanduser("~")
    dirPath = os.path.join(homePath, "processManager")
    return dirPath

def get_user_config_path():
    """Get path to user's config file"""
    
    dirPath = get_user_folder_path()
    configPath = os.path.join(dirPath, "userConfig.json")
    return configPath

def read_user_config_file():
    """Read the json configuration file, return dictionnary"""
    
    configPath = get_user_config_path()
    if not os.path.exists(configPath):
        return None
    else:
        with open(configPath, 'r') as f:
            parameters = json.load(f)
        return parameters
    
def get_klusta_path():
    homePath = os.path.expanduser("~")
    potentialPaths = ["anaconda/envs/klusta/bin/klusta", "anaconda3/envs/klusta/bin/klusta",
                      "miniconda/envs/klusta/bin/klusta", "miniconda3/envs/klusta/bin/klusta"]
    for path in potentialPaths:
        full = os.path.join(homePath, path)
        if os.path.exists(full):
            return full
    return "klusta"


#------------------------------------------------------------------------------------------
#    Main Window   
#------------------------------------------------------------------------------------------
TITLE = "Klusta Process Manager"

#------------------------------------------------------------------------------------------
#    Database
#------------------------------------------------------------------------------------------
DEFAULT_ICON = "folder-grey.png"

#------------------------------------------------------------------------------------------
# Server
#------------------------------------------------------------------------------------------
RSYNC_ARG_FROM_BACKUP_TO_SERVER = ["-rlzutO","--prune-empty-dirs","--include","*/","--include=*.prm",
                                   "--include=*.prb","--include=*.dat","--exclude=*"]

SERVER_PATH = "/home/david/Code/application/test/dataServer"
BACK_UP_PATH = '/home/david/Code/application/test/fakeNAS'
PORT = 1234



