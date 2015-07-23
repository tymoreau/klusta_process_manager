
23 juillet 2015

New Features:
------------

- Open files with double click (in the top right view)
  kwik files are opened with klustaviewa
  you can close the application, even if you opened file through it (= it
  won't close klustaviewa if you close the app)

- In the bottom left view, right click on an experiment to see a menu:
     experiment "waiting to be.." -> "cancel" button
     experiment "klusta running" -> "kill" button (kill klusta, don't ask
     confirmation)
     other -> no menu
     
- When processing on the server: once everything is sync to the back-up
(experiment are "waiting to be processed", or running), you can close the
application. Open it later and reconnect to the server to see the progress.

- Can manage different time format for folder's name:
    in userConfig, you can put
    dateTime_format=["yyyy_MM_dd_HH_mm","yyyy-MM-dd_HH-mm-ss"] to have both
    the regular format and the openephys format

- On server side:
    - don't deleta .dat file if klusta crash
    - "kill" button reimplemented


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

2) In a terminal, in the application's folder (where there is a setup.py file):
> python setup.py install

3) The install should have created a folder "processManager" in your home.
Inside, you'll find a file userConfig.py where you can change default
parameter.


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
