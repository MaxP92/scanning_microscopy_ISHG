# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2017

@author: Maxime PINSARD
"""

# worker for APT without the XY stage controled by low-level commands

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal, QTimer
path_computer = 'C:/Users/admin/Documents/Python'

# # don't put imports here !!
# # the Processes will see them
        
class Worker_apt(QObject):
    
    '''
    You have to divide this class into one class for each device (to have them independent)
    '''

    pos_phshft_signal = pyqtSignal(int, str)
    angle_rot_signal = pyqtSignal(int, float)
    pos_trans_signal = pyqtSignal(int, str)
    motor_phshft_finished_move_signal = pyqtSignal(int)
    motor_trans_finished_move_signal = pyqtSignal(int)
    motor_polar_finished_move_signal = pyqtSignal(int)
    motor_phshft_homed_signal = pyqtSignal()
    motor_trans_homed_signal = pyqtSignal()
    motor_polar_homed_signal = pyqtSignal()
    vel_acc_bounds_signal = pyqtSignal(int, float, float)
    vel_acc_define_signal = pyqtSignal(int, float, float)
    apt_is_imported_signal = pyqtSignal(list, list, list)
    close_timer_sign = pyqtSignal()

    def __init__(self, motor_phshft_ID, motor_rot_ID, motor_trans_ID, motorX_ID, motorY_ID, dist_mm_typical_phshft, queue_disconnections, jobs_window, jobs_scripts, params_mtr_set_func, time): 
    
        super(Worker_apt, self).__init__()
        
        self.motor_phshft = 0

        self.motor_phshft_ID = motor_phshft_ID; self.motor_rot_ID = motor_rot_ID; self.motor_trans_ID = motor_trans_ID
        self.motorX_ID = motorX_ID; self.motorY_ID = motorY_ID
        self.queue_disconnections = queue_disconnections
        self.jobs_window = jobs_window ; self.jobs_scripts = jobs_scripts
        self.dist_mm_typical_phshft = dist_mm_typical_phshft
        self.params_mtr_set_func = params_mtr_set_func
        self.time = time
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.background_get_func)
        self.timer.start(300) # msec
        self.ct_timer = 0
        self.wait_flag = False # # keep it there also, otherwise can be undefined !

    @pyqtSlot()
    def open_lib(self):
     
        self.motor_phshft_is_here = self.motor_trans_is_here = self.motor_rot_is_here = name_cube_plr = name_cube_tr = name_cube_ps = 0
        
        import os, sys
        path1 = os.getcwd()
        os.chdir('%s/Packages/thorlabs_apt-0.1' % path_computer)
        print('Importing Thorlabs APT ...')
        if 'thorlabs_apt' in sys.modules: # has already been imported
            # # del self.apt
            # # del sys.modules['thorlabs_apt']
            # # importlib.reload(self.apt) # using reload or new apt import does not detect changes
            
            if hasattr(self, 'apt'):
                self.apt.cleanup() # clean
                self.apt.reinit() # re-init
                # # self.apt.core._lib = self.apt.core._load_library() # # !!!
            else:
                try:
                    self.apt = thorlabs_apt
                except Exception as e:
                    print(e)
                    import thorlabs_apt
                    self.apt=thorlabs_apt                
        else: # new
            import thorlabs_apt
            self.apt=thorlabs_apt
        print('APT imported')
        os.chdir(path1)
        
        list = self.apt.list_available_devices()
        print('Available APT devices :', list)
        
        for i in range(len(list)):
            
            # if list[i][1] == self.motorX_ID:
            # 
            #     self.motor_stageX_is_here = 1
            #     self.motorX = self.apt.Motor(self.motorX_ID)
            #     
            # elif list[i][1] == self.motorY_ID:
            #     
            #     self.motor_stageY_is_here = 1
            #     self.motorY = self.apt.Motor(self.motorY_ID)
            
            if (list[i][1] == self.motor_phshft_ID and not self.motor_phshft_is_here): # # phase-shift mtr (rot plate)
            # # keep the not self.motor_phshft_is_here, for the cases reload apt
                
                try:
                    
                    self.motor_phshft = self.apt.Motor(self.motor_phshft_ID)
                    self.motor_phshft_is_here = 1  
                    self.motor_rotplate = self.motor_phshft
       
                    pos_mm, max_acc, max_vel, name_cube_ps = self.params_mtr_set_func(self.motor_phshft, self.motor_phshft_ID, -24, 24, 4, 2.6, self.dist_mm_typical_phshft  )
                    self.pos_phshft_signal.emit(1, ('%.3f' % (pos_mm*1000))) # because has to be in um, not mm
                    self.vel_acc_bounds_signal.emit(1,  max_vel, max_acc)
                    self.jobs_window.pos_motor_phshft_edt.setEnabled(True)
                except Exception as err:
                    self.motor_phshft_is_here = 0
                    print('ERROR: mtr phshft seems not to be connected to the detected T-cube !')
                    print(err)
                else:
                    self.motor_phshft_is_here = 1
                                    
            elif (list[i][1] == self.motor_trans_ID and not self.motor_trans_is_here): # # trans mtr (calcites)
                
                # try:
                self.motor_trans = self.apt.Motor(self.motor_trans_ID)
                self.motor_trans_is_here = 1

                pos_mm, max_acc, max_vel, name_cube_tr = self.params_mtr_set_func(self.motor_trans, self.motor_trans_ID, -27.9, 32, 4, 2.6, self.dist_mm_typical_phshft  )
                self.vel_acc_bounds_signal.emit(2, max_vel, max_acc)
                self.pos_trans_signal.emit(2, ('%.3f' % (pos_mm*1000))) # because has to be in um, not mm
                self.jobs_window.pos_motor_trans_edt.setEnabled(True)
            # except Exception as err:
            #     self.motor_trans_is_here = 0
            #     print('ERROR: mtr trans seems not to be connected to the detected T-cube !')
            #     print(err)
            # else:
                self.motor_trans_is_here = 1
                
            elif (list[i][1] == self.motor_rot_ID and not self.motor_rot_is_here):  # # turn polar
                
                try:
                    self.motor_rot = self.apt.Motor(self.motor_rot_ID)
                    
                    t = self.motor_rot.get_stage_axis_info()
                    name_cube_plr = self.motor_rot.hardware_info[0].decode()
                    self.motor_rot.set_stage_axis_info(0, 360, 2, t[3]) # min pos, max pos, unit (2 = deg), pitch
                    self.motor_rot.set_motor_parameters(steps_per_rev=512, gear_box_ratio=67)
                    self.motor_rot.set_move_home_parameters(direction=2, lim_switch=1, velocity=20, zero_offset=0)
                    opt_vel = (10*20/2)**0.5 # # step of ~ 10deg, accn = 20deg/s2 max
                    self.motor_rot.set_velocity_parameters(0, accn=20, max_vel=opt_vel)
                    
                    print('motor ID %d is here' % self.motor_rot_ID)
                    
                    angle_rot_m = self.motor_rot.position # is in mm
                                    
                    self.angle_rot_signal.emit(1, angle_rot_m) # 1 for the TL rot motor
                    
                except Exception as err:
                    self.motor_rot_is_here = 0
                    print('ERROR: mtr polar seems not to be connected to the detected T-cube !')
                    print(err)
                else:
                    self.motor_rot_is_here = 1
                
            elif list[i][1] in (self.motorX_ID, self.motorY_ID):
                print('\n !! motors XY in APT, not independent !!\n')
        
        self.wait_flag = False
        self.apt_is_imported_signal.emit([self.motor_rot_is_here, name_cube_plr], [self.motor_phshft_is_here, name_cube_ps], [self.motor_trans_is_here, name_cube_tr])
        
    @pyqtSlot(int, bool)
    def move_home_phshft(self, ID, forced):    
    # is connected by home_motor_phshft_signal and this latter is emitted when cal_calcites_meth (in GUI) is called 
    
        if ID == 0: # rotplate
            mtr = self.motor_rotplate
            here = self.motor_phshft_is_here
            sign = self.pos_phshft_signal
            sign_home = self.motor_phshft_homed_signal
            name = 'phshft rot.'
        elif ID == 1: # trans
            mtr = self.motor_trans
            here = self.motor_trans_is_here
            sign = self.pos_trans_signal
            sign_home = self.motor_trans_homed_signal
            name= 'trans'
            
        if here:
            pos_phshft_ini = mtr.position
            
            if ((pos_phshft_ini <= -6 or pos_phshft_ini > 6)): # position that has no sense, got to home the motor
                
                print('pos_ini_phshft = %.3g  mm !!\n' % pos_phshft_ini)
                mtr.move_home(self.wait_flag) # execute only if needed, compulsory if first init
                
                print("Moved phshft motor home \n")
                
            self.pos0_phshft = mtr.position # is in mm
            
            if forced:
                mtr.move_home(self.wait_flag) # execute only if needed, compulsory if first init
            
            str1=('%.3g' % (self.pos0_phshft*1000))
            sign.emit(ID+1, str1) # because has to be in um, not mm
            
            sign_home.emit() # was homed
            
            print("Actual %s motor pos defined \n" % name)
            
        else:
            print('motor %s was not defined : is it connected ?' % name)
        
    
    @pyqtSlot()
    def move_home_polar(self):    
    # is connected by home button on 2nd window of GUI 
    
        if self.motor_rot_is_here:
                 
            self.motor_rot.move_home(self.wait_flag) # execute only if needed, compulsory if first init
            
            print("Moved polar motor home \n")
                
            self.pos0_polar = self.motor_rot.position # is in mm
            self.angle_rot_signal.emit(1, self.pos0_polar)  # 1 for rot # ('%.3g' % (
            self.motor_polar_homed_signal.emit()
                        
        else:
            print('motor polar was not defined : is it connected ?')
        
    @pyqtSlot(float, bool)    
    def move_motor_phshft(self, pos_phshft, send): 
        # function to move the phshft motor
        self.jobs_scripts.move_ph_shft_meth(self.wait_flag, 1, self.motor_phshft, pos_phshft, self.pos_phshft_signal, self.motor_phshft_finished_move_signal, send) # # 1 for rot gp
        self.motor_phshft_is_here = True # if success, to reconnect motor from bug in com
        
    @pyqtSlot(float)    
    def move_motor_rot_polar(self, angle_rot):
        # function to move the rotation motor
        
        self.jobs_scripts.move_rot_polar_meth(self.wait_flag, self.motor_rot, angle_rot, self.angle_rot_signal, self.motor_polar_finished_move_signal, 'APT', 1) # flag_wait, id_motor
        self.motor_rot_is_here = True # if success, to reconnect motor from bug in com
        
    @pyqtSlot(float, bool)    
    def move_motor_trans(self, pos, send): 
    
        if hasattr(self, 'motor_trans'):
            self.jobs_scripts.move_ph_shft_meth(self.wait_flag, 2, self.motor_trans, pos, self.pos_trans_signal, self.motor_trans_finished_move_signal, send) # # 2 for trans
            self.motor_trans_is_here = True # if success, to reconnect motor from bug in com
            
    @pyqtSlot()
    def get_pos_polar(self):   
        # is connected by home button on 2nd window of GUI 

        pos0_polar = self.motor_rot.position # is in deg
        self.angle_rot_signal.emit(1, pos0_polar)  # 1 for rot # ('%.3g' %
        self.motor_rot_is_here = True # if success, to reconnect motor from bug in com
        
    def get_pos_ps(self, bb):   
        # 
        prec = 3+round(bb/15)*3
        str = '%.3f' if prec <=3 else '%.6g'
        if (bb in (1, 11) and self.motor_phshft_is_here): # # rot gp
            mtr = self.motor_phshft
            sign = self.pos_phshft_signal
        elif (bb in (2, 22) and self.motor_trans_is_here): # trans
            mtr = self.motor_trans
            sign =  self.pos_trans_signal # #  if bb == 2 else self.pos_trans_signal
        else:
            return # anormal
        pos_mm = mtr.position # is in deg
        sign.emit(bb, str % (pos_mm*1000))  # 1 for rot # ('%.3g' %
    
    @pyqtSlot(int, float, float)    
    def vel_acc_set_func(self, num_mtr, max_acc, opt_vel):
        # # direct call or signal
        
        if num_mtr == 0: # # polar
            motor_instr = self.motor_polar
        elif num_mtr == 1: # # rot. gp
            motor_instr = self.motor_rotplate # glass plate
        elif num_mtr == 2: # # trans.
            motor_instr = self.motor_trans
        
        motor_instr.set_velocity_parameters(0, accn= max_acc, max_vel=opt_vel)
        [min_vel, acc, vel]= motor_instr.get_velocity_parameters()
        print('get_vel_acc', motor_instr.get_velocity_parameters())
        self.vel_acc_define_signal.emit(num_mtr, vel, acc)
     
    @pyqtSlot()   
    def stop_func(self):
        # # button GUI
    
        # # for mtr in (self.motor_rot, 
        if (self.motor_trans_is_here and self.motor_trans.is_in_motion):
            self.motor_trans.stop_profiled()
            self.jobs_window.pos_motor_trans_edt.blockSignals(True)
            self.jobs_window.pos_motor_trans_edt.setText(self.jobs_window.trans_pos_live_lbl.text())
            self.jobs_window.pos_motor_trans_edt.blockSignals(False)
        if (self.motor_rot_is_here and self.motor_rot.is_in_motion):
            self.motor_rot.stop_profiled()
        if (self.motor_phshft_is_here and self.motor_phshft.is_in_motion):
            self.motor_phshft.stop_profiled()
        
    @pyqtSlot()
    def clean_apt(self): 
    
       # print(self.apt.list_available_devices())
        self.apt.cleanup() # warning cleanup is from a MODIFIED version of core.py of APT (copy the function _cleanup into cleanup)
        # WARNING : it erased only the available devices
        # it's used in other libraries to disconnect : http://qosvn.physik.uni-ulm.de/trac/qudi/browser/hardware/motor/aptmotor.py
        self.queue_disconnections.put(3) # tell the GUI the APT is closed : APT's signature is 3
    
    @pyqtSlot()    
    def background_get_func(self):
        # timer
        self.ct_timer += 1
        id = 0
        # # if self.ct_timer
        if self.motor_rot_is_here:
            # # self.get_pos_polar()
            try:
                pos0_polar = self.motor_rot.position # is in deg
                self.angle_rot_signal.emit(11, pos0_polar)  # # 11 for live (rot)
            except Exception as e:
                if (type(e) == Exception):
                    print('mtr APT ID%d is not here anymore' % id)
                else:
                    print('unknown err APT ID%d' % id)
                self.motor_rot_is_here = False
        id_list = []
        if self.motor_phshft_is_here:
            id_list.append( 11) # rot gp, 11 for live
        if self.motor_trans_is_here:
            id_list.append( 22)
        for id in id_list:
            if id > 0:
                try:
                    self.get_pos_ps(id) # trans, 22 for live
                except Exception as e:
                    # # print(type(e)); 
                    # # print(type(e) == Exception, e == 'Getting position failed: Internal error.') # # true false
                    if (type(e) == Exception): ##and e == 'Getting position failed: Internal error.'):
                        print('mtr APT ID%d is not here anymore' % id)
                    else:
                        print('unknown err APT ID%d' % id)
                    if id == 22: self.motor_trans_is_here = False
                    else: self.motor_phshft_is_here = False
    
    @pyqtSlot()        
    def close_timer(self):
        self.timer.stop()
        
def params_mtr_set_func(motor, motor_ID, min_pos_mm, max_pos_mm, max_acc00, max_vel00, dist_mm_typical_phshft ):
# # called directly

    # set profile
    (profile_mode, jerk) = motor.get_dc_profile_mode_parameters() # profile_mode, jerk
    # # (2, 7979.7294921875) for mts25 trans
    motor.set_dc_profile_mode_parameters( 0, jerk) # # 0 for trapez
    t = motor.get_stage_axis_info()
    name_cube = motor.hardware_info[0].decode()
    if name_cube == 'TDC001': # # old T cube
        motor.set_motor_parameters(steps_per_rev=48, gear_box_ratio=256)
        max_acc = 0.45 # # mm/s2
        max_vel = 0.5 # # mm/sec
    elif name_cube == 'KDC001': # # new K cube
        # # values for the Z825B !
        max_acc = max_acc00 # 4 # # mm/s2
        max_vel = max_vel00 #  2.6 # # mm/sec
    motor.set_stage_axis_info(min_pos_mm, max_pos_mm, 1, t[3]) # min pos, max pos, unit (1 = mm), pitch
    opt_vel = min(max_vel, (dist_mm_typical_phshft*max_acc/2)**0.5) # # step of ~ 0.07mm = 1deg, accn = 0.4mm/s2 max
    motor.set_velocity_parameters(0, accn= max_acc, max_vel=opt_vel)
    
    print('motor ID %d is here' % motor_ID)
    return motor.position, max_acc, max_vel, name_cube # is in mm