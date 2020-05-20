# -*- coding: utf-8 -*-
"""
Created on Aug 18 15:35:13 2017

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

# put as little as import here because they are re-imported for nothing by processes
    
class Worker_stageXY(QObject):
    
    '''
    Use pySerial and low-lvl commands and not APT for XY stage
   
    '''
    
    home_ok = pyqtSignal(int)
    
    ask_if_safe_pos_for_homing_signal = pyqtSignal(bool) # don't put int, slot is bool !!
    
    new_img_to_disp_signal = pyqtSignal()
    
    reload_scan_worker_signal = pyqtSignal(int)
    
    stageXY_is_imported_signal = pyqtSignal(bool)
    
    scan_depend_workerXY_togui_signal = pyqtSignal(float, float, float, float)
    
    calc_param_scan_stg_signal = pyqtSignal(float, float, float, float, float, float, float, float, float, int, float, tuple) 
    
    new_scan_stage_signal = pyqtSignal( bool, int, list, list, int, bool, tuple, int)
    
    posX_indic_real_signal = pyqtSignal(float)
    posY_indic_real_signal = pyqtSignal(float)
    
    def __init__(self, time, queue_com_to_acq, queue_special_com_acqstage_stopline, queue_list_arrays, queue_moveX_inscan, queue_moveY_inscan, queue_disconnections, stop_motorsXY_queue, scan_thread_available_signal, piezoZ_step_signal, motor_blocking_meth, use_serial_not_ftdi, XYstage_comport,  time_out_stageXY, motorXY_SN, prof_mode , prof_mode_slow, jerk_mms3_slow, PID_scn_lst, PID_dflt_lst, acc_max, block_slow_stgXY_before_return, trigout_maxvelreached, time_out, trig_src_name_stgscan, bnd_posXY_l,  max_val_pxl_l, thorlabs_lowlvl_list, numpy ): 
    
        super(Worker_stageXY, self).__init__()
        
        # self.motorX_ID = motorX_ID
        # self.motorY_ID = motorY_ID
        
        self.max_accn_motorX_current = 0
        self.max_accn_motorY_current = 0
        self.max_speed_motorX_current = 0
        self.max_speed_motorY_current = 0
        self.ct_init_fail =  0
        self.thorlabs_lowlvl_list = thorlabs_lowlvl_list
        self.queue_com_to_acq = queue_com_to_acq; self.queue_special_com_acqstage_stopline = queue_special_com_acqstage_stopline
        self.queue_list_arrays = queue_list_arrays
        self.time = time
        self.queue_moveX_inscan = queue_moveX_inscan; self.queue_moveY_inscan = queue_moveY_inscan
        self.queue_disconnections = queue_disconnections
        self.stop_motorsXY_queue = stop_motorsXY_queue
        self.scan_thread_available_signal = scan_thread_available_signal
        self.piezoZ_step_signal = piezoZ_step_signal
        self.motor_blocking_meth = motor_blocking_meth
        self.use_serial_not_ftdi = use_serial_not_ftdi
        self.XYstage_comport = XYstage_comport
        self.time_out_stageXY = time_out_stageXY
        self.motorXY_SN = motorXY_SN
        self.prof_mode = prof_mode ;  self.prof_mode_slow =  prof_mode_slow
        self.jerk_mms3_slow = jerk_mms3_slow
        self.PID_scn_lst = PID_scn_lst; self.PID_dflt_lst = PID_dflt_lst
        self.acc_max = acc_max; self.block_slow_stgXY_before_return = block_slow_stgXY_before_return
        self.numpy = numpy
        self.trigout_maxvelreached = trigout_maxvelreached ;  
        self.time_out = time_out; self.trig_src_name_stgscan = trig_src_name_stgscan 
        [self.min_posX, self.max_posX, self.min_posY, self.max_posY] = bnd_posXY_l; [self.max_value_pixel_6110, self.max_value_pixel_6259 ] =  max_val_pxl_l
        
        self.flag_imp = False # import APT after, or not
        self.home_done = False
        
    @pyqtSlot()
    def open_lib(self):
        
        from queue import Empty as queueEmpty
        self.queueEmpty = queueEmpty

        self.motor_stageX_is_here = 0
        self.motor_stageY_is_here = 0
        success_mtr = False # # init

        if self.use_serial_not_ftdi: # use Serial
            from serial.tools.list_ports import comports # mandatory, cannot import it with serial only
            import serial # pySerial
            # ---------- control Serial  ---------------
            
            # serial_ports = [(x[0], x[1], dict(y.split('=', 1) for y in x[2].split(' ') if '=' in y)) for x in serial.tools.list_ports.comports()] # long version
            serial_ports_short = [(x[0]) for x in comports()] # short version
            XYstg_comport = ''.join(str(x) for x in serial_ports_short if x == self.XYstage_comport) # verify that the COM port is connected
            
            # print(XYstg_comport)
            # print(serial_ports_short)
            if XYstg_comport is not None:
                try:
                    self.motor_stageXY = serial.Serial(XYstg_comport ,baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, timeout=self.time_out_stageXY, rtscts=True, write_timeout = 2)
                
                except Exception as e: 
                    # # print(type(e))
                    if type(e) == serial.serialutil.SerialException:
                        # if str(e) == "No USB device matches URL":
                        # print("\n Problem with Motor XY ! \n")
                        print("\n Motor XY not available !!!! \n")
                    else:
                        print(e)
                        #raise # do error  
                # self.motor_stageXY = 0 # to be removed !
                else:
                    self.motor_stageXY.reset_input_buffer()
                    self.motor_stageXY.reset_output_buffer()
                    success_mtr = True
        else:
            from pyftdi.ftdi import Ftdi
            import time
            # PID seems to be FAF0 in device manager
            Ftdi.add_custom_product(0x403, 0xfaf0) # uses only the USB port
            try:
                self.motor_stageXY = Ftdi.create_from_url('ftdi://0x403:0xfaf0/1')
            
            except Exception as e:
                
                if str(e) == "No USB device matches URL ftdi://0x403:0xfaf0/1":
                    print("\n Motor XY not recognized ! \n") # goes to the end
                else:
                    raise # do error
            else:
                self.motor_stageXY.open_from_url(url = 'ftdi://0x403:0xfaf0/1')
                self.motor_stageXY.set_baudrate(115200)
                self.motor_stageXY.set_line_property(8, 1, 'N', break_=0) # 'N' = parity_none
                self.time.sleep(50e-3) # pre-purge
                self.motor_stageXY.purge_buffers() # purge RX and TX buffers
                self.time.sleep(50e-3) # post-purge
                self.motor_stageXY._reset_device() # private module, unlock it to public if no access
                self.motor_stageXY.set_flowctrl('hw') # 'hw' means RTS/CTS UART lines
                # f1.set_rts(state) # not sure for this one, the doc does not specify the 'state'
                self.motor_stageXY.read=self.motor_stageXY.read_data
                self.motor_stageXY.write=self.motor_stageXY.write_data
                success_mtr = True

        if success_mtr: #succesful
    
            print('Stage XY %s is here' % self.motorXY_SN)
            # while (not bool(bb) and (time.time() - start_time) < timeout_sec):
            self.motor_stageXY.write(b'\x18\x00\x00\x00\x11\x01') # no_flash_prog
            bb = self.thorlabs_lowlvl_list.req_info_ch_meth(0, self.motor_stageXY)
            print(bb[10:16], bb[24:67]) 
            bb = self.thorlabs_lowlvl_list.req_info_ch_meth(1, self.motor_stageXY)
            print(bb[10:16], bb[24:52]) 
            bb = self.thorlabs_lowlvl_list.req_info_ch_meth(2, self.motor_stageXY) 
            print(bb[10:16], bb[24:52]) 
            
            # ---------- Enable channels  ---------------
            
            if self.thorlabs_lowlvl_list.get_chstate_bycommand_meth(1, self.motor_stageXY) != 1: # can be 2
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_En0) 
                # self.thorlabs_lowlvl_list.get_chstate_bycommand_meth(0, motor_stageXY) does not work
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_EnCH1)

            if self.thorlabs_lowlvl_list.get_chstate_bycommand_meth(2, self.motor_stageXY) != 1: # can be 2
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_EnCH2)
                
                # time.sleep(0.1)
                
            self.motor_stageX_is_here = 1 # for X
            self.motor_stageY_is_here = 1 # for Y
            
            # -------------- control if profile is indeed trapezoidal  --------------------
            
            # at first, all the motors parameters are set to slow motor default
            
            if self.prof_mode < 2: # 0 or 1 : prof. trapez
                good_prof_key1 = self.thorlabs_lowlvl_list.key_prof_trapez1 # currently
                good_prof_key2 = self.thorlabs_lowlvl_list.key_prof_trapez2 # currently
                good_prof_verif = self.thorlabs_lowlvl_list.verif_prof_trapez # currently
                good_prof_lbl = self.thorlabs_lowlvl_list.lbl_prof_trapez
    
                other_prof_verif = self.thorlabs_lowlvl_list.verif_prof_scurve 
                other_prof_lbl = self.thorlabs_lowlvl_list.lbl_prof_scurve
                other_prof_key1 = self.thorlabs_lowlvl_list.key_prof_scurve1 
                other_prof_key2 = self.thorlabs_lowlvl_list.key_prof_scurve2 
                
            else: #if self.prof_mode == 2:  # prof. S-curve
                good_prof_key1 = self.thorlabs_lowlvl_list.key_prof_scurve1  # currently
                good_prof_key2 = self.thorlabs_lowlvl_list.key_prof_scurve2  # currently
                good_prof_verif = self.thorlabs_lowlvl_list.verif_prof_scurve # currently
                good_prof_lbl = self.thorlabs_lowlvl_list.lbl_prof_scurve
                other_prof_verif = self.thorlabs_lowlvl_list.verif_prof_trapez 
                other_prof_lbl = self.thorlabs_lowlvl_list.lbl_prof_trapez

            # # time.sleep(0.5) # post  
            prof1, jerk1 = self.thorlabs_lowlvl_list.get_profile_bycommand_meth(1, self.motor_stageXY)
            # print(prof1, good_prof_verif, jerk1, good_prof_key1)
            if (prof1 < 2 and good_prof_verif < 2): # good profile
            # trapezoidal wanted  
                print('Profile CH1 was indeed %s : OK' % good_prof_lbl)
            elif (prof1 == good_prof_verif and abs(jerk1 - self.jerk_mms3_slow) < 1e-3): # S-curve wanted and Jerk param is good
                print('Profile CH1 was indeed %s : OK and Jerk was %.2f mm/s3!' % (good_prof_lbl, jerk1))
                
            else: # not good profile
                
                if prof1 == other_prof_verif: 
                    print('Profile CH1 was %s : WARNING !' % other_prof_lbl)
                else:
                    print('Profile CH1 was %s : WARNING and Jerk was %.2f mm/s3!' % (prof1, jerk1))
                command_set_profile = self.thorlabs_lowlvl_list.commandGen_setProfile_withjerk_meth(1, good_prof_key1, self.jerk_mms3_slow)
                self.motor_stageXY.write(command_set_profile)  # set profile to trapezoidal for both channels
                # control
                prof1, jerk1 = self.thorlabs_lowlvl_list.get_profile_bycommand_meth(1, self.motor_stageXY)

                if ((prof1 < 2 and good_prof_verif < 2) or (prof1 == good_prof_verif and abs(jerk1 - self.jerk_mms3_slow) < 1e-3)): # good profile
                # trapezoidal wanted OR S-curve wanted and Jerk param is good
                    print('Profile CH1 is now %s : OK and jerk is %.2f' % (good_prof_lbl, jerk1 ))
                elif prof1 == other_prof_verif: 
                    print('Profile CH1 is now %s : WARNING ! and jerk is %.2f' % (other_prof_lbl_lbl, jerk1))
                elif prof1 == good_prof_verif: # indeed s-curve but differnt jerk
                    print('Profile CH1 is indeed %s : OK and Jerk is %.2f mm/s3!' % (good_prof_lbl, jerk1))
                else:
                    print('Profile CH1 is now %s : WARNING and Jerk is %.2f mm/s3!' % (prof1, jerk1))
                    
            # time.sleep(0.5) # post    
            prof2, jerk2 = self.thorlabs_lowlvl_list.get_profile_bycommand_meth(2, self.motor_stageXY)
            # print(prof2)
            if (prof2 < 2 and good_prof_verif < 2): # good profile
            # trapezoidal wanted 
                print('Profile CH2 was indeed %s : OK' % good_prof_lbl)
            elif (prof2 == good_prof_verif and abs(jerk2 - self.jerk_mms3_slow) < 1e-3): #  S-curve wanted and Jerk param is good
                print('Profile CH2 was indeed %s : OK and Jerk was %.2f mm/s3!' % (good_prof_lbl, jerk2))
                
            else: # not good profile
                
                if prof2 == other_prof_verif: # S-curve
                    print('Profile CH2 was %s : WARNING !' % other_prof_lbl)
                else:
                    print('Profile CH2 was %s : WARNING and Jerk was %.2f mm/s3!' % (prof2, jerk2))
                command_set_profile2 = self.thorlabs_lowlvl_list.commandGen_setProfile_withjerk_meth(2, good_prof_key2, self.jerk_mms3_slow)
                self.motor_stageXY.write(command_set_profile2)  # set profile to trapezoidal for both channels
                # control
                prof2, jerk2 = self.thorlabs_lowlvl_list.get_profile_bycommand_meth(2, self.motor_stageXY)

                if ((prof2 < 2 and good_prof_verif < 2) or (prof2 == good_prof_verif and abs(jerk2 - self.jerk_mms3_slow) < 1e-3)): # good profile
                # trapezoidal wanted OR S-curve wanted and Jerk param is good
                    print('Profile CH2 is now %s : OK and jerk is %.2f' % (good_prof_lbl, jerk2 ))
                elif prof2 == other_prof_verif: 
                    print('Profile CH2 is now  %s : WARNING ! and jerk is %.2f' % (other_prof_lbl, jerk2))
                elif prof2 == good_prof_verif: # indeed s-curve but differnt jerk
                    print('Profile CH2 is indeed %s : OK and Jerk is %.2f mm/s3!' % (good_prof_lbl, jerk2))
                else:
                    print('Profile CH2 is now  %s : WARNING and Jerk is %.2f mm/s3!' % (prof2, jerk2))
            
            # -------------- control trigger OUT  ------------------------------------
                
            # set TRIGGER OUT to Max Vel. Reached for both channels
            #- none – none – none- none - TRIGOUT HIGH – none – none - Max Vel. 
            # 0-0-0-0-1-0-0-1 in reverse way so 10010000 
            # OR - none – none – none- none - TRIGOUT HIGH – IN-MOTION – none - none
            # 0-0-0-0-1-1-0-0 in reverse way so 00110000 
            
            if self.trigout_maxvelreached == 1: # max vel. reached
                other_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_inmotion # currently
                other_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_inmotion # currently
                other_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_inmotion
                good_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                good_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                good_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
                other_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_inmotion # currently
                other_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_inmotion # currently
                other_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_inmotion
                good_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                good_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                good_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
            elif self.trigout_maxvelreached == 2: # in motion
                good_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_inmotion # currently
                good_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_inmotion # currently
                good_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_inmotion
                other_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                other_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                other_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
                good_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_inmotion # currently
                good_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_inmotion # currently
                good_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_inmotion
                other_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                other_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                other_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
            elif self.trigout_maxvelreached == 0: # trigger off
                good_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_off # currently
                good_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_off # currently
                good_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_off
                other_trig_key1 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                other_trig_verif1 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                other_trig_lbl1 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
                good_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_off # currently
                good_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_off # currently
                good_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_off
                other_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
                other_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
                other_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
                
            # does not help to put the trigger to 0 for Y
            # good_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_off # currently
            # good_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_off # currently
            # good_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_off
            # other_trig_key2 = self.thorlabs_lowlvl_list.key_trigout_maxvelreached # currently
            # other_trig_verif2 = self.thorlabs_lowlvl_list.verif_trigout_maxvelreached # currently
            # other_trig_lbl2 = self.thorlabs_lowlvl_list.lbl_trig_maxvelreached
            self.good_trig_key1 = good_trig_key1
            # time.sleep(0.5) # post  
            # control if TRIGGER OUT to Max Vel. Reached for both channels
            trigger1 = self.thorlabs_lowlvl_list.get_trig_bycommand_meth(1, self.motor_stageXY)
            if trigger1 == good_trig_verif1: # 
                print('Trigger CH1 was indeed OUT HIGH when %s : OK' % good_trig_lbl1)
            else: # not good trigger
                if trigger1 == other_trig_verif1: # 
                    print('Trigger CH1 was OUT HIGH when %s : WARNING !' % other_trig_lbl1)
                else:
                    print('Trigger CH1 was other : %s : WARNING !' % trigger1)
                self.thorlabs_lowlvl_list.set_trig_meth(1, self.motor_stageXY, good_trig_key1) # set TRIGGER OUT
                # control
                trigger1 = self.thorlabs_lowlvl_list.get_trig_bycommand_meth(1, self.motor_stageXY)
                if trigger1 == good_trig_verif1: # 
                    print('Trigger CH1 is now OUT HIGH when %s : OK' % good_trig_lbl1)
                elif trigger1 == other_trig_verif1: # 
                    print('Trigger CH1 is OUT HIGH when %s : WARNING !' % other_trig_lbl1)
                else:
                    print('Trigger CH1 is other : %s : WARNING !' % trigger1)
            
            # time.sleep(0.5) # post    
            trigger2 = self.thorlabs_lowlvl_list.get_trig_bycommand_meth(2, self.motor_stageXY)
            if trigger2 == good_trig_verif2: # 
                print('Trigger CH2 was indeed OUT HIGH when %s : OK' % good_trig_lbl2)
            else: # not good trigger
                if trigger2 == other_trig_verif2: # 
                    print('Trigger CH2 was OUT HIGH when %s : WARNING !' % other_trig_lbl2)
                else:
                    print('Trigger CH2 was other : % s : WARNING !' % trigger2)
                self.thorlabs_lowlvl_list.set_trig_meth(2, self.motor_stageXY, good_trig_key2)
                # control
                trigger2 = self.thorlabs_lowlvl_list.get_trig_bycommand_meth(2, self.motor_stageXY)
                if trigger2 == good_trig_verif2: # 
                    print('Trigger CH2 is now OUT HIGH when %s : OK' % good_trig_lbl2)
                elif trigger2 == other_trig_verif2: # 
                    print('Trigger CH2 is OUT HIGH when %s : WARNING !' % other_trig_lbl2)
                else:
                    print('Trigger CH2 is other : % s : WARNING !' % trigger2)
            
            # -------------- PID parameters  ------------------------------------
            
            self.PID_meth(self.PID_dflt_lst)
            
            min_vel, max_accn_motorX, max_speed_motorX = self.thorlabs_lowlvl_list.get_velparam_bycommand_meth(1, self.motor_stageXY)
            min_vel, max_accn_motorY, max_speed_motorY = self.thorlabs_lowlvl_list.get_velparam_bycommand_meth(2, self.motor_stageXY)
            self.scan_depend_workerXY_togui_signal.emit( max_accn_motorX, max_accn_motorY, max_speed_motorX, max_speed_motorY)
            
            # re-init the read count to 0 (limited to 50)
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
        else: 
            if not hasattr(self, 'motor_stageXY'): self.motor_stageXY = None
        
        if not self.flag_imp:
            self.stageXY_is_imported_signal.emit(False) # False to not st thread_apt (import apt) again
        else:    
            self.stageXY_is_imported_signal.emit(True) # even if stageXY is not here, APT Worker can be started, here automatically. User can also choose to start it by button
        self.flag_imp = False
    
    # not a slot
    def PID_meth(self, varargin): 
    
        [Kp_pos_val_toset, Ki_pos_val_toset, Ilim_pos_val_toset, Kd_pos_val_toset, DerTime_pos_val_toset, OutGain_pos_val_toset, VelFeedFwd_pos_val_toset, AccFeedFwd_pos_val_toset, PosErrLim_pos_val_toset, Kp_pos_val2_toset, Ki_pos_val2_toset, Ilim_pos_val2_toset, Kd_pos_val2_toset, DerTime_pos_val2_toset, OutGain_pos_val2_toset, VelFeedFwd_pos_val2_toset, AccFeedFwd_pos_val2_toset, PosErrLim_pos_val2_toset] = varargin
        
        self.motor_stageXY.reset_output_buffer() # empty the orders
        self.motor_stageXY.reset_input_buffer() # empty the buffer
        # -------------- PID parameters  ------------------------------------
        
        Kp_pos_val, Ki_pos_val, Ilim_pos_val, Kd_pos_val, DerTime_pos_val, OutGain_pos_val, VelFeedFwd_pos_val, AccFeedFwd_pos_val, PosErrLim_pos_val = self.thorlabs_lowlvl_list.req_PIDposition_params_ch_meth(1, self.motor_stageXY)
        if (Kp_pos_val_toset != Kp_pos_val or Ki_pos_val_toset != Ki_pos_val or Ilim_pos_val_toset != Ilim_pos_val or Kd_pos_val_toset != Kd_pos_val or DerTime_pos_val_toset != DerTime_pos_val or OutGain_pos_val_toset != OutGain_pos_val or VelFeedFwd_pos_val_toset != VelFeedFwd_pos_val or AccFeedFwd_pos_val_toset != AccFeedFwd_pos_val or PosErrLim_pos_val_toset != PosErrLim_pos_val):
        
            command_set_PIDpos = self.thorlabs_lowlvl_list.commandGen_PIDposition_set_params_ch_meth(1, Kp_pos_val_toset, Ki_pos_val_toset, Ilim_pos_val_toset, Kd_pos_val_toset, DerTime_pos_val_toset, OutGain_pos_val_toset, VelFeedFwd_pos_val_toset, AccFeedFwd_pos_val_toset, PosErrLim_pos_val_toset)
            self.motor_stageXY.write(command_set_PIDpos)
            Kp_pos_val, Ki_pos_val, Ilim_pos_val, Kd_pos_val, DerTime_pos_val, OutGain_pos_val, VelFeedFwd_pos_val, AccFeedFwd_pos_val, PosErrLim_pos_val = self.thorlabs_lowlvl_list.req_PIDposition_params_ch_meth(1, self.motor_stageXY)
            print('Motor 1 PID is now :', Kp_pos_val, Ki_pos_val, Ilim_pos_val, Kd_pos_val, DerTime_pos_val, OutGain_pos_val, VelFeedFwd_pos_val, AccFeedFwd_pos_val, PosErrLim_pos_val)
        else:
            print('Motor 1 PID was good')
            
        Kp_pos_val2, Ki_pos_val2, Ilim_pos_val2, Kd_pos_val2, DerTime_pos_val2, OutGain_pos_val2, VelFeedFwd_pos_val2, AccFeedFwd_pos_val2, PosErrLim_pos_val2 = self.thorlabs_lowlvl_list.req_PIDposition_params_ch_meth(2, self.motor_stageXY)
        if (Kp_pos_val2_toset != Kp_pos_val2 or Ki_pos_val2_toset != Ki_pos_val2 or Ilim_pos_val2_toset != Ilim_pos_val2 or Kd_pos_val2_toset != Kd_pos_val2 or DerTime_pos_val2_toset != DerTime_pos_val2 or OutGain_pos_val2_toset != OutGain_pos_val2 or VelFeedFwd_pos_val2_toset != VelFeedFwd_pos_val2 or AccFeedFwd_pos_val2_toset != AccFeedFwd_pos_val2 or PosErrLim_pos_val2_toset != PosErrLim_pos_val2):
            
            command_set_PIDpos2 = self.thorlabs_lowlvl_list.commandGen_PIDposition_set_params_ch_meth(2, Kp_pos_val2_toset, Ki_pos_val2_toset, Ilim_pos_val2_toset, Kd_pos_val2_toset, DerTime_pos_val2_toset, OutGain_pos_val2_toset, VelFeedFwd_pos_val2_toset, AccFeedFwd_pos_val2_toset, PosErrLim_pos_val2_toset)
            self.motor_stageXY.write(command_set_PIDpos2)
            Kp_pos_val2, Ki_pos_val2, Ilim_pos_val2, Kd_pos_val2, DerTime_pos_val2, OutGain_pos_val2, VelFeedFwd_pos_val2, AccFeedFwd_pos_val2, PosErrLim_pos_val2 = self.thorlabs_lowlvl_list.req_PIDposition_params_ch_meth(1, self.motor_stageXY)
            print('Motor 2 PID is now :', Kp_pos_val2, Ki_pos_val2, Ilim_pos_val2, Kd_pos_val2, DerTime_pos_val2, OutGain_pos_val2, VelFeedFwd_pos_val2, AccFeedFwd_pos_val2, PosErrLim_pos_val2)
        else:
            print('Motor 2 PID was good')
        
        # # # self.thorlabs_lowlvl_list.commandGen_setProfile_withjerk_meth(1, 2, 0.0108) # jerk in mm/s3
        # # prof1 = self.thorlabs_lowlvl_list.get_profile_bycommand_meth(1, self.motor_stageXY)
        # # print('jerk ', prof1[1])
        
        # re-init the read count to 0 (limited to 50)
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
    
    def control_if_thread_stage_avail_meth(self):  
        # just to control availability
        bb = self.thorlabs_lowlvl_list.req_info_ch_meth(0, self.motor_stageXY)
        self.home_ok.emit(0) # connected for mosaic to a different Slot
    
    @pyqtSlot()
    def control_if_home_stage_necessary_meth(self):
        # control if home stage is necessary, and ask for it if yes
        
        # try:
        if not self.motor_stageX_is_here:
            self.ct_init_fail += 1 # add
            print('\n motor stageX was not defined : is it connected ? %d\n' % self.ct_init_fail)
            # raise Exception # goes to except block
        else: # motor X connected
                
            if not self.motor_stageY_is_here:
                self.ct_init_fail += 1 # add
                print('\n motor stageY was not defined : is it connected ? %d \n' % self.ct_init_fail)
                # raise Exception # goes to except block
                
            else:  # motor X and Y connected
                self.ct_init_fail =  0 # reset
                if self.home_done:
                    print('already homed, check the option above if you want to force it !')
                else:
                    # pos_trans_ini = self.motor_trans.position
    
                    posX = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, self.motor_stageXY) # x
                    
                    posY = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, self.motor_stageXY) # y
                    
                    if (posX >= 0.1 and posY >= 0.1): # in mm, both motors have been homed previously
                        # self.posX0 = self.motorX.position
                        # self.posY0 = self.motorY.position
                        
                        self.posX0 = posX
                        self.posY0 = posY
                        
                        self.posX_indic_real_signal.emit(self.posX0) # change the indic box in the GUI (without further notifications)
                        self.posY_indic_real_signal.emit(self.posY0) # change the indic box in the GUI (without further notifications)
                    
                        self.home_ok.emit(0)
                        print("Stage actual pos. defined \n")
                        self.home_done = True
                        
                        if (posX < 8 or posY < 8): # unusual
                            self.ask_if_safe_pos_for_homing_signal.emit(True) # # True for telling that this pos is unusual, and to ask if re-home
                
                    else:
                        print('Need to (re)-init the stage motors ...')
                        self.ask_if_safe_pos_for_homing_signal.emit(False) # send to the GUI to open a prompt to ask if objective pos are safe ; 0 because of no pos defined
            
        if self.ct_init_fail > 3:
            self.close_motorXY(False) # # false not GUI end
            self.reload_scan_worker_signal.emit(1) # # 1 for real close and reinit
            
    @pyqtSlot()
    def home_stage_meth_forced(self):
        
        # empty the queue
        try:
            self.stop_motorsXY_queue.get_nowait()
        except self.queueEmpty:  # nothing in queue
            pass # do nothing
        
        try:
            if self.motor_stageX_is_here:
                
                print("Stage X is moving home ...")
                # self.motorX.move_home(True)
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_home1)
                
                blocking = True
                self.motor_blocking_meth(self.motor_stageXY, 1, self.stop_motorsXY_queue, self.queueEmpty, self.thorlabs_lowlvl_list, -1, 6, self.time, blocking)
        
                self.posX0 = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, self.motor_stageXY) # x
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
        
            else:
                print('\n motor stageX is not here : is it connected ?\n')
                
            if self.motor_stageY_is_here:
                print("Stage Y is moving home ... \n")
                #self.motorY.move_home(True)
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_home2)
                
                blocking = True
                self.motor_blocking_meth(self.motor_stageXY, 2, self.stop_motorsXY_queue, self.queueEmpty, self.thorlabs_lowlvl_list, -1, 6, self.time, blocking)
        
                self.posY0 = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, self.motor_stageXY) # y
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
                
            else:
                print('\n motor stageY is not here : is it connected ?\n')
            
            if (self.posX0 < 0 or self.posY0 < 0):
                
                print('error on init stage motors')
                # raise Exception # goes to except block
            else: # no error
                self.posX_indic_real_signal.emit(self.posX0) # change the indic box in the GUI (without further notifications)
                self.posY_indic_real_signal.emit(self.posY0) # change the indic box in the GUI (without further notifications)
                
                self.home_ok.emit(0)
                self.home_done = True
                
                print("Moved stage home forced\n")
            
        except:
            
            print('Could not home motor FORCED : trying to import again lib, you should retry after that... \n')

            self.open_lib()
    
    @pyqtSlot(float)
    def move_motor_X(self, posX):
        
        # empty the queue
        try:
            self.stop_motorsXY_queue.get_nowait()
        except self.queueEmpty:  # nothing in queue
            pass # do nothing
        
        # # print('received order to move X to %f' % posX)
        
        if (posX < self.min_posX):
            posX = self.min_posX
            
        if posX > self.max_posX:
            posX = self.max_posX
            
        # # self.motorX.move_to(posX, True) 
        
        command_moveAbs1 = self.thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(1, posX)
        
        self.motor_stageXY.write(command_moveAbs1)
        
        blocking = True # # blocking but stop still possible
        self.motor_blocking_meth(self.motor_stageXY, 1, self.stop_motorsXY_queue, self.queueEmpty, self.thorlabs_lowlvl_list, -1, 20, self.time, blocking)
 
        posX_real = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, self.motor_stageXY) # real posX set
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
        
        self.posX_indic_real_signal.emit(posX_real) # change the indic box in the GUI (without further notifications)
        
        # print(self.motor_stageXY.readline())
        
    
    @pyqtSlot(float)
    def move_motor_Y(self, posY):
        
        # empty the queue
        try:
            self.stop_motorsXY_queue.get_nowait()
        except self.queueEmpty:  # nothing in queue
            pass # do nothing 
    
        # print('received order enter in moveY...')
        # posY = self.queue_posY.get()
        
        # # print('received order to move Y to %f' % posY)
        
        if (posY < self.min_posY):
            posY = self.min_posY
            
        if posY > self.max_posY:
            posY = self.max_posY
        
        # self.motorY.move_to(posY, True) 
        
        command_moveAbs2 = self.thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(2, posY)
        
        self.motor_stageXY.write(command_moveAbs2)
        
        blocking = True # # blocking but stop still possible
        self.motor_blocking_meth(self.motor_stageXY, 2, self.stop_motorsXY_queue, self.queueEmpty, self.thorlabs_lowlvl_list,  -1, 20, self.time, blocking)
            
        posY_real = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, self.motor_stageXY) # real posX set
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
        
        self.posY_indic_real_signal.emit(posY_real) # change the indic box in the GUI (without further notifications)
    
    '''
    # not used
    @pyqtSlot()
    def stop_motors_stageXY_meth(self):
        # stop both motors
        
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_stop1) # x
        blocking = True
        if blocking: # wait for MGMSG_MOT_MOVE_COMPLETED
            
            bb = self.motor_stageXY.read(20) 
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
            
        self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_stop2) # y
        blocking = True
        if blocking: # wait for MGMSG_MOT_MOVE_STOPPED
            bb = self.motor_stageXY.read(20)  
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
         
    '''
            
    @pyqtSlot(float, float, float, float, int, int, float)
    def change_scan_dependencies(self, max_accn_motorX, max_accn_motorY, max_speed_motorX, max_speed_motorY, lbl_mtr_fast, profile_mode_fast, jerk_fast ): 
        # change speed, acc. or profile of motor
    
        # scan_dependencies = self.queue_scan_dependencies.get() # a list of speed, acceleration
        # 
        # self.max_accn_motorX = scan_dependencies[0]
        # self.max_accn_motorY = scan_dependencies[1]
        # self.max_speed_motorX = scan_dependencies[2]
        # self.max_speed_motorY = scan_dependencies[3]
        
        if (hasattr(self, 'motor_stageXY') and self.motor_stageXY is not None):
            self.motor_stageXY.reset_input_buffer()
            self.motor_stageXY.reset_output_buffer()
        
            if (max_accn_motorX != self.max_accn_motorX_current or max_speed_motorX != self.max_speed_motorX_current):
                # self.motorX.set_velocity_parameters(0, max_accn_motorX, max_speed_motorX) # first arg is 0 and ignored
                
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(1, max_speed_motorX, max_accn_motorX))
                
                min_vel, max_accn_motorX, max_speed_motorX = self.thorlabs_lowlvl_list.get_velparam_bycommand_meth(1, self.motor_stageXY)
                print('For CH1 : min_vel = %.1f, max_acc = %.2f, max_vel = %.6f' % (min_vel, max_accn_motorX, max_speed_motorX))
                # as the round is precise to +-1, the precision on the speed is 1/MLS203_scfactor_vel = 7.45e-06 mm/s
                # as the round is precise to +-1, the precision on the speed is 1/MLS203_scfactor_acc = 7.28e-02 mm/s2
            
            if (max_accn_motorY != self.max_accn_motorY_current or max_speed_motorY != self.max_speed_motorY_current):
                #self.motorY.set_velocity_parameters(0, max_accn_motorY, max_speed_motorY) # first arg is 0 and ignored
                self.motor_stageXY.write(self.thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(2, max_speed_motorY, max_accn_motorY))
                
                min_vel, max_accn_motorY, max_speed_motorY = self.thorlabs_lowlvl_list.get_velparam_bycommand_meth(2, self.motor_stageXY)
                print('For CH2 : min_vel = %.1f, max_acc = %.2f, max_vel = %.6f' % (min_vel, max_accn_motorY, max_speed_motorY))
                
            self.max_accn_motorX_current = max_accn_motorX # something proper to this Worker, no communication with the GUI
            self.max_accn_motorY_current = max_accn_motorY
            self.max_speed_motorX_current = max_speed_motorX
            self.max_speed_motorY_current = max_speed_motorY
            
            command_set_profile = self.thorlabs_lowlvl_list.commandGen_setProfile_withjerk_meth(lbl_mtr_fast, profile_mode_fast, jerk_fast)
            self.motor_stageXY.write(command_set_profile)
            
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive1)
            self.motor_stageXY.write(self.thorlabs_lowlvl_list.command_serv_alive2)
            
            self.scan_depend_workerXY_togui_signal.emit( max_accn_motorX, max_accn_motorY, max_speed_motorX, max_speed_motorY)
            
        else:
            print('I did not do anything in scan dep. since the motorXY was not defined !\n')

        
    @pyqtSlot(bool, int, list, list, int, bool, tuple, int)
    def scan_stage_meth(self, debug_mode, scan_mode, min_val_volt_list, max_val_volt_list, device_used_AIread, sec_proc_forishgfill, dep_dflt_list, real_time_disp): 
    # # called by new_scan_stage_signal
    
        msg = 'def scan in stageXY worker'
        if debug_mode: msg+='\n IN DEBUG MODE !!!!\n'
        print(msg)
        try: # # check if motor ok before starting anything
            posX = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, self.motor_stageXY) # x
            posY = self.thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, self.motor_stageXY) # y
        except Exception as e:
            print('ERROR:',  e)
            # # return
        else: print('pos before scan:', posX, posY)
            
        from modules import go_scan_stage2
        # I just need that, and it's a pain to transfer via Signal
    
        # if you put this outside this function, the code has the good idea to import it all the time you do a scan

        # # the launch scan button in GUI should check if parameters changed: if so, it should send via queue the info
        if self.motor_stageXY is not None: # # for simu
            self.PID_meth(self.PID_scn_lst)
        else:  self.good_trig_key1 = None   # # for simu
        
        trig_src = [device_used_AIread, self.trig_src_name_stgscan]
        
        if device_used_AIread == 1: # 6110
            max_value_pixel = self.max_value_pixel_6110
        elif device_used_AIread == 2: # 6259
            max_value_pixel = self.max_value_pixel_6259
        
        self.scan_thread_available_signal.emit(False)
            # scan_mode is 0 for stage scan (useless here)
        try:
            go_scan_stage2.go_stage_scan_func_mp(self.motor_stageXY, min_val_volt_list, max_val_volt_list, trig_src, scan_mode, self.queue_com_to_acq, self.queue_special_com_acqstage_stopline, self.queue_list_arrays, max_value_pixel, self.time, self.numpy, self.time_out, self.new_img_to_disp_signal, self.queue_moveX_inscan, self.queue_moveY_inscan, self.reload_scan_worker_signal, self.queueEmpty, self.trigout_maxvelreached, self.calc_param_scan_stg_signal, self.stop_motorsXY_queue, self.prof_mode_slow, self.jerk_mms3_slow, self.acc_max, self.motor_blocking_meth, self.block_slow_stgXY_before_return, self.piezoZ_step_signal, self.good_trig_key1, sec_proc_forishgfill, real_time_disp, dep_dflt_list, debug_mode) 
        
        except:
            import traceback
            traceback.print_exc()
        
        finally: # in all cases
            self.motor_stageXY.reset_input_buffer() # empty the unread msgs
            self.motor_stageXY.reset_output_buffer() # empty the orders
            # # walla it's necessary, because it was shown some bug can occur if stage scan fast
            self.time.sleep(0.5) # post-purge
            self.PID_meth(self.PID_dflt_lst)
            
            print('The scan stage method has terminated properly') 
            
            self.scan_thread_available_signal.emit(True)
            # the end of this method will allow the close_motor_signal to be received (if closing GUI) and go to close_motorXY(self)
        
    @pyqtSlot(bool)
    def close_motorXY(self, flag_end):
        
        # # print(self.motor_stageX_is_here , self.motor_stageY_is_here)
        if (self.motor_stageX_is_here and self.motor_stageY_is_here):
            # # print('closed')
            self.motor_stageXY.close() # works with Serial or FTDI
        
        if flag_end: # end of program    
            self.queue_disconnections.put(2) # tell the GUI can kill this QThread : motorXY's signature is 2
        
## definition of a very used method for moving

# putting it outside the Class allow to easily use it in other scripts
def motor_blocking_meth(motor_stageXY, str_motor_stop, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_motion , tot_bytes2read, time, blocking):
    '''
    blocking = True (or 1) : blocking
        = 2 : verify channel is good
        = 3 : verify channel + returns if there is a 0 
    '''
    
    if str_motor_stop == 1: # X
        command_stop = thorlabs_lowlvl_list.command_stop1
        command_alive = thorlabs_lowlvl_list.command_serv_alive1
        good_b = b'!'
    elif str_motor_stop == 2: # Y
        command_stop = thorlabs_lowlvl_list.command_stop2
        command_alive = thorlabs_lowlvl_list.command_serv_alive2
        good_b = b'"'

    timed_out = False
    stop_scanloop = 0
    # blocking or not
    if blocking: # wait for MGMSG_MOT_MOVE_COMPLETED
        bb = b'' # binary empty
        st_time = time.time()
        while (len(bb) < tot_bytes2read): # not bool(bb):
        
            if (time_out_motion >= 0 and (time.time() - st_time) >= time_out_motion): # time_out_motion = -1 for infinite waiting
                print('\n read move complete timed out for motor %d !! \n' % str_motor_stop)
                timed_out = True
                print(bb)
                break
            
            try:
                stop_motorsXY_queue.get_nowait()
                
            except queueEmpty:  # no stop msg, normal
                bb_new = motor_stageXY.read(tot_bytes2read - len(bb)) # try to read the MOVE_COMPLETED string, during time_out seconds only (short time) !
                motor_stageXY.write(command_alive)
                bb = bb + bb_new
                # # print(bb)
                
            else:  # stop msg !
                        
                motor_stageXY.write(command_stop) # stop X, profiled
                stpgarbage = b'' # binary empty
                while len(stpgarbage) < 20: # not bool(bb):
                    stpgarbage = motor_stageXY.read(20 - len(stpgarbage))  # wait for MGMSG_MOT_MOVE_STOPPED, during time_out seconds only (short time) !
                    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive1)
                    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive2)
                stop_scanloop = 1
                break # outside big 'while' loop
        # # print(bb)

        if blocking == 2:
            if len(bb)>=6:
                # do not re-use good_b 
                if bb[5:6] != good_b: # wrong channel read
                    good_b = False
            # #     else: # good channel read
            # #         good_b = True # good ch
            # # else:
            # #     good_b = True # good ch

            return stop_scanloop, good_b, timed_out
                
    return stop_scanloop