#------------------------------------------------------------------------------------------
#    PATH
#------------------------------------------------------------------------------------------
#Path to the backup (NAS/harddrive mounted on computer)
NAS_PATH="./test/fakeNAS"

#Path to data
ROOT='./test/dataLocal'

#------------------------------------------------------------------------------------------
#    Processing: > klusta fileName.prm
#------------------------------------------------------------------------------------------

#PROGRAM="klusta"

# To avoid "source activate klusta", put full path
PROGRAM="/home/david/anaconda/envs/klusta/bin/klusta"

#------------------------------------------------------------------------------------------
#    Transfer:  > rsync RSYNC_ARG /source/ /destination     
#------------------------------------------------------------------------------------------

#Rsync arguments | -a=archive (recursive, update permission and timestamp, keep symlink...) -u=update (do not downgrade files)
RSYNC_ARG="-au"


#------------------------------------------------------------------------------------------
#Console
#------------------------------------------------------------------------------------------
#separator printed in the console view 
SEPARATOR='---'*10


#------------------------------------------------------------------------------------------
# Client: where to find server by default
#------------------------------------------------------------------------------------------
IP="10.51.101.29"
PORT=8000


#------------------------------------------------------------------------------------------
# if running serverTCP.py 
#------------------------------------------------------------------------------------------
#where to put data on the server
SERVER_PATH="./test/dataServer"
#Default ip
IP_server="127.0.0.1"