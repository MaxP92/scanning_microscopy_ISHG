# -*- coding: utf-8 -*-
"""
Created on Feb 11 15:35:13 2019

@author: Maxime PINSARD
"""
from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt5 import QtWidgets
import serial # pySerial


'''
Fonction 01 : Get Status [8701]
Fonction 02: Stop [8702]
Fonction 03 : Start Mode XX [8703XX]
Start mode 0 : [870300] # # 2000us
Start mode 1 : [870301] # # 200us
Start mode 2 : [870302] # # 20us
Start mode DC: [870303] # # 20us
'''

timesleep = 0.2 # sec

class Worker_EOMph(QObject):
    '''
    '''
    #
    #                 self.thread_EOMph.quit() ;  self.thread_EOMph.wait(); print('EOMph Terminated.')
    # pyqtSignals
    
    EOMph_setHV_signal = pyqtSignal(float, bool)
    EOMph_here_signal = pyqtSignal(int)
    EOMph_msg_signal = pyqtSignal(str)
    mdltr_voltSet_signal = pyqtSignal(int) # # mtr finished moved signal
    EOM_voltget_signal = pyqtSignal(int)
    
    def __init__(self, queue_disconnections, write_termination_EOMph, EOMphAxis_comport, EOMph_baudrate , time_out_EOMph, msg_getStatusEOM,  code_resp_getstatus,  msg_stopEOM, code_resp_getHV,  code_resp_getHVvar, code_resp_getHVval, code_resp_getHVval2, code_resp_getHVval3, msg_ONVoltageEOM , msg_OFFVoltageEOM, msg_SetVoltageEOM,  msg_stModeEOM, msg_getStatusVoltageEOM, msg_ReadVoltageEOM, code_resp_mode1, code_resp_getHVon, time): 
    
        super(Worker_EOMph, self).__init__()
    
        # # self.queueEmpty = queueEmpty
        self.queue_disconnections = queue_disconnections
        # # self.jobs_window = jobs_window
        print('Worker_EOMph started.')
        self.modulator_thread_in_queue_disconn = False
        self.write_termination_EOMph = write_termination_EOMph
        self.EOMphAxis_comport = EOMphAxis_comport ; self.EOMph_baudrate = EOMph_baudrate ; self.time_out_EOMph = time_out_EOMph; self.msg_getStatusEOM = msg_getStatusEOM; self.code_resp_getstatus = code_resp_getstatus
        self.msg_stopEOM = msg_stopEOM; self.code_resp_getHV = code_resp_getHV; self.code_resp_getHVvar = code_resp_getHVvar;  self.msg_ONVoltageEOM = msg_ONVoltageEOM ; self.msg_OFFVoltageEOM = msg_OFFVoltageEOM;  self.msg_SetVoltageEOM =  msg_SetVoltageEOM;  self.msg_stModeEOM = msg_stModeEOM
        self.msg_getStatusVoltageEOM = msg_getStatusVoltageEOM; self.msg_ReadVoltageEOM = msg_ReadVoltageEOM ; self.code_resp_getHVval = code_resp_getHVval
        self.code_resp_getHVval2 = code_resp_getHVval2 ; self.code_resp_getHVval3  = code_resp_getHVval3
        self.code_resp_mode1 = code_resp_mode1 ; self.code_resp_getHVon = code_resp_getHVon
        self.time = time
        self.msg_dict = {msg_getStatusEOM: 'getSt', code_resp_getstatus: 'StOK', msg_stopEOM: 'Stop', code_resp_getHV: 'repGetHV', code_resp_getHVvar: 'repGetHV2', code_resp_getHVval: 'valHV', code_resp_getHVval2: 'valHVOFF', code_resp_getHVval3: 'valHVnm', msg_ONVoltageEOM: 'onEOM', msg_OFFVoltageEOM: 'offEOM', msg_SetVoltageEOM: 'setHV',  msg_stModeEOM: 'stmode', msg_getStatusVoltageEOM: 'gethv', msg_ReadVoltageEOM: 'readhv', code_resp_mode1: 'mode', code_resp_getHVon: 'repGetHVon', None: '-', '': '-'  }
        self.void = '*void*'
        self.mod_DC_on = False
        # # the latency time of USB was put to 1ms instead of 16ms default !!!!
        
    def writefunc(self, msg):
        print('to EOM', msg)
        try:
            self.EOMph.write(('%s%s'% (msg, self.write_termination_EOMph)).encode('ascii'))    
        except Exception as e: 
            # # print(type(e))
            if type(e) == serial.serialutil.SerialException:
                print('EOMph port not avail. anymore')
            else: print(e)    
            
    def query(self, msg):
        self.writefunc( msg)
        self.time.sleep(timesleep)
        bb = self.EOMph.readline().decode()
        # # print(bb)
        if len(bb) == 0: bb = self.void
        return bb # unicode not ascii
        
    
    def format_disp_util(self, stat):
        if stat in self.msg_dict.keys(): str = self.msg_dict[stat]; stat = stat[max(0, len(stat) -24):max(0, len(stat) -24)+12]
        else: 
            str = '' if stat[-1] == 'V' else '?' # # V = a voltage
        disp = '%s %s %s' % (self.time.strftime("%Hh%M:", self.time.localtime()), stat, str)
        self.EOMph_msg_signal.emit(disp)
        return disp
    
    @pyqtSlot()
    def connect_modulator(self):  
        from serial.tools.list_ports import comports # mandatory, cannot import it with serial only
        # # called by thread start, and by com_EOMph_button is 2nd+ try to open          
        serial_ports_short = [(x[0]) for x in comports()] # short version
        EOMphAxis_comport = ''.join(str(x) for x in serial_ports_short if x == self.EOMphAxis_comport) # verify that the COM port is connected
        
        if EOMphAxis_comport is not None:
            try:
                self.EOMph= serial.Serial(EOMphAxis_comport , baudrate=self.EOMph_baudrate, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, timeout=self.time_out_EOMph, rtscts=False) # # NOT rtscts
            except Exception as e: 
                if type(e) == serial.serialutil.SerialException:
                    # if str(e) == "No USB device matches URL":
                    # print("\n Problem with Motor XY ! \n")
                    print("EOMphase used elsewhere (port not available).")
                else:
                    print(e)
                    #raise # do error  
                error_raised = 1
            else:
                stat = self.query('[%d]' % self.msg_getStatusEOM)
                if stat == self.void:
                    error_raised = 1
                    print("EOMphase not detected (port ok).")
                else: # good msg
                    disp = self.format_disp_util( stat)
                    print(disp)
                    error_raised = 0
        else:    # no COM
            error_raised = 1
            print("port %d EOMphase not here." % self.EOMphAxis_comport)
        # any case
        if error_raised:
            print("EOM phase not available !!!! \n")
            if hasattr(self, 'EOMph'):
                self.EOMph.close() # close resource
            self.success_EOMph = False
            self.EOMph_here_signal.emit(0) # NOT here
            self.EOMph = None
        else:
            self.EOMph.reset_input_buffer()
            self.EOMph.reset_output_buffer()
            self.success_EOMph = True
            self.EOMph_here_signal.emit(1) # here
    
    @pyqtSlot()            
    def get_status_modulator(self):
        if self.EOMph is not None:
            self.EOMph.reset_input_buffer()
            self.EOMph.reset_output_buffer()
            stat = self.query('[%d]' % self.msg_getStatusEOM) # # [] compulsory !!
            try:
                int(stat[1:-1])
            except ValueError:
                print('wrong type of get msg (EOM ph)', stat)
            if stat == self.code_resp_getstatus:
                print('EOMph: Got ok')
            else:
                print('EOMph: strange response to GetStatus :%s ...' % stat)
                bb = self.EOMph.readline().decode()
                if len(bb)==0: bb = self.void
                print('...2nd try', bb, ' better ?')
        else:
            stat = '?'
        disp = self.format_disp_util( stat)
    
    @pyqtSlot()
    def stop_modulator(self):    
        self.writefunc( '[%d]' % self.msg_stopEOM) # # [] compulsory !!
        # no read
        self.time.sleep(0.15) #
    
    @pyqtSlot(int)
    def st_mode_modulator(self, mode): 
    # # 0 = 2000us, 1 = 200us, 2 = 20us, 3 = DC
        mode -= 1 # spnbx 0 is nothing
        if (mode < 0 or mode > 3): # # wrong !
            if (mode < -1 or mode > 3): print('Wrong mode for modulator !!')
            return
        self.writefunc( '[%d0%d]' % (self.msg_stModeEOM, mode)) # # [] compulsory !!
        print('wrkr EOM received order mode %d' % mode)
        self.time.sleep(1.8) # 1.5sec
        bb = self.EOMph.readline().decode()
        print(bb) ##, len(bb), bb is None, bb == '') # '(0504000001)(8203000001)(0504000001)'
        disp = self.format_disp_util(bb)
    
    @pyqtSlot()
    def get_voltage_modulator(self):
        # # called by button get, or directly in job
        # # print('in get eom' , self.sender(), )
        
        widget_caller=self.sender()
        # # print(isinstance(widget_caller, QtWidgets.QPushButton))
        # # '''
        # # used only to modify the HV standalone
        if self.EOMph is not None: 
            self.EOMph.reset_input_buffer()
            self.EOMph.reset_output_buffer()
        stat = self.query( '[%s]' % self.msg_ReadVoltageEOM) # # [] compulsory !!
        # # try:
        # #     int(stat[1:-1])
        # # except ValueError:
        # #     print('wrong type of get HV (EOM ph)', stat)
        val_HV = -1 # dflt
        if stat in (self.code_resp_getHVval2, self.code_resp_getHVval3): # self.code_resp_getHVval, 
            print('EOMph: Got HV standby ok')
        elif stat[1:5] == '0504' and stat[-3:-1] == '05':
            val_HV = int(stat[7:9] + stat[5:7],16)
            # # ex [05041400] = 20 V
            print('EOMph: Got HV ok: %d V' % val_HV)
            stat += (' %d V' % val_HV)
        else:
            print('EOMph: strange response to GetHV :', stat) 
        disp = self.format_disp_util( stat)
        self.EOM_voltget_signal.emit(val_HV)
        # # '''
        if not isinstance(widget_caller, QtWidgets.QPushButton): # # direct call
            self.time.sleep(1.5) # be sure that the voltage is set
            self.mdltr_voltSet_signal.emit(1) # 1 is useless but used to match other signals
    
    @pyqtSlot(int)         
    def on_off_voltage_modulator(self, b):    
        # # used only to modify the HV standalone  
        if b: # # set to ON 
            print(self.EOMph.readline().decode())
            stat = self.query( '[%s]' % self.msg_getStatusVoltageEOM) # # get
            if stat in (self.code_resp_getHV, self.code_resp_getHVvar): #  # indeed off
                # self.writefunc( '[%s]' % self.msg_ONVoltageEOM) # # [] compulsory !!
                self.st_mode_modulator(4) # DC
            else: # # OFF or other
                print(stat, 'not OFF detected, won`t put on')
                b = 0
        else: # OFF
            # # self.writefunc( '[%s]' % self.msg_OFFVoltageEOM) # # [] compulsory !!
            self.stop_modulator()
        self.time.sleep(2.5*timesleep)
        stat = self.query( '[%s]' % self.msg_getStatusVoltageEOM) # # get
        nothappy = False
        if stat != self.code_resp_mode1:  # (0504000001)(8203000001)(0504000001)
            try:
                int(stat[1:-1])
            except ValueError:
                print('wrong type of get HV status (EOM ph)', stat)
                nothappy = True
        if not nothappy:    
            if b: # # set to ON
                cond1 = (stat[1:5] == '0504' and stat[-3:-1] == '01')
            else: # want off 
                cond1 = stat in (self.code_resp_getHV, self.code_resp_getHVvar)
            if cond1:
                print('EOMph: Got HV status ok')
                if b: # on
                    self.mod_DC_on = True
                else:
                    self.mod_DC_on = False
            else:
                print('EOMph: strange response to GetHVstatus :', stat) 
        disp = self.format_disp_util( stat)
    
    @pyqtSlot(float, bool)    
    def set_voltage_modulator(self, volt, job):
        # # used only to modify the HV standalone 
        if job:  # # ina job # # in mV
            volt = 1000*volt
        print('modulator received voltage', volt, job)
        
        if self.mod_DC_on: print('mod is indeed on')
        else: print('mod needs to be in DC'); self.on_off_voltage_modulator(1)
            
        volt = int(max(0, min(volt, 1400)))
        v = hex(volt) # hex string
        LSB = v[-2:].upper()
        if len(v) == 4: # small    
            MSB = '0'
        elif len(v) == 5: # big
            MSB = v[-3]
        elif len(v) == 3: # very small   
            MSB = '0'
            LSB = '0'+v[-1]
        self.writefunc('[%s%s0%s]' % (self.msg_SetVoltageEOM, LSB, MSB)) # # [] compulsory !!
        # # ex [05041400] = 20 V
        # set VOLT 
        # # Get Status, TURN ON, Set Voltage, TURN OFF
        # # int('0x1F4',16) = 500
        
        # # yy = array.array('h',[500])
        # # a=yy.tostring()
        wt = 2.5 # # sec
        print('waiting for EOM to set voltage during %g sec !' % wt)
        self.time.sleep(wt) # if too fast it will get the wrong volt values
        if job:  # # ina job
            self.get_voltage_modulator() # # direct call
        
    
    @pyqtSlot()
    def close_modulator(self):   
        if (hasattr(self, 'EOMph') and self.success_EOMph and self.EOMph is not None):
            self.stop_modulator()
            self.EOMph.reset_input_buffer()
            self.EOMph.reset_output_buffer()
            self.EOMph.close() # close resource
            print('EOMph instr closed.')
            self.success_EOMph = False
            self.EOMph_here_signal.emit(0) # NOT here
        if not self.modulator_thread_in_queue_disconn:    
            self.queue_disconnections.put(8) # tell the GUI can kill this QThread : EOMph's signature is 8
            self.modulator_thread_in_queue_disconn = True