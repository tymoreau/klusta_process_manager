
03_07_2015

Requirements
------------

Python 3.4 and PyQt4 (already in Anaconda)
Should also work with Python2.7

With Miniconda or Anaconda install, do:
> conda update conda
> conda update pyqt


Install
-------

1) Get source from DropBox: copy-paste zip file, unzip

2) Change parameters (path to your data, adress of server...) in /config/config.py
/!\ You have to re-install everytime you change parameters

3) In a terminal, in the application's folder:
> python setup.py install



To launch
-----

In a terminal, anywhere:
> klusta_process_manager


Server
------
Parameters in config.py
PORT=1234
IP=10.51.101.61

To launch the server
>klusta_server
