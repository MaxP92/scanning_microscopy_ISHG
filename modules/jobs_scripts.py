# -*- coding: utf-8 -*-
"""
Created on Mon Nov 07 11:35:13 2016

@author: Maxime PINSARD
"""

from PyQt5 import QtWidgets
from modules import param_ini

def truncate(f, n): # # returns string !!
    '''Truncates/pads a float f to n decimal places without rounding'''
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d+'0'*n)[:n]])
    
    ## def jobs

def list_calib_motor_phshft_func(numpy, nb_frame, eq_deg_um_theo, max_angle, add_modulo_2pi):
    # for calibration
    
    # eq_um_deg = round(5.2/180*10000)/10000
    
    list_deph_deg = numpy.linspace(0, max_angle, nb_frame) 
    
    if add_modulo_2pi:
        # just to ensure the step is sufficently high not to enter in the error step of the motor
        v = [0, -360]
        vv = numpy.tile(v, int(round(nb_frame/2))+1)  # # round sometimes gives .0 !
        vv= vv[0:len(list_deph_deg)] # for odd number cases
        list_deph_deg_p = list_deph_deg + vv
    else:
        list_deph_deg_p = list_deph_deg
        
    list_pos_wrt_origin = numpy.round(list_deph_deg_p/eq_deg_um_theo,1) # in um
    
    return list_pos_wrt_origin
    
    
def list_steps_motor_phshft_func(numpy, eq_deg_um, step_phase_shift, nb_fr_stp, force_incr_ps):
    # for acquisition of stack
    
    # # if not use_calib: # # use steps
    list_deph_deg_1 = numpy.linspace(0, 180-step_phase_shift, int(round(360/step_phase_shift/2)))  # # round sometimes gives .0 !
    list_deph_deg_2 = list_deph_deg_1 + 180 
    if nb_fr_stp == 3: # # 0, 180, 360 deg
        list_deph_deg_3 = list_deph_deg_1 + 360 
    elif nb_fr_stp == 2: # # 0, 180 deg
        list_deph_deg_3 = None
    else: # 1
        list_deph_deg_1 = numpy.linspace(0, 360-step_phase_shift, int(round(360/step_phase_shift)))  # # round sometimes gives .0 !
        list_deph_deg_2 = list_deph_deg_3 = None
        
    arr = numpy.reshape(numpy.vstack((list_deph_deg_1, list_deph_deg_2, list_deph_deg_3)).T, (1, nb_fr_stp*len(list_deph_deg_1))) if nb_fr_stp > 1 else list_deph_deg_1
    list_deph_deg = numpy.ndarray.flatten(arr) # list of phase-shift as it was usually used by Rivard
        
        # list_deph_deg = list_deph_deg[1:len(list_deph_deg)] # remove 1st 
        # the smallest step is 360 - step_phase_shift, so it is high indeed and normally does not enter in the error step of the motor
    list_pos_wrt_origin = list_deph_deg/eq_deg_um # in um
    # # else:
    if force_incr_ps: list_pos_wrt_origin = numpy.sort(list_pos_wrt_origin) # increasing
    
    nb_frame_ps = len(list_pos_wrt_origin)
    
    return list_pos_wrt_origin, nb_frame_ps 
    
def list_steps_stack_func(numpy, strt_stack, step_stack, end_stack, nb_frame_stack):
    # everything in mm
    
    if (nb_frame_stack == 0): # nb frames not imposed
        nb_frame = int(round((end_stack - strt_stack)/step_stack))+1 # # # round sometimes gives .0 !
    else:
        nb_frame = nb_frame_stack
    
    list_pos_stack_abs = numpy.linspace(strt_stack, end_stack, nb_frame)
    
    # # print('list_pos_stack_abs = ', list_pos_stack_abs)
    
    step_calc = list_pos_stack_abs[1] - list_pos_stack_abs[0]
    
    return list_pos_stack_abs, nb_frame, step_calc   

def load_ps_list_func(QtWidgets, numpy):

    uu  = QtWidgets.QFileDialog.getOpenFileName(None, 'Open your file !', 'C:/Users/admin/Desktop/list.txt', '*.txt', '*.txt') #, 'C:/Users/admin/Documents/Python/prog microscope 7') #, '.txt') # (QWidget parent = None, QString caption = '', QString directory = '', QString filter = '', QString selectedFilter = '', Options options = 0)
    if uu is not None:
        print(uu[0])
        # list_pos_wrt_origin = numpy.loadtxt(uu[0], delimiter=',')
        ff = open(uu[0], 'r') 
        ll = ff.read().split(',')
        if len(ll[len(ll)-1] ) == 0:
            del ll[len(ll)-1]
        list_pos_wrt_origin = numpy.array([float(x) for x in ll])
        
        # # numpy.array([0.610000,0.904616,1.126819,0.667730,0.945151,1.159842,0.721008,0.984027,1.191991,0.770828,1.021542,1.223329,0.817834,1.057809,1.253915,0.862208,1.092854,1.283792])*1000
        
        print('Pos phshft hijacked for working with glass plate !', list_pos_wrt_origin)
    else:   list_pos_wrt_origin = None
        
    return list_pos_wrt_origin
    
def ld_xls_to_polar_lists(full_path, numpy, pandas, st, step, lst, nb_polar):

    df = pandas.read_excel(full_path, index_col = None, header = None) # dataFrame
    
    # is a string #.isdigit()
    hdr = 1 if type(df[1][0]) == str else 0
    
    if isinstance(df[0][0+hdr], str): # CP
        if nb_polar == 2: # indeed a correctly set CD job
            print('CD job')
        else:
            print('\n the args in the xls are for CD jobs, but you configured more than 2 angles: a CD job is assumed ! \n')
        polars = numpy.array([[df[1][0+hdr], df[2][0+hdr]], [df[1][1+hdr], df[2][1+hdr]]]) # for CD
        polar_numbers =None
    else:    
        try:
            df[2][1+hdr] # error ?
            num_col = 2
        except KeyError: # no QWP
            num_col = 1
        polars = numpy.zeros((nb_polar, num_col), dtype=numpy.float64) # # 1st is HWP, 2nd is QWP
        k=0; ct=0
        # if df[0][0] == 1:
        #     polar_numbers= numpy.arange(st, lst+1e-12, step) # 1e-12 to have the right number
        # else:
        polar_numbers= numpy.arange(st, lst+1e-12, step) # 1e-12 to have the right number
            
        # # print('l423, p n = ', polar_numbers)
        
        for ii in polar_numbers:
            if ct >= len(polars): # # nb_polar does not correspond to polar_numbers
                polar_numbers = polar_numbers[:ct]
                break
            while df[0][k+hdr] < ii:
                k+=1
            if (df[0][k+hdr] == ii or ct<2):
                polars[ct, 0:num_col] = [round(df[1][k+hdr], 1), round(df[2][k+hdr], 1)]
            else:
                polars[ct, 0:num_col] = [round(2*polars[ct-1, 0] - polars[ct-2, 0], 1), round(2*polars[ct-1, 1] - polars[ct-2, 1], 1)]
            ct+=1  
        
    return polars, polar_numbers
    
    ## various calc
    
    
def find_angle_polar_array(numpy, vect_wps_angles, polar_angle_wanted, twoWPflag):
    # # vect_wps_angles= numpy.vstack((self.polar_numberswanted_list, self.polars_xls[:,0], self.polars_xls[:,1]))
    
    hwp_angle = qwp_angle = 0 # init
    
    diff_arr = ( vect_wps_angles[0] - polar_angle_wanted)
    argmin = numpy.abs(diff_arr).argmin()
    dist = diff_arr[argmin]
    if abs(dist) > 1e-2: # # tolerance, case 0 has to be avoided also
        arg2 =  min(len(vect_wps_angles[0])-1, max(0, argmin - int(numpy.sign(dist))))
        p1=1/numpy.abs(dist); p2 = 1/numpy.abs(diff_arr[arg2])
        
        hwp_angle = (p1*vect_wps_angles[1, argmin] + p2*vect_wps_angles[1, arg2])/(p1+p2)
    else: hwp_angle = vect_wps_angles[1, argmin] ##; print('safasdf')
    if twoWPflag:
        qwp_angle =  (p1*vect_wps_angles[2, argmin] + p2*vect_wps_angles[2, arg2])/(p1+p2) if dist > 1e-2 else vect_wps_angles[2, argmin]
        
    # # print('hhl162jobs', dist, abs(dist) < 1e-2, hwp_angle, qwp_angle, argmin, vect_wps_angles[1, argmin], vect_wps_angles)
    
    return hwp_angle, qwp_angle

    ## jobs action
    
def launch_job_general(self):
    # not for stage scan
    
    # if self.count_job == 0: # calib job
    #     self.mode_scan_box.setCurrentIndex(2) # static acq.
        
    self.nb_img_max_box.setValue(1)
    
    # # if (self.set_new_scan != 2): # not first scan 
    # #     self.force_whole_new_scan = 1
    # #     self.set_new_scan = 1
        
    self.launch_scan_button_single.animateClick() # launch a scan of 1 frame
    
# def launch_job_general_stage(self):
#     
#     self.nb_img_max_box.setValue(1) #len(self.list_pos_wrt_origin))
#     
#     # # try: # kill current scan worker if exist
#     # #     self.queue_com_to_acq.put([-1]) # kill current acq processes of data_acquisition, and the qthread
#     # #     print('GUI sent to acq process a poison-pill')
#     # # except: # if no scan was previously done
#     # #     pass # do nothing
#     if self.set_new_scan != 2:
#         self.set_new_scan = 1 # whole new scan forced
#     # 
#     self.launch_scan_button_single.animateClick() # launch a scan of 1 frame
    
    
def move_ph_shft_meth(wait_flag, ID, motor_phshft, pos_phshft, pos_phshft_signal, motor_phshft_finished_move_signal, send):
    # # called inside APT worker
    
    motor_phshft.move_to(pos_phshft, blocking=wait_flag)
    # min step = 0.05um ; minimum repeatable step = 0.8um
    
    name = 'phsft rot.' if ID == 1 else 'trans'
        
    if wait_flag:
        pos_phshft_m = motor_phshft.position # is in mm
        pos_phshft_signal.emit(ID, ('%.3f' % (pos_phshft_m*1000))) # because has to be in um, not mm
        str_done = 'and moved to %f mm' % pos_phshft_m
    else:
        str_done = ''
    if send:
        motor_phshft_finished_move_signal.emit(1) # int useless, but keep it for the case of 2 WPs
        
    print('In APT worker, received signal to move %s to %f mm %s\n' % (name, pos_phshft, str_done))

    
def move_rot_polar_meth(wait_flag, motor_rot, angle_rot, rot_signal, motor_finished_move_signal, name_motor, id_motor):
    # # called inside APT worker or newport
    
    motor_rot.move_to(angle_rot, blocking=wait_flag)
    # min step = 0.05um ; minimum repeatable step = 0.8um
    
    if wait_flag:
        angle_rot_m = motor_rot.position # is in mm
        rot_signal.emit(id_motor, angle_rot_m) # 1 for the TL rot motor, 2 for the newport
        str_done = 'and moved to %f deg' % angle_rot_m
    else:
        str_done = ''
    
    print('In %s worker, received signal to move rot to %f mm %s\n' % (name_motor, angle_rot, str_done))
    
    motor_finished_move_signal.emit(id_motor) # int useless, but keep it for the case of 2 WPs


def launch_job_z_stack_meth(self):
    
    
    if self.use_piezo_for_Z_stack: # use piezo
        
        while True:
            try:
                self.progress_piezo_signal.disconnect() # disconnects all, including link to self.piezo_ready_meth
            except:
                break
            
        if self.connect_new_img_to_move_Z_obj: # zstack as primary (or secondary alone) job
            
            self.progress_piezo_signal.connect(self.send_new_img_to_acq)
            
        elif self.connect_end_apt_to_move_Z: # zstack as secondary job
            self.progress_piezo_signal.connect(self.job_apt_meth) #lambda: job_apt_meth(self)) # launch a new ps scan
        
    else: # forced to use motor Z
        
        if (self.imic_was_init_var and self.worker_imic is not None): 
            while True:
                try:
                    self.worker_imic.progress_motor_signal.disconnect() # disconnects all, including link to self.motorZ_ready_meth
                except:
                    break
                
            if self.connect_new_img_to_move_Z_obj: # zstack as primary (or secondary alone) job
        
                self.worker_imic.progress_motor_signal.connect(self.send_new_img_to_acq)
                
            elif self.connect_end_apt_to_move_Z: # zstack as secondary job, apt for ps and polar
                
                self.worker_imic.progress_motor_signal.connect(self.job_apt_meth) #lambda: job_apt_meth(self)) # launch a new ps scan
    
    if self.connect_new_img_to_move_Z_obj: # zstack as primary (or secondary alone) job 
        print('Z-stack job primary of secondary alone initiated')
        self.launch_scan_button_single.animateClick() # launch a scan of 1 frame
        
    # # if ((self.jobs_window.z_job_sec_radio.isChecked() and self.jobs_window.ps_job_prim_radio.isChecked()) and self.count_job_Z_stack == 0): # secondary job = z-stack, and primary = ps
    if self.connect_end_apt_to_move_Z: # apt for ps and polar
        self.job_apt_meth()
        

def pos_init_motor_phshft_meth(self):
    # # called directly in end_job_apt
    
    self.worker_apt.wait_flag = True # for cases of sec. jobs
     
    self.change_phshft_sgnl.emit(self.pos_phshft0, True) # must be a float, has to be in mm, not um # re-init motor phshft
    # # else: # stage scan
    # #     self.queue_com_to_acq.put([2]) # tell the acq process to move phshft
    str1 = self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:3]
    if str1 == 'rot': widg = self.jobs_window.pos_motor_phshft_edt
    elif str1 == 'tra': widg = self.jobs_window.pos_motor_trans_edt
    
    if 'widg' in locals(): widg.blockSignals(True); widg.setText('%.1f' % self.pos_phshft0); widg.blockSignals(False)
    
    print('\n Move phshft # %s/%d \n' % ('origin', len(self.list_pos_wrt_origin)))   
    
    # #     new_job_line_in_table_meth(self)
    
def pos_init_motor_polar_meth(self):
    # # called directly in end_job_apt
    
    self.worker_apt.wait_flag = True # for cases of sec. jobs
    
    self.move_motor_rot_polar_signal.emit(self.pos_polar0) # must be a float
    
    self.jobs_window.angle_polar_bx.blockSignals(True); self.jobs_window.angle_polar_bx.setValue(self.pos_polar0); self.jobs_window.angle_polar_bx.blockSignals(False) # # for disp

    print('\n Move polar # %s/%d \n' % ('origin', len(self.list_polar)))   
    
def frst_ini_apt_job_def_list_meth(self, motor): 
# # is called in start_job_after_meth  
# # to define the list to do for the job, and move motor to 1st pos 
    # print('in frwst')
    
    if motor == 1: # ps
        list_ps = [float(i) for i in self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)]
        
        self.worker_apt.wait_flag = True
        self.change_phshft_sgnl.emit(list_ps[0]/1000 + self.offset_pos_motor_ps/1000, True)
        
        print('\n List of phase-shift pos to do :', list_ps)
                
    elif motor == 2: # polar TL
        self.move_motor_rot_polar_signal.emit(self.pos_polar0)
        print('\n List of polar pos to do :', self.list_polar)
        
    elif motor == 3: # polar newport
        self.move_motor_newport_signal.emit(self.pos_polar0b)
    
def cancel_meth(self):
    
    self.count_job_Z_stack = len(self.list_pos_Z_to_move_piezo_or_motorZ)  # reinit
    self.count_job_ps = len(self.list_pos_wrt_origin)
    self.count_job_polar = len(self.list_polar)
    if (hasattr(self, 'list_pos_job_mosXY') and len(self.list_pos_job_mosXY) > 0): self.count_job_mosXY = len(self.list_pos_job_mosXY[0])
    if (hasattr(self, 'count_job_singlenomtr') and self.count_job_singlenomtr > 1): # started
        self.count_job_singlenomtr = int(float(self.jobs_window.table_jobs.item(self.row_jobs_current, param_ini.nbfr_posWrt0_jobTable).text()))
    
    self.iterationInCurrentJob = self.path_tmp_job = None
    if not self.real_time_disp_chck.isChecked(): self.real_time_disp_chck.setChecked(True)
    self.offset_pos_motor_ps = 0 # important !!
    
    if (self.shutter_is_here and self.use_shutter_combo.currentIndex() == 2):  # # close shutter only at end of job
        self.shutter_send_close() # ordr to close it (before for == 1)
        self.shutter_outScan_mode() # display closed
    
    if (self.row_jobs_current is not None and self.jobs_window.table_jobs.columnCount() is not None):
        max_val = self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.average_posWrtEnd_jobTable) # nb avg
        if max_val is not None:
            self.count_avg_job = int(max_val.text()) # max value
        
        self.jobs_window.table_jobs.setItem(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem('-1')) # job done or not
    self.acq_name_edt.setText(self.name0)
    
    
# is not pyQtSlot
def ZstckEnd_reconnectNormal_meth(self):

        try:
            # if self.use_piezo_for_Z_stack: # use piezo
            # else: # forced to use motor Z
            self.progress_piezo_signal.disconnect() # disconnects all
        except TypeError: # if had no connection
            pass  
        
        if (self.imic_was_init_var and self.worker_imic is not None):     
            try:
                self.worker_imic.progress_motor_signal.disconnect() # disconnects all
            except TypeError: # if had no connection
                pass 
            self.worker_imic.progress_motor_signal.connect(self.posZ_slider.setValue) # reconnect 
        self.progress_piezo_signal.connect(self.posZ_slider_piezo.setValue)
        
        # reconnect the button to change Z
        self.posZ_motor_edt_1.valueChanged.connect(self.z_motor_edt1_changed) # to make changed in Z value
        self.posZ_motor_edt_2.valueChanged.connect(self.z_motor_edt2_changed) # to make changed in Z value
        self.posZ_motor_edt_3.valueChanged.connect(self.z_motor_edt3_changed) # to make changed in Z value
        self.posZ_piezo_edt_1.valueChanged.connect(self.z_piezo_edt1_changed)
        self.posZ_piezo_edt_2.valueChanged.connect(self.z_piezo_edt2_changed)
        self.posZ_piezo_edt_3.valueChanged.connect(self.z_piezo_edt3_changed)
    
# is not pyQtSlot
def z_defmoveList_meth(use_onlymotor_for_Z_stack, numpy,  list_pos_Z_stack_abs):
    # # is called by init_job_Z
    
    nb_digit_piezo = 5 # for a number in mm, not precise better than 10nm
    nb_digit_motorZ = 3 # for a number in mm, not precise better than 1um
    range = list_pos_Z_stack_abs[-1] - list_pos_Z_stack_abs[0]
    
    list_pos_Z_to_move_piezo_or_motorZ=[] 
    
    # print(list_pos_Z_stack_abs)
    # print(len(list_pos_Z_stack_abs))
    len_stack = len(list_pos_Z_stack_abs)
    
    use_piezo_for_Z_stack = not use_onlymotor_for_Z_stack
    
    if use_piezo_for_Z_stack:
    
        if list_pos_Z_stack_abs[0] - float(truncate(list_pos_Z_stack_abs[0], 0)) + range <= param_ini.max_range_piezoZ: # init pos has little digits : ex --> 20.1
        # possible to do the scan just with piezo, by moving only the piezo for init pos
            
            motor_Z_to_set = round(float(truncate(list_pos_Z_stack_abs[0], 0)), nb_digit_motorZ)
            piezo_Z_to_set = round(list_pos_Z_stack_abs[0] - float(truncate(list_pos_Z_stack_abs[0], 0)), nb_digit_piezo)
            
            for ii in numpy.arange(len_stack-1): # don't know why range does not work
                list_pos_Z_to_move_piezo_or_motorZ.append(round(list_pos_Z_stack_abs[ii+1] - float(truncate(list_pos_Z_stack_abs[0],0)), nb_digit_piezo))
                
                # # print(round(list_pos_Z_stack_abs[ii+1] - float(truncate(list_pos_Z_stack_abs[0],0)), nb_digit_piezo))
        
            
        else: # init pos has large digits : 19.9 for instance
            if list_pos_Z_stack_abs[0] - float(truncate(list_pos_Z_stack_abs[0], 1)) + range <= param_ini.max_range_piezoZ: # init pos has little digits after 1st : ex --> 19.91
                motor_Z_to_set = round(float(truncate(list_pos_Z_stack_abs[0], 1)), nb_digit_motorZ)
                piezo_Z_to_set = round(list_pos_Z_stack_abs[0] - float(truncate(list_pos_Z_stack_abs[0], 1)), nb_digit_piezo)
                
                for ii in numpy.arange(len_stack-1): # don't know why range does not work
                    list_pos_Z_to_move_piezo_or_motorZ.append(round(list_pos_Z_stack_abs[ii+1] - float(truncate(list_pos_Z_stack_abs[0],1)), nb_digit_piezo))
                
            else: # init pos has large digits after 1st : ex --> 19.99
                
                motor_Z_to_set = round(list_pos_Z_stack_abs[0], nb_digit_motorZ)
                piezo_Z_to_set = 0 # for simplicity
                    
                if range > param_ini.max_range_piezoZ: # mm, scan Z cannot be made using only the piezo, so the piezo won't be used
                
                    use_piezo_for_Z_stack = 0
                    
                    list_pos_Z_to_move_piezo_or_motorZ = list_pos_Z_stack_abs[1:len_stack] 
                else: # possible to do the scan with the piezo only but init must be set with the move of motor
                    for ii in numpy.arange(len_stack-1): # don't know why range does not work
                        list_pos_Z_to_move_piezo_or_motorZ.append(round(list_pos_Z_stack_abs[ii+1] - list_pos_Z_stack_abs[0], nb_digit_piezo))
    else: # only motor Z
        list_pos_Z_to_move_piezo_or_motorZ = list_pos_Z_stack_abs
        motor_Z_to_set = list_pos_Z_stack_abs[0]
        piezo_Z_to_set = 0

    list_pos_Z_to_move_piezo_or_motorZ.insert(0, list_pos_Z_stack_abs[0]) # # 2019.07: job with PI only was not doing one pos without this !
    return list_pos_Z_to_move_piezo_or_motorZ, use_piezo_for_Z_stack, motor_Z_to_set, piezo_Z_to_set

def ps_polar_jobs_end_util(self):
    # # is called directly by end_job_stack_Z or end_job_apt_suite or nomtr

    if (self.connect_end_z_to_move_phshft or self.connect_end_polar_to_move_ps): # ps scan as secondary job
    
        self.connect_end_z_to_move_phshft = 0
        self.connect_end_polar_to_move_ps = 0
    
        list_ps = [float(i) for i in self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)]
        if self.count_job_ps==0: self.count_job_ps = 1 # # important because with Zphi, is at 0 instead of 1 !!
        print('\n Indic. : phshft # %d/%d \n' % (self.count_job_ps, len(list_ps)))
        if self.count_job_ps < len(list_ps):
            print('sent move to worker_phshft, in ps_jobs_end_util')
            self.send_move_to_worker_phshft() # call another method of GUI
            
        else: # scan ps finished 
            print('sent signal to end ps  job, in ps_jobs_end_util')
            self.end_job_apt_signal.emit(1) # send to a function in the GUI
            # 1 for ps
            
    elif (self.connect_end_Z_to_move_polar or self.connect_end_ps_to_move_polar): # polar as sec. job
    
        self.connect_end_Z_to_move_polar = 0
        self.connect_end_ps_to_move_polar = 0
    
        print('\n Indic. : polar # %d/%d \n' % (self.count_job_polar, len(self.list_polar)))

        if self.count_job_polar < len(self.list_polar):
            print('sent move to worker_polar, in polar_jobs_end_util')
            self.send_move_to_worker_polar() # call another method of GUI
            
        else: # scan polar finished 
            print('sent signal to end polar job, in polar_jobs_end_util')
            self.end_job_apt_signal.emit(2) # send to a function in the GUI
            # 2 for polar
            
    else: # NO secondary job
        if (hasattr(self, 'worker_apt') and self.worker_apt is not None): self.worker_apt.wait_flag = self.wait_flag_apt_current
        self.jobs_window.strt_job_button.setEnabled(True)
        # if self.count_avg_job is not None: # slow job
        if (self.jobs_window.treatmatlab_chck.isChecked() and self.path_tmp_job is not None): # # send to matlab ISHG
            incr_ordr = 0; nb_slice_per_step =3; ctr_mult=2 # standard 
            matlab_treat_ishg_call(self, None, None, incr_ordr, nb_slice_per_step, ctr_mult, self.path_tmp_job)
            self.path_tmp_job = None #re-init
        self.job_manager_meth()

def no_job_running_meth(self):
    self.count_avg_job = self.path_tmp_job = None # None means no job is running
    self.iterationInCurrentJob = None # to signify no job is running, also
    self.offset_pos_motor_ps = 0 # important !!
    self.nb_img_max_box.setValue(self.nbmax00)        

    ## mosaic
    
def mosaic_job_ini(self, param_ini, numpy):
    
    posX0str = self.jobs_window.table_jobs.item(self.row_jobs_current, param_ini.centerX_posWrt0_jobTable).text()
    if not posX0str.replace('.','',1).isdigit(): # does not contains a string
        print('X center undefined, stageXY not here for mosaic ??')
        self.cancel_scan_meth() # cancel
        return
        
    self.list_pos_job_mosXY = [[], []] # X ; Y
    posX0=float(posX0str) # is used
    posY0=float(self.jobs_window.table_jobs.item(self.row_jobs_current, param_ini.centerY_posWrt0_jobTable).text())
    listmosaic = self.jobs_window.table_jobs.item(self.row_jobs_current, param_ini.mosaic_posWrt0_jobTable).text().split(param_ini.list_stgscn_separator) # invX, invY, XthenY
    
    diffZX = float(listmosaic[3]); diffZY = float(listmosaic[4])
    if (diffZX != 0 or diffZY != 0): # Z corr. needed
        currZ = self.currZ_util()
        self.mos_Z0_pz = currZ[1] # # mtr + piezo, all in mm
        self.Zplane_mosaic_um_r = mosaic_Z_calc(numpy, int(listmosaic[0]), self.nbstXmos, self.bstXmos, self.nbstYmos, self.bstYmos, float(listmosaic[1]), float(listmosaic[2]), diffZX, diffZY) # # relative to the Z origin, in um
        if (self.mos_Z0_pz+numpy.max(self.Zplane_mosaic_um_r)/1000 > param_ini.max_range_PI or self.mos_Z0_pz+numpy.min(self.Zplane_mosaic_um_r)/1000 < 0): # # piezoZ won`t be sufficient
            self.usePZ_mos = False # use mtr
            self.mos_Z0 = currZ[0]
            if (self.imic_was_init_var and self.worker_imic is not None): 
                self.worker_imic.progress_motor_signal.connect(self.mosaic_after_move) # int between 1 and 100
        else:
            self.usePZ_mos = True
            self.progress_piezo_signal.connect(self.mosaic_after_move) # int between 1 and 100
        print( 'Zplane_mosaic_um', self.Zplane_mosaic_um_r[0,0], self.Zplane_mosaic_um_r[-1,0], self.Zplane_mosaic_um_r[0,-1], self.Zplane_mosaic_um_r[-1,-1], 'usePZ_mos', self.usePZ_mos) 
    else:
        self.Zplane_mosaic_um_r = None # # no Z correc°
    
    exprX = 'self.list_pos_job_mosXY[0].append(posX0 +float(listmosaic[1])*ii*self.bstXmos/1000)' # X pos, mm
    exprY = 'self.list_pos_job_mosXY[1].append(posY0 +float(listmosaic[2])*jj*self.bstYmos/1000)' # Y pos, mm'
    if not int(listmosaic[0]): # X then Y
        self.nbStMosSlow = self.nbstYmos
        self.nbStMosFast = self.nbstXmos
    else: # Y then X
        self.nbStMosSlow = self.nbstXmos
        self.nbStMosFast = self.nbstYmos
    
    for jj in range(self.nbStMosSlow+1):
        for ii in range(self.nbStMosFast+1):
            exec(exprX) # not to copy the same twice
            exec(exprY) # not to copy the same twice
    
    if (self.chck_homed and ((self.nbstYmos >0 and self.bstYmos >0) or (self.nbstXmos >0 and self.bstXmos >0))):
        self.connect_new_img_to_move_XY = 1
        self.worker_stageXY.home_ok.disconnect() # disconnects all, if connection there is
        self.worker_stageXY.home_ok.connect(self.mosaic_after_move)  # both X and Y ready -> new img
    print( 'list_pos_job_mosXY', self.list_pos_job_mosXY)   
    launch_job_general(self)
    
def mosaic_Z_calc(numpy, YthenX, nbX, stX, nbY, stY, invX, invY, diffZX, diffZY):
    # # z=a*x+b*y 
    
    Xmax = invX*(nbX)*stX # invX == 1 if not, -1 if yes ; same for Y
    Ymax = invY*(nbY)*stY 
    vectX = numpy.linspace(0, Xmax, nbX+1) # relative
    vectY = numpy.linspace(0, Ymax, nbY+1) # relative
    a = diffZX/Xmax
    b = diffZY/Ymax
    [XX, YY] = numpy.meshgrid(vectX, vectY, sparse=True, indexing='xy') 
    # # so grid with NY lines and NX column, and the indexing is (Y,X) !!
    Zplane = a*XX + b*YY # # Zplane, 2D array # relative to the Z origin, in mm
    if YthenX:
        Zplane = Zplane.transpose() # # so grid with NX lines and NY column, and the indexing is (X,Y) !!
    
    return Zplane # # Zplane, 2D array # relative to the Z origin, in mm

    ## calib FAST

def res_theo(res_theo_deg, lambda_shg_m, vg1, vg2, alpha_calc_deg, nb_pass, math):
    # # calculates the theoretical resolution in mm of calcite (mtr) displacement to match the wanted resolution in °
    
    c = 3e8 # # m/sec
    return 1000*res_theo_deg/180/(2*c/lambda_shg_m)/(1/vg1-1/vg2)/math.sin(alpha_calc_deg/180*3.14)/(max(abs(nb_pass), 0.1)) # in mm, 30deg <-> 0.40um for double-pass
     # # res_theo_mm_mtr =
     # # max(nb_pass, 0.1) not to divide by 0

def calib_fast_calc(math, res_theo_deg, alpha_calc_deg , min_exp_time, vel_max_instr, accn_max, d_mm, lambda_shg_m, vg1, vg2, x_st, inv_order, nb_pass):
    
    # # phi = 2pi*nu*delta_t with delta_t = δL*(1/vg1-1/vg2)
    # # δx = δL/sin(α) = phi/(2pi*nu)/(1/vg1-1/vg2)/sin(α)
    # # lambda = lambda_shg car c'est elle qui est déphasée in fine
    
    # # pi is simplified num. and den.
    min_exp_time = param_ini.time_by_point # 20us
    res_theo_mm_mtr = res_theo(res_theo_deg, lambda_shg_m, vg1, vg2, alpha_calc_deg, nb_pass, math)
    vel_mtr_max = res_theo_mm_mtr/min_exp_time  # 23.5mm/s
    vel_mtr = min(vel_mtr_max, vel_max_instr) # 0.5mm/sec with TDC
    exp_time_real = res_theo_mm_mtr/vel_mtr # sec, 1000usec with 0.5um and 0.5mm/sec
    off_acc = 0.5*vel_mtr**2/accn_max*(1-2*inv_order)  # mm
    d_tot_mm = d_mm + 2*off_acc # # tot
    
    t_line = d_mm/vel_mtr # sec, 4
    t_tot = 2*vel_mtr/accn_max + t_line  # acc+dec
    target_begin = x_st - off_acc
    target_end =  x_st  + d_mm + off_acc
    # # if trapez
    nb_px_line = max(1, int(round(t_tot/exp_time_real))) # 4000 pts
    # # d_mm is the total displacement for covering the whole autoco
    # # print('l632 jobs', d_mm,vel_mtr,exp_time_real, nb_px_line, d_tot_mm, res_theo_deg, res_theo_mm_mtr)

    return vel_mtr, exp_time_real, nb_px_line, t_line, t_tot, target_begin, target_end, off_acc, res_theo_mm_mtr
    
def calib_disttot_mtr_set_val_util(self):
    # # not a slot
    if self.jobs_window.ps_fast_radio.isChecked(): # # fast
        dist = self.jobs_window.max_angle_calib_phshft_spbx.value()/self.jobs_window.eq_deg_unit_test_spnbx.value() +2*0.5*self.jobs_window.mtrps_velset_spbx.value()**2/self.jobs_window.mtrps_accnset_spbx.value()*1000
    elif self.jobs_window.ps_slow_radio.isChecked(): # # slow
        dist = self.jobs_window.max_angle_calib_phshft_spbx.value()/self.jobs_window.restheo_fastcalib_spbx.value() # #if not self.jobs_window.ps_mtr_dcvolt_radio.isChecked() else
        if self.jobs_window.ps_mtr_dcvolt_radio.isChecked():
            dist = dist*self.jobs_window.eq_deg_unit_test_spnbx.value()
    
    self.jobs_window.num_frame_calib_phshft_spbx.blockSignals(True)
    self.jobs_window.num_frame_calib_phshft_spbx.setValue(int(round(dist)))
    self.jobs_window.num_frame_calib_phshft_spbx.blockSignals(False)
    
def plot_autoco_frog_meth(plt, numpy, trace, tit, indexes_wl, dvdr, frog):
    # # # # called by disp_autoco_frog_meth
    # # matplotlib.pyplot as plt
    
    plt.close(101)
    fig1=plt.figure(num=101)
    ax = fig1.add_axes([0.1,0.1,0.8,0.8])
    if frog:
        trace_real=trace[indexes_wl[0]+1, 1::dvdr] # # crop in window of interest
        # # trace_real=trace[numpy.s_[(indexes_wl[0][0]+1):(indexes_wl[0][-1]+1)], 1:] # # crop in window of interest
        wlth = trace[ indexes_wl[0]+1, 0]
        delay = trace[0, 1::dvdr]
    else:
        trace_real=trace
    [sy, sx] = trace_real.shape
    x_h_str = 'delay [fs]'
    dvdry = max(10, int((sy-1)/20))
    dvdrx = max(10, int((sx-1)/20))

    if frog:
        im1 = ax.imshow(trace_real)
        plt.xticks(numpy.arange(0, int((sx-1)), dvdrx), numpy.int64(10*delay[ 1::dvdrx])/10, rotation='vertical') # # delay
        # # yt=; print(yt.shape)
        plt.yticks(numpy.arange(0, int((sy-1)), dvdry), numpy.int64(10*wlth[ 1::dvdry])/10) # # wavelength
        im1.autoscale()
        ax.axis('auto')
        plt.colorbar(im1, ax=ax)
        t_h_str = 'FROG raw trace'
        y_h_str= 'XHG wavelength [nm]'
        
    else: # autoco
        ax.plot(trace[0, :], trace[1, :])
        t_h_str = 'Autoco trace'
        y_h_str= 'counts [a.u.]'
    
    ax.set_title('%s - %s' % (t_h_str, tit))
    ax.set_xlabel(x_h_str)
    ax.set_ylabel(y_h_str)
    
    plt.draw()
    try:
        plt.show()
    except ValueError:
        pass
    # fig1.show(False)
    
def disp_autoco_frog_meth(self, sys, glob, os, numpy, frog, paquet):  
# # this func calls  plot_autoco_frog_meth
    
    tit = 'res%.f°, exp.%.fus, vel.%.3fmm/sec' % (self.res_theo_deg, self.exp_time_real_calib_sec*1e6,  self.vel_mtr_phsft)
    if not ('matplotlib.pyplot'in sys.modules):
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.rcParams['toolbar'] = 'toolbar2'
    else: plt=sys.modules['matplotlib.pyplot']
    if frog:
        if not ('scipy.io'in sys.modules):
            import scipy.io
            sio = scipy.io
        else:
            sio=sys.modules['scipy.io']
        list_of_files = glob.glob(self.path_frog + '\\*.mat') # * means all if need specific format then *.csv
        latest_file = max(list_of_files, key=os.path.getctime)
        paquet = sio.loadmat(latest_file[:-4]) 
        str=list(paquet.keys())[-1]
        data =  paquet[str]
        data = numpy.transpose(data)
        dvdr = max(1, int(len(data)/ 1e4))
        indexes_wl = numpy.where((data[1:, 0] > self.lwr_bound_exp_shgjob) & (data[1:, 0] < self.upr_bound_exp_shgjob)) #numpy.s_[1:len(data)-1]
        print('sddf', data.shape, indexes_wl)
        
    else: # autoco
        dvdr = 1
        indexes_wl = None
        nb = paquet.size
        # # print('in disp_autoco', paquet.shape)
        if self.nb_pass_calcites > 0: lst = self.vel_mtr_phsft*self.exp_time_real_calib_sec*nb*((1/self.vg1 - 1/self.vg2)*1e12*self.nb_pass_calcites)
        else: lst = self.jobs_window.max_angle_calib_phshft_spbx.value()
        vectX = numpy.linspace(0, lst, nb) 
        data = numpy.vstack((vectX, numpy.reshape(paquet, (1, nb))))
    plot_autoco_frog_meth(plt, numpy, data, tit, indexes_wl , dvdr, frog) # # False for autoco
    
def save_pltfig_pkl_meth(sys, os, txt, path_computer, saveflag):
    
    if not ('matplotlib.pyplot'in sys.modules):
        import matplotlib.pyplot as plt
    else:
        plt=sys.modules['matplotlib.pyplot']
    
    if not ('pickle' in sys.modules):
        import pickle
    else:
        pickle = sys.modules['pickle']
    
    try:
        if saveflag:    
            ff = QtWidgets.QFileDialog.getSaveFileName(None, 'Save pkl in folder ...', (r'%s\%s.pkl' % (path_computer, txt)), '*.pkl', '*.pkl')[0] # round(len(list_row_selected)/nb_field_table*2)
                # ax1 = pickle.load(fid)
            if len(ff) > 0:
                with open(ff,'wb') as fid: # # 'rb' for load
                    pickle.dump(plt.gcf().axes[0], fid)
        else: # load
        
            ff = QtWidgets.QFileDialog.getOpenFileName(None, 'Load file pkl ...', path_computer, '*.pkl', '*.pkl')[0]
            
            with open(ff,'rb') as fid: # # 'rb' for load
                figx = pickle.load(fid) #'FigureObject.fig.pickle', 'rb'))
                plt.axes(figx)
                plt.show()
    except FileNotFoundError: return path_computer
            
    return os.path.dirname(ff)
    
    ## EOMph
    
def matlab_treat_ishg_call(self, sys, QThread, incr_ordr, nb_slice_per_step, ctr_mult, fldrnm):
        
    if (not hasattr(self, 'worker_matlab') or self.thread_matlab is None):
        if QtWidgets.QMessageBox.question(None, 'Start matlab instance ?', "Start MatLab instance?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No: self.jobs_window.treatmatlab_chck.setChecked(False); return
        from modules import matlab_treat_ishg_call
        self.thread_matlab = QThread()
        self.worker_matlab = matlab_treat_ishg_call.Matlab_treat(sys, self.path_save)  # , EmittingStream, self.logger_window.normalOutputWritten
        self.worker_matlab.moveToThread(self.thread_matlab)
        
        self.thread_matlab.started.connect(self.worker_matlab.start_matlab)
        self.worker_matlab.matlabGUI_treatphase_signal.connect(self.worker_matlab.matlabGUI_treatphase)
        self.worker_matlab.test_GUI_signal.connect(self.worker_matlab.test_GUI_here)
        self.worker_matlab.show_instance_signal.connect(self.worker_matlab.show_instance)
        # # Start QThread
        self.thread_matlab.start()
    else: # test if GUI here
        # print('test GUI here!')
        self.worker_matlab.test_GUI_signal.emit() #test_GUI_here() # fast
        
    if fldrnm is not None:  # otherwise just start the engine and prog 
        self.worker_matlab.matlabGUI_treatphase_signal.emit(incr_ordr, nb_slice_per_step, ctr_mult, fldrnm)
        #self.engmatlab.python_matlabGUI_treatphase(incr_ordr, nb_slice_per_step, ctr_mult,fldrnm, nargout=0);
    
def EOMph_pltsave_meth(PIL, numpy, os, array_3d, array_ishg_4d, array_ctr_3d, arrlist, dict_tiff_really_disp, fname00, path_save, ct, rate_MHz, nb_pmt, pack_pg, acq_name, list_ishg_EOM_AC, ImageDescription, spec_str, sz_str, newdirpath, ct_pmt):
    # # called in GUI
    dirpath_ret = newdirpath
    if (ct_pmt ==0 or newdirpath is None):
        dirpath_ret = newdirpath = ('%s/tmp/%s%s_%s%s%.1fMHz_%g+%g+%gus' % (path_save, fname00[:21], acq_name, spec_str, sz_str, rate_MHz, list_ishg_EOM_AC[1]*1e6, (list_ishg_EOM_AC[-2][1]+list_ishg_EOM_AC[-2][0])*1e6, list_ishg_EOM_AC[-2][2]*1e6))
        os.makedirs(newdirpath)
    elif ct_pmt > 0: 
        newdirpath = '%s/pm%d' % (newdirpath, ct_pmt+1)
        os.makedirs(newdirpath)
    
    if array_3d is not None: # # in ISHG, the 'normal' array is also saved in the folder, for simplicity
        fullname = '%s/%s_SUMISHG' % (newdirpath, fname00)
        result = PIL.Image.fromarray(array_3d.astype(param_ini.bits_save_img))
        result.save(('%s.tif' % fullname), tiffinfo= dict_tiff_really_disp)
    
    if array_ishg_4d is not None: # # filled array in ishg
        
        for k in range(numpy.size(array_ishg_4d, 3)): # phases
            fname = fname00[:19]+str(int(k+100))+fname00[21:] if fname00[19:21].isdigit() else fname00 # fname00[19:21]+
            fullname = '%s/%s_ph%d' % (newdirpath, fname, k)
            result = PIL.Image.fromarray(array_ishg_4d[ct, :,:, k].astype(param_ini.bits_save_img))
            result.save(('%s.tif' % fullname), tiffinfo= dict_tiff_really_disp)
        if (nb_pmt >= 1 and array_ctr_3d is not None):
            [img_hist_plot_mp, img_item_pg, hist, LUT] = pack_pg
            # # print('in pg2')
            img_hist_plot_mp.plot_img_hist(numpy, LUT, array_ctr_3d[nb_pmt-1, :,:], img_item_pg, hist, None)
            # # img_item_pg.setLookupTable(LUT) # # will be done afterward
            # # hist.gradient.setColorMap(cmap_pg)
            # # hist.autoHistogramRange()
    else: # save params
        file = open('%s/%sparams.txt' % (newdirpath, fname00),'w') 
        file.write(ImageDescription)
        file.write(str(list_ishg_EOM_AC)) 
        file.close()
        
        # # list_ishg_EOM_AC
            
    if (arrlist is not None and type(arrlist) in (list, tuple) and len(arrlist) > 0 and ct_pmt ==0):  # # saved data whole list
        if type(arrlist[0]) == list: # # list of list
        # # [[data, meas_line_time_list]1, [data, meas_line_time_list]2, ...]
            # # arrlist[k] will be [array, line_dur] and not array
            str1 = 'with durations'
        else: # # no durations
            str1 = 'with smps only'
        maxk = len(arrlist)
        print('saving arr_list', str1)
        for k in range(maxk): # !!!!!
            try: numpy.save('%s/buffer#%d.npy' % (newdirpath, k), arrlist[k])
            except ValueError: print('\n!! error saving array #', k)
    
    return dirpath_ret

def EOMph_nb_samps_phpixel_meth(sample_rate_new, ishg_EOM_AC, tolerance, exploit_all_acqsamps, ps_step_closest_possible_so_lstsamps_inddtime, add_nb):  
    # # used in daq_control_mp2.init_daq() AND 

    # # # ishg_EOM_AC is initially [flag, ramp time sec00, step phsft theo (deg), Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime] with the times in sec !!
    ishg_EOM_AC_insamps = list(ishg_EOM_AC) # # new !!
    nb_samps_ramp = int(round(sample_rate_new*ishg_EOM_AC[1]) - ishg_EOM_AC_insamps[-2][0]) # # the 1st offset is removed from the actual ramp time
    ishg_EOM_AC_insamps[1] = nb_samps_ramp # # ramptime00, was in sec, now in samps
    ishg_EOM_AC_insamps[-2] = (int(ishg_EOM_AC_insamps[-2][0]), int(round(ishg_EOM_AC[-2][1]*sample_rate_new)), int(round(ishg_EOM_AC[-2][2]*sample_rate_new)), int(round(ishg_EOM_AC[-2][3]*sample_rate_new))) # # deadtime begin, was in sec, now in samps
    # # deadtime end, was in sec, now in samps
    # # print(ishg_EOM_AC_insamps[-2])
    # nb_samps_oneperiod_ph = round(sample_rate_new*(ishg_EOM_AC[1] + ishg_EOM_AC[-2][1] + ishg_EOM_AC[-2][2])) # nb samps per ramp != nb samps for phshft !
    add_str = ''
    if exploit_all_acqsamps: # # will set the p-s step to maximize the number of samps used (max nb of p-s, min step)
        str_stp = 'not optimized'
        nb_ph_apriori = int(ishg_EOM_AC[4]/ishg_EOM_AC[3]*180/ishg_EOM_AC[2]) + add_nb # 1400/273*180/step_ph_wanted_deg
        # # take the int and not round, otherwise you can have nb_ps*step > nb_samps_tot !!
        k = 0; flag=False; add=None
        while k < nb_ph_apriori:
            for i in (-k, k):
                if not nb_samps_ramp%(nb_ph_apriori + i): # dividing
                    add = i
                    # # print(add)
                    flag=True
                # # else:
            if flag:
                break
            else:
                k+=1
        if (not flag or (add is not None and abs(add/nb_ph_apriori)*100 > tolerance)): # nothing found, or too far
            nb_ph = nb_ph_apriori
            to_remove = nb_samps_ramp%nb_ph # # deadtime begin, in samps
            nb_samps_phpixel = (nb_samps_ramp - nb_samps_ramp%nb_ph_apriori)/nb_ph_apriori # don't put int. now, it will be controlled later
            # # in that case only the last ph will have some pixels of the next ramp, but they will remain available for the next ramp
        else: # # nb_samps matches exactly the nb of ps and step !!
            nb_ph = nb_ph_apriori + add; to_remove = 0
            nb_samps_phpixel = nb_samps_ramp/nb_ph # don't put int now, it will be controlled later
    else: # # will impose the samps used to exactly match the wanted p-s step (min number of p-s., exact step, unused samples)
        str_stp = 'optimized'
        nb_ph = int(round(ishg_EOM_AC[4]/ishg_EOM_AC[3]*180/ishg_EOM_AC[2])) + add_nb # 1400/273*180/step_ph_wanted_deg
        # # flag = not bool(nb_samps_ramp%nb_ph_apriori); add = 0
        nb_samps_phpixel = int(round(nb_samps_ramp/nb_ph)) if ps_step_closest_possible_so_lstsamps_inddtime else (nb_samps_ramp-nb_samps_ramp%nb_ph)/nb_ph
        # # True means p-s step will be the closest possible to asked value, with perhaps the last samples of last p-s taken in the deadtime if not enough in the ramp
        # # False means that the p-s will try to be closest to asked, but without the use of samples from deadtime: instead, a less good value might be chosen, and some sample will be unused in the ramp
        to_remove = nb_samps_ramp - nb_samps_phpixel*nb_ph
        # nb_samps_ramp -= to_remove
        if ps_step_closest_possible_so_lstsamps_inddtime: add_str = ', closest'

    print( 'nb phshft', nb_ph, ', divided by', ''.join(['%d:%r; ' % (i, not bool(nb_ph%i)) for i in range(2,6)]))
    not_happy = 1
    [dt0, dtbeg00, dtend00, off_begline_eom] = ishg_EOM_AC_insamps[-2]
    # # print(ishg_EOM_AC_insamps[-2])

    while not_happy:
        if not_happy > 1:
            print('optimized nb_samps_per_ps N°', not_happy)
        again = False # # init
        dtbeg = dtbeg00 # # reset
        dtend = dtend00 # # reset
        dt0 = ishg_EOM_AC_insamps[-2][0]
        if to_remove > 0:  # # will crop in the ramp itself 
            # # print('h1')
            str_disp = 'croped from ramp'
            dt0 += int(to_remove) # # deadtime offset00
            print('\n warning, imposed step phsft leads to a nb_phsft that was not adujstable within tolerance of %d samps: first %d samps of ramp (meaning %.1f°) will be croped !' % (tolerance, to_remove, to_remove/nb_samps_phpixel*ishg_EOM_AC[2])) 
        elif to_remove < 0: # # will add to the ramp itself by cropping to deadtimes 
            # # print('h2')
            str_disp = 'added from deadtime'
            dtend -= abs(to_remove) # # deadtime end
            if dtend < 0: # # too many removed
                dtend = 0
                dtbeg -= (abs(to_remove)-dtend00) # # deadtime begin
                if dtbeg < 0: # # too many removed, no more
                    print('taking the closest value of phsft step leads to not enough samples in one ramp, I will decrease the phshft step')
                    add_str = '' # not so optimized
                    again = True
            # # ishg_EOM_AC_insamps[-2][1] = dtbeg
            # # ishg_EOM_AC_insamps[-2][2] = dtend
            # # ishg_EOM_AC_insamps[-2][0] = dt0
            ishg_EOM_AC_insamps[-2] = (dt0, dtbeg, dtend, off_begline_eom)
            if (again or (ps_step_closest_possible_so_lstsamps_inddtime != 2 and (int(nb_samps_phpixel) - ishg_EOM_AC[2]/(ishg_EOM_AC_insamps[4]*180/ishg_EOM_AC_insamps[3]/round(sample_rate_new*ishg_EOM_AC[1])) >= 1))): # # the ps step is not the best possible
            # # ps_step_closest_possible_so_lstsamps_inddtime = 2 means to not have samples unused in ramp at all
                nb_samps_phpixel -=1
                again = True # # pass again
                to_remove = nb_samps_ramp - nb_samps_phpixel*nb_ph
            if not again: ishg_EOM_AC_insamps[1] += abs(to_remove) # # if no error
        
        if again:
            not_happy += 1
            continue # # will pass the if again
        not_happy = 0
    
    # # print(ishg_EOM_AC_insamps[-2])
    ishg_EOM_AC_insamps[2] = nb_ph; ishg_EOM_AC_insamps[5] = int(nb_samps_phpixel)
    
    if to_remove!= 0:
        print('!! %s %d+%d samps !!' % (str_disp, abs(ishg_EOM_AC_insamps[1] - nb_samps_ramp),dt0))
    
    print(' %d samps per phasepxl' % nb_samps_phpixel, 'exp_ph %.2f us' % (nb_samps_phpixel/sample_rate_new*1e6), 'step %.2f° %s \n' % (ishg_EOM_AC_insamps[4]*180/ishg_EOM_AC_insamps[3]/round(sample_rate_new*ishg_EOM_AC[1])*ishg_EOM_AC_insamps[5], str_stp+add_str))
    
    ovrsmp_ph = ishg_EOM_AC_insamps[1] + ishg_EOM_AC_insamps[-2][0] + dtbeg + dtend
    ishg_EOM_AC_insamps[-2] = (dt0, dtbeg, dtend, off_begline_eom)
    
    ishg_EOM_AC_insamps[-1] = (ishg_EOM_AC_insamps[-1][0], ovrsmp_ph) # tuple (flag, ovrsmp_ph)
    
    # # ishg_EOM_AC is now [flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, (flag_impose_ramptime_as_exptime, oversmp_ph)] with the times in nb smps !!
    
    return ishg_EOM_AC_insamps
    
def ishgEOM_defexptime_func(ishg_EOM_AC): # # define new exp time
# # ishg_EOM_AC in sec
    return ishg_EOM_AC[1] + ishg_EOM_AC[-2][1] + ishg_EOM_AC[-2][2]
    
def ishgEOM_defnbcol_func(fake_size_fast, oversampling, ovrsmp_ph):
    return int(fake_size_fast*oversampling/ovrsmp_ph) # # new nb of columns
    
def ishgEOM_adjdtvsrate_func(sample_rate_new, max_rate, min_rate, master_clock_rate, ishg_EOM_AC, exptime0, rate_fixed, dtb_fixed, dte_fixed, expfixed):
    # # rate in Hz, times in sec
    # # !! in us MHz it caused errors !!
    # # print('max_rate', max_rate, sample_rate_new >= max_rate)
    
    def loop_rate_dt_exp (rate, rate00, rate_fixed, master_clock_rate, min_rate, max_rate, var, var_fixed, ishg_EOM_AC, str):
        
        r0 = rate; rate_prev = max_rate
        # # print('max_rate',max_rate)
        if (not rate_fixed and rate <= max_rate):
            ind = 1; 
            while True:
                rate = (int(r0*var)+ind)/var
                # # print(rate)
                if (rate < max_rate and (master_clock_rate % rate)): # # # not a divider of the master clock rate of 20MHz
                    rate_prev = rate
                    ind+= 1 
                else: 
                    if rate > max_rate: rate = rate_prev
                    if rate <= max_rate: print('chose rate higher (Hz)',rate, str )
                    break
            # if (master_clock_rate % rate): rate = master_clock_rate/math.ceil(master_clock_rate/rate)
        if (rate > max_rate or rate_fixed):
            if not rate_fixed:
                ind = 0 ; rate_prev = min_rate
                while True:
                    rate = (int(r0*var)-ind)/var
                    # # print(rate, var, r0, master_clock_rate % rate)
                    if (rate > min_rate and (master_clock_rate % rate)): # # # not a divider of the master clock rate of 20MHz
                        rate_prev = rate; ind+= 1 
                    else:
                        if rate < min_rate: rate = rate_prev
                        rate = (int(rate*var))/var # min_rate, min(
                        if rate >= min_rate: print('chose rate lower (Hz)',rate, str )
                        break
                
            if (rate < min_rate or rate_fixed):
                rate  = rate00
                if not var_fixed: 
                    # # print('hey1', str == 'exptime' and ishg_EOM_AC[0], str == 'exptime',ishg_EOM_AC[0])
                    if (str == 'exptime' and ishg_EOM_AC[0]): # # fast ISHG EOM): # var = exptime
                        var =  ishg_EOM_AC[1] + ishg_EOM_AC[-2][1] + ishg_EOM_AC[-2][2]
                    # # print('hey', rate*var, round(rate*var), var, rate )
                    if rate*var != round(rate*var): 
                        var = (round(rate*var))/rate # change dt rather
                    print('chose %s' % str, var )
                else:
                    print('could not correct %s*rate by changing the rate !' % str)
        return rate, var
    
    rate = round(sample_rate_new, 9) #*1e-6; max_rate = max_rate*1e-6;  min_rate =  min_rate*1e-6 # Hz MHz
    rate00 = rate
    exptime = round(exptime0, 9)  # sec *1e6# us # # precision up to the nsec 
    # # print(rate,exptime, rate*exptime , abs(rate*exptime - round(rate*exptime)))  
    # # master_clock_rate = master_clock_rate #*1e-6
    dt_beg = ishg_EOM_AC[-2][1]; dt_end = ishg_EOM_AC[-2][2]
    # # !! all in MHz or us !!
    # # print('aaf', dt_beg, dt_end, rate, rate*dt_beg,round(rate*dt_beg))
    condbeg = abs(rate*dt_beg - round(rate*dt_beg)) > 1e-6 #and (not dtb_fixed or 
    condend = abs(rate*dt_end - round(rate*dt_end)) > 1e-6 # and not dte_fixed
    
    if (condbeg or condend): # rate not high enough to adjust dt_beg within precision
        if (not (rate*(dt_beg+dt_end)%2) and not dtb_fixed and not dte_fixed): # even
            dt_beg = dt_end = (dt_beg+dt_end)/2
            print('sum dt even', dt_beg )
        elif (rate*(dt_beg+dt_end) == int(rate*(dt_beg+dt_end)) and not dtb_fixed and not dte_fixed): # sum ok ?
            dt_beg = int((dt_beg+dt_end)/2); dt_end = int((dt_beg+dt_end)/2)+1
            print('sum dt ok', dt_beg )
        else: # sum not a solution
            # # print(condbeg, condend, rate,dt_beg,dt_end, rate*dt_beg - round(rate*dt_beg), rate*dt_end - round(rate*dt_end), rate*(dt_beg+dt_end) == int(rate*(dt_beg+dt_end)), (rate*(dt_beg+dt_end)%2))
            dt = [dt_beg, dt_end]; dt_fixed_flag =[dtb_fixed, dte_fixed] # cond = (condbeg, condend); 
            for k in range(2):
                if abs(rate*dt[k] - round(rate*dt[k])) < 1e-9:
                    rate, dt[k] = loop_rate_dt_exp (rate, rate00, rate_fixed, master_clock_rate, min_rate, max_rate, dt[k], dt_fixed_flag[k], ishg_EOM_AC, 'dt')
            [dt_beg, dt_end] = dt
            # # print('change deadtimes (sec) from', ishg_EOM_AC[-2], 'to', dt)
    # # else: rate = dt_beg = dt_end = None # # unchanged
        # # if rate is not None: # otherwise unchanged
        sample_rate_new = rate # *1e6;  dt_beg = dt_beg*1e-6; dt_end = dt_end*1e-6
        if sample_rate_new != rate00: rate_fixed = True
        ishg_EOM_AC[-2] = (ishg_EOM_AC[-2][0], dt_beg,  dt_end, ishg_EOM_AC[-2][3]) # tuple
        
    
    rate0 = rate
    # # print('2', rate,exptime, rate*exptime , abs(rate*exptime - round(rate*exptime)))    
    if (abs(rate*exptime - round(rate*exptime)) > 1e-6):  # # rate*exptime != int(rate*exptime) was too random
        rate, exptime = loop_rate_dt_exp(rate, rate0, rate_fixed, master_clock_rate, min_rate, max_rate, exptime, expfixed, ishg_EOM_AC, 'exptime')
        exptime0 = exptime #*1e-6 # to sec
        sample_rate_new = rate #*1e6
    
    return sample_rate_new, ishg_EOM_AC, exptime0
    
def dt_ishg_setnewval_meth(self, dtb, dte):
    
    self.jobs_window.deadtimeBeg_us_EOMph_spbx.blockSignals(True)
    self.jobs_window.deadtimeBeg_us_EOMph_spbx.setValue(dtb*1e6) # us
    self.jobs_window.deadtimeBeg_us_EOMph_spbx.blockSignals(False)
    
    self.jobs_window.deadtimeEnd_us_EOMph_spbx.blockSignals(True)
    self.jobs_window.deadtimeEnd_us_EOMph_spbx.setValue(dte*1e6) # us
    self.jobs_window.deadtimeEnd_us_EOMph_spbx.blockSignals(False)

def EOMph_3d_diff_meth(ishg_EOM_AC_insamps, array_ishg_4d):
    ind180 = int(round(ishg_EOM_AC_insamps[3]/ishg_EOM_AC_insamps[4]*(ishg_EOM_AC_insamps[2]-1))) # # round sometimes gives .0 !
    return array_ishg_4d[:,
:, :, 0] - array_ishg_4d[:, :, :, ind180] # # flag, ramp samps, nbph, Vpi, VMax, nb_samps_perphsft, task_mtrtrigger_out, offset_samps, flag_impose_ramptime_as_exptime # #  array_ishg_3d_diff =
