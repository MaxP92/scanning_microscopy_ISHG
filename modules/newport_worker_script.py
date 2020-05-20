# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2018

@author: Maxime PINSARD
"""

# newport

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
path_computer = 'C:/Users/admin/Documents/Python'

        
class Worker_newport(QObject):
    
    '''
    You have to divide this class into one class for each device (to have them independent)
    '''
    esp_imported_signal = pyqtSignal(bool)
    motor_newport_homed_signal = pyqtSignal()
    pos_newport_signal = pyqtSignal(int, float)
    motor_newport_finished_move_signal = pyqtSignal(int)

    def __init__(self, queue_disconnections, jobs_window, newportstage_comport, motornewport_SN, jobs_scripts): 
    
        super(Worker_newport, self).__init__()
        
        self.queue_disconnections = queue_disconnections
        self.jobs_window = jobs_window
        
        self.newportstage_comport = newportstage_comport
        self.motornewport_SN = motornewport_SN
        self.jobs_scripts = jobs_scripts
        # # self.time_out_newport


    @pyqtSlot()
    def open_lib(self):
        
        import serial
        from serial.tools.list_ports import comports # mandatory, cannot import it with serial only
        from modules import newportESP
        
        self.motor_newport_is_here = False # default
        serial_ports_short = [(x[0]) for x in comports()] # short version
        newportstg_comport = ''.join(str(x) for x in serial_ports_short if x == self.newportstage_comport) # verify that the COM port is connected
        
        if newportstg_comport is not None:
            
            try:
                self.esp = newportESP.ESP(newportstg_comport)
                err_occured = 0
            except Exception as e: # # if port already defined before
                # # print(type(e))
                if type(e) == serial.serialutil.SerialException:
                    # if str(e) == "No USB device matches URL":
                    # print("\n Problem with Motor XY ! \n")
                    print('serial problem')
                    err_occured = 1
                else:
                    print(e)
                    err_occured = 1
                    #raise # do error    
            else: #succesful
                try:
                    msg = self.esp.version
                    if len(msg) == 0:
                        msg = self.esp.version
                    print(msg)
                except Exception as e: 
                    if type(e) != serial.serialutil.SerialTimeoutException:
                        print(e)
                    else:
                        print('esp timed out')
                    err_occured = 1

            if not err_occured:
                self.motor_newport = self.esp.axis(1) # 1 for 1 axis
                print('Stage newport %s is here !' % self.motornewport_SN)
                self.motor_newport.on()
                self.motor_newport_is_here = True
            else:
                print("\n newport motor not available !!!! \n")
        
        self.esp_imported_signal.emit(self.motor_newport_is_here)

                
    @pyqtSlot()
    def move_home_newport(self):    
    
        if self.motor_newport_is_here:

            self.motor_newport.home_search(blocking=True)            
            pos = self.motor_newport.position
            self.pos_newport_signal.emit(2, pos) # 2 is newport's ID
            self.motor_newport_homed_signal.emit()

            
    @pyqtSlot(float)    
    def move_motor_newport(self, pos_newport): 
    
        # # self.motor_newport.move_to( pos_newport, blocking=False)
        self.jobs_scripts.move_rot_polar_meth(True, self.motor_newport, pos_newport, self.pos_newport_signal, self.motor_newport_finished_move_signal, 'newport', 2) # flag_wait, id_motor
        
    @pyqtSlot()
    def get_pos_newport(self):  
    # # connected to push button
    
        pos = self.motor_newport.position
        self.pos_newport_signal.emit(2, pos) # 2 is newport's ID
        
    @pyqtSlot(bool)
    def close_motor_newport(self,  flag_end):
        
        # # print(self.motor_stageX_is_here , self.motor_stageY_is_here)
        # # if self.motor_newport_is_here:
            # # print('closed')
        self.esp.closeESP()
        # # try:
        # #     del self.motor_newport # # equivalent to self.motor_newport.off()
        # # except (NameError, AttributeError):
        # #     pass
        # # try:
        # #     del self.esp # # will close the conn.
        # # except (NameError, AttributeError):
        # #     pass
        # #     # # self.motor_newport.close() # works with Serial or FTDI
        
        if flag_end: # end of program    
            self.queue_disconnections.put(6) # tell the GUI can kill this QThread : newport's signature is 6
            