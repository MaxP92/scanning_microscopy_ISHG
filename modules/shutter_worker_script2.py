# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 2018

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
import time, warnings
        
class Worker_shutter(QObject):
    
    '''
    The shutter repeat the Write in Read
    To write use query
    to read use query for the command, and read after
    '''
    # pyqtSignals
    
    shutter_wasOpenClose_signal = pyqtSignal(int)
    shutter_here_signal = pyqtSignal(int)
    
    def __init__(self, queueEmpty, queue_disconnections, read_termination_shutter, write_termination_shutter, ressource_shutter, baud_rate_shutter_dflt, baud_rate_shutter, timeout_shutter, t_understand_order, t_shutter_trans): 
    
        super(Worker_shutter, self).__init__()
    
        self.queueEmpty = queueEmpty
        self.queue_disconnections = queue_disconnections
        self.eol = read_termination_shutter.encode()
        self.leneol = len(self.eol)
        self.read_termination_shutter = read_termination_shutter
        self.write_termination_shutter = write_termination_shutter; self.ressource_shutter = ressource_shutter
        self.baud_rate_shutter_dflt = baud_rate_shutter_dflt; self.baud_rate_shutter = baud_rate_shutter
        self.timeout_shutter = timeout_shutter
        
        self.t_understand_order = t_understand_order; self.t_shutter_trans = t_shutter_trans
    
    def writefunc(self, msg):
        self.shutter.write(('%s%s'% (msg, self.write_termination_shutter)).encode('ascii'))    
        # self.shutter_io.flush() # get data out now
    def query(self, msg):
        self.writefunc(msg)
        # # print(self.readlinefunc().decode())
        return self.readlinefunc().decode() # unicode
        
    def readlinefunc(self):
        line = bytearray()
        while True:
            c = self.shutter.read(1) # self.
            if c:
                line += c
                if line[-self.leneol:] == self.eol:
                    line = line[:-self.leneol]
                    break
            else:
                break
        return bytes(line)

    @pyqtSlot()
    def open_resource(self):
        # called by start of the QThread
        
        # # print('Importing VISA in shutter...')
        # # import visa
        # # print('VISA ok in shutter.')
        # # self.visa_constants = visa.constants
        # current_txt = self.shutter_com_combo.currentText()
        # for pyvisa and not pyvisa-py
        # if current_txt[6] == '(':
        #     current_txt = current_txt[0:6]
        # else:
        #     current_txt = current_txt[0:7]
        
        # print('ressource_shutter =', self.ressource_shutter)
        # # self.rm = visa.ResourceManager('@py') # # '@py' for pyvisa-py
        
        self.set_instr()
    
    @pyqtSlot()
    def set_instr(self): 
        #  called by previous function OR signal
        warnings.filterwarnings('error', category = UserWarning) #message=msg_warning_read_noTermChar)

        if hasattr(self, 'shutter'):
            try:
                self.shutter.reset_input_buffer() # flush buffer
                self.shutter.reset_output_buffer() # flush orders
                self.query('baud?')
                self.readlinefunc().decode() # response
            except: # disconnected
                self.shutter.close() # restart
            else: # ok 
                self.shutter_here_signal.emit(1) # 1 means is here
                warnings.filterwarnings('default', category = UserWarning)
                return                
        # # otherwise the processes will import it many times !
        print('Importing serial in shutter...')
        import serial
        print('serial ok in shutter.')
        error_occured = 0
        try:
            # # if not hasattr(self, 'shutter'):
            # # self.shutter = self.rm.open_resource(self.ressource_shutter)
            self.shutter = serial.Serial(self.ressource_shutter, xonxoff=False, rtscts=False, baudrate=self.baud_rate_shutter_dflt , bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, timeout=self.timeout_shutter, write_timeout = 2)
            
        except Exception as e: 
            if type(e) == serial.serialutil.SerialException:
                print(e, '\n ERROR : instr in used elsewhere')
            else:
                print('ERROR shutter', e)
            error_occured = 1
        else:
            self.shutter.reset_input_buffer() # flush buffer
            self.shutter.reset_output_buffer() # flush orders
            # # self.shutter.baud_rate = self.baud_rate_shutter_dflt 
            # # self.shutter.data_bits = self.bits_shutter 
            # # self.shutter.parity = self.visa_constants.Parity.none 
            # # self.shutter.stop_bits = self.visa_constants.StopBits.one
            # # self.shutter.flow_control = self.flow_control_shutter 
            # # self.shutter.read_termination  = self.read_termination_shutter 
            # # self.write_termination = self.write_termination_shutter
            # # self.shutter.timeout = self.timeout_shutter 
        # #     self.shutter_io = io.TextIOWrapper(io.BufferedRWPair(self.shutter, self.shutter)) # to deal with term char
        # # # # TOO LONG

            try:
                self.query('baud?')
            except UnicodeDecodeError: # baud rate is already 115200 for the SC10
                a=self.readlinefunc().decode()
                if len(a) == 0: # baud rate is already 115200 for the SC10
                    self.shutter.baudrate = self.baud_rate_shutter # 115200
                    print('baud rate shutter was already 115200')
                    try:
                        self.query('baud?')
                    except UnicodeDecodeError: # baud rate is already 115200 for the SC10
                        self.shutter.baudrate = self.baud_rate_shutter_dflt 
                        print('baud rate shutter was actually NOT 115200 !!')
                    # # a=self.readlinefunc().decode()
                    # # if len(a) == 0: # baud rate was NOT 115200 for the SC10
                    # #     self.shutter.baudrate = self.baud_rate_shutter_dflt 
                    # #     print('baud rate shutter was actually NOT 115200 !!')
            # # except UserWarning:
            # #     # if type(err) is UserWarning:
            # #     
            except Exception as e:
                print('ERROR shutter 2', e)
                error_occured = 1
            # else: # rate is 9600
       
            if not error_occured:
                a=self.readlinefunc().decode()
                # # print('a', a)
                if len(a) == 0: # # no read
                    print('read timed out : shutter not here')
                    error_occured = 1
                else:
                    if len(a) != 1: # something like 'Command error CMD_NOT_DEFINED\n', try again
                        print('act. msg shutter', a)
                        self.query('baud?')
                        a=self.readlinefunc().decode()
                        if len(a) == 0:
                            self.query('baud?')
                            a=self.readlinefunc().decode()
                        # # if len(a) > 1: # THOR ...
                        # #     warnings.filterwarnings('ignore', category = UserWarning)
                        # #     aa = '0'
                        # #     while True:
                        # #         a= aa
                        # #         aa=self.readlinefunc().decode()
                        # #         if len(aa) == 0: # nothing to read
                        # #             warnings.filterwarnings('default', category = UserWarning)
                        # #             break
                        elif len(a) > 1: # # > baud ?
                            a=self.readlinefunc().decode()
                            # # print(a, len(a))
    
                    if (len(a) > 0 and a.isdigit() and int(a) == 0 and self.baud_rate_shutter != self.baud_rate_shutter_dflt): # rate is 9600
                        print('baud rate shutter was 9600 !') 
                        self.writefunc('baud=1') # set to 115200
                        try: # sometimes it reads directly 'baud=1'
                            self.readlinefunc().decode()
                        except UnicodeDecodeError: # sometimes not
                            pass
                        self.shutter.baudrate = self.baud_rate_shutter # 115200
                        try:
                            a=self.query('baud?')
                        except UnicodeDecodeError: # don't know why
                            a=self.query('baud?') 
                    if len(a) > 1: # read command
                        a=self.readlinefunc().decode()
                    if (len(a) > 0 and a.isdigit() and int(a) == 1):
                        print('baud rate shutter is now 115200')     
                            
                    try:
                        a=self.query('id?')
                    except UserWarning:
                        # if type(err) is UserWarning:
                        print('read timed out : shutter not here')
                        error_occured = 1
                    except UnicodeDecodeError: # normal if reconnection
                        error_occured = 0
                    except Exception as e:
                        print('error unknown', e)
                        error_occured = 1
                    finally: 
                        if not error_occured:
                            # maybe return error msg, it's normal
                            warnings.filterwarnings('default', category = UserWarning)
                            a=self.readlinefunc().decode()
                            if a[:13] != 'Command error': # normal
                                print('msg', a)
                            
                            # error_occured = 0
            
                            self.query('mode=1') # mode=1: Sets the unit to Manual Mode
                            #mode=2: Sets the unit to Auto Mode
                            #mode=3: Sets the unit to Single Mode : for use if you want to control the close time by a hardware way 
                            #mode=4: Sets the unit to Repeat Mode
                            #mode=5: Sets the unit to the External Gate Mo
                            
                            warnings.filterwarnings('ignore', category = UserWarning)
                            # # while True:
                            aa=self.readlinefunc().decode()
                                # # if len(aa) == 0: # nothing to read
                                # #     break
                            # enable is when the unit is active or waiting for a trigger event
                            # In the MANUAL mode, the ENABLE keypad on the front panel will open and close the shutter
                            
                            # to perhaps allow it to go to the correct state
                            time.sleep(2*(self.t_understand_order + self.t_shutter_trans)/1000) # in sec
                            self.query('closed?')
                            a=self.readlinefunc().decode()
                            if not a.isdigit(): # not 1 or 0
                                a=self.readlinefunc().decode()
                            if not bool(int(a)): # 0 if open, Returns '1' if the shutter is closed
                                self.query('ens') # Toggle enable, to close it
        
        finally:
            if error_occured:
                print('shutter is NOT here')
                self.shutter_here_signal.emit(0) # 0 means is NOT here
                self.shutter_was_detected = 0
                if hasattr(self, 'shutter'):
                    try:
                        self.shutter.close()
                    except TypeError:
                        pass # normal
            else:
                print('shutter is here')
                self.shutter_here_signal.emit(1) # 1 means is here
                self.shutter_was_detected = 1
        
        warnings.filterwarnings('default', category = UserWarning)
        
    @pyqtSlot(int)
    def open_close_shutter_meth(self, state_wanted):
        # called by GUI's open_close_shutter_signal
            
        print('in open/close shutter')
        
        self.query('closed?')
        msg = self.readlinefunc().decode()
        if len(msg) > 1: # # read something like ">closed ?"
            msg = self.readlinefunc().decode()
        if len(msg) > 0: # # no response
            if not msg.isdigit(): msg = self.readlinefunc().decode()
            if msg.isdigit():
                if state_wanted >= 1: # close wanted
                    condition_wanted_bool = bool(int(msg)) # Returns “1” if the shutter is closed or “0” if open
                else: # open wanted
                    condition_wanted_bool = not bool(int(msg)) 
        
                if not condition_wanted_bool:
                    self.query('ens') # toggles enable
        
            # to be sure that the shutter actually had the time to do the order
            time.sleep((self.t_understand_order + self.t_shutter_trans)/1000) # in sec
            # total shutter time opf at least 70ms was found to work
            
            # I don't verify if the state is attained or not, because it can take up to 20ms and this is a time lost for the image
            # Even worth, this can mean the app waits to move and the laser stays at one point during that time, possibly implying damages
            # while True: 
                # if condition_wanted_bool: # can be fullfiled with no action of shutter if was already ok
            if state_wanted < 1: # open wanted, otherwise it toggles and bugs !
                self.shutter_wasOpenClose_signal.emit(bool(state_wanted)) # emit the signal that the shutter is closed or open
                    # break # outside 'while' loop
        else: print('no response shutter !')
    
    @pyqtSlot(float)
    def waitin_shutter_meth(self, time_diff):
        
        time.sleep(time_diff)
        self.open_close_shutter_meth(0) # open
    
    @pyqtSlot()
    def terminate_shutter(self):
        
        # the instr is opened anyway
        if hasattr(self, 'shutter'):
            # if self.shutter_was_detected:
            self.shutter.reset_input_buffer() # flush buffer
            self.shutter.reset_output_buffer() # flush orders
            self.shutter.close() # close resource
            
        self.queue_disconnections.put(5) # tell the GUI can kill this QThread : shutter's signature is 5