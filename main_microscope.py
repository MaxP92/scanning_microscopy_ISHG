# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2016

@author: Maxime PINSARD
"""

import sys, os

path11 = os.getcwd() # 'C:\\Users\\admin\\Documents\\Python'
path_computer = path11.replace('\\prog microscope 18', '')
# # path_computer = r'C:\Users\admin\Documents\Python' # # 'C:\Users\pc\Documents\These\Python'
sys.path.append(r'%s\Packages' % path_computer) # for imic.dll
# # path11 = r'%s\prog microscope 18' % path_computer
sys.path.append(path11) # for imicinitmp

from PyQt5 import QtWidgets
from modules import gui_script

"""
Normally, iMic lib loaded by CDLL
APT loaded by winDLL in #2
"""
    
if __name__=='__main__':
    
    # just to avoid pyqt5 to quit when an error is raised
    def my_excepthook(type, value, tback):
        # log the exception here
        # then call the default handler
        sys.__excepthook__(type, value, tback)
    sys.excepthook = my_excepthook
    
    app = QtWidgets.QApplication(sys.argv)
    # # print("Main application thread is : ", app.thread().currentThreadId())
    main = gui_script.Main(path_computer)
    main.show()
    # # multiprocessing.log_to_stderr() # # !!! # logging.INFO
    # # input('press enter to exit')
    sys.exit(app.exec_())
    
    