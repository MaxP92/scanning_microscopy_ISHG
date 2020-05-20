# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
# from pyqtgraph.Qt import QtCore

# print('Imports ok.')

class Worker_scan(QObject):

    new_img_to_disp_signal = pyqtSignal()
    # # buffer_to_disp_signal = QtCore.pyqtSignal(numpy.ndarray, numpy.ndarray, int, int, int)
    setnewparams_scan_signal = pyqtSignal(tuple)

    def __init__(self, queue_com_to_acq_process, queue_list_arrays, queue_disconnections, queue_special_com_acqGalvo_stopline , scan_thread_available_signal, piezoZ_step_signal): 
    
        super(Worker_scan, self).__init__()
        
        self.queue_com_to_acq_process = queue_com_to_acq_process
        self.queue_list_arrays = queue_list_arrays
        self.queue_disconnections = queue_disconnections
        self.queue_special_com_acqGalvo_stopline = queue_special_com_acqGalvo_stopline
        self.scan_thread_available_signal = scan_thread_available_signal
        self.piezoZ_step_signal = piezoZ_step_signal
        
    @pyqtSlot(int, int, list, list, int, int, int, int, int, bool, str)
    def scan_galvos_meth(self, external_clock, real_time_disp, min_val_volt_list, max_val_volt_list, device_used_AIread, write_scan_before, num_dev_anlgTrig, num_dev_watcherTrig, num_dev_AO, start_sec_proc_beg, path_computer):
        print('import libs in scan galvos')
        from modules import param_ini, go_scan_galvos
        import math, time, numpy

        # cannot define the galvo digital resource here because it's not pickable in a Process
        
        trig_src =  [device_used_AIread, param_ini.trig_src_name_dig_galvos] 
        
        if device_used_AIread == 1: # 6110
            max_value_pixel = param_ini.max_value_pixel_6110
        elif device_used_AIread == 2: # 6259
            max_value_pixel = param_ini.max_value_pixel_6259
        
        try:
            self.scan_thread_available_signal.emit(False) # # scan not free
            go_scan_galvos.go_galvos_scan_func_mp(min_val_volt_list, max_val_volt_list, param_ini.time_out,  time, numpy,  math,  param_ini.delay_trig, param_ini.timebase_src_end, trig_src, param_ini.time_out_sync, self.queue_com_to_acq_process, self.queue_list_arrays, self.new_img_to_disp_signal, external_clock, max_value_pixel, real_time_disp, self.queue_special_com_acqGalvo_stopline, write_scan_before, self.piezoZ_step_signal, num_dev_anlgTrig, num_dev_watcherTrig, num_dev_AO, start_sec_proc_beg, self.setnewparams_scan_signal, path_computer) #, self.buffer_to_disp_signal) # int32 is the ctypes class c_long
        
        except:
            import traceback
            traceback.print_exc()
            
        finally: # in all cases
            print('scan galvo processes terminated safely')
            self.scan_thread_available_signal.emit(True)
            
    @pyqtSlot()
    def close_scanThread(self):
        
        ''' ask the main gui to kill the qthread, because impossible to do it here as it is a class that does not contain the qthread
        # a priori the signal is sufficient to kill, but here it will communicate with quit_GUI_meth to be killed by this method and not the classic one if the user wants to quit the whole GUI
        
        kill the whole QThread was compulsory at first because I didn't know how to pass new parameters to a QThread without restarting it
        Now I know that I can use pyQtSignals or queues
        So you could make this QThread to not exit every time and to stay constantly alive
        '''
        
        self.queue_disconnections.put(0) # tell the GUI the scan galvos is done : its signature is 0
        # print('Worker scan asks GUI to terminate him')