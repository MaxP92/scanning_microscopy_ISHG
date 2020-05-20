# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2016

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

class Worker_imic(QObject):
    """
    uses msl_loadlib version 0.4.1.dev0 and more
    """

    progress_motor_signal = pyqtSignal(int)
    fltr_top_choice_set = pyqtSignal(int)
    fltr_bottom_choice_set = pyqtSignal(int)
    obj_choice_set = pyqtSignal(int)
    posZ_mtr_str = pyqtSignal(int)
    imic_was_ini_signal = pyqtSignal(bool)
    posZ_piezo_str= pyqtSignal(int)

    def __init__(self, path_computer, queue_disconnections, motorZ_changeDispValue_signal, piezoZ_changeDispValue_signal, progress_piezo_signal,  max_pos_Z_motor, port_imic): 
    
        super(Worker_imic, self).__init__()
        
        self.imic_was_ini = False
        self.path_computer = path_computer

        # otherwise it is imported every time a galvo scan is launched ...
        print('Import imic_core...')
        from modules import imic_my_client
        import time, numpy
        # otherwise it is imported every time a galvo scan is launched ...
        
        self.time = time
        self.queue_disconnections = queue_disconnections
        self.motorZ_changeDispValue_signal = motorZ_changeDispValue_signal
        self.piezoZ_changeDispValue_signal = piezoZ_changeDispValue_signal
        self.progress_piezo_signal = progress_piezo_signal
        self.max_pos_Z_motor = max_pos_Z_motor
        self.port_imic = port_imic
        self.ct_init_fail = -1 # never used
        self.minTime_wait2read_ms = 200 # ms
        try:
            self.imic_core=imic_my_client.MyClient_imic()
        # except AttributeError:
        except Exception as err:
            print('imic ERR', err)
            if type(err) == AttributeError:
                print('iMic not here (Client64 bug)')
                return


    @pyqtSlot()
    def open_com(self):
        
        # print("Slot is executed in thread : ", self.thread().currentThreadId())
        if hasattr(self, 'imic_core'): # no bug
            self.imic_core.open_lib() # define library
            self.handle1_val = self.imic_core.OpenByRS232(self.port_imic) # open COM port
            print('imic handle', self.handle1_val)
        else:
            print('No imic to open!')
        
    @pyqtSlot()
    def imic_ini(self):
        # is called by init_imic_button
        # # print('core', hasattr(self, 'imic_core'))
        if hasattr(self, 'imic_core'): # no bug
            ee = self.imic_core.init_imic(self.handle1_val) 
        else:
            ee = -1 
        
        if ee != 0: # error seen by Python or iMic
            if ee == -1: # no imic core
                print('imic_core not here (Client64 bug)')
            else:
                print('imic could not be opened!')
            self.imic_was_ini_signal.emit(False)
            return # out the func
       
        # # if self.ct_init_fail >= 0: # not 1st time
        
        if self.ct_init_fail < 0: self.ct_init_fail = 0 # now there was a 1st time
        elif self.ct_init_fail > 5:  # # too many
            self.close_imic_meth(False) # # not GUI end
            self.imic_was_ini_signal.emit(False)
            return # out the func

        try: self.posFilt_1_get = self.imic_core.filter_pos_top_get(self.handle1_val)
        except:  # possible that worked beofre, but not now
            self.ct_init_fail += 1
            print('failed using imic %d\n' % self.ct_init_fail)
            return # out
        else: self.ct_init_fail = 0 # success

        # get infos ************************************
        self.posFilt_2_get = self.imic_core.filter_pos_bottom_get(self.handle1_val)
        
        self.choice_obj = self.imic_core.obj_choice_get(self.handle1_val)
        
        self.posZ_motor_get = self.imic_core.pos_Z_motor_get(self.handle1_val)
        self.posZ_piezo_get = self.imic_core.pos_Z_piezo_get(self.handle1_val)
        
        # set param ***************************************************
        # self.posFilt_1_get = 0
        # self.posFilt_2_get = 0
        # self.choice_obj = 0
        # self.posZ_motor_get = 0
        # self.posZ_piezo_get = 0
            
        # else:
        #     self.posFilt_1_get = self.posFilt_1_get.value
        #     self.posFilt_2_get = self.posFilt_2_get.value
        #     self.choice_obj = self.choice_obj.value
        #     self.posZ_motor_get.value = self.posZ_motor_get
        #     self.posZ_piezo_get.value = self.posZ_piezo_get
        
        self.fltr_top_choice_set.emit(self.posFilt_1_get)
        
        self.fltr_bottom_choice_set.emit(self.posFilt_2_get) 
        
        self.obj_choice_set.emit(self.choice_obj) 
        
        self.posZ_mtr_str.emit(self.posZ_motor_get)
        
        self.posZ_piezo_str.emit(self.posZ_piezo_get)
        
        self.imic_was_ini_signal.emit(True)
        self.imic_was_ini = True
        
    @pyqtSlot(float)
    def change_z_motor_meth(self, posZ_motor):
        
        # print("Slot is executed in thread : ", self.thread().currentThreadId())
        # self.posZ_motor_get = self.imic_core.pos_Z_motor_get(self.handle1_val)     
           
        self.posZ_motor = posZ_motor
        self.imic_core.pos_Z_motor_set(self.handle1_val, posZ_motor)
        
        # self.time.sleep(abs(self.posZ_motor_get - posZ_motor)/self.speed_motorZ_imic + self.minTime_wait2read_ms/1000) # it already sleep
        self.posZ_motor_get = self.imic_core.pos_Z_motor_get(self.handle1_val) # get real pos
        # # print("Z motor (worker)= %.3f mm" % self.posZ_motor_get)
        
        self.progress_motor_signal.emit(max(1, round(self.posZ_motor_get/self.max_pos_Z_motor*100)))
        self.motorZ_changeDispValue_signal.emit(self.posZ_motor_get) # in mm
        
    @pyqtSlot(float)
    def change_z_piezo_meth(self, posZ_piezo):
        
        # # print('l124', time.time())
                
        self.posZ_piezo = posZ_piezo
        
        self.imic_core.pos_Z_piezo_set(self.handle1_val, posZ_piezo)
        
        self.get_z_piezo_meth()
    
    @pyqtSlot(float)
    def step_z_piezo_meth(self, stepZ_piezo):    
        
        self.imic_core.step_z_piezo(self.handle1_val, stepZ_piezo)
        
        self.get_z_piezo_meth()
        
    def get_z_piezo_meth(self):
        
        max_pos_Z_piezo = 0.25 # mm

        self.posZ_piezo_get = self.imic_core.pos_Z_piezo_get(self.handle1_val) # in mm
        self.posZ_piezo_get = round(self.posZ_piezo_get*1000*100)/100/1000  # in mm
        # # print("Z piezo (got) = %.4f um" % (self.posZ_piezo_get*1000))
        
        # # print('prog : ', round(self.posZ_piezo_get/max_pos_Z_piezo*100))
        self.progress_piezo_signal.emit(max(1, round(self.posZ_piezo_get/max_pos_Z_piezo*100)))
        self.piezoZ_changeDispValue_signal.emit(self.posZ_piezo_get) # in mm
        
    @pyqtSlot(int)
    def filter_top_meth(self, posFilt_top):
        
        self.posFilt_top = posFilt_top
        
        self.imic_core.filter_pos_top_set(self.handle1_val, posFilt_top)
        
        self.time.sleep( self.minTime_wait2read_ms/1000)
        
        posFilt_1_got = self.imic_core.filter_pos_top_get(self.handle1_val)
        
        self.fltr_top_choice_set.emit(posFilt_1_got)
        
        
    @pyqtSlot(int)
    def filter_bottom_meth(self, posFilt_bottom):
        
        self.posFilt_bottom = posFilt_bottom
        
        self.imic_core.filter_pos_bottom_set(self.handle1_val, posFilt_bottom)
        
        self.time.sleep( self.minTime_wait2read_ms/1000)
        
        posFilt_2_got = self.imic_core.filter_pos_bottom_get(self.handle1_val)
        self.fltr_bottom_choice_set.emit(posFilt_2_got) 

        
    @pyqtSlot(int)
    def obj_choice_meth(self, obj_choice):
        
        self.obj_choice = obj_choice
        
        self.imic_core.obj_choice_set(self.handle1_val, obj_choice)
        
        self.time.sleep( self.minTime_wait2read_ms/1000)
        
        choice_obj = self.imic_core.obj_choice_get(self.handle1_val)
        
        self.obj_choice_set.emit(choice_obj) 

        
    @pyqtSlot()
    def update_Z_values_meth(self):
        
        self.posZ_motor_get = self.imic_core.pos_Z_motor_get(self.handle1_val)
        self.motorZ_changeDispValue_signal.emit(self.posZ_motor_get) # in mm
        
    
    def close_imic_meth(self, the_end):
        # print('In closing Imic !')
        
        close_server = 1
        if self.imic_was_ini:
            try: # bug if imic closed by user
                if hasattr(self, 'imic_core'): # no bug
                    self.imic_core.close_imic(self.handle1_val)
            except Exception as err:
                print(err)
                close_server = 0
                
        if close_server:
            if hasattr(self, 'imic_core'): # no bug
                print('I close server32 imic')
                self.imic_core.shutdown_server32()
                # # self.imic_core.cleanup_subprocess()
                del self.imic_core
        
        if the_end:
            self.queue_disconnections.put(1) # tell the GUI the iMic is closed : iMic's signature is 1