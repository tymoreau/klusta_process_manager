#------------------------------------------------------------------------------------------
#    PATH
#------------------------------------------------------------------------------------------
#Path to the backup (NAS/harddrive mounted on computer)
BACK_UP='../test/fakeNAS'

#Path to data
ROOT="../test/dataLocal"

#------------------------------------------------------------------------------------------
#    Processing: > klusta fileName.prm
#------------------------------------------------------------------------------------------

#PROGRAM="klusta"
# To avoid "source activate klusta", put full path
PROGRAM="/home/david/anaconda/envs/klusta/bin/klusta"

#------------------------------------------------------------------------------------------
#    Client: where to find server by default
#------------------------------------------------------------------------------------------
IP="10.51.101.61"
PORT=1234




#------------------------------------------------------------------------------------------
#    Main Window   
#------------------------------------------------------------------------------------------
WIDTH=1000
HEIGHT=1000
MIN_WIDTH=int(WIDTH*0.75)
MIN_HEIGHT=int(HEIGHT*0.75)
TITLE="Klusta Process Manager"

#------------------------------------------------------------------------------------------
#    FileBrowser     
#------------------------------------------------------------------------------------------

DEFAULT_ICON="folder-grey.png"
LENGTH_ID=3
DATE_TIME_FORMAT="yyyy_MM_dd_HH_mm"
EXP_PATH="/Experiments"

#------------------------------------------------------------------------------------------
#    Client: where to find server by default
#------------------------------------------------------------------------------------------
IP="10.51.101.29"
PORT=1234

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
#    Console
#------------------------------------------------------------------------------------------
#separator printed in the console view 
SEPARATOR='---'*10

#------------------------------------------------------------------------------------------
# Server
#------------------------------------------------------------------------------------------
SERVER_PATH="../test/dataServer"
BACK_UP_PATH='../test/fakeNAS'



