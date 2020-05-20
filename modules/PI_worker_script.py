# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2018

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

# # path_computer = 'C:/Users/admin/Documents/Python'
        
class Worker_PI(QObject):
        
    PI_ishere_signal = pyqtSignal(bool)

    def __init__(self, queue_disconnections, jobs_window, progress_piezo_signal, piezoZ_changeDispValue_signal, PI_pack): 
    
        super(Worker_PI, self).__init__()
        
        self.queue_disconnections = queue_disconnections
        self.jobs_window = jobs_window
        self.progress_piezo_signal = progress_piezo_signal
        self.piezoZ_changeDispValue_signal = piezoZ_changeDispValue_signal
        [self.PI_conn_meth, self.PI_comport,  self.PI_baud, self.PI_SERVOMODE , self.PI_CONTROLLERNAME, self.max_range_PI]= PI_pack

    @pyqtSlot()
    def open_instr(self):
        from pipython import GCSDevice, pitools, GCSError
        
        self.pitools = pitools
        self.pi_device = GCSDevice (self.PI_CONTROLLERNAME)	# Load PI Python Libraries
        try:  
            if self.PI_conn_meth == 'usb':
                self.pi_device.ConnectUSB (self.PIezo_USB_ID) 	# Connect to the controller via USB
            else:
                self.pi_device.ConnectRS232(comport=self.PI_comport, baudrate=self.PI_baud) # # the timeout is very long, 30 sec !!
        except Exception as err:
            if (type(err)==GCSError and err.val == -9):  # # 'There is no interface or DLL handle with the given ID (-9)'
                print('No PI device !!')
            else:
                print('PI device lead to UNKNOWN error!!')
            self.PI_is_here = False
        else:
            self.PI_is_here = True
            print('PI device here.')
            self.pi_device.SVO (self.pi_device.axes, self.PI_SERVOMODE) # 1 = servo on (closed-loop operation) ; 0 = open-loop (servo OFF)
            # # open loop resolution (0.4nm) is a lower value than the closed loop resolution (0.7nm) due to the noise of the sensor signal. Open loop is subject to hysteresis, meaning the position could be off by up to 15%. When operated in closed loop, the hysteresis is compensated for, and virtually eliminated.
            self.getpos_motor_PI()
            
        self.PI_ishere_signal.emit(self.PI_is_here)
    
    @pyqtSlot(float)    
    def step_motor_PI(self, stp): 
        # function to move the PI motor
        
        self.pi_device.MVR (self.pi_device.axes, -stp) 	# Command axis "A" to step RELATIVE
        # um
        
        self.getpos_motor_PI()
    
    @pyqtSlot(float)    
    def move_motor_PI(self, pos): 
        # function to move the PI motor
        # # pos in mm
        
        self.pi_device.MOV (self.pi_device.axes, max((self.max_range_PI- pos)*1000, 0)) 	# Command axis "A" to position pos ABSOLUTE
        # # moves the sample to the top, so converted to act as if the objective moves to the top (moving sample to bottom)
        # um
        self.pitools.waitontarget(self.pi_device)
        
        self.getpos_motor_PI()
        
    @pyqtSlot()    
    def getpos_motor_PI(self): 
    
        st=0
        while True:
            if (not self.pi_device.IsMoving(self.pi_device.axes)[self.pi_device.axes[0]] or st>=20): # True if is moving
                break
            else:
                st+=1 # usually finish after only 1, or 2 for big moves
        position = self.max_range_PI*1000 - self.pi_device.qPOS (self.pi_device.axes)[self.pi_device.axes[0]]	# Query current position of axis
         # # moves the sample to the top, so converted to act as if the objective moves to the top (moving sample to bottom)
        # um
        self.progress_piezo_signal.emit(int(round(position/1000/self.max_range_PI*100)))
        self.piezoZ_changeDispValue_signal.emit(position/1000) # has to be emitted in mm
        
        
    @pyqtSlot(bool)
    def close_instr(self, flag_end):
        
        if self.PI_is_here:
            print('closing PI...')
            self.pi_device.CloseConnection()
        
        if flag_end: # end of program    
            self.queue_disconnections.put(7) # tell the GUI can kill this QThread : PI's signature is 7