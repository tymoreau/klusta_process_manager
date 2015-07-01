Requirements
------------

Python 3.x and PyQt4 (already in Anaconda)
Should also work with Python2.x

With Miniconda or Anaconda install, do:
> conda install conda

> conda update pyqt


Install
-------

1) Get source
* From DropBox: copy paste whole folder
* From GitHub: 
        > git clone https://github.com/tymoreau/klusta_process_manager.git

        
2) Change parameters (path to your data, adress of server...) in /config/config.py
/!\ You have to re-install everytime you change parameters

3) In a terminal, in the folder:
> python setup.py install



To launch
-----

In a terminal, anywhere:
> klusta_process_manager


Server
------
Parameters in config.py

To launch the server
>klusta_server
