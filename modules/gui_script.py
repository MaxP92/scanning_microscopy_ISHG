# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2016

@author: Maxime PINSARD
"""
import os, glob, sys, traceback
import datetime, time
import shutil, importlib
from subprocess import call as subproc_call 
import warnings
from decimal import Decimal

import queue
import multiprocessing

from PyQt5.uic import loadUiType
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot
from PyQt5 import QtCore, QtWidgets, QtGui

import pyqtgraph

import numpy, math

import PIL.Image

from modules import imic_worker_script2, apt_worker_script2, scan_main_script, img_hist_plot_mp, param_ini, save_img_tiff_script2, jobs_scripts,  spectro_worker_script2, pg_plot_scripts, stage_xy_worker_script, calc_scan_param_stagescan_script, shutter_worker_script2, new_galvos_funcs, daq_control_mp2, newport_worker_script, PI_worker_script, EOM_phase_ctrl_script

"""
Using a queue between main GUI and process inside a qthread does not work
"""

Ui_MainWindow, QMainWindow = loadUiType('main_microscope.ui') # loading the GUI

Ui_JobsWindow, QSecondWindow = loadUiType('scan_phase_shift_z_jobs.ui') # loading the dialog box for jobs 

class Main(QMainWindow, Ui_MainWindow):
    
    move_motorX_signal = pyqtSignal(float)
    move_motorY_signal = pyqtSignal(float)
    change_scan_dependencies_signal = pyqtSignal(float, float, float, float, int, int, float)
    
    motorZ_move_signal = pyqtSignal(float)
    piezoZ_move_signal = pyqtSignal(float)
    piezoZ_step_signal = pyqtSignal(float)
    obj_choice_signal = pyqtSignal(int)  
    fltr_top_ch_signal = pyqtSignal(int)
    fltr_bottom_ch_signal = pyqtSignal(int)
    motorZ_changeDispValue_signal = pyqtSignal(float)
    piezoZ_changeDispValue_signal = pyqtSignal(float)
    progress_piezo_signal = pyqtSignal(int)
    
    move_motor_phshft_signal = pyqtSignal(float, bool)
    move_motor_trans_signal = pyqtSignal(float, bool)
    move_motor_rot_polar_signal = pyqtSignal(float)
    move_motor_newport_signal = pyqtSignal(float)
    both_polars_finished_move_signal = pyqtSignal(int)
    
    end_job_apt_signal = pyqtSignal(int)
    
    home_motor_phshft_signal  = pyqtSignal(int, bool)
    home_motor_newport_signal = pyqtSignal()
    
    do_force_stage_homing_signal = pyqtSignal()
    
    close_motorXY_signal = pyqtSignal(bool)
    close_newport_signal = pyqtSignal(bool)
    close_PI_signal = pyqtSignal(bool)
    
    open_close_shutter_signal = pyqtSignal(int)
    conn_instr_shutter_signal = pyqtSignal()
    terminate_shutter_signal = pyqtSignal()
        
    end_job_stackZ_signal = pyqtSignal() 
    
    # # new_job_line_in_table_signal = pyqtSignal() 
    spectro_connect_signal = pyqtSignal(int) 
    acquire_spectrum_continuous_signal = pyqtSignal(int)
    
    scan_thread_available_signal = pyqtSignal(bool)
    kill_worker_scan_signal = pyqtSignal()
    scan_galvo_launch_processes_signal = pyqtSignal(int, int, list, list, int, int, int, int, int, bool, str)
    waitin_shutter_signal = pyqtSignal(float)
    
    eomph_send_onoff_signal = pyqtSignal(int)
    eomph_stmodeAC_signal = pyqtSignal(int)
        
    def __init__(self, path_computer):
        
        super(Main, self).__init__()
        self.setupUi(self)
        
        # # path_computer = r'C:\Users\admin\Documents\Python'
        self.path_computer = path_computer
        self.path_save = (r'%s\prog microscope 18' % path_computer)
        self.path_recycle = ((r'%s\Recycle imgs') % path_computer)
        total_sizesave = 0
        for dirpath, dirnames, filenames in os.walk(self.path_save):
            if (len(filenames) == 0 and dirpath != self.path_save): continue # empty #  shutil.rmtree(dirpath); 
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try: total_sizesave += os.path.getsize(fp)
                except FileNotFoundError: print(fp, 'not found')
        
        # clean Recycle if too large ?
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.path_recycle):
            if (len(filenames) == 0 and dirpath != self.path_recycle): shutil.rmtree(dirpath); continue # empty
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try: total_size += os.path.getsize(fp)
                except FileNotFoundError: print(fp, 'not found2')
        total_size += total_sizesave # # add the files size from tmp
        total_size_Mo = total_size/1e6 # in Mo
        if total_size_Mo > param_ini.max_size_recycle_Mo:
            print('\n Size of recycle too large : %.2f Mo, I have to clean it (max imposed size is %.2fMo\n' % (total_size_Mo, param_ini.max_size_recycle_Mo))
            nb_files_to_remove = round((total_size_Mo - param_ini.max_size_recycle_Mo)/param_ini.size_dflt_onefile)
            ct = 0; brk_here = False
            size0 = total_size_Mo
            max_size_recycle_Mo = param_ini.max_size_recycle_Mo
            for dirpath, dirnames, filenames in os.walk(self.path_recycle):
                # # print(dirpath, dirnames, size0)

                if brk_here: break
                ct0 = 0
                while True:
                    size_temp =size_tempf = 0
                    if (size0 < max_size_recycle_Mo or (ct > len(filenames)-1 and ct0 >= len(dirnames)) or ct >nb_files_to_remove): break # print(size0);
                    if (ct0 < len(dirnames)):
                        if dirnames[ct0] != self.path_recycle: 
                            print('rm',dirnames[ct0])
                            max_size_recycle_Mo += 500 # # with ishg folders, tolerance is higher
                            try: size_temp = sum(os.path.getsize(os.path.join(dirpath, dirnames[ct0],f)) for f in os.listdir(os.path.join(dirpath,dirnames[ct0])) if os.path.isfile(os.path.join(dirpath,dirnames[ct0],f)))/1e6 # Mo
                            except FileNotFoundError: print(f, 'not found4')
                            p1 = os.path.join(dirpath,dirnames[ct0])
                            # shutil.copytree(p1, os.path.join(r'C:\$Recycle.Bin',dirnames[ct0]))
                            shutil.rmtree(p1)
                            ct0+=1
                    if (ct < len(filenames)):
                        fp = os.path.join(dirpath, filenames[ct])
                        print('rm', fp)
                        try: size_tempf = os.path.getsize(fp)/1e6 # Mo
                        except FileNotFoundError: print(fp, 'not found5')
                        else: os.remove(fp) # success
                        ct += 1
                    size0 -= (size_temp + size_tempf)
                            
        # # remove the files from tmp folder !!!
        files = glob.glob(('%s\\tmp\\*' % self.path_save))
        print('Putting previous files in Recycle...')
        for f in files:
            try:
                shutil.copy2(f, self.path_recycle)
                os.remove(f)
            except PermissionError: # folder
                try:
                    shutil.copytree(f,'%s\\%s' % (self.path_recycle, os.path.basename(f)))
                except FileExistsError: # already existing
                    shutil.copytree(f,'%s\\%s_2' % (self.path_recycle, os.path.basename(f)))
                shutil.rmtree(f)
            except FileNotFoundError: print(f, 'not found6')
            
        print('... Recycle filled !')
        
        self._want_to_close = False        
        self.try_quit = 0 
        self.apt_here = 0
        
        self.jobs_window = Jobs_GUI(self)

        ## imic init/params
        
        self.objective_choice.setEnabled(False)
        self.imic_was_init_var = 0
        self.filter_top_choice.setEnabled(False)
        self.filter_bottom_choice.setEnabled(False)
        self.posZ_motor_edt_1.setEnabled(False)
        self.posZ_motor_edt_2.setEnabled(False)
        self.posZ_motor_edt_3.setEnabled(False)
        self.posZ_motor_edt_4.setEnabled(False)
        
        self.posZ_piezo_edt_1.setEnabled(False)
        self.posZ_piezo_edt_2.setEnabled(False)
        self.posZ_piezo_edt_3.setEnabled(False)
        self.posZ_piezo_edt_4.setEnabled(False)
        self.posZ_piezo_edt_5.setEnabled(False)
        
        self.posX_edt.setKeyboardTracking(False) # the selection wait for the whole number to be changed
        self.posY_edt.setKeyboardTracking(False)
        self.posZ_motor_edt_1.setKeyboardTracking(False)
        self.posZ_motor_edt_2.setKeyboardTracking(False)
        self.posZ_motor_edt_3.setKeyboardTracking(False)
        self.posZ_piezo_edt_1.setKeyboardTracking(False)
        self.posZ_piezo_edt_2.setKeyboardTracking(False)
        self.posZ_piezo_edt_3.setKeyboardTracking(False)
        self.posZ_piezo_edt_4.setKeyboardTracking(False)
        self.posZ_piezo_edt_5.setKeyboardTracking(False)
        
        self.posFilt_top = self.posFilt_bottom ='N/A' 
        self.obj_choice = 0
        
        self.posZ_motor=0
        self.posZ_piezo = 0
        # self.sizeX_um_spbx.valueChanged.connect(self.px_X_change) # editingFinished was just on 'enter' press
        # self.sizeY_um_spbx.valueChanged.connect(self.px_Y_change)
        
        self.posZ_motor_edt_2_current = 0
        self.posZ_motor_edt_3_current = 0
        self.posZ_motor_edt_4_current = 0
        self.posZ_piezo_edt_2_current = 0
        self.posZ_piezo_edt_3_current = 0
        self.posZ_piezo_edt_4_current = 0
        self.posZ_piezo_edt_5_current = 0
        
        self.objective_choice.currentIndexChanged.connect(self.put_obj_zero_meth)
        self.filter_top_choice.currentIndexChanged.connect(self.fltr_top_changed)
        self.filter_bottom_choice.currentIndexChanged.connect(self.fltr_bottom_changed)
        self.posZ_motor_edt_1.valueChanged.connect(self.z_motor_edt1_changed) # to make changed in Z value
        self.posZ_motor_edt_2.valueChanged.connect(self.z_motor_edt2_changed) # to make changed in Z value
        self.posZ_motor_edt_3.valueChanged.connect(self.z_motor_edt3_changed) # to make changed in Z value
        self.posZ_motor_edt_4.valueChanged.connect(self.z_motor_edt4_changed) # to make changed in Z value
        self.posZ_piezo_edt_1.valueChanged.connect(self.z_piezo_edt1_changed)
        self.posZ_piezo_edt_2.valueChanged.connect(self.z_piezo_edt2_changed)
        self.posZ_piezo_edt_3.valueChanged.connect(self.z_piezo_edt3_changed)
        self.posZ_piezo_edt_4.valueChanged.connect(self.z_piezo_edt4_changed)
        self.posZ_piezo_edt_5.valueChanged.connect(self.z_piezo_edt5_changed)
        self.motorZ_changeDispValue_signal.connect(self.motorZ_changeDispValue_meth)
        self.piezoZ_changeDispValue_signal.connect(self.piezoZ_changeDispValue_meth)
        
        self.prev_pos_imic_chck.stateChanged.connect(self.prev_pos_imic_meth)
        self.use_piezo_for_Z_stack = 0
        self.init_imic_button.clicked.connect(self.frstiniIMIC_meth) # will be disconnect. after ; lambda: is a 'def'
        
        self.fname_fileparams = 'var.txt'
        
        self.jobs_window.max_widgZ_mm_spnbx.setValue(round(param_ini.max_pos_Z_motor))
        self.jobs_window.max_widgZ_mm_spnbx.valueChanged.connect(self.max_widgZ_mm_changed)
        
        self.anlggalv_bottom_slider_pos = self.stgscn_bottom_slider_pos = param_ini.mirrordirect_bottom_slider_pos
        self.diggalv_bottom_slider_pos = param_ini.empty_bottom_slider_pos
        self.jobs_window.only_motorZ_chck.setEnabled(False)
        
        ## stage XY

        self.stageXY_is_here = 0 # default
        self.vel_acc_X_reset_by_move = False # default
        self.vel_acc_Y_reset_by_move = False # default
        
        self.max_accn_x = self.acc_max_motor_X_spinbox.value()
        self.max_accn_y = self.acc_max_motor_Y_spinbox.value()
        self.max_vel_x = self.speed_max_motor_X_spinbox.value()
        self.max_vel_y = self.speed_max_motor_Y_spinbox.value()
        
        self.posX_10_push.clicked.connect(self.posX_10_push_meth)
        self.posX_100_push.clicked.connect(self.posX_100_push_meth)
        self.posX_1000_push.clicked.connect(self.posX_1000_push_meth)
        self.posY_10_push.clicked.connect(self.posY_10_push_meth)
        self.posY_100_push.clicked.connect(self.posY_100_push_meth)
        self.posY_1000_push.clicked.connect(self.posY_1000_push_meth)
        self.posX_m10_push.clicked.connect(self.posX_m10_push_meth) # minus
        self.posX_m100_push.clicked.connect(self.posX_m100_push_meth) # minus
        self.posX_m1000_push.clicked.connect(self.posX_m1000_push_meth) # minus
        self.posY_m10_push.clicked.connect(self.posY_m10_push_meth) # minus
        self.posY_m100_push.clicked.connect(self.posY_m100_push_meth) # minus
        self.posY_m1000_push.clicked.connect(self.posY_m1000_push_meth) # minus
        
        self.max_vel_x_current = self.max_vel_x; self.max_vel_y_current = self.max_vel_y;
        self.max_accn_x_current = self.max_accn_x; self.max_accn_y_current = self.max_accn_y
        self.stage_scn_block_moves_current = False
        self.stagescn_wait_fast_current = False
        self.invDir_slow_current = False
        self.force_reinit_AI_eachimg_current = False
        self.stage_scn_block_stp_lbl.setVisible(False)
        self.stage_scn_block_stp_chck.setVisible(False)
        self.stagescn_wait_fast_chck.setVisible(False)
        self.stagescn_wait_fast_lbl.setVisible(False)
        self.applylive_params_stgscn_chck.setVisible(False)
        self.applylive_params_stgscn_lbl.setVisible(False)
        self.coupleaccnvel_stgscn_chck.setVisible(False)
        self.coupleaccnvel_stgscn_lbl.setVisible(False)
        
        self.posX = 55
        self.posY = 37.5
        
        self.posX_edt.setEnabled(False)
        self.posY_edt.setEnabled(False)
        self.posX_10_push.setEnabled(False)
        self.posX_100_push.setEnabled(False)
        self.posX_1000_push.setEnabled(False)
        self.posY_10_push.setEnabled(False)
        self.posY_100_push.setEnabled(False)
        self.posY_1000_push.setEnabled(False)
        self.posX_m10_push.setEnabled(False)
        self.posX_m100_push.setEnabled(False)
        self.posX_m1000_push.setEnabled(False)
        self.posY_m10_push.setEnabled(False)
        self.posY_m100_push.setEnabled(False)
        self.posY_m1000_push.setEnabled(False)
        
        self.chck_homed = 0
        
        # self.px_X_change() # apply good parameters by default
        # self.px_Y_change() # apply good parameters by default
        
        # because default is galvo scan
        self.bidirec_check.setCurrentIndex(0) # 0 is bidirek
        self.bidirec_check.setVisible(True)
        self.xscan_radio.setVisible(False)
        self.yscan_radio.setVisible(False)
        self.acc_offset_spbox.setVisible(False)
        self.dec_offset_spbox.setVisible(False)
        # self.pixell_offset_dir_spbox.setVisible(False)
        # self.pixell_offset_rev_spbox.setVisible(False)
        # self.cancel_inline_button.setVisible(False)
        self.acc_offset_theo_lbl.setVisible(False)
        self.label_pixell_trans2.setVisible(False)
        # self.label_pixell_read.setVisible(False)
        # self.label_pixell_read2.setVisible(False)
        # self.label_pixell_read3.setVisible(False)
        self.pixell_offset_theo_lbl.setVisible(False)
        # # self.profile_mode_cmbbx.setVisible(False)
        # # self.profile_mode_lbl.setVisible(False)
        self.jerk_fast_lbl.setVisible(False)
        self.jerk_fast_spnbx.setVisible(False)
        self.label_pixell_trans3.setVisible(False)
        self.label_pixell_trans4.setVisible(False)
        self.lock_stage_scan_dep_chck.setVisible(False)
        self.modeEasy_stgscn_cmbbx.setVisible(False)
        self.acc_offset_spbox.valueChanged.connect(self.buffer_read_change_wrt_acc_offset_meth)
        self.lock_stage_scan_dep_chck.stateChanged.connect(self.lock_stage_scan_dep_meth)
        
        self.scan_thread_available = 1 # not True
        
        self.quick_init_button.clicked.connect(self.frstini_PI_meth)
        self.quick_init_button.clicked.connect(self.quick_init_meth)
        # # self.quick_init_button.clicked.connect(self.init_imic_button.animateClick)
        
        self.profile_mode_cmbbx.setCurrentIndex(param_ini.prof_mode - 1)
        self.jerk_fast_spnbx.setValue(param_ini.jerk_mms3)
        self.profile_mode_stgXY_current = param_ini.prof_mode # 1 for trapez, 2 for S-curve
        self.jerk_stgXY_current = param_ini.jerk_mms3 # in mm/s3
        
        # # print('param_ini.jerk_mms3 ', param_ini.jerk_mms3)
        
        self.jerk_fast_spnbx.editingFinished.connect(self.after_jerk_stgscn_changed_meth)
        self.profile_mode_cmbbx.currentIndexChanged.connect(self.after_profile_mode_stgscn_changed_meth)
        # # self.profile_mode_cmbbx.currentIndexChanged.connect(self.scan_dependencies_changed)
        
        self.stop_xy_motors_push.pressed.connect(self.after_stop_motorsXY_meth) # pressed avoid activation by keyboard, I hesitated with released (this option is the safest for the motor, not the acquisition)
        
        self.stgscn_livechgX_chck.setVisible(False)
        self.stgscn_livechgY_chck.setVisible(False)
        
        self.ct_adj_vel_size_msg = 0
        
        self.acc_offset_spbox.valueChanged.connect(self.duration_change)
        self.dec_offset_spbox.valueChanged.connect(self.duration_change)
    
        self.posX_edt.valueChanged.connect(self.posX_changed)
        self.posY_edt.valueChanged.connect(self.posY_changed)
        self.speed_max_motor_X_spinbox.valueChanged.connect(self.scan_dependencies_changed)
        self.acc_max_motor_X_spinbox.setValue(param_ini.acc_dflt)
        self.acc_max_motor_Y_spinbox.setValue(param_ini.acc_dflt)
        self.speed_max_motor_X_spinbox.setValue(param_ini.vel_dflt)
        self.speed_max_motor_Y_spinbox.setValue(param_ini.vel_dflt) # call scan_dependencies_changed just once
        self.speed_max_motor_Y_spinbox.valueChanged.connect(self.scan_dependencies_changed) 
        self.acc_max_motor_X_spinbox.valueChanged.connect(self.scan_dependencies_changed)
        self.acc_max_motor_Y_spinbox.valueChanged.connect(self.scan_dependencies_changed)
                 
        # # self.ctrl_res_stage_button.clicked.connect(self.stgscn_Easymode_changed_meth) # fake
        self.modeEasy_stgscn_cmbbx.currentIndexChanged.connect(self.stgscn_Easymode_changed_meth) # action of programmatically
        self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:coral;') #,"background-color:black;"
        self.modeEasy_stgscn_cmbbx.setItemData(0, QtGui.QColor('coral'), QtCore.Qt.BackgroundRole) # orange pale
        self.modeEasy_stgscn_cmbbx.setItemData(1, QtGui.QColor('darksalmon'), QtCore.Qt.BackgroundRole) # salmon
        self.modeEasy_stgscn_cmbbx.setItemData(2, QtGui.QColor('gold'), QtCore.Qt.BackgroundRole) # yellow
        self.modeEasy_stgscn_cmbbx.setItemData(3, QtGui.QColor('lightgreen'), QtCore.Qt.BackgroundRole) # green pale
        self.modeEasy_stgscn_cmbbx.setItemData(4, QtGui.QColor('skyblue'), QtCore.Qt.BackgroundRole) # skyblue
        self.modeEasy_stgscn_cmbbx.setItemData(5, QtGui.QColor('lightsteelblue'), QtCore.Qt.BackgroundRole) # grey
        
        self.profile_mode_cmbbx.currentIndexChanged.connect(self.stgscn_block_ornot_meth)
        self.home_stage_button.clicked.connect(self.firstini_stageXY_meth)
        
        self.rotate = param_ini.rotate
        self.acc_dflt = param_ini.acc_dflt
        self.vel_dflt = param_ini.vel_dflt
        self.offsetX00_stgscn = param_ini.offsetX00_stgscn
        self.offsetY00_stgscn = param_ini.offsetY00_stgscn
        self.acc_max = param_ini.acc_max
        self.tolerance_speed_accn_diff_real_value = param_ini.tolerance_speed_accn_diff_real_value
        self.trigout_stgXY_current = param_ini.trigout_maxvelreached
        self.trigout_stgXY = param_ini.trigout_maxvelreached
        self.action_stg_params_cmb.currentIndexChanged.connect(self.action_stg_params_meth)
        self.debug_mode_stgscn = False # # set it manually to True to debug stage scan without motor
        self.transXY_imgplane_anlggalv_chck.setVisible(True)
                
        ## PMTs parameters
        
        self.pmt1_physMin_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt1_physMax_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt2_physMin_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt2_physMax_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt3_physMin_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt3_physMax_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt4_physMin_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        self.pmt4_physMax_spnbx.valueChanged.connect(self.define_real_PMT_range_meth)
        
        self.pmt1_physMin_spnbx.setValue(-11) # to be sure it enters in the function ^^
        self.pmt1_physMin_spnbx.setValue(param_ini.min_val_volt_list[0])
        self.pmt2_physMin_spnbx.setValue(param_ini.min_val_volt_list[1])
        self.pmt3_physMin_spnbx.setValue(param_ini.min_val_volt_list[2])
        self.pmt4_physMin_spnbx.setValue(param_ini.min_val_volt_list[3])
        self.pmt1_physMax_spnbx.setValue(param_ini.max_val_volt_list[0])
        self.pmt2_physMax_spnbx.setValue(param_ini.max_val_volt_list[1])
        self.pmt3_physMax_spnbx.setValue(param_ini.max_val_volt_list[2])
        self.pmt4_physMax_spnbx.setValue(param_ini.max_val_volt_list[3])
        
        self.bound_AI_1 = 10
        self.bound_AI_2 = 10
        self.bound_AI_3 = 10
        self.bound_AI_4 = 10
        
        self.pmt1_chck.stateChanged.connect( self.after_pmt_changed)
        self.pmt2_chck.stateChanged.connect( self.after_pmt_changed)
        self.pmt3_chck.stateChanged.connect( self.after_pmt_changed)
        self.pmt4_chck.stateChanged.connect( self.after_pmt_changed)
        self.pmt5_chck.stateChanged.connect( self.after_pmt_changed)
        self.pmt6_chck.stateChanged.connect( self.after_pmt_changed)
        
        self.gainPMT_indic_1.editingFinished.connect( self.gainPMT_changed_meth) # Return or Enter key is pressed or the line edit loses focus
        self.gainPMT_indic_2.editingFinished.connect( self.gainPMT_changed_meth) # Return or Enter key is pressed or the line edit loses focus
        self.gainPMT_indic_3.editingFinished.connect( self.gainPMT_changed_meth) # Return or Enter key is pressed or the line edit loses focus
        self.gainPMT_indic_4.editingFinished.connect( self.gainPMT_changed_meth) # Return or Enter key is pressed or the line edit loses focus
        
        self.cmap_curr = [0,0,0,0]
        self.shutter_curr_mode = 1 # # at  all imgs
        
        ## shutter
        
        self.use_shutter_combo.currentIndexChanged.connect(self.shutter_using_changed) # don't use stateChanged
        self.shutter_closed_chck.clicked.connect(self.shutter_force_openClose_toggled) # don't use stateChanged
        self.was_in_send_new_img_func = 0
        self.out_scan = True
        
        ## scan parameters
        
        self.scan_thread_available_signal.connect(self.scan_not_running_def_meth)

        self.offsetX_dflt = self.offsetX_mm_spnbx.value() # fixed in designer
        self.offsetY_dflt = self.offsetY_mm_spnbx.value()
        
        self.nb_pmt_checkable = 4 # see GUI
        self.pmt_current = (1, 0, 0, 0, 0, 0)
        self.after_pmt_changed()
        self.set_new_scan = 2 # 3 for 1st scan
        self.scan_mode_str = 'static acq'
        
        self.num_experiment = 0
       
        self.stage_scan_mode = self.stage_scan_mode_before = 2 # static acq
        self.stage_scan_mode_current = 2
        
        self.filter_top_choice_curr_index = 0
        
        self.stage_scn_block_stp_chck.stateChanged.connect(self.stage_scn_block_stp_chg_meth)
        self.stagescn_wait_fast_chck.stateChanged.connect(self.duration_change)
        
        self.step_ref_val_stage = param_ini.step_ref_val_stage #um
        self.step_ref_val_galvo = param_ini.step_ref_val_galvo # um
        self.too_much_sizeum_slow_stage = 51 # um
        self.dflt_sizeum_slow_stage = 50 # um
        self.max_vel_stage = 200 # mm/s
        self.sizeX_galvo_prev = param_ini.size_um_dflt
        self.sizeY_galvo_prev = param_ini.size_um_dflt
        self.update_rate_spnbx.setValue(1/param_ini.update_time) # Hz
        self.update_time = 1/self.update_rate_spnbx.value() # sec # param_ini.update_time # for now
        
        self.scan_parameters = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        self.scan_dependencies = [0,0,0,0]
        
        self.acc_offset_theo_label_dflt = self.acc_offset_theo_lbl.text()
        self.pixell_offset_theo_label_dflt = self.pixell_offset_theo_lbl.text()
    
        # # self.stepX_um_edt.valueChanged.connect(self.px_X_change) 
        # # self.stepY_um_edt.valueChanged.connect(self.px_Y_change)
        # # self.nbPX_X_ind.valueChanged.connect(self.size_X_change) 
        # # self.nbPX_Y_ind.valueChanged.connect(self.size_Y_change)
        
        self.sizeX_um_spbx.valueChanged.connect(self.duration_change) # editingFinished was just on 'enter' press
        self.sizeY_um_spbx.valueChanged.connect(self.duration_change)
        self.stepX_um_edt.valueChanged.connect(self.duration_change) 
        self.stepY_um_edt.valueChanged.connect(self.duration_change)
        self.nbPX_X_ind.valueChanged.connect(self.duration_change) 
        self.nbPX_Y_ind.valueChanged.connect(self.duration_change)
        
        self.eff_na_bx.valueChanged.connect(self.set_th_res_meth)
        self.lambda_bx.valueChanged.connect(self.set_th_res_meth)
        self.index_opt_bx.valueChanged.connect(self.set_th_res_meth)
        self.stepX_um_edt.valueChanged.connect(self.change_nyquist_meth) # protected against infinite loops
        self.stepY_um_edt.valueChanged.connect(self.change_nyquist_meth) # protected against infinite loops
        self.th_xy_res_edt.textChanged.connect(self.change_nyquist_meth) # protected against infinite loops
        
       
        self.nbPX_X_ind.valueChanged.connect(self.change_nyquist_meth) # protected against infinite loops
        self.nbPX_Y_ind.valueChanged.connect(self.change_nyquist_meth) # protected against infinite loops
        self.nbPX_X_ind.valueChanged.connect(self.nb_px_x_changed_meth) # protected against infinite loops
        self.nbPX_Y_ind.valueChanged.connect(self.nb_px_y_changed_meth) # protected against infinite loops
        self.nbPX_X_ind.valueChanged.connect(self.nb_px_xy_to_sampling_meth) # protected against infinite loops
        self.nbPX_Y_ind.valueChanged.connect(self.nb_px_xy_to_sampling_meth) # protected against infinite loops
        
        self.nyquist_slider.valueChanged.connect(self.nyquist_slider_changed_meth)
        self.nyquist_slider.sliderReleased.connect(self.nyquist_slider_finished_meth)
        self.sampling_bx.valueChanged.connect(self.sampling_changed_meth)
        self.frac_FOV_spn_bx.valueChanged.connect(self.after_fov_perc_changed_meth)
        self.magn_obj_bx.valueChanged.connect(self.after_fov_perc_changed_meth)
        self.magn_obj_bx.editingFinished.connect(self.magn_init_meth) # # if loses focus OR enter pressed (but NOT if value changed only)
        self.magn_obj_bx.valueChanged.connect(self.up_volt_anlg_galvo_meth) 
        
        self.size_um_dflt = param_ini.size_um_dflt
        self.sizeX_um_spbx.valueChanged.connect(self.after_sizeX_um_changed_meth) # protected against infinite loops
        self.sizeY_um_spbx.valueChanged.connect(self.after_sizeY_um_changed_meth) # protected against infinite loops

        self.stepX_um_edt.valueChanged.connect(self.stepX_um_changed_meth)
        self.stepY_um_edt.valueChanged.connect(self.stepY_um_changed_meth)

        self.square_img_chck.stateChanged.connect(self.square_img_changed_meth)
        self.square_px_chck.stateChanged.connect(self.square_px_changed_meth)
        
        # # self.speed_max_motor_X_spinbox.valueChanged.connect(self.duration_change)
        # # self.speed_max_motor_Y_spinbox.valueChanged.connect(self.duration_change)
        
        self.bidirec_check.currentIndexChanged.connect(self.duration_change)
        
        self.dwll_time_edt.valueChanged.connect(self.exp_time_changed_meth)
        self.duration_indic.editingFinished.connect(self.adjust_steps_function_duration_time)
         
        self.yscan_radio.toggled.connect(self.x_or_y_scan_changed)
        
        self.launch_scan_button.clicked.connect(self.define_if_new_scan) # galvo scan is default
        self.external_clock = 0 # default is internal clock
        self.external_clock_current = self.external_clock

        self.launch_scan_button_single.clicked.connect(self.force_single_scan_meth)# galvo scan is default
        # self.mode_scan_box.currentIndexChanged.connect(self.cancel_scan_meth) # allow to change the mode of scan
        self.mode_scan_box.currentIndexChanged.connect(self.scan_mode_changed) # allow to change the mode of scan
        
        self.name_img_table.itemSelectionChanged.connect(self.display_img_selected)
        self.swappg_img_button.clicked.connect(self.display_img_selected)
        
        self.magn_obj_bx.setValue(param_ini.magn_obj_dflt)
        self.obj_mag = param_ini.magn_obj_dflt
        if self.obj_mag == 20:
            self.objective_name = 'Obj 1'
            # self.NA_obj = 0.8
            self.eff_na_bx.setValue(param_ini.eff_na_20X)
            self.size_um_fov = param_ini.size_um_fov_20X # um

        elif self.obj_mag == 40:
            self.objective_name = 'Obj 2' #  40X dflt
            # self.NA_obj = 0.8
            self.eff_na_bx.setValue(param_ini.eff_na_40X)
            self.size_um_fov = param_ini.size_um_fov_40X # um
            
        self.magn_init = False
        
        self.obj_mag_current = self.obj_mag
        self.new_szX_um_current = self.sizeX_um_spbx.value() 
        self.new_szY_um_current = self.sizeY_um_spbx.value()
        self.px_sz_x_current = self.stepX_um_edt.value()
        self.px_sz_y_current = self.stepY_um_edt.value()
        self.nb_px_x_current = round(self.nbPX_X_ind.value())
        self.nb_px_y_current = round(self.nbPX_Y_ind.value())
        self.center_x_current = self.offsetX_mm_spnbx.value()
        self.center_y_current = self.offsetY_mm_spnbx.value()
        
        self.real_time_disp_current = self.real_time_disp_chck.isChecked()
        
        self.nb_bins_hist_current = self.nb_bins_hist_box.value()
                
        self.y_fast_current = self.yscan_radio.isChecked() # y fast
        self.unidirectional_current = self.bidirec_check.currentIndex() # 1 or 2 for unidirec
        self.dist_offset_current = self.acc_offset_spbox.value()
        #self.dist_offset_rev_current = self.dist_offset_current
        self.dist_offset_rev_current = self.dec_offset_spbox.value()
        self.read_buffer_offset_direct_current = self.pixell_offset_dir_spbox.value()
        self.read_buffer_offset_reverse_current = self.pixell_offset_rev_spbox.value()
        
        self.pmt_channel_list_current = [1,0,0,0]
        
        self.clrmap_nb_current = self.clrmap_choice_combo.currentIndex()
        self.delete_px_fast_begin = 0 # in PX, avoid motor translation artefact
        self.delete_px_fast_end = 0 # in PX, avoid motor translation artefact
        self.delete_px_slow_begin = 0 # in PX, avoid read buffer artefact
        self.delete_px_slow_end = 0  # in PX, not used a priori
        self.delete_px_fast_begin_current = self.delete_px_fast_begin ;self.delete_px_fast_end_current = self.delete_px_fast_end; self.delete_px_slow_begin_current = self.delete_px_slow_begin; self.delete_px_slow_end_current = self.delete_px_slow_end; self.update_time_current = self.update_time
        self.sampleRateRead_current = self.read_sample_rate_spnbx.value()
        self.nb_img_max_current = self.nb_img_max_box.value()
        
        self.dwll_time_edt.setValue((param_ini.time_by_point*1e6))
        self.time_by_point = param_ini.time_by_point
        
        self.duration_indic.setText(('%.1f' % (self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6)))
        
        self.nb_img_max = 1
        self.exp_time_current = self.dwll_time_edt.value()
        self.time_base_ext_current = self.timebase_ext_diggalvo_chck.isChecked()
        self.force_whole_new_scan = 0
        
        self.curr_row_img = -1
        
        self.change_nyquist_meth()
        self.square_img_changed_meth()
        self.exp_time_changed_meth()
        
        self.read_sample_rate_spnbx.valueChanged.connect(self.read_sample_rate_changed_meth)
        self.nb_accum_current = self.nb_packet_acc_spnbx.value()
        
        self.scan_xz_current = False # default is XY
        # self.job_name = ''
        # # self.new_job_line_in_table_signal.connect(jobs_trans_Zstack_scripts.new_job_line_in_table_meth(self))
        self.dev_to_use_AI_box.currentIndexChanged.connect(self.dev_to_use_AI_chg_after_meth)
        self.read_sample_rate_spnbx.setValue(param_ini.smp_rate_AI_dflt)
        
        self.list_scan_params = []
        
        self.ext_smp_clk_chck.stateChanged.connect(self.ext_smp_clk_changed_meth)
        
        self.currentDevice_AI_current = 0
        
        self.size_max_px_for_display = param_ini.size_max_px_for_display
        
        self.center_x = 0 ; self.center_y = 0 ; self.new_szX_um = 200 ; self.new_szY_um = 200 ; self.nb_px_x = 400  ; self.nb_px_y = 400 ; self.nb_img_max = 1;  self.unidirectional = 1; self.unidirectional_current = 1; self.y_fast = 0 ;  self.nb_bins_hist =100;  self.real_time_disp = 1 ;  self.delete_px_fast_begin= 0; self.delete_px_fast_end = 0; self.delete_px_slow_begin = 0; self.delete_px_slow_end = 0; self.eff_wvfrm_an_galvos = self.eff_wvfrm_an_galvos_spnbx.value() ; self.mult_trig_fact_anlg_galv= self.trig_safety_perc_spnbx.value()/100; self.trig_perc_hyst= self.hyst_perc_trig_spnbx.value(); self.nb_accum = 1; self.scan_xz = 0; self.external_clock = 0; self.time_base_ext = 0; self.read_buffer_offset_direct = 0; self.read_buffer_offset_reverse = 0
        self.nb_pass_calcites = param_ini.nb_pass_calcites
        # self.coupleaccnvel_stgscn_chck.stateChanged(self.coupleaccnvel_stgscn_changed_meth)

        self.method_fast_stgscn = param_ini.method_fast_stgscn
        
        self.sample_rate_current = self.read_sample_rate_spnbx.value()
        
        ## galvos dig params
        
        self.use_preset_sync_dig_galv_chck.stateChanged.connect(self.preset_sync_dig_galv_changed_meth)
        self.pause_trig_sync_dig_galv_chck.stateChanged.connect(self.pause_trig_sync_dig_galv_changed_meth)
        self.timebase_ext_diggalvo_chck.stateChanged.connect(self.timebase_ext_diggalvo_changed_meth)
        self.corr_sync_inPx_current = 0
        self.offsetX00_Galvos = None
        self.offsetY00_Galvos = None
        self.pause_trig_sync_dig_galv_chck.stateChanged.emit(self.pause_trig_sync_dig_galv_chck.isChecked())
        
        self.offsetX00_digGalvos = param_ini.offsetX00_digGalvos
        self.offsetY00_digGalvos = param_ini.offsetY00_digGalvos
        self.eff_loss_dig_galvos = param_ini.eff_loss_dig_galvos
        
        self.pause_trig_sync_dig_galv_chck.setVisible(False) # dig. galvos is not dflt scan         
        
        self.anlgtriggalvos_dev_box.setVisible(False)  # # for anlg galvos
        self.aogalvos_dev_box.setVisible(False)
        self.watch_triggalvos_dev_box.setVisible(False) 
        
        self.acqline_galvo_mode_box.currentIndexChanged.connect(self.acqline_galvo_mode_changed_meth)

        ## galvos anlg new params
        
        self.write_scan_before_anlg = param_ini.write_scan_before_anlg
        self.write_scan_before_anlg_current = self.write_scan_before_anlg
        self.pause_trig_diggalvo_current = 1
        self.num_dev_anlgTrig = param_ini.num_dev_anlgTrig  # # for anlg galvos
        self.num_dev_watcherTrig = param_ini.num_dev_watcherTrig
        self.num_dev_AO = param_ini.num_dev_AO # # for anlg galvos
        self.mult_trig_fact_anlg_galv_current = self.mult_trig_fact_anlg_galv
        self.trig_perc_hyst_current = self.trig_perc_hyst
        self.eff_wvfrm_an_galvos_spnbx.valueChanged.connect(self.duration_change)
        self.eff_wvfrm_an_galvos_spnbx.valueChanged.connect(self.eff_new_galvos_adjustMax_meth)
        self.trig_safety_perc_spnbx.valueChanged.connect(self.duration_change)
        self.trig_safety_perc_spnbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
        self.hyst_perc_trig_spnbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
        self.ai_readposX_anlggalvo = param_ini.ai_readposX_anlggalvo ; self.ai_readposY_anlggalvo =  param_ini.ai_readposY_anlggalvo
        self.factor_trigger = param_ini.factor_trigger
        self.factor_trigger_chan = param_ini.factor_trigger_chan
        self.fact_buffer_anlgGalvo_spbx.setValue(param_ini.fact_buffer_anlgGalvo)

        self.offsetX00_anlgGalvos = param_ini.offsetX00_anlgGalvos
        self.offsetY00_anlgGalvos = param_ini.offsetY00_anlgGalvos
        self.method_watch = param_ini.method_watch
        self.eff_wfrm_anlggalv_dflt = param_ini.eff_wfrm_anlggalv_dflt
        self.eff_wvfrm_an_galvos_spnbx.setValue(self.eff_wfrm_anlggalv_dflt)
        self.acqline_galvo_mode_current = self.acqline_galvo_mode = 0 if param_ini.method_watch == 7 else 1
        # # 0 for linetime meas., 1 for callback each line 
        
        ## plot definition

        pg_plot_scripts.pg_plot_init(self, pyqtgraph, numpy, param_ini)
        # # global isoLine_pg, iso_pg
        # # self.clrmap_choice_combo.setCurrentIndex(0) # grey
        self.clrmap_choice_combo.setCurrentIndex(1) # Fire
        
        self.clrmap_nb = 1
        self.clrmap_nb_2 = 1
        
        self.graphicsView_img.scene().sigMouseMoved.connect(self.mouseMoved)
        self.graphicsView_img.scene().sigMouseClicked.connect(self.mouseClicked)
        self.roi_button.clicked.connect(self.roi_pg_after_meth)
        self.set_from_ROI_button.clicked.connect(self.def_scan_roi_pg_meth)
        self.roi_pg_current = 0 # dflt
        self.offsetX_pg_curr = 0
        self.offsetY_pg_curr = 0
        self.up_offset_pg = False
        
        self.load_img_button.clicked.connect(self.load_disp_img_from_file_meth)
        warnings.filterwarnings('ignore', message='overflow encountered in short_scalars')
        
        ## queues definition
        
        self.queue_moveX_inscan = queue.Queue() # queue.Queue only (not multiprocessing) because communicating with a thread, not a process
        self.queue_moveY_inscan = queue.Queue() # queue.Queue only (not multiprocessing) because communicating with a thread, not a process
        
        self.queue_com_to_acq_process = multiprocessing.Queue() # multiprocessing Queue because communicating with a process
        self.queue_com_to_acq_stage = queue.Queue()  # queue.Queue only (not multiprocessing) because communicating with a thread, not a process
        self.queue_com_to_acq = self.queue_com_to_acq_process # by default the galvo scan is the selected one
        self.queue_special_com_acqstage_stopline = queue.Queue() # only for stage scan, a queue to stop acq between two lines
        self.queue_special_com_acqGalvo_stopline = multiprocessing.Queue() # only for Galvo scan, a queue to stop acq between two lines
        self.queue_special_com_acq_stopline = self.queue_special_com_acqGalvo_stopline # default

        self.queue_list_arrays = multiprocessing.Queue() # Pipe does not work
        self.queue_disconnections = queue.Queue() # for disconnecting the workers
        self.stop_motorsXY_queue = queue.Queue() # for stopping motorXY while moving
        
        # # self.queue_OpenClose_shutter = queue.Queue()
        
        # self.queue_scan_parameters = queue.Queue()
        
        ## general buttons connect
        
        self.quit_button.setStyleSheet('background-color:coral;') #,"background-color:black;"
        self.cancel_scan_button.clicked.connect(self.cancel_scan_meth)
        self.cancel_inline_button.clicked.connect(self.cancel_scan_button.animateClick)
        self.cancel_inline_button.clicked.connect(self.cancel_inline_meth)
        
        self.cpt_row_table_img = 1
        self.list_arrays = [] # list where the arrays will be stored

        self.save_img_button.clicked.connect(self.save_img_stack)
        self.save_last_button.clicked.connect(self.save_last_meth)
        # self.save_last_button.showText('Save the # of images specified above the cursor')
        self.erase_img_button.clicked.connect(self.erase_last_meth)
        self.offset_table_img = self.offset_save_img = 0
        # # self.ctrl_res_stage_button.clicked.connect(self.ctrl_res_stage_meth)
        
        # # self.quit_button.clicked.connect(self.wait_gui_quit_meth
        self.quit_button.clicked.connect(self.quit_gui_func)
        # # self.user_want_to_quit_gui = 0 # do not put this to 1, unless gui will self-quit !
        self.table_copy_content_button.clicked.connect(self.table_copy_content_meth)
        
        self.kill_scan_thread_button.clicked.connect(self.kill_scanThread_meth)
        self.mtrreturninitposjob = True
        self.mtrreturninitposjob_set = True
        
        ## general def
         
        self.path_frog = r'%s\Desktop' % os.path.abspath(self.path_computer + '/../' + '/../')
        
        self.name_img_table.setColumnWidth(0, 25) # num
        self.name_img_table.setColumnWidth(1, 40) # num PMT
        self.name_img_table.setColumnWidth(5, 60) # X
        self.name_img_table.setColumnWidth(6, 60) # Y
        self.name_img_table.setColumnWidth(7, 80) # Z
        self.name_img_table.setColumnWidth(8, 70) # Z pz
        self.name_img_table.setColumnWidth(9, 90) # off
        self.name_img_table.setColumnWidth(16, 60) # sat val
        
        self.reg_shift_img_push.clicked.connect(self.shift_reg_xcorr_meth)
        
        self.jobs_window.qthread_rst_edt.returnPressed.connect(self.qthread_rst_meth) # # for putting command to exec (see GUI 2nd win)
        
        self.pathwalk =  r'%s\Desktop' % (os.path.abspath(path_computer + '/../' + '/../'))
        
        self.jobs_window.autoscalelive_plt_cmb.currentIndexChanged.connect(self.autoscalelive_plt_cmb_index_meth)
        
        ## jobs button
        
        self.name0 = ''
        self.end_job_apt_signal.connect(self.end_job_apt)
        
        self.jobs_window.angle_polar_bx.setEnabled(False)
        self.jobs_window.home_tl_rot_button.setEnabled(False)
        self.jobs_window.newport_polar_bx.setEnabled(False)
        self.jobs_window.home_newport_rot_button.setEnabled(False)
        
        # self.pos_motor_phshft_spinbx.setKeyboardTracking(False) # wait for the whole value to be entered in keyboard

        self.connect_new_img_to_move_phshft = 0
        self.connect_new_img_to_move_polar = 0
        self.connect_new_img_to_move_Z_obj = 0
        self.connect_end_z_to_move_phshft = 0
        self.connect_end_Z_to_move_polar = 0
        self.connect_end_apt_to_move_Z = 0
        self.connect_end_polar_to_move_ps = 0
        self.connect_end_ps_to_move_polar = 0
        self.connect_new_img_to_single = 0
        self.pos_polar0b = 0
        self.connect_new_img_to_move_XY= 0
        
        # self.open_jobs_window_button.clicked.connect(self.open_jobs_window_meth)
        
        self.jobs_window.cal_ps_button.setEnabled(True)
        # self.jobs_window.ps_job_off_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.z_job_off_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.ps_job_prim_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.z_job_prim_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.ps_job_sec_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.z_job_sec_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.ps_job_alt_radio.toggled.connect(self.define_good_job_meth)
        # self.jobs_window.z_job_alt_radio.toggled.connect(self.define_good_job_meth)
                
        self.jobs_window.strt_Z_stack_spnbx.valueChanged.connect(self.change_nb_frame_Z_stack)
        self.jobs_window.stp_Z_stack_spnbx.valueChanged.connect(self.change_nb_frame_Z_stack)
        self.jobs_window.end_Z_stack_spnbx.valueChanged.connect(self.change_nb_frame_Z_stack)
        self.jobs_window.nb_frame_Z_job_spbx.valueChanged.connect(self.after_nbFrame_Zstck_chg_meth)
        
        self.jobs_window.strt_polar_angle_spnbx.valueChanged.connect(self.change_nb_frame_polar_meth)
        self.jobs_window.step_polar_angle_spnbx.valueChanged.connect(self.change_nb_frame_polar_meth)
        self.jobs_window.stop_polar_angle_spnbx.valueChanged.connect(self.change_nb_frame_polar_meth)
        self.jobs_window.nb_frame_polar_job_spbx.valueChanged.connect(self.after_nbFrame_polar_chg_meth)
        
        self.jobs_window.get_Z_for_start_button.clicked.connect(self.get_Z_start_from_indic_meth)
        self.jobs_window.get_diffZ_button.clicked.connect(self.get_diffZ_from_indic_meth)
        self.jobs_window.get_Z_for_end_button.clicked.connect(self.get_Z_end_from_indic_meth)
        
        self.jobs_window.nb_frame_phase_shift_spbx.setValue(round(360/self.jobs_window.step_phase_shift_spbx.value()*1.5))
        # self.jobs_window.step_phase_shift_spbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        # self.jobs_window.nb_frame_phase_shift_spbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        self.jobs_window.load_ps_list_button.clicked.connect(self.load_ps_list_meth)
        
        self.jobs_window.step_calib_phshft_spnbx.valueChanged.connect(self.change_nb_frame_calibps_meth)
        self.jobs_window.st_calib_phshft_spnbx.valueChanged.connect(self.change_nb_frame_calibps_meth)
        self.jobs_window.end_calib_phshft_spnbx.valueChanged.connect(self.change_nb_frame_calibps_meth)
        self.jobs_window.num_frame_calib_phshft_spbx.valueChanged.connect(self.change_step_calibps_meth)
        
        self.jobs_window.home_calcites_button.clicked.connect(self.home_motor_phshft)
        self.jobs_window.home_tl_phsft_button.clicked.connect(self.home_motor_phshft)
        # self.jobs_window.pos_motor_phshft_edt.setEnabled(False) # if use of a translation motor
        
        self.jobs_window.pos_motor_phshft_edt.returnPressed.connect(self.pos_phshft_changed) # not valueChanged
        self.jobs_window.pos_motor_trans_edt.returnPressed.connect(self.pos_phshft_changed)
        
        self.jobs_window.angle_polar_bx.valueChanged.connect(self.after_angle_polar_changed_meth)
        self.jobs_window.newport_polar_bx.valueChanged.connect(self.after_angle_polar_changed_meth)
        
        self.jobs_window.show()
        
        self.jobs_window.cal_ps_button.clicked.connect(self.after_cal_button_meth)
        
        self.force_homing_chck.toggled.connect(self.after_force_homing_stage_toggled_meth)
        self.jobs_window.force_homing_phshft_chck.toggled.connect(self.after_force_homing_phshft_toggled_meth)
        
        self.jobs_window.offset_pos_motor_ps_edt.editingFinished.connect(self.offset_pos_mot_ps_def_meth)
        # # self.jobs_window.offset_pos_motor_ps_edt.setKeyboardTracking(False) # wait for the whole value to be entered in keyboard
        self.jobs_window.offset_pos_motor_ps_edt.setEnabled(True) # wait for the whole value to be entered in keyboard

        self.offset_pos_motor_ps = 0
        
        self.end_job_stackZ_signal.connect(self.end_job_stack_Z)
            
        self.start_Z_current = 0
        self.nb_frame_stack_current = 0
        # # self.job_stack_Z_is_running = 0
        self.nb_frame_phase_shift_current = 0
        self.row_jobs_current = None
        self.new_ps_list_flag = None
        self.calib_job = False
        self.count_avg_job = None # None means no job is running
        self.iterationInCurrentJob = None
        
        # # self.list_pos_wrt_origin = numpy.array([0,180*0.0289,360*0.0289])
        
        self.force_single_scan = 0
        self.job_name_previous = param_ini.name_dflt00
        self.acq_name_edt.editingFinished.connect(self.acq_name_changed_meth)
        
        # # self.jobs_window.get_current_pos_mot_ps_as_offset_button.clicked.connect(self.get_current_pos_mot_ps_as_offset_meth)
        
        self.count_job_Z_stack = 0 
        self.count_job_ps = 0
        self.count_job_polar = 0
        self.list_pos_Z_to_move_piezo_or_motorZ = []
        self.list_pos_wrt_origin = [] # ps
        self.list_polar= []
        
        self.jobs_window.job_choice_combobx.currentIndexChanged.connect(self.after_job_choice_chg_meth)
        
        self.jobs_window.add_job_button.clicked.connect(self.add_job2list_meth)
        self.jobs_window.del_job_button.clicked.connect(self.del_jobFromlist_meth)
        self.jobs_window.strt_job_button.clicked.connect(self.job_manager_meth)
        # # self.jobs_window.strt_job_button_2.clicked.connect(self.job_manager_meth)
        self.jobs_window.reset_job_flag_button.clicked.connect(self.after_reset_jobFlags_meth)
        self.jobs_window.remove_done_jobs_button.clicked.connect(self.remove_jobs_done_meth)
        self.jobs_window.ascendSelJob_button.clicked.connect(self.ascendSelJob_meth)
        self.jobs_window.descendSelJob_button.clicked.connect(self.descendSelJob_meth)
        
        self.jobs_window.redetect_APT_button.clicked.connect(self.after_redetect_APT)
        
        self.jobs_window.set_anGalvo_pos_button.clicked.connect(self.send_anlgGlvo_pos_static_meth)
        self.jobs_window.get_anGalvo_pos_button.clicked.connect(self.get_anlgGlvo_pos_stat_meth)
        self.jobs_window.use_ini_val_galvo_anlg_chck.stateChanged.connect(self.use_ini_val_galvo_anlg_meth)
        self.jobs_window.fast_wantedPos_anlgGalvo_spbx.valueChanged.connect(self.pos_anlg_galvos_chg_after_meth)
        self.jobs_window.slow_wantedPos_anlgGalvo_spbx.valueChanged.connect(self.pos_anlg_galvos_chg_after_meth)
        self.off_fast_anlgGalvo_current = param_ini.offset_y_deg_00
        self.off_slow_anlgGalvo_current = param_ini.offset_x_deg_00
        self.fact_buffer_anlgGalvo_current = param_ini.fact_buffer_anlgGalvo
        self.jobs_window.off_fast00_anlgGalvo_spbx.setValue(self.off_fast_anlgGalvo_current)
        self.jobs_window.off_slow00_anlgGalvo_spbx.setValue(self.off_slow_anlgGalvo_current)

        self.jobs_window.redetect_stageXY_button.clicked.connect(self.redetect_stageXY_meth)
        self.jobs_window.redetect_newport_button.clicked.connect(self.redetect_newport_meth)
        
        self.jobs_window.mode_wp_polar_cmb.setEnabled(False)
        self.jobs_window.load_polar_xls_button.clicked.connect(self.load_polar_xls_meth)
        self.jobs_window.exec_code_button.clicked.connect(self.exec_code_meth)
        self.previous_exec_code_str = self.previous_exec_code_str_current = self.jobs_window.exec_code_edt.toPlainText()
        self.jobs_window.newline_exec_button.clicked.connect(self.print_msg_forexec_meth)
        self.jobs_window.print_exec_button.clicked.connect(self.print_msg_forexec_meth)
        self.jobs_window.implib_exec_button.clicked.connect(self.print_msg_forexec_meth)
        self.jobs_window.previoustr_exec_button.clicked.connect(self.print_msg_forexec_meth)
        
        self.jobs_window.nb_average_job_spbx.valueChanged.connect(self.jobs_avg_repeat_changed_meth)
        self.jobs_window.nb_repeat_job_spbx.valueChanged.connect(self.jobs_avg_repeat_changed_meth)
        self.repeat_job_prev = 1 # init
        self.avg_job_prev = 1 # init
        self.jobs_window.up_time_job_button.clicked.connect(self.update_time_job_meth)
        
        self.jobs_window.mtr_tl_chck.stateChanged.connect(self.mtr_tl_chck_meth)
        self.jobs_window.mtr_newport_chck.stateChanged.connect(self.mtr_newport_chck_meth)
        self.nb_img_max_box.setValue(param_ini.nb_img_cont_dflt)
        self.Z_to_set_tmp = []
        self.start_polar_current = 0
        
        self.jobs_window.get_polar_start_button.clicked.connect(self.get_polar_start_from_indic_meth)
        self.jobs_window.get_polar_diff_button.clicked.connect(self.get_diffpolar_from_indic_meth)
        self.jobs_window.get_polar_stop_button.clicked.connect(self.get_polar_end_from_indic_meth)
        
        self.jobs_window.mos_Z_Xmax_get_push.clicked.connect(self.mos_Z_XorYmax_get)
        self.jobs_window.mos_Z_Ymax_get_push.clicked.connect(self.mos_Z_XorYmax_get)
        
        self.jobs_window.ps_mtr_rot_radio.toggled.connect(self.after_toggled_choice_ps_instr)
        self.jobs_window.ps_mtr_trans_radio.toggled.connect(self.after_toggled_choice_ps_instr) # DC volt will toggle alone
        
        self.jobs_window.step_phase_shift_spbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        self.jobs_window.nb_frame_phase_shift_spbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        self.jobs_window.eq_deg_unit_test_spnbx.valueChanged.connect(self.change_step_calibps_meth)
        self.jobs_window.eq_deg_unit_test_spnbx.valueChanged.connect(self.jobs_window.eq_deg_um_spnbx.setValue)
        self.jobs_window.eq_deg_um_spnbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        self.jobs_window.max_angle_calib_phshft_spbx.valueChanged.connect(self.change_step_calibps_meth)
        self.jobs_window.nb_fr_stp_ps_spbx.valueChanged.connect(self.change_nb_frame_ps_meth)
        
        self.jobs_window.groupBox_mosaic.setVisible(False)
        self.jobs_window.visible_mosaic_chck.setChecked(False)
        self.jobs_window.visible_mosaic_chck.stateChanged.connect(self.groupBox_mosaic_visible_meth)
        self.stageXY_ready_mos = False
        self.pos_max_phshft_um = param_ini.pos_max_phshft_um
        self.motorPhshftIsHere00 = self.motorPhshftIsHere = self.motorRotIsHere = self.motorTransIsHere = False # dflt
        
        self.res_theo_deg = param_ini.res_theo_calibfast_deg # deg meaning 6 points by slope of cos
        # # phi = 2pi*nu*delta_t with delta_t = δL*(1/vg1-1/vg2)
        # # δx = δL/sin(α) = phi/(2pi*nu)/(1/vg1-1/vg2)/sin(α)
        # lambda = lambda_shg car c'est elle qui est déphasée in fine
        self.alpha_calc_deg = param_ini.alpha_calc_deg # # angle of calcite prism
        self.divider_lines_calib_fast = param_ini.divider_lines_calib_fast
        self.lambda_shg_um = param_ini.wlgth_center_expected_nm/1000/2 # # um
        self.vg1 = param_ini.vg1  ; self.vg2 =  param_ini.vg2
        self.min_exp_time_calibfast_sec = param_ini.time_by_point # 20us, in sec
        # #  min_exp_time, vel_max_instr, d_tot_mm, 
        
        self.bound_mtr_rot_plate = param_ini.bound_mtr_rot_plate
        self.bound_mtr_trans = param_ini.bound_mtr_trans
        self.after_toggled_choice_ps_instr()
        self.jobs_window.ps_slow_radio.toggled.connect(self.ps_slowfast_toggled_meth)
        self.jobs_window.ps_slow_radio.toggled.emit(False)
        self.jobs_window.autoco_frog_pushButton.clicked.connect(self.autocofrog_toggled_meth)
        
        self.jobs_window.mtrps_velset_spbx.valueChanged.connect(self.mtrps_def_vel_accn_meth)
        self.jobs_window.mtrps_accnset_spbx.valueChanged.connect(self.mtrps_def_vel_accn_meth)
        self.jobs_window.restheo_fastcalib_spbx.valueChanged.connect(self.mtrps_def_vel_accn_meth) # # not the good signal, but will do stuff and after exit function without touching the vel and acc
        self.jobs_window.restheo_fastcalib_spbx.valueChanged.connect(self.change_step_calibps_meth)
        self.min_exptime_msec = param_ini.min_exptime_msec
        self.mtrps_def_vel_accn_meth(param_ini.max_vel_TC_dflt)
        self.keep_wlth_frog = False # # same time to remove the wlth
        self.cal_ps_button_stop00 = 'Stop calib'
        self.rg_autoco_dflt_um = 4000
        # # self.eq_deg_movemm_calcite = 
        self.jobs_window.exptime_fastcalib_vallbl.textChanged.connect(self.change_step_calibps_meth)
        self.jobs_window.calc_nbpass_cmbbx.currentIndexChanged.connect(self.nbpass_calcite_changed_meth)
        self.cal_ps_button_txt00 = self.jobs_window.cal_ps_button.text()
        self.jobs_window.stop_EOMph_button.clicked.connect(self.stop_modulatorEOMph_meth) # stop
        self.jobs_window.simu_job_list_push.clicked.connect(self.list_pos_job_def_util)
        
        self.jobs_window.save_pltfig_pkl_push.clicked.connect(self.save_pltfig_pkl_after)
        self.jobs_window.save_pltfig_pkl_push.setContextMenuPolicy(QtCore.Qt.CustomContextMenu) # for right-click
        self.jobs_window.save_pltfig_pkl_push.customContextMenuRequested.connect(self.load_pltfig_pkl_after) # for right-click
        self.autoscalelive_plt = self.autoscalelive_plt_current = self.jobs_window.autoscalelive_plt_cmb.currentIndex() # # 1 for Live, 0 for 10 1st lines
        self.lock_smprate_current = self.lock_smprate = self.lock_smp_clk_chck.isChecked()
        self.lock_uptime_current = self.lock_uptime = self.lock_uprate_chck.isChecked()

        self.jobs_window.exec_code_edt.setPlainText(param_ini.exec_dflt)
        self.vel_mtr_job = self.jobs_window.mtrps_velset_spbx.value()
        
        self.jobs_window.single_polar_useloaded_chck.stateChanged.connect(self.single_polar_useloaded_ch_meth)
        
        self.nbmax00 = param_ini.nb_img_cont_dflt
        self.jobs_window.matlab_cmb.currentIndexChanged.connect(self.matlab_cmb_meth)
        
        self.motor_phshft_ID = param_ini.motor_phshft_ID
        self.motor_rot_ID = param_ini.motor_rot_ID
        self.motor_trans_ID = param_ini.motor_trans_ID
        self.path_tmp_job = None
        self.gather_calib_flag = None
        
        ## EOM phase AC
        
        self.jobs_window.voltmax_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.voltpi_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.steptheo_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.mode_EOM_ramps_spec_AC_cb.currentIndexChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.ramptime_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)

        self.ishg_EOM_AC_current = param_ini.ishg_EOM_AC_dflt # do not group !!
        # # self.jobs_window.mode_EOM_ramps_AC_chk.stateChanged.connect(self.mode_EOMph_changed_meth)
        self.jobs_window.mode_EOM_ramps_AC_chk.stateChanged.connect(self.EOMph_params_ch_meth)
        
        self.jobs_window.voltmax_EOMph_spbx.setValue(self.ishg_EOM_AC_current[0])
        self.jobs_window.steptheo_EOMph_spbx.setValue(self.ishg_EOM_AC_current[2])
        self.jobs_window.voltpi_EOMph_spbx.setValue(self.ishg_EOM_AC_current[3])
        self.jobs_window.voltmax_EOMph_spbx.setValue(self.ishg_EOM_AC_current[4])
        self.jobs_window.deadtimeBeg_us_EOMph_spbx.setValue(self.ishg_EOM_AC_current[-2][1]*1e6) # beg, us
        self.jobs_window.deadtimeEnd_us_EOMph_spbx.setValue(self.ishg_EOM_AC_current[-2][2]*1e6) # end, us
        self.jobs_window.deadtimeLine_us_EOMph_spbx.setValue(self.ishg_EOM_AC_current[-2][3]*1e6) # line, us
        self.jobs_window.mode_EOM_ramps_spec_AC_cb.setCurrentIndex(param_ini.dfltmodesave_fastishg) # dflt
        self.ishg_EOM_AC = param_ini.ishg_EOM_AC_dflt
        self.jobs_window.stop_EOMph_button.setStyleSheet('background-color:coral;')
        self.jobs_window.com_EOMph_button.clicked.connect(self.frstini_EOMph_meth)
        
        self.jobs_window.expert_EOMph_chck.stateChanged.connect(self.expert_EOMph_chck_meth)
        self.jobs_window.expert_EOMph_chck.setChecked(False)
        self.EOMph_afterhere_meth(False) # # just init the correct state of button
        
        self.jobs_window.impose_rmptime_exptime_EOMph_chck.stateChanged.connect(self.impose_rmptime_exptime_EOMph_meth)
        self.jobs_window.impose_rmptime_exptime_EOMph_chck.stateChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.deadtimeBeg_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth) # beg, us
        self.jobs_window.deadtimeEnd_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.deadtimeLine_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)
        self.jobs_window.ramptime_us_EOMph_spbx.setValue(self.ishg_EOM_AC_current[1]*1e6) # sec to us, keep it last !!
        
        self.isec_proc_forishgfill = param_ini.sec_proc_forishgfill
        self.jobs_window.scndProcfill_EOMph_chck.setChecked(bool(self.isec_proc_forishgfill))
        
        self.lower_bound_shgjob = param_ini.lower_bound_shgjob ; self.upper_bound_shgjob = param_ini.upper_bound_shgjob ; self.lwr_bound_exp_shgjob = param_ini.lwr_bound_exp_shgjob; self.upr_bound_exp_shgjob = param_ini.upr_bound_exp_shgjob
        self.save_live_frog_calib = param_ini.save_live_frog_calib; self.save_big_frog_calib = param_ini.save_big_frog_calib ; self.save_excel_frog_calib = param_ini.save_excel_frog_calib
        
        self.jobs_window.simparams_EOMph_button.clicked.connect(self.EOMph_simulate_params_meth)
        
        self.read_sample_rate_spnbx.valueChanged.connect(self.dt_rate_ishg_match_meth)
        self.jobs_window.deadtimeEnd_us_EOMph_spbx.valueChanged.connect(self.dt_rate_ishg_match_meth)
        self.jobs_window.deadtimeBeg_us_EOMph_spbx.valueChanged.connect(self.dt_rate_ishg_match_meth)
        
        self.jobs_window.treatmatlab_chck.stateChanged.connect(self.treatmatlab_chck_after)
        
        ## PI piezo
        self.jobs_window.use_piezo_cmbbx.currentIndexChanged.connect(self.piezo_currIndCh_meth)
        self.use_PI_notimic = param_ini.use_PI_notimic
        # # self.update_Z_values_button.clicked.connect(self.frstini_PI_meth)
        self.jobs_window.redetect_PI_button.clicked.connect(self.redetect_PI_meth)
        self.PI_here = False # default
        if not self.use_PI_notimic:
            self.use_piezo_cmbbx.setCurrentIndex(1) # imic
        else:
            self.piezo_currIndCh_meth(0) # default
        
        ## spectro
        self.spectro_link_button.clicked.connect(self.spectro_conn_disconn_push_meth)
        
        self.spectro_acq_flag_queue = queue.Queue()
    
        # # threads start
        self.thread_scan = self.thread_imic = self.thread_apt = self.thread_spectro = self.thread_shutter = self.thread_newport = self.thread_PI = None # default
        # in the end
        # # self.setupThread_imic() # starts the iMic worker !! forced to start here, because of stdout !!!!
        # # self.setupThread_stageXY() # starts the stageXY worker
        # # self.setupThread_spectro() # starts the spectro worker
        # # self.setupThread_shutter() # starts the shutter worker
        # # self.setupThread_newport() # starts the newport worker
        # # if param_ini.PI_conn_meth != 'usb': # # 'rs232'
        # #     self.setupThread_PI() # starts the PI worker
        self.shutter_is_here = self.esp_here = self.PI_here = self.spectro_connected = self.EOMph_is_connected = self.spectro_toggled_forfastscan = False # init
        
        self.lower_bound_window = param_ini.lower_bound_window;  self.upper_bound_window = param_ini.upper_bound_window; self.lwr_bound_expected = param_ini.lwr_bound_expected; self.upper_bound_expected = param_ini.upper_bound_expected; self.integration_time_spectro_microsec = param_ini.integration_time_spectro_microsec; self.wait_time_spectro_seconds = param_ini.wait_time_spectro_seconds
        self.lambda_bx.setValue(param_ini.wlgth_center_expected_nm/1000) # um
        
        
        ## other
        
        self.disp_img_loaded_meth(r'%s\snakes\snake_eating_labview_inverted.png' % self.path_computer)
        
        self.quick_init_flag = False
        use_logger =  True # False #
        if use_logger:
            # # custom logger
            self.logger_window = QTextEditLogger(self)
            # # Install the custom output stream
            sys.stdout = EmittingStream(textWritten = self.logger_window.normalOutputWritten) # prints
            sys.stderr = EmittingStream(textWritten = self.logger_window.normalOutputWritten) # errors
            self.logger_window.show() # # show the custom logger
            print('Hello', self.path_save[max(0,len(self.path_save)-18):], time.ctime())

        
    def __del__(self):
        # Restore sys.stdout & stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
    
    # # def normalOutputWritten(self, text):
    # #     # for the logging 
    # #     # # self.jobs_window.exec_code_edt.appendPlainText(text)
    # #     plainTxtWidg = self.jobs_window.exec_code_edt
    # #     cursor = plainTxtWidg.textCursor()
    # #     cursor.movePosition(QtGui.QTextCursor.End)
    # #     cursor.insertText(text)
    # #     plainTxtWidg.setTextCursor(cursor)
    # #     plainTxtWidg.ensureCursorVisible()
    
        ## general meth    

    
    @pyqtSlot()    
    def quit_gui_func(self):
        
        if QtWidgets.QMessageBox.question(None, 'Quit software ??', "Are you sure you want to quit?",
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            
            # Restore sys.stdout & stderr
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print(  self.logger_window.widget.toPlainText()) # # comment for not having too many str
            
            print("User chose to close ...")
            
            self._want_to_close = True # True close
            # closing secondary windows
            self.jobs_window._want_to_close = True
            try: self.jobs_window.close() # real close
            except RuntimeError: pass # already closed
                        
            list_processes = [] 
            
            # try:#if 'self.thread_scan' in locals():
            # 
            
            # # if not self.scan_thread_available: # Scan Thread was still in Process
            try:# empty the order queue
                while True:
                    self.queue_com_to_acq.get_nowait() # empty the queue
            except queue.Empty: # if empty, it raises an error (or if worker scan undefined)
                pass
                
            [self.queue_com_to_acq.put([-1]) for i in range(2)] # kill current acq processes of data_acquisition, and the qthread
            
            if not self.scan_thread_available: # Scan Thread was still in Process
                print('Terminating scan process ...')    
                if self.stage_scan_mode != 1: # galvo or static scan
                
                    try: # if a scan wasn't launch, worker_scan is not defined
                        self.kill_worker_scan_signal.emit()
                        list_processes.append('thread scan_galvos')
                    except AttributeError: # if worker_scan is not defined
                        pass
                    
            # worker galvos is disconnected in another meth :
                
            # except:
            #     pass
            # # open('var.txt', 'w').close() # erase
            file_write = open(self.fname_fileparams,'r')
            list_params = file_write.readlines() 
            # # print(list_params)
            file_write.close() # erase
            # # file_write.truncate(0) # erase
            file_write = open(self.fname_fileparams, 'w') # will erase

            file_write.write('offset X (mm)\n') 
            file_write.write(str(self.offsetX_mm_spnbx.value()))
            file_write.write('\noffset Y (mm)\n') 
            file_write.write(str(self.offsetY_mm_spnbx.value()))
            piezo_wrote = False # local init
            posZ_piezo = self.posZ_piezo_edt_1.value() + self.posZ_piezo_edt_2.value()/10 + self.posZ_piezo_edt_3.value()/100 + self.posZ_piezo_edt_4.value()/1000 + self.posZ_piezo_edt_5.value()/10000 # in um
            if type(posZ_piezo) != float: posZ_piezo = posZ_piezo[0]
            if type(posZ_piezo) != float: posZ_piezo = self.posZ_piezo_edt_1.value()
            
            if self.imic_was_init_var: # Imic was initiated (put all to 0 )
                
                file_write.write('\nObj choice\n') 
                file_write.write(str(self.objective_choice.currentIndex()))
                file_write.write('\nfilter_top_choice\n') 
                file_write.write(str(self.filter_top_choice.currentIndex()))
                file_write.write('\nfilter_bottom_choice\n') 
                file_write.write(str(self.filter_bottom_choice.currentIndex()))
                posZ_motor = self.posZ_motor_edt_1.value() + self.posZ_motor_edt_2.value()/10 + self.posZ_motor_edt_3.value()/100  + self.posZ_motor_edt_4.value()/1000 # in mm
                file_write.write('\nZ motor (mm)\n') 
                file_write.write(str(posZ_motor)) 
                if not self.use_PI_notimic: # imic as piezo  or self.PI_here
                    file_write.write('\nZ piezo (um)\n') 
                    file_write.write('.3f' % posZ_piezo) # # be sure it's always in the end
                    piezo_wrote = True
  
                if self.jobs_window.rst_fltr_imic.isChecked(): # reset imic filter
                    if self.filter_top_choice.currentIndex() != param_ini.empty_top_slider_pos:
                        print('putting all filter sliders to default !')
                        self.fltr_top_ch_signal.emit(param_ini.empty_top_slider_pos)
                        time.sleep(0.4)
                    if self.filter_bottom_choice.currentIndex() != param_ini.empty_top_slider_pos:
                        # # self.filter_bottom_choice.setCurrentIndex(param_ini.empty_bottom_slider_pos) # to avoid getting blocked after is iMic is not init
                        self.fltr_bottom_ch_signal.emit(param_ini.empty_bottom_slider_pos)
                        time.sleep(0.6)
                                
            else: # not connected, can terminate the Thread now
                if len(list_params) > 5:
                    file_write.write('\n')
                    for i in range(min(8, len(list_params)-4-2)):
                        file_write.write(list_params[i+4])
            
            if (self.PI_here and not piezo_wrote): # imic as piezo  or self.PI_here
                file_write.write('\nZ piezo (um)\n')
                try: file_write.write('%.3f' % posZ_piezo) # # be sure it's always in the end
                except TypeError: print('posZ_piezo wrong type', posZ_piezo, type(posZ_piezo))
                piezo_wrote = True
            elif not piezo_wrote:
                if len(list_params) > 0:
                    file_write.write('\nZ piezo (um)\n')  
                    file_write.write(list_params[-1]) # previous one   
                
            file_write.close()
                
            if self.stageXY_is_here:
                self.change_scan_dependencies_signal.emit(self.acc_dflt, self.acc_dflt, self.vel_dflt, self.vel_dflt, int(self.yscan_radio.isChecked()) + 1, param_ini.prof_mode, param_ini.jerk_mms3_trapez )
                list_processes.append('stageXY')
                self.close_motorXY_signal.emit(True) # send to worker stageXY to close the motor port
            elif (hasattr(self, 'thread_stageXY') and self.thread_stageXY is not None):  # not connected, can terminate the Thread now
                self.thread_stageXY.quit()
                print('stageXY Terminated.')
            else: # no thread val
                self.thread_stageXY  = None
            
            if (hasattr(self, 'thread_apt') and self.thread_apt is not None): 
                self.worker_apt.close_timer_sign.emit()
                if self.apt_here:
                    list_processes.append('APT')
                    self.worker_apt.clean_apt()
                else:
                    self.thread_apt.quit()
                    print('APT Terminated.')
                 
            if self.shutter_is_here:
                list_processes.append('Shutter')
                self.shutter_send_close() # close the shutter
                self.terminate_shutter_signal.emit()
            elif (hasattr(self, 'thread_shutter') and self.thread_shutter is not None): # not connected, can terminate the Thread now
                self.thread_shutter.quit()
                print('Shutter Terminated.')

            if self.esp_here: #newport
                list_processes.append('newport')
                self.close_newport_signal.emit(True) # send to worker newport to close the motor port
            elif (hasattr(self, 'thread_newport') and self.thread_newport is not None): # not connected, can terminate the Thread now
                self.thread_newport.quit()
                print('Newport Terminated.')
                
            if self.PI_here: # # PI
                list_processes.append('PI')
                self.close_PI_signal.emit(True) # send to worker PI to close the motor
            elif (hasattr(self, 'thread_PI') and self.thread_PI is not None):# not connected, can terminate the Thread now
                self.thread_PI.quit()
                print('PI Terminated.')
                
            # disconnect spectro
            if self.spectro_connected:
                self.spectro_acq_flag_queue.put([-1]) # -1 to kill the worker
                list_processes.append('Spectro') 
            elif (hasattr(self, 'thread_spectro') and self.thread_spectro is not None): # not connected, can terminate the Thread now
                self.thread_spectro.quit()
                print('Spectro Terminated.')

            if (self.imic_was_init_var and self.worker_imic is not None):  # Imic was initiated (put all to 0 )
                self.worker_imic.close_imic_meth(True) # True for final close
                list_processes.append('iMic') # maybe not init, but still have to close the QThread
            elif (hasattr(self, 'thread_imic') and self.thread_imic is not None): # not connected, can terminate the Thread now
                self.thread_imic.quit()
                print('iMic Terminated.')
                
            if self.EOMph_is_connected: # here ?
                self.jobs_window.close_EOMph_button.clicked.emit() # will close the instr
                list_processes.append('EOMph') 
            elif (hasattr(self, 'thread_EOMph') and self.thread_EOMph is not None): # not connected, can terminate the Thread now
                self.thread_EOMph.quit()
                print('EOMph Terminated.')
            else:
                self.thread_EOMph = None
            
            names_workers = ['thread scan_galvos', 'iMic', 'stageXY', 'APT', 'Spectro', 'Shutter', 'newport', 'PI', 'EOMph'] # it's just the list of names, order is important !!
            list_threads = [self.thread_scan, self.thread_imic, self.thread_stageXY, self.thread_apt, self.thread_spectro, self.thread_shutter, self.thread_newport, self.thread_PI, self.thread_EOMph] # it's just the list of names, order is important !!
            if (hasattr(self, 'worker_matlab') and self.thread_matlab is not None):  # quit engine matlab
                self.thread_matlab.quit(); self.thread_matlab.wait(2)
                        
            for i in range(len(list_processes)): # disconnect only the present instruments
                try:
                    msg = self.queue_disconnections.get(block=True, timeout=param_ini.time_out_discon_sec) # block time_out seconds, after raise Exception
                except Exception as e: # 
                    print('err in quit threads, timeout')
                    mm = min(i, len(list_processes)-1)
                    if i < len(list_processes)-1 and mm == len(list_processes)-1:
                        print(e)
                    else:
                        print(list_processes[mm], e)
                else:
                    print('worker %s is done ...' % names_workers[msg])
                    if names_workers[msg] in list_processes: list_processes.remove(names_workers[msg])
                    else: print('strange: %s not in list process' % names_workers[msg])
                    print('Terminating %s Worker ...' % names_workers[msg])
                    st_time = time.time()
                    list_threads[msg].quit()
                    list_threads[msg].wait(param_ini.time_out_quit_qthreads_ms)
                    if (time.time()-st_time) >= param_ini.time_out_quit_qthreads_ms/1000:
                        print('!!!! %s worker timed out!' % names_workers[msg])
                    else:
                        print('%s worker quitted.' % names_workers[msg]) 
                    
            
            i = -1        
            for i in range(len(list_processes)):        
                print('Wait for %s disconnections timed out (%d s)!' % (list_processes[i], param_ini.time_out_discon_sec))
            
            if i > -1:
                print('I will now try to still close the main GUI, but few chances of success since one worker failed (press Ctrl+C) if I keep failing')

            # time.sleep(2)
            sys.exit()
            self.close()
            
    # # @pyqtSlot()      
    # # def wait_gui_quit_meth(self):
    # #     
    # #     max_quit = 3
    # #     self.user_want_to_quit_gui = 1 # notify that user want to quit GUI just after APT imported
    # #     self.try_quit += 1 # after X times, the user is allow to quit without APT imported (if bug)
    # #     print('\n Just wait few seconds that APT is imported (try # %d/%d)!\n' % (self.try_quit, max_quit))
    # #     if self.try_quit > max_quit: # user really want to quit (if APT bugs for instance)
    # #         self.quit_gui_func() # quit meth
    
    def closeEvent(self, event): # method to overwrite the close event, because otherwise the object is no longer available
        # self.deleteLater()
        if self._want_to_close:
            
            super(Main, self).closeEvent(event)
        else:
            event.ignore()
            self.setWindowState(QtCore.Qt.WindowMinimized)
    
    @pyqtSlot()      
    def exec_code_meth(self):
        
        ss = str(self.jobs_window.exec_code_edt.toPlainText())
        print(ss)
        try:
            exec(ss)
        except Exception as e:
            print('ERROR')
            traceback.print_exc()
        else: # # success
            if self.previous_exec_code_str != ss:
                if self.previous_exec_code_str is None:
                    self.previous_exec_code_str = ss
                self.previous_exec_code_str_current = self.previous_exec_code_str
                self.previous_exec_code_str = ss
    
    
    @pyqtSlot()      
    def print_msg_forexec_meth(self):
        
        widg = self.sender()
        if widg == self.jobs_window.print_exec_button: 
            self.jobs_window.exec_code_edt.setPlainText('print(%s)' % self.jobs_window.exec_code_edt.toPlainText())
        elif widg == self.jobs_window.newline_exec_button:     
            self.jobs_window.exec_code_edt.setPlainText('%s\n ' % self.jobs_window.exec_code_edt.toPlainText())
        elif widg == self.jobs_window.implib_exec_button:
            self.jobs_window.exec_code_edt.setPlainText("importlib.reload(sys.modules['modules.%s'])" % self.jobs_window.exec_code_edt.toPlainText())
        elif widg == self.jobs_window.previoustr_exec_button:
            self.jobs_window.exec_code_edt.setPlainText(self.previous_exec_code_str_current)
    
    @pyqtSlot()      
    def qthread_rst_meth(self):
        
        str1 = self.jobs_window.qthread_rst_edt.text()
        
        strdisp = "self.thread_%s.quit();self.thread_%s.wait(); print('ok');self.thread_%s = None;" % ((str1,)*3 )
        
        if str1 == 'EOMph': strdisp+= 'self.frstini_EOMph_meth()'
        elif str1 == 'imic': strdisp+= 'self.frstiniIMIC_meth()'
        elif str1 == 'PI': strdisp+= 'self.frstini_PI_meth()'
        elif str1 == 'stageXY': strdisp+= 'self.redetect_stageXY_meth()' 
        elif str1 == 'shutter': strdisp+= 'self.shutter_using_changed()' 
        elif str1 == 'setupThread_apt': strdisp+= 'self.setupThread_apt()'
        elif str1 == 'spectro': strdisp+= 'self.spectro_conn_disconn_push_meth()'
        elif str1 == 'newport': strdisp+= 'self.redetect_newport_meth()'
        
        self.jobs_window.exec_code_edt.setPlainText(strdisp)
            
    @pyqtSlot()      
    def table_copy_content_meth(self):
        
        selected = self.name_img_table.selectedRanges()
        
        # construction du texte à copier, ligne par ligne et colonne par colonne
        texte = ""
        for i in range(selected[0].topRow(), selected[0].bottomRow() + 1):
            for j in range(selected[0].leftColumn(), selected[0].rightColumn() + 1):
                try:
                    texte += self.name_img_table.item(i, j).text() + "\t"
                except AttributeError:
                    # quand une case n'a jamais été initialisée
                    texte += "\t"
            texte = texte[:-1] + "\n"  # le [:-1] élimine le '\t' en trop
        
        # enregistrement dans le clipboard # ctrl+C
        QtGui.QApplication.clipboard().setText(texte)
    
    @pyqtSlot() 
    def quick_init_meth(self):
        self.quick_init_flag = True
        self.init_imic_button.animateClick()
            
        ## imic buttons
    
    @pyqtSlot()      
    def frstiniIMIC_meth(self):
        # called by first push on init
        
        # # don't know why, have to rewire this temporally
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        self.setupThread_imic() # init
        # #  rewire 
        time.sleep(0.8)
        self.init_imic_button.clicked.emit() # will try to init iMIC
    
    @pyqtSlot(bool)    
    def imic_was_init(self, is_init):
        
        # even if fail and user does not want to retry
        if sys.stdout == sys.__stdout__:
            sys.stdout = EmittingStream(textWritten = self.logger_window.normalOutputWritten) # prints
        if sys.stderr == sys.__stderr__:
            sys.stderr = EmittingStream(textWritten = self.logger_window.normalOutputWritten)
        
        if is_init: # was init successfully
            self.posFilt_top = self.posFilt_bottom ='0'
            self.update_Z_values_button.clicked.connect(self.worker_imic.update_Z_values_meth)
            if not self.use_PI_notimic: # use imic, not PI
                self.update_Z_values_button.clicked.connect(self.worker_imic.get_z_piezo_meth)
            self.objective_choice.setEnabled(True)
            self.filter_top_choice.setEnabled(True)
            self.filter_bottom_choice.setEnabled(True)
            self.posZ_motor_edt_1.setEnabled(True)
            self.posZ_motor_edt_2.setEnabled(True)
            self.posZ_motor_edt_3.setEnabled(True)
            self.posZ_motor_edt_4.setEnabled(True)
            if not self.use_PI_notimic: # use imic, not PI #self.jobs_window.use_piezo_cmbbx.currentIndex() == 1: # use iMic
                self.posZ_piezo_edt_1.setEnabled(True)
                self.posZ_piezo_edt_2.setEnabled(True)
                self.posZ_piezo_edt_3.setEnabled(True)
                self.posZ_piezo_edt_4.setEnabled(True)
                self.posZ_piezo_edt_5.setEnabled(True)
            self.imic_was_init_var = 1
            self.jobs_window.only_motorZ_chck.setEnabled(True)
            if self.prev_pos_imic_chck.isChecked():
                self.prev_pos_imic_meth()
            
        else: # error
            if QtWidgets.QMessageBox.question(None, 'try iMic again ?', "Init failed : you have to turn ON iMic, when ok do you want to try again (try at least twice) ?",
                                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
                # # self.worker_imic.close_imic_meth(False) # not final close
                self.thread_imic.quit() # quit the worker (mandatory)
                self.thread_imic.wait(5) # sec
                time.sleep(0.8)
                self.setupThread_imic() # reload the worker (mandatory)
                # # self.worker_imic.open_com()
                self.init_imic_button.animateClick() # to avoid direct call
                
                # # self.worker_imic.imic_ini()                
            # # else:
            # #     return    
        if self.quick_init_flag: self.home_stage_button.animateClick()
        
    @pyqtSlot()      
    def z_motor_edt1_changed(self):
        # only to be consistent with other decimal functions
        
        pos_mot1 = self.posZ_motor_edt_1.value()
        pos_mot2 = self.posZ_motor_edt_2.value()
        pos_mot3 = self.posZ_motor_edt_3.value()
        pos_mot4 = self.posZ_motor_edt_4.value()
        
        self.z_motor_changed(pos_mot1, pos_mot2, pos_mot3, pos_mot4) # call the move function
    
    @pyqtSlot()      
    def z_motor_edt2_changed(self):
        
        pos_mot1 = self.posZ_motor_edt_1.value()
        pos_mot2 = self.posZ_motor_edt_2.value()
        pos_mot3 = self.posZ_motor_edt_3.value()
        pos_mot4 = self.posZ_motor_edt_4.value()
    
        # print('self.posZ_motor_edt_2_current', self.posZ_motor_edt_2_current)
        if (self.posZ_motor_edt_2_current == 9 and pos_mot2 == 10):
            
            if  pos_mot1 == self.posZ_motor_edt_1.maximum():
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_2.setValue(9)
                # # self.posZ_motor_edt_2.blockSignals(False)
                pos_mot2 = 9
            else:   
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_1.blockSignals(True)
                # # self.posZ_motor_edt_2.setValue(0) 
                # # self.posZ_motor_edt_1.setValue(self.posZ_motor_edt_1.value()+1)
                # # self.posZ_motor_edt_2.blockSignals(False)
                # # self.posZ_motor_edt_1.blockSignals(False)
                pos_mot2 = 0
                pos_mot1 += 1
                
        elif (self.posZ_motor_edt_2_current == 0 and  pos_mot2 == -1):
            
            if pos_mot1 == self.posZ_motor_edt_1.minimum():
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_2.setValue(0)
                # # self.posZ_motor_edt_2.blockSignals(False)
                pos_mot2 = 0
            else:
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_1.blockSignals(True)
                # # self.posZ_motor_edt_1.setValue(self.posZ_motor_edt_1.value()-1)
                # # self.posZ_motor_edt_2.setValue(9)
                # # self.posZ_motor_edt_2.blockSignals(False)
                # # self.posZ_motor_edt_1.blockSignals(False)
                pos_mot2 = 9
                pos_mot1 -= 1
                
        self.posZ_motor_edt_2_current = pos_mot2
        
        self.z_motor_changed(pos_mot1, pos_mot2, pos_mot3, pos_mot4) # call the move function
    
    @pyqtSlot()      
    def z_motor_edt3_changed(self):
        
        pos_mot1 = self.posZ_motor_edt_1.value()
        pos_mot2 = self.posZ_motor_edt_2.value()
        pos_mot3 = self.posZ_motor_edt_3.value()
        pos_mot4 = self.posZ_motor_edt_4.value()
    
        if (self.posZ_motor_edt_3_current == 9 and pos_mot3 == 10):
            
            if  pos_mot2 == self.posZ_motor_edt_2.maximum():
                # # self.posZ_motor_edt_3.blockSignals(True)
                # # self.posZ_motor_edt_3.setValue(9)
                pos_mot3 = 9
                # # self.posZ_motor_edt_3.blockSignals(False)
            else:   
                # # self.posZ_motor_edt_3.blockSignals(True)
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_3.setValue(0) 
                # # self.posZ_motor_edt_2.setValue(self.posZ_motor_edt_2.value()+1)
                pos_mot2 += 1
                pos_mot3 = 0
                # # self.posZ_motor_edt_3.blockSignals(False)
                # # self.posZ_motor_edt_2.blockSignals(False)
                
        elif (self.posZ_motor_edt_3_current == 0 and  pos_mot3 == -1):
            
            if pos_mot2 == self.posZ_motor_edt_2.minimum():
                # # self.posZ_motor_edt_3.blockSignals(True)
                # # self.posZ_motor_edt_3.setValue(0)
                pos_mot3 = 0
                # # self.posZ_motor_edt_3.blockSignals(False)
            else:
                # # self.posZ_motor_edt_3.blockSignals(True)
                # # self.posZ_motor_edt_2.blockSignals(True)
                # # self.posZ_motor_edt_2.setValue(self.posZ_motor_edt_2.value()-1)
                # # self.posZ_motor_edt_3.setValue(9)
                pos_mot2 -= 1
                pos_mot3 = 9
                # # self.posZ_motor_edt_3.blockSignals(False)
                # # self.posZ_motor_edt_2.blockSignals(False)
                
        self.posZ_motor_edt_3_current = pos_mot3
        
        self.z_motor_changed(pos_mot1, pos_mot2, pos_mot3, pos_mot4) # call the move function
        
    @pyqtSlot()      
    def z_motor_edt4_changed(self):
        
        pos_mot1 = self.posZ_motor_edt_1.value()
        pos_mot2 = self.posZ_motor_edt_2.value()
        pos_mot3 = self.posZ_motor_edt_3.value()
        pos_mot4 = self.posZ_motor_edt_4.value()
        
        if (self.posZ_motor_edt_4_current == 9 and pos_mot4 == 10):
            
            if (pos_mot3 == (self.posZ_motor_edt_3.maximum()-1) and pos_mot2 == self.posZ_motor_edt_2.maximum()): # pos2 = 9 & pos1 = 21
                 # self.posZ_motor_edt_4.blockSignals(True)
                 # self.posZ_motor_edt_4.setValue(9)
                 # self.posZ_motor_edt_4.blockSignals(False)
                 pos_mot4 = 9
                 
            else:# pos2 < 9 | pos1 < 21
                # self.posZ_motor_edt_4.blockSignals(True)
                # self.posZ_motor_edt_4.setValue(0)
                # self.posZ_motor_edt_3.setValue(self.posZ_motor_edt_3.value()+1)
                # self.posZ_motor_edt_4.blockSignals(False)
                pos_mot3 += 1
                pos_mot4 = 0
            
        elif (self.posZ_motor_edt_4_current == 0 and  pos_mot4 == -1):
            
            if (pos_mot3 == (self.posZ_motor_edt_3.minimum()+1) and pos_mot2 == self.posZ_motor_edt_2.minimum()): # pos2 = 0 & pos1 = 0
                # self.posZ_motor_edt_4.blockSignals(True)
                # self.posZ_motor_edt_4.setValue(0)
                # self.posZ_motor_edt_4.blockSignals(False)
                pos_mot4 = 0
                
            else: # pos2 > 0 | pos1 > 0
                # self.posZ_motor_edt_4.blockSignals(True)
                # self.posZ_motor_edt_3.setValue(self.posZ_motor_edt_3.value()-1) 
                # self.posZ_motor_edt_4.setValue(9)
                # self.posZ_motor_edt_4.blockSignals(False)
                pos_mot3 -= 1
                pos_mot4 = 9
        
        self.posZ_motor_edt_4_current = pos_mot4
        
        self.z_motor_changed(pos_mot1, pos_mot2, pos_mot3, pos_mot4) # call the move function
           
    # unmovable a priori because depends on Ui function and button
    def z_motor_changed(self, pos_mot1, pos_mot2, pos_mot3, pos_mot4):
        
        self.posZ_motor = pos_mot1 + pos_mot2/10 + pos_mot3/100 + pos_mot4/1000 # in mm
        
        self.motorZ_move_signal.emit(self.posZ_motor) # send a signal to worker imic (connexion defined in imic thread function)
    
    @pyqtSlot()      
    def z_piezo_edt1_changed(self):
        # only to be consistent with other decimal functions
        
        posZ_piezo_1 = self.posZ_piezo_edt_1.value()
        posZ_piezo_2 = self.posZ_piezo_edt_2.value()
        posZ_piezo_3 = self.posZ_piezo_edt_3.value()
        posZ_piezo_4 = self.posZ_piezo_edt_4.value()
        posZ_piezo_5 = self.posZ_piezo_edt_5.value()

        self.z_piezo_changed(posZ_piezo_1, posZ_piezo_2, posZ_piezo_3, posZ_piezo_4, posZ_piezo_5) # call the move function
     
    @pyqtSlot()      
    def z_piezo_edt2_changed(self):   
        cond = self.posZ_piezo_edt_1.value() <= self.posZ_piezo_edt_1.minimum()
        self.posZ_piezo_edt_2_current = self.z_piezo_edt_util(self.posZ_piezo_edt_2_current, self.posZ_piezo_edt_2, self.posZ_piezo_edt_1, cond)
        
    @pyqtSlot()      
    def z_piezo_edt3_changed(self):
        
        cond = self.posZ_piezo_edt_2.value() <= self.posZ_piezo_edt_2.minimum()
        self.posZ_piezo_edt_3_current = self.z_piezo_edt_util(self.posZ_piezo_edt_3_current, self.posZ_piezo_edt_3, self.posZ_piezo_edt_2, cond)
        
    @pyqtSlot()      
    def z_piezo_edt4_changed(self):
        
        cond = self.posZ_piezo_edt_3.value() <= self.posZ_piezo_edt_3.minimum()
        self.posZ_piezo_edt_4_current = self.z_piezo_edt_util(self.posZ_piezo_edt_4_current, self.posZ_piezo_edt_4, self.posZ_piezo_edt_3, cond)
        
        
    @pyqtSlot()      
    def z_piezo_edt5_changed(self):
        
        cond = (self.posZ_piezo_edt_4.value() <= (self.posZ_piezo_edt_4.maximum()-1) and self.posZ_piezo_edt_3.value() >= self.posZ_piezo_edt_3.maximum()-1) # for put it to 0
        self.posZ_piezo_edt_5_current = self.z_piezo_edt_util(self.posZ_piezo_edt_5_current, self.posZ_piezo_edt_5, self.posZ_piezo_edt_4, cond)
        
    def z_piezo_edt_util(self, posZ_piezo_edt_current, posZ_piezo_edt, posZ_piezo_edt_bel, cond):
        
        posZ_piezo_1 = self.posZ_piezo_edt_1.value() # um
        posZ_piezo_2 = self.posZ_piezo_edt_2.value() # um
        posZ_piezo_3 = self.posZ_piezo_edt_3.value() # um
        posZ_piezo_4 = self.posZ_piezo_edt_4.value() # um
        posZ_piezo_5 = self.posZ_piezo_edt_5.value() # um
        
        posZ_piezo = posZ_piezo_edt.value()
        posZ_piezo_bel = posZ_piezo_edt_bel.value()
        
        if (posZ_piezo_edt_current == 9 and posZ_piezo == 10):
            
            if cond:
                 # # self.posZ_piezo_edt_3.blockSignals(True)
                 # # self.posZ_piezo_edt_3.setValue(9)
                 # # self.posZ_piezo_edt_3.blockSignals(False)
                 posZ_piezo = 9
            else:
                # self.posZ_piezo_edt_3.blockSignals(True)
                # # self.posZ_piezo_edt_2.blockSignals(True)
                # self.posZ_piezo_edt_3.setValue(0)
                # self.posZ_piezo_edt_2.setValue(self.posZ_piezo_edt_2.value()+1)
                # self.posZ_piezo_edt_3.blockSignals(False)
                # # self.posZ_piezo_edt_2.blockSignals(False)
                posZ_piezo = 0
                posZ_piezo_bel += 1
                
        elif (posZ_piezo_edt_current == 0 and posZ_piezo == -1):
            
            if cond:
                # # self.posZ_piezo_edt_3.blockSignals(True)
                # # self.posZ_piezo_edt_3.setValue(0)
                # # self.posZ_piezo_edt_3.blockSignals(False)
                posZ_piezo = 0
            else:
                # self.posZ_piezo_edt_3.blockSignals(True)
                # # # self.posZ_piezo_edt_2.blockSignals(True)
                # # self.posZ_piezo_edt_3.setValue(9)
                # # self.posZ_piezo_edt_2.setValue(self.posZ_piezo_edt_2.value()-1)   
                # # self.posZ_piezo_edt_3.blockSignals(False)
                # # # self.posZ_piezo_edt_2.blockSignals(False)   
                posZ_piezo = 9
                posZ_piezo_bel -= 1
        
        self.z_piezo_changed(posZ_piezo_1, posZ_piezo_2, posZ_piezo_3, posZ_piezo_4, posZ_piezo_5) # call the move function
        return posZ_piezo

    
    def z_piezo_changed(self, posZ_piezo_1, posZ_piezo_2, posZ_piezo_3, posZ_piezo_4, posZ_piezo_5):
        # # self.posZ_piezo = round((self.posZ_piezo_edt_1.value() + self.posZ_piezo_edt_2.value()/10 + self.posZ_piezo_edt_3.value()/100)*100)/100/1000 # in mm
        self.posZ_piezo = float(round(Decimal(posZ_piezo_1 + posZ_piezo_2/10 + posZ_piezo_3/100 + posZ_piezo_4/1000 + posZ_piezo_5/10000), 4)/1000)  # in mm
        # # print('posPZ = ', self.posZ_piezo)
        # # print('posPZ3 = ', self.posZ_piezo_edt_3.value())
        self.piezoZ_move_signal.emit(self.posZ_piezo) # send a signal to worker imic (connexion defined in imic thread function)
        

    @pyqtSlot() 
    def put_obj_zero_meth(self):
        
        self.motorZ_put_to_zero = 0
        self.piezoZ_put_to_zero = 0
        
        cond1 = (self.posZ_motor_edt_1.value() == 0 and self.posZ_motor_edt_2.value() == 0 and self.posZ_motor_edt_3.value() == 0) # not motor 4
        
        if (not self.use_PI_notimic): # # use imic piezo
            cond1 = cond1 and (self.posZ_piezo_edt_1.value() == 0 and self.posZ_piezo_edt_2.value() == 0 and self.posZ_piezo_edt_3.value() == 0 and self.posZ_piezo_edt_4.value() == 0 and self.posZ_piezo_edt_5.value() == 0)
        
        if cond1: # # all is 0
            
            # print('0 all')
            self.obj_choice_changed()
            
        else:
            
            if (not (self.use_PI_notimic) and (not (self.posZ_piezo_edt_1.value() == 0 and self.posZ_piezo_edt_2.value() == 0 and self.posZ_piezo_edt_3.value() == 0 and self.posZ_piezo_edt_4.value() == 0 and self.posZ_piezo_edt_5.value() == 0))):
                self.progress_piezo_signal.connect(self.obj_choice_changed) # temporary, one shot
                self.posZ_piezo_edt_1.setValue(0)
                self.posZ_piezo_edt_2.setValue(0)
                self.posZ_piezo_edt_3.setValue(0)
                self.posZ_piezo_edt_4.setValue(0)
                self.posZ_piezo_edt_5.setValue(0)
                self.piezoZ_put_to_zero = 1
  
            if not (self.posZ_motor_edt_1.value() == 0 and self.posZ_motor_edt_2.value() == 0 and self.posZ_motor_edt_3.value() == 0):
                if (self.imic_was_init_var and self.worker_imic is not None):  self.worker_imic.progress_motor_signal.connect(self.obj_choice_changed) # temporary, one shot
                self.posZ_motor_edt_1.setValue(0)
                self.posZ_motor_edt_2.setValue(0)
                self.posZ_motor_edt_3.setValue(0)
                self.posZ_motor_edt_4.setValue(0)
                self.motorZ_put_to_zero = 1
        
    @pyqtSlot()    
    def obj_choice_changed(self):
        
        # print('in obj_changed')
        self.obj_choice_prev = self.obj_choice
        self.obj_choice = self.objective_choice.currentIndex()
        
        if (self.obj_choice == 2 or (self.obj_choice_prev == 2 and self.obj_choice == 0)): # pos 3 or pos3 going to 0 (danger)
            if self.obj_choice == 2:
                pos=1 
            elif (self.obj_choice_prev == 2 and self.obj_choice == 0):
                pos=3
            if QtWidgets.QMessageBox.question(None, 'obj. pos correct ?', 'Is the pos #%d turret empty, or with a small objective (not to scratch to the back of the stage) ??' % pos, QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No:
                return # outside function
        
        if self.imic_was_init_var:
            self.obj_choice_signal.emit(self.obj_choice) # send a signal to worker imic (connexion defined in imic thread function)
        
        if self.motorZ_put_to_zero:
            self.worker_imic.progress_motor_signal.disconnect(self.obj_choice_changed)
        if self.piezoZ_put_to_zero:
            self.progress_piezo_signal.disconnect(self.obj_choice_changed)
    
    @pyqtSlot()    
    def fltr_top_changed(self):
        
        posFilt_top = self.filter_top_choice.currentIndex()
        
        self.fltr_top_ch_signal.emit(posFilt_top) # send a signal to worker imic (connexion defined in imic thread function)
        
        # # if (not self.scan_thread_available or posFilt_top == 0): # during a scan
        self.filter_top_choice_curr_index = self.filter_top_choice.currentIndex() 
        
        self.posFilt_top = str(posFilt_top) # # number of filtr
        if self.filter_top_choice_curr_index == param_ini.mddle_top_slider_pos: 
            self.filter_top_choice.setEditable(True); self.filter_top_choice.setCurrentText(param_ini.str_top_slider_posmiddle) # changeable
        else: self.filter_top_choice.setEditable(False)
    
    @pyqtSlot()    
    def fltr_bottom_changed(self): 
    
        posFilt_bottom = self.filter_bottom_choice.currentIndex()
        
        self.fltr_bottom_ch_signal.emit(posFilt_bottom) # send a signal to worker imic (connexion defined in imic thread function)  
        self.posFilt_bottom = str(posFilt_bottom) # # number of filtr
        self.filter_bot_choice_curr_index = self.filter_bottom_choice.currentIndex() 

    @pyqtSlot()    
    def prev_pos_imic_meth(self):
        
        if self.prev_pos_imic_chck.isChecked():
            pp=os.getcwd()
            if pp != os.path.normpath(self.path_save): # importing thorlabs
                print(pp)
                return
            file_param = open(self.fname_fileparams,'r')
            
            list_params = file_param.readlines() 
            file_param.close()
            
            if len(list_params) >= 3:
                self.offsetX_mm_spnbx.setValue(float(list_params[1])) # set the offset
                self.offsetY_mm_spnbx.setValue(float(list_params[3]))
                
            if self.imic_was_init_var:
                
                self.prev_pos_imic_chck.setChecked(False)
                
                if len(list_params) <= 5:
                    print('imic not recorded')
                else:
                    if QtWidgets.QMessageBox.question(None, 'set iMic previous ?', "You will set obj. %d to %.1f mm : continue ??" % (int(list_params[5]), float(list_params[11])),
                                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                        QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
                    
                        self.objective_choice.setCurrentIndex(int(list_params[5]))
                        self.filter_top_choice.setCurrentIndex(int(list_params[7]))
                        self.filter_bottom_choice.setCurrentIndex(int(list_params[9]))
                        self.posZ_motor = float(list_params[11])
                        self.motorZ_move_signal.emit(self.posZ_motor)
                        if (len(list_params) > 11 and (not self.use_PI_notimic)): # imic, or PI but it must be here  or self.PI_here
                        #  # len(list_params) == 11 if piezo not saved because mtr piezo was not here at last closing
                            self.posZ_piezo = float(list_params[13])/1000 # um to mm
                            self.piezoZ_move_signal.emit(self.posZ_piezo) # in mm
                            
            if (self.PI_here and self.use_PI_notimic): 
                num = 13
                if len(list_params) >= num:
                    self.posZ_piezo = float(list_params[num])/1000 # um to mm
                    self.piezoZ_move_signal.emit(self.posZ_piezo) # in mm
    
    def mtrZ_setVal_util(self, motor_Z_to_set):
        # # not a slot
        
        pos1 = round(float(jobs_scripts.truncate(motor_Z_to_set, 0)))
        pos2 = round((float(jobs_scripts.truncate(motor_Z_to_set, 1)) - float(jobs_scripts.truncate(motor_Z_to_set, 0)))*10)
        pos3 = round((float(jobs_scripts.truncate(motor_Z_to_set, 2)) - float(jobs_scripts.truncate(motor_Z_to_set, 1)))*100)
        pos4 = round((float(jobs_scripts.truncate(motor_Z_to_set, 3)) - float(jobs_scripts.truncate(motor_Z_to_set, 2)))*1000)
        self.posZ_motor_edt_1.setValue(pos1)
        self.posZ_motor_edt_2.setValue(pos2)
        self.posZ_motor_edt_3.setValue(pos3)
        self.posZ_motor_edt_4.setValue(pos4)
        
        if self.posZ_motor_edt_4.value() == 10:
            self.posZ_motor_edt_4.setValue(0)
            self.posZ_motor_edt_3.setValue(self.posZ_motor_edt_3.value()+1)
    
    @pyqtSlot(float)    
    def motorZ_changeDispValue_meth(self, motor_Z_to_set):
        
        self.posZ_motor_edt_1.blockSignals(True)
        self.posZ_motor_edt_2.blockSignals(True)
        self.posZ_motor_edt_3.blockSignals(True)
        self.posZ_motor_edt_4.blockSignals(True)
        
        self.posZ_motor = motor_Z_to_set
        self.mtrZ_setVal_util(motor_Z_to_set)
        
        self.posZ_motor_edt_1.blockSignals(False)
        self.posZ_motor_edt_2.blockSignals(False)
        self.posZ_motor_edt_3.blockSignals(False)
        self.posZ_motor_edt_4.blockSignals(False)
        
        print('MotorZ DispValue updated') # #  : ', pos1, pos2, pos3, pos4)
        
    @pyqtSlot(float)    
    def piezoZ_changeDispValue_meth(self, piezo_Z_to_set):
        
        self.posZ_piezo_edt_1.blockSignals(True)
        self.posZ_piezo_edt_2.blockSignals(True)
        self.posZ_piezo_edt_3.blockSignals(True)
        self.posZ_piezo_edt_4.blockSignals(True)
        self.posZ_piezo_edt_5.blockSignals(True)
        self.posZ_piezo = max(piezo_Z_to_set, 0)

        self.piezoZ_setVal_util(self.posZ_piezo)
        
        # # if self.posZ_piezo_edt_3.value() == 10:
        # #     self.posZ_piezo_edt_3.setValue(0)
        # #     self.posZ_piezo_edt_2.setValue(self.posZ_piezo_edt_2.value()+1)
        
        self.posZ_piezo_edt_1.blockSignals(False)
        self.posZ_piezo_edt_2.blockSignals(False)
        self.posZ_piezo_edt_3.blockSignals(False)
        self.posZ_piezo_edt_4.blockSignals(False)
        self.posZ_piezo_edt_5.blockSignals(False)
        print('PiezoZ DispValue updated')
    
    def piezoZ_setVal_util(self, piezo_Z_to_set):
        self.posZ_piezo_edt_1.setValue(round(float(jobs_scripts.truncate(piezo_Z_to_set*1000, 0)))) # in um
        self.posZ_piezo_edt_2.setValue(round((float(jobs_scripts.truncate(piezo_Z_to_set*1000, 1)) - float(jobs_scripts.truncate(piezo_Z_to_set*1000, 0)))*10))
        # print('digit 2 =', round((float(jobs_scripts.truncate(piezo_Z_to_set*1000, 1)) - float(jobs_scripts.truncate(piezo_Z_to_set*1000, 0)))*10))
        self.posZ_piezo_edt_3.setValue(round((float(jobs_scripts.truncate(piezo_Z_to_set*1000, 2)) - float(jobs_scripts.truncate(piezo_Z_to_set*1000, 1)))*100))
        self.posZ_piezo_edt_4.setValue(round((float(jobs_scripts.truncate(piezo_Z_to_set*1000, 3)) - float(jobs_scripts.truncate(piezo_Z_to_set*1000, 2)))*1000))
        self.posZ_piezo_edt_5.setValue(round((float(jobs_scripts.truncate(piezo_Z_to_set*1000, 4)) - float(jobs_scripts.truncate(piezo_Z_to_set*1000, 3)))*10000))    
        
    @pyqtSlot(int)    
    def imic_objTurret_changed_meth(self, val):
        # # just display the value measured from imic
        
        self.objective_choice.blockSignals(True)
        self.objective_choice.setCurrentIndex(val)
        self.objective_choice.blockSignals(False)
        
    @pyqtSlot(int)    
    def imic_fltr_top_changed_meth(self, val):
        # # just display the value measured from imic
        
        self.filter_top_choice.blockSignals(True)
        self.filter_top_choice.setCurrentIndex(val)
        self.filter_top_choice.blockSignals(False)
    
    @pyqtSlot(int)    
    def imic_fltr_bottom_changed_meth(self, val):
        # # just display the value measured from imic
        
        self.filter_bottom_choice.blockSignals(True)
        self.filter_bottom_choice.setCurrentIndex(val)
        self.filter_bottom_choice.blockSignals(False)
    
    @pyqtSlot(int)    
    def max_widgZ_mm_changed(self, val):
        
        val = min(param_ini.max_pos_Z_motor, val)
        self.posZ_motor_edt_1.setMaximum(round(val))
        self.jobs_window.strt_Z_stack_spnbx.setMaximum(round(val))
        self.jobs_window.end_Z_stack_spnbx.setMaximum(round(val))
        
        ##  PI 
    
    @pyqtSlot(int)
    def piezo_currIndCh_meth(self, ind):
        # # called by jobs_window.use_piezo_cmbbx
        use_PI_notimic_old = self.use_PI_notimic
        
        if ind == 0: # PI
            self.use_PI_notimic = True
            self.posZ_piezo_edt_1.setMaximum(param_ini.max_range_PI*1000-1)
        elif ind == 1: # imic
            self.use_PI_notimic = False
            self.posZ_piezo_edt_1.setMaximum(param_ini.max_range_pz_imic*1000-1)
        if self.use_PI_notimic != use_PI_notimic_old: # change
            print('\n you should re-init the iMic and PI thread, or connect by hand the good signals !')
    
    @pyqtSlot(bool)        
    def PI_imported_after_meth(self, here_bool):
      
        self.PI_here =  here_bool
        if (self.PI_here and self.jobs_window.use_piezo_cmbbx.currentIndex() == 0): # use PI
            self.posZ_piezo_edt_1.setEnabled(True)
            self.posZ_piezo_edt_2.setEnabled(True)
            self.posZ_piezo_edt_3.setEnabled(True)
            self.posZ_piezo_edt_4.setEnabled(True)
            self.posZ_piezo_edt_5.setEnabled(True)
            self.update_Z_values_button.clicked.connect(self.worker_PI.getpos_motor_PI)
            
    
    @pyqtSlot()
    def frstini_PI_meth(self):
        self.quick_init_button.clicked.disconnect(self.frstini_PI_meth)
        if (not hasattr(self, 'thread_PI') or self.thread_PI is None):
            # # if param_ini.PI_conn_meth != 'usb': # # 'rs232'
            self.setupThread_PI() # starts the PI worker
       
    @pyqtSlot()
    def redetect_PI_meth(self):
        
        if (not hasattr(self, 'thread_PI') or self.thread_PI is None):
            # # if param_ini.PI_conn_meth != 'usb': # # 'rs232'
            self.setupThread_PI() # starts the PI worker
        else:
            print('trying to redect PI ...')
            self.close_PI_signal.emit(False) # send to worker PI to close the motor port
            # # msg = self.queue_disconnections.get(block=True, timeout=param_ini.time_out_discon_sec) # empty the queue 
            self.thread_PI.started.emit() # to call open_lib, faking a start
            
    @pyqtSlot()    
    def after_pmt_changed(self):
        
        # print('detected changes in PMT...')
        
        # if self.pmt1_chck.isChecked():
        #     if self.pmt2_chck.isChecked():
        #         
        #         self.pmt_channel = 2 # 1 for 1 channel ai0, 2 for 2 channels, 0 for ai1 only
        #         
        #     else:
        #         self.pmt_channel = 1 # only 1st pmt
        #         
        # else: # PMT 1 not checked
        #     if self.pmt2_chck.isChecked():
        #         self.pmt_channel = 0 # only 2nd pmt
        #     else:
        #         self.pmt_channel = -1 # no PMT channel
        
        pmt_check_list = [self.pmt1_chck, self.pmt2_chck, self.pmt3_chck, self.pmt4_chck, self.pmt5_chck, self.pmt6_chck]
        
        self.pmt_channel_list = []
        
        for k in range(0, self.nb_pmt_checkable):
            
            if pmt_check_list[k].isChecked():
                self.pmt_channel_list.append(1)
            else:
                self.pmt_channel_list.append(0)
        
        if (self.mode_scan_box.currentIndex() in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1): # # callback galvos
            self.szarray_readAI_willchange_meth()
            
        print('PMT' , self.pmt_channel_list)
                
        ## stage XY buttons
        
    @pyqtSlot(bool)   
    def stageXY_imported_after_meth(self, imp_apt):
        # importation of stageXY is linked to this method by Signal
        
        if imp_apt:
            self.setupThread_apt() # starts the APT worker, old method
            # !! interfere with stage XY !!!!
        
        self.stageXY_is_here = 1
        
    @pyqtSlot()    
    def posX_changed(self): 
    
        if self.chck_homed:
            posX00 = self.posX
            self.posX = self.posX_edt.value()
            
            if (self.stage_scan_mode != 1 or self.scan_thread_available == 1): # no scan stage running, or not a scan stage at all
        # 1 important
                run_str = 'now'

                if (self.transXY_imgplane_anlggalv_chck.isChecked()): # # anlg galvos + transf. coordinates
                    self.posY = self.posY_edt.value() 
                    self.posX += (self.posX-posX00)*math.cos(self.rotate) ##+ self.posY*math.sin(self.rotate)
                    self.posY += -(self.posX-posX00)*math.sin(self.rotate) ## + self.posY*math.cos(self.rotate)
                    # # print('\ndg', self.posX, self.posY)
                    self.move_motorY_signal.emit(self.posY)
                
                self.move_motorX_signal.emit(self.posX) 
                
            else: # scan stage running
                if self.stgscn_livechgX_chck.isChecked(): 
                    run_str = 'sent to stage scan'
                else:
                    run_str = 'will be set later'
                try:# empty the queue, because otherwise if you send several move order like this, the motor will execute them at the next scan in a row...
                    while True:
                        self.queue_moveX_inscan.get_nowait() # empty the queue
                except queue.Empty: # if empty, it raises an error 
                    pass
                
                if self.stgscn_livechgX_chck.isChecked(): # live change
                
                    paquetX = [self.posX, 1]
                    
                else: # change only at beginning of scans
                    paquetX = [self.posX, 0]
                    
                self.queue_moveX_inscan.put(paquetX)
            
            # self.queue_posX.put(self.posX)
            # 
            # print('sent order to move X to %f' % self.posX)
            # self.worker_apt.move_motor_X()
            # # WARNING : without this command, it was not working well
            print('posX imposed manually = %g, %s' % (self.posX, run_str))
            
        else:
            print('in posX_changed, motor not yet initialised')
    
    @pyqtSlot()    
    def posY_changed(self): 
    
        if self.chck_homed:
            posY00 = self.posY
            self.posY = self.posY_edt.value()
            
            if (self.stage_scan_mode != 1 or self.scan_thread_available == 1): # no scan stage running, or not a scan stage at all
        # 1 important
                run_str = 'now'
                    
                if (self.transXY_imgplane_anlggalv_chck.isChecked()): # # anlg galvos + transf. coordinates
                    self.posX = self.posX_edt.value() 
                    self.posX += (self.posY-posY00)*math.sin(self.rotate)
                    self.posY += (self.posY-posY00)*math.cos(self.rotate)
                    self.move_motorX_signal.emit(self.posX)
                    
                self.move_motorY_signal.emit(self.posY) 
            else:
                if self.stgscn_livechgY_chck.isChecked(): 
                    run_str = 'sent to stage scan'
                else:
                    run_str = 'will be set later'
                try:# empty the queue, because otherwise if you send several move order like this, the motor will execute them at the next scan in a row...
                    while True:
                        self.queue_moveY_inscan.get_nowait() # empty the queue
                except queue.Empty: # if empty, it raises an error 
                    pass
                
                if self.stgscn_livechgY_chck.isChecked(): # live change
                
                    paquetY = [self.posY, 1]
                    
                else: # change only at beginning of scans
                    paquetY = [self.posY, 0]
                    
                self.queue_moveY_inscan.put(paquetY)
            
            print('posY imposed manually = %g, %s' % (self.posY, run_str))
    
            # self.queue_posX.put(self.posX)
            # 
            # print('sent order to move X to %f' % self.posX)
            # self.worker_apt.move_motor_X()
            # # WARNING : without this command, it was not working well
        else:
            print('in posY_changed, motor not yet initialised')

    @pyqtSlot(float)    
    def posX_indic_real(self, posXreal): 
    
        self.posX_edt.valueChanged.disconnect(self.posX_changed) # avoid infinite connection loops
        self.posX_edt.setValue(posXreal)
        self.posX_edt.valueChanged.connect(self.posX_changed) # reconnect
    
    
    @pyqtSlot(float)    
    def posY_indic_real(self, posYreal): 
    
        self.posY_edt.valueChanged.disconnect(self.posY_changed) # avoid infinite connection loops
        self.posY_edt.setValue(posYreal)
        self.posY_edt.valueChanged.connect(self.posY_changed) # reconnect
    
    @pyqtSlot()
    def after_stop_motorsXY_meth(self): 
        
        # empty the queue
        while True:
            try:
                self.stop_motorsXY_queue.get_nowait()
            except queue.Empty:  # nothing in queue
                break # outside of 'while' loop
                
        self.stop_motorsXY_queue.put(1) # send order to stageXY Worker to stop
    
    @pyqtSlot(int)    
    def has_been_homed(self, v): 
    # v is useless but used to match the signal
    
        self.chck_homed = 1
        print('set stageXY home : ok')
        
        self.posX_edt.setEnabled(True)
        self.posY_edt.setEnabled(True)
        self.posX_edt.setEnabled(True)
        self.posY_edt.setEnabled(True)
        self.posX_10_push.setEnabled(True)
        self.posX_100_push.setEnabled(True)
        self.posX_1000_push.setEnabled(True)
        self.posY_10_push.setEnabled(True)
        self.posY_100_push.setEnabled(True)
        self.posY_1000_push.setEnabled(True)
        self.posX_m10_push.setEnabled(True)
        self.posX_m100_push.setEnabled(True)
        self.posX_m1000_push.setEnabled(True)
        self.posY_m10_push.setEnabled(True)
        self.posY_m100_push.setEnabled(True)
        self.posY_m1000_push.setEnabled(True)
        
        self.posX = self.posX_edt.value(); self.posY = self.posY_edt.value()
        
        self.force_homing_chck.setChecked(False) # default
        
    @pyqtSlot(bool)
    def ask_if_safe_pos_for_homing_meth(self, v):
        
        if v: # value of motors defined, but strange: ask if home
        
            if QtWidgets.QMessageBox.question(None, 'unusual pos.', "posX is %.1f and posY is %.1f (UNUSUAL): want to re-home XY ?" % (self.posX_edt.value(), self.posY_edt.value()), QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No:  
                return # outside function
        
        if QtWidgets.QMessageBox.question(None, 'Safe ??', "Are ALL the objectives at a safe position?",
                                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                    QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.Yes:
            
            self.do_force_stage_homing_signal.emit() # send to worker APT to do forced homing                        
            # # self.worker_apt.home_stage_meth_forced # executing this directly would freeze the GUI
    
    @pyqtSlot()
    def after_force_homing_stage_toggled_meth(self):
        
        
        if self.force_homing_chck.isChecked(): # force homing
            try:
                self.home_stage_button.clicked.disconnect(self.worker_stageXY.control_if_home_stage_necessary_meth) # if you call here a gui function, it will freeze the GUI
            except TypeError: # if had no connection
                pass
            self.home_stage_button.clicked.connect(self.ask_if_safe_pos_for_homing_meth) # if you call here a gui function, it will freeze the GUI
            
        else: # normal homing
            try:
                self.home_stage_button.clicked.disconnect(self.ask_if_safe_pos_for_homing_meth) # if you call here a gui function, it will freeze the GUI
            except TypeError: # if had no connection
                pass
            self.home_stage_button.clicked.connect(self.worker_stageXY.control_if_home_stage_necessary_meth) # if you call here a gui function, it will freeze the GUI
            
    @pyqtSlot()        
    def firstini_stageXY_meth(self):
        # # called by home button
        try:
            self.home_stage_button.clicked.disconnect(self.firstini_stageXY_meth)
        except TypeError:
            pass
        if (not hasattr(self, 'thread_stageXY') or self.thread_stageXY is None): # no thread yet
            print('started stage thread')
            self.setupThread_stageXY()
            time.sleep(0.5) # thread starts
            self.home_stage_button.clicked.emit()
        
    @pyqtSlot()
    def posX_10_push_meth(self):
    #posX_10_push
    
        self.posX_edt.setValue(self.posX_edt.value() + 10/1000)
    
    @pyqtSlot()
    def posX_100_push_meth(self):
    #posX_10_push
    
        self.posX_edt.setValue(self.posX_edt.value() + 100/1000)
    
    @pyqtSlot()
    def posX_1000_push_meth(self):
    #posX_10_push
    
        self.posX_edt.setValue(self.posX_edt.value() + 1000/1000)
    
    @pyqtSlot()
    def posX_m10_push_meth(self):
    # minus
    
        self.posX_edt.setValue(self.posX_edt.value() - 10/1000)
    
    @pyqtSlot()
    def posX_m100_push_meth(self):
    # minus
    
        self.posX_edt.setValue(self.posX_edt.value() - 100/1000)
    
    @pyqtSlot()
    def posX_m1000_push_meth(self):
    # minus
    
        self.posX_edt.setValue(self.posX_edt.value() - 1000/1000)
        
    @pyqtSlot()
    def posY_10_push_meth(self):
    #posX_10_push
    
        self.posY_edt.setValue(self.posY_edt.value() + 10/1000)
    
    @pyqtSlot()
    def posY_100_push_meth(self):
    #posX_10_push
    
        self.posY_edt.setValue(self.posY_edt.value() + 100/1000)
    
    @pyqtSlot()
    def posY_1000_push_meth(self):
    
    
        self.posY_edt.setValue(self.posY_edt.value() + 1000/1000)
        
    @pyqtSlot()
    def posY_m10_push_meth(self):
    # minus
    
        self.posY_edt.setValue(self.posY_edt.value() - 10/1000)
    
    @pyqtSlot()
    def posY_m100_push_meth(self):
    # minus
    
        self.posY_edt.setValue(self.posY_edt.value() - 100/1000)
    
    @pyqtSlot()
    def posY_m1000_push_meth(self):
    # minus
    
        self.posY_edt.setValue(self.posY_edt.value() - 1000/1000)
    
    @pyqtSlot(int)
    def action_stg_params_meth(self, b):
        if b == 0: # # action
            pass
        else: # # action
            if b == 1: # # apply params
                self.scan_dependencies_changed(-1) # -1 for forced
            elif b == 2: # # force update
                tt = 1
                for i in range(tt):
                    self.adjust_vel_wrt_size()
                    if i < tt -1:
                        time.sleep(1);
                        # # if self.profile_mode_cmbbx.currentIndex() == 1: self.jerk_fast_spnbx.valueChanged.emit(1)
                        time.sleep(0.1)
            elif b == 3: # # old scan
                self.reset_prev_vel_acc_scnstg_meth()
            elif b == 4: # # opt params
                self.stgscn_chg_primary_param_meth()
            self.action_stg_params_cmb.blockSignals(True); self.action_stg_params_cmb.setCurrentIndex(0); self.action_stg_params_cmb.blockSignals(False)
    
    def reset_prev_vel_acc_scnstg_meth(self):
        # # is called by oldscn_params_put_button via button func, and define new scan directly
        
        if (self.vel_acc_X_reset_by_move): # stage scan, the position must use default (fast) speed and acc. to be set, and after put the previous parameters
            self.acc_max_motor_X_spinbox.setValue(self.prev_accMax_X)
            self.speed_max_motor_X_spinbox.setValue(self.prev_speedMax_X)
            self.vel_acc_X_reset_by_move = False
        if (self.vel_acc_Y_reset_by_move): # stage scan, the position must use default (fast) speed and acc. to be set, and after put the previous parameters
            self.acc_max_motor_Y_spinbox.setValue(self.prev_accMax_Y)
            self.speed_max_motor_Y_spinbox.setValue(self.prev_speedMax_Y)
            self.vel_acc_Y_reset_by_move = False
    
    @pyqtSlot()
    def redetect_stageXY_meth(self):
        
        if (not hasattr(self, 'thread_stageXY') or self.thread_stageXY is None): # no thread yet
            self.setupThread_stageXY()
        else: # thread already init before !
            self.close_motorXY_signal.emit(False) # send to worker stageXY to close the motor port
            # False not to close the Qthread
            # msg = self.queue_disconnections.get(block=True, timeout=param_ini.time_out_discon_sec) 
            self.thread_stageXY.started.emit() # to call open_lib, faking a start

        ## APT thorlabs
    
    @pyqtSlot(list, list, list)        
    def apt_imported_after_meth(self, motorRotIsHere_l, motorPhshftIsHere_l, motorTransIsHere_l):
        
        self.apt_here = 1
        
        self.wait_flag_apt_current = self.worker_apt.wait_flag

        self.motorRotIsHere = motorRotIsHere_l[0]
        self.motorPhshftIsHere00 = motorPhshftIsHere_l[0]
        self.motorTransIsHere = motorTransIsHere_l[0]
        
        if self.motorTransIsHere:
            if motorTransIsHere_l[1] == 'TDC001': # # old T cube
                max_acc = param_ini.max_acc_TC_dflt # # mm/s2
                max_vel = param_ini.max_acc_TC_dflt # # mm/sec
            elif motorTransIsHere_l[1] == 'KDC001': # # new K cube
                # # values for the Z825B !
                max_acc = param_ini.max_acc_KC_dflt # 4 # # mm/s2
                max_vel = param_ini.max_vel_KC_dflt #  2.6 # # mm/sec
                
            self.jobs_window.mtrps_velset_spbx.setMaximum(max_vel)
            self.jobs_window.mtrps_accnset_spbx.setMaximum(max_acc)
        
        if self.jobs_window.ps_mtr_rot_radio.isChecked(): # rot
            self.motorPhshftIsHere = True if self.motorPhshftIsHere00 else False
        elif self.jobs_window.ps_mtr_trans_radio.isChecked(): # trans
            self.motorPhshftIsHere = True if self.motorTransIsHere else False
        elif self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # DC volt
            self.motorPhshftIsHere = True if self.EOMph_is_connected else False
        
        # # if self.user_want_to_quit_gui:
        # #     self.quit_gui_func() # quit GUI
        # # else: # just re-link the quit button to quit meth
        # # try:
        # #     self.quit_button.clicked.disconnect(self.wait_gui_quit_meth)
        # # except TypeError:
        # #     pass
        # # self.quit_button.clicked.connect(self.quit_gui_func)
        if param_ini.PI_conn_meth == 'usb': # # 'rs232'
            self.setupThread_PI() # starts the PI worker
        # otherwise interferes !!
        
        self.jobs_window.ps_mtr_rot_radio.toggled.emit(self.jobs_window.ps_mtr_rot_radio.isChecked())
        
        self.vlmtrjob_def_util()
    
    @pyqtSlot()        
    def pos_phshft_changed(self):
        
        widg = self.sender()
        if widg == self.jobs_window.pos_motor_phshft_edt:
            mtr_sign = self.move_motor_phshft_signal
            name = 'phshft'
            min_pos = -self.bound_mtr_rot_plate*1000 ; max_pos = self.bound_mtr_rot_plate*1000 # 6000 # um
        elif widg == self.jobs_window.pos_motor_trans_edt: # # trans
            mtr_sign = self.move_motor_trans_signal
            name = 'trans'
            min_pos = -self.bound_mtr_trans*1000 ; max_pos = self.bound_mtr_trans*1000 # um
        
        self.pos_phshft = float(widg.text()) # in um
        
        # # if self.jobs_window.ps_mtr_rot_radio.isChecked(): # use motor rot.
        # #    
        # # else:
        # #     min_pos = 0 # um
        # #     max_pos = self.pos_max_phshft_um # um
        
        if self.pos_phshft < min_pos:
            self.pos_phshft = min_pos
            widg.setText('0')
        elif self.pos_phshft >= max_pos: # too high
            self.pos_phshft = max_pos-1
            widg.setText(str(max_pos-1))
        
        print('\n pos %s changed meth toggled \n' % name)
            
        mtr_sign.emit(self.pos_phshft/1000, False)    # # False for no job   
        
    @pyqtSlot()
    def after_force_homing_phshft_toggled_meth(self):
        
        print('\n Warning: motor ps+trans will be homed physically when homing button, be sure that nothing blocks the motor and that the actual pos. is unimportant !')
        # # l_instr = [self.jobs_window.home_calcites_button, self.jobs_window.home_tl_phsft_button]
        # # 
        # # for button in l_instr:
        # #     if self.jobs_window.force_homing_phshft_chck.isChecked(): # force homing
        # #         try:
        # #             button.clicked.disconnect(self.home_motor_phshft) # if you call here a gui function, it will freeze the GUI
        # #         except TypeError: # if had no connection
        # #             pass
        # #         button.clicked.connect(self.worker_apt.move_home_phshft_forced) # if you call here a gui function, it will freeze the GUI
        # #     else: # normal homing
        # #         try:
        # #             button.clicked.disconnect(self.worker_apt.move_home_phshft_forced) # if you call here a gui function, it will freeze the GUI
        # #         except TypeError: # if had no connection
        # #             pass
        # #         button.clicked.connect(self.home_motor_phshft) # if you call here a gui function, it will freeze the GUI
            
    @pyqtSlot()    
    def home_motor_phshft(self):
        
        if self.thread_apt is None: # not here
            self.setupThread_apt() # starts the APT worker
        
        if self.sender() == self.jobs_window.home_tl_phsft_button: # # rotplate
            ID = 0
        elif self.sender() == self.jobs_window.home_calcites_button: # # trans
            ID = 1
        else: 
            print('sender not recogn. (in home_motor_phshft)', self.sender())
            return
        
        print('Received order to home motor phshft ... \n')
        
        # # if not self.scan_thread_available: # scan stage running
        # # 
        # #     self.queue_com_to_acq.put([-1]) # kill current acq processes of data_acquisition, and the qthread
        # #     print('GUI sent to acq process a poison-pill')
        
        if self.jobs_window.force_homing_phshft_chck.isChecked(): # force homing
            forced = True
        else: #normal
            forced = False
        # else: # normal homing
            # # try:
            # #     self.home_motor_phshft_signal.disconnect(self.worker_apt.move_home_phshft) 
            # # except TypeError: # if had no connection
            # #     pass
            # # self.home_motor_phshft_signal.disconnect(self.worker_apt.move_home_phshft_forced) 
        self.home_motor_phshft_signal.emit(ID, forced) # signal to make the home of the motor phshft
        # # if self.jobs_window.force_homing_phshft_chck.isChecked(): # force homing
        # # # else: # normal homing
        # #     try:
        # #         self.home_motor_phshft_signal.disconnect(self.worker_apt.move_home_phshft_forced)  
        # #     except TypeError: # if had no connection
        # #         pass
        # #     self.home_motor_phshft_signal.disconnect(self.worker_apt.move_home_phshft) 
        
    @pyqtSlot()
    def after_motor_phshft_homed_meth(self): # just to set the button enabled
        
        self.jobs_window.cal_ps_button.setEnabled(True)
        self.jobs_window.pos_motor_phshft_edt.setEnabled(True)
        self.jobs_window.force_homing_phshft_chck.setChecked(False) # default
        
    @pyqtSlot()
    def after_motor_trans_homed_meth(self): # just to set the button enabled
    
        self.jobs_window.cal_ps_button.setEnabled(True)
        self.jobs_window.pos_motor_trans_edt.setEnabled(True)
        self.jobs_window.force_homing_phshft_chck.setChecked(False) # default
    
    @pyqtSlot()
    def after_motor_polar_homed_meth(self): # just to set the button enabled
    
        self.jobs_window.home_tl_rot_button.setStyleSheet('background-color:lightgreen;') # lightgreen # greenyellow
        
    @pyqtSlot()
    def after_redetect_APT(self):
        
        if (not hasattr(self, 'thread_stageXY') or self.thread_stageXY is None): # first init, because APT overrides it
            # self.setupThread_stageXY()
            self.firstini_stageXY_meth()
        else: # thread XY ok
            if not self.stageXY_is_here: # motorXY not recognized, try to scan it again  
                self.worker_stageXY.open_lib()
        
        if (self.apt_here and hasattr(self, 'thread_apt') and self.thread_apt is not None): # APT has already been imported
            self.worker_apt.open_lib()
        else: # APT not yet imported
            self.setupThread_apt() # starts the APT worker
        
        # # if (worker_stageXY and not self.stageXY_is_here): # motorXY not recognized, try to scan it again  
        # #     self.worker_stageXY.open_lib()
        
    @pyqtSlot(int, float, float)
    def mtr_phsft_APT_def_velacc(self, bb, vel_max_mtr_phsft , accn_max_mtr_phsft):
    # # bb = 1 for rot gp and 2 for trans
    
        self.vel_mtr_phsft = vel_max_mtr_phsft 
        self.accn_mtr_phsft = accn_max_mtr_phsft
    
        ##  ESP Newport
    
    @pyqtSlot(bool)        
    def esp_imported_after_meth(self, motorNewportIsHere):
        
        # # print('in esp after')
        self.esp_here =  motorNewportIsHere
        if self.esp_here: # # here
            self.jobs_window.home_newport_rot_button.setEnabled(True)
        else: # # not here
            self.jobs_window.home_newport_rot_button.setEnabled(False)
    
    @pyqtSlot()    
    def home_motor_newport(self):
        
        print('Received order to home motor newport ... \n')   
        if self.esp_here:     
            self.home_motor_newport_signal.emit()
        else:
            print('...but motor is not here')  
            
    @pyqtSlot()        
    def pos_newport_changed(self):
        
        self.pos_newport = self.jobs_window.newport_polar_bx.value()
        self.move_motor_newport_signal.emit(self.pos_newport) 
        
    @pyqtSlot()
    def redetect_newport_meth(self):
        
        if (not hasattr(self, 'thread_newport') or self.thread_newport is None):
            self.setupThread_newport()
        else: # thread here already
            self.close_newport_signal.emit(False) # send to worker newport to close the motor port
            # # try:
            # #     msg = self.queue_disconnections.get(block=True, timeout=param_ini.time_out_discon_sec)
            # # except queue.Empty:
            # #     pass
            self.thread_newport.started.emit() # to call open_lib, faking a start
             
        ## PMT methods
    
    @pyqtSlot()
    def define_real_PMT_range_meth(self):
        
        widget_caller = self.sender()
        if isinstance(widget_caller, QtWidgets.QDoubleSpinBox):
            name = widget_caller.objectName()
            
        if self.dev_to_use_AI_box.currentIndex() == 0: # 6110
            dev = 1
            max_val = 42
        else: # 6259
            dev = 2
            max_val = 10
        
        if int(name[3]) == 1:
            label = self.pmt1_valIndic_labl
            max_widg = self.pmt1_physMax_spnbx
            val = max(abs(self.pmt1_physMin_spnbx.value()), abs(max_widg.value()))
        elif int(name[3]) == 2:
            label = self.pmt2_valIndic_labl
            max_widg = self.pmt2_physMax_spnbx
            val = max(abs(self.pmt2_physMin_spnbx.value()), abs(max_widg.value()))
        elif int(name[3]) == 3:
            label = self.pmt3_valIndic_labl
            max_widg = self.pmt3_physMax_spnbx
            val = max(abs(self.pmt3_physMin_spnbx.value()), abs(max_widg.value()))
        elif int(name[3]) == 4:
            label = self.pmt4_valIndic_labl
            max_widg = self.pmt4_physMax_spnbx
            val = max(abs(self.pmt4_physMin_spnbx.value()), abs(max_widg.value()))
            
        if val > max_val:
            val = max_val
            max_widg.blockSignals(True)
            max_widg.setValue(max_val)
            max_widg.blockSignals(False)
            
        bound = daq_control_mp2.bounds_AI_daq(val, dev, max_val) 
            
        label.setText(' [%.1f, %.1f] V' % (-bound, bound))
        
        if int(name[3]) == 1:
            self.bound_AI_1 = bound
        elif int(name[3]) == 2:
            self.bound_AI_2 = bound
        elif int(name[3]) == 3:
            self.bound_AI_3 = bound
        elif int(name[3]) == 4:
            self.bound_AI_4 = bound
        
        self.min_val_volt_list = [self.pmt1_physMin_spnbx.value(), self.pmt2_physMin_spnbx.value(), self.pmt3_physMin_spnbx.value(), self.pmt4_physMin_spnbx.value()]
        self.max_val_volt_list = [self.pmt1_physMax_spnbx.value(), self.pmt2_physMax_spnbx.value(), self.pmt3_physMax_spnbx.value(), self.pmt4_physMax_spnbx.value()]
    
    @pyqtSlot(int)
    def dev_to_use_AI_chg_after_meth(self, ind):
        chg = False # # dflt
        if (ind == 0 and not self.lock_smp_clk_chck.isChecked() and self.read_sample_rate_spnbx.value() != param_ini.smp_rate_AI_dflt): # 6110
            self.read_sample_rate_spnbx.setValue(param_ini.smp_rate_AI_dflt)
            chg = True
        else: # 6259
            if self.read_sample_rate_spnbx.value() > param_ini.sample_rate_max_6259: 
                self.read_sample_rate_spnbx.setValue(param_ini.sample_rate_max_6259)
                chg = True
                
        if chg: self.kill_scanThread_meth()
        
    @pyqtSlot()
    def gainPMT_changed_meth(self):
        # # called by gainPMT_indic_1 2 3 4
        
        widg = self.sender()
        if widg == self.gainPMT_indic_1: pmt = 1; sp_pm = self.pmt1_physMin_spnbx
        elif widg == self.gainPMT_indic_2: pmt = 2; sp_pm = self.pmt2_physMin_spnbx
        
        tx = widg.text()
        if not tx.isdigit(): return
        gain = float(widg.text())
        minval_volt_wrtgain = numpy.array(param_ini.minval_volt_wrtgain_list)
        diff_arr = ( minval_volt_wrtgain[:,0] - gain)
        argmin = numpy.abs(diff_arr).argmin()
        dist = diff_arr[argmin]
        if abs(dist) > 1e-2: # # tolerance, case 0 has to be avoided also
            arg2 =  min(len(minval_volt_wrtgain)-1, max(0, argmin - int(numpy.sign(dist))))
            p1=1/numpy.abs(dist); p2 = 1/numpy.abs(diff_arr[arg2])
            val = (p1*minval_volt_wrtgain[argmin, pmt] + p2*minval_volt_wrtgain[arg2, pmt])/(p1+p2)
        else: val = minval_volt_wrtgain[argmin, pmt] ##; print('safasdf')
        sp_pm.setValue(val)
    
    @pyqtSlot(int)    
    def autoscalelive_plt_cmb_index_meth(self, ind):
        
        if ind == self.jobs_window.autoscalelive_plt_cmb.count()-1: # last one
        # self.jobs_window.autoscalelive_plt_cmb.currentIndex()
            self.jobs_window.autoscalelive_plt_cmb.setEditable(True)
        else: self.jobs_window.autoscalelive_plt_cmb.setEditable(False)
        
        ## shutter methods
    
    @pyqtSlot(int)
    def shutter_here_meth(self, val):
        
        self.shutter_is_here = bool(val)
        self.use_shutter_combo.blockSignals(True)

        if (not self.shutter_is_here): # shutter not here
            self.shutter_closed_chck.setEnabled(False)
            if self.use_shutter_combo.currentIndex():
                self.use_shutter_combo.setCurrentIndex(0)

        else: # shutter here
            self.shutter_closed_chck.setEnabled(True)
            if not self.use_shutter_combo.currentIndex():
                self.use_shutter_combo.setCurrentIndex(self.shutter_curr_mode)
            
        self.use_shutter_combo.setEnabled(True)
        self.use_shutter_combo.blockSignals(False)

    @pyqtSlot()
    def shutter_using_changed(self):
        
        if (not hasattr(self, 'thread_shutter') or self.thread_shutter is None): # never started
            self.setupThread_shutter()
            return
        
        # # if not self.shutter_is_here: # shutter not here
        shutter_curr_mode_prev = self.shutter_curr_mode
        self.shutter_curr_mode = self.use_shutter_combo.currentIndex()

        if (self.shutter_curr_mode and not shutter_curr_mode_prev):
            print('Trying to verify shutter')
            self.conn_instr_shutter_signal.emit() # try to connect shutter
            self.use_shutter_combo.blockSignals(True)
            self.use_shutter_combo.setEnabled(False)
            self.use_shutter_combo.setCurrentIndex(0)
            self.use_shutter_combo.blockSignals(False)
    
    @pyqtSlot()
    def shutter_force_openClose_toggled(self):
        # is called by the check box of state closed on GUI
        
        val = bool(self.shutter_closed_chck.isChecked())
        self.open_close_shutter_signal.emit(val) # val = 2 if checked, so 1
        # val = 0 if not checked, so 0
    
    def shutter_outScan_mode(self):
        self.shutter_closed_chck.setEnabled(True)
        self.shutter_closed_chck.blockSignals(True)
        self.shutter_closed_chck.setChecked(True) # just display that the shutter is closed
        self.shutter_closed_chck.blockSignals(False)
        self.out_scan = True
    
        ## scan methods
    
    @pyqtSlot(bool)
    def scan_not_running_def_meth(self, is_free):
        
        print('is changing state: scan is running %r (mode %d)' %  (not is_free, self.stage_scan_mode))
        if is_free: # # scan_not_running
            self.scan_thread_available = 1
            # # if self.set_new_scan == 1: # # called by define_if_new_scan
            # #     self.empty_queue_send_reset_scan(False) # # arg for direct call
            # # else:
            self.set_new_scan = 2
            if (self.stage_scan_mode_before == 1 or self.stage_scan_mode == 1): # before was stage scan, or stage scan (only 1)
    
                self.prev_accMax_X = self.acc_max_motor_X_spinbox.value()
                self.prev_speedMax_X = self.speed_max_motor_X_spinbox.value()
                # # self.acc_max_motor_X_spinbox.setValue(self.acc_dflt)
                # # self.speed_max_motor_X_spinbox.setValue(self.vel_dflt)
                # # self.acc_max_motor_Y_spinbox.setValue(self.acc_dflt)
                # # self.speed_max_motor_Y_spinbox.setValue(self.vel_dflt)
                # # self.vel_acc_X_reset_by_move = True
                self.prev_accMax_Y = self.acc_max_motor_Y_spinbox.value()
                self.prev_speedMax_Y = self.speed_max_motor_Y_spinbox.value() # to store the values !!
                
                self.change_scan_dependencies_signal.emit(self.acc_dflt, self.acc_dflt, self.vel_dflt, self.vel_dflt, int(self.yscan_radio.isChecked()) + 1, param_ini.prof_mode, param_ini.jerk_mms3_trapez )
                
                # # self.vel_acc_Y_reset_by_move = True
                self.posX_changed()
                self.posY_changed() # update the changed value during the time the thread was out
                try:# empty the queue, because otherwise if you send several move order like this, the motor will execute them at the next scan in a row...
                    while True: self.queue_moveX_inscan.get_nowait() # empty the queue
                except queue.Empty: pass # if empty, it raises an error 
                try:# empty the queue, because otherwise if you send several move order like this, the motor will execute them at the next scan in a row...
                    while True: self.queue_moveY_inscan.get_nowait() # empty the queue
                except queue.Empty: pass # if empty, it raises an error 
                
        else: # # has only begun
            self.scan_thread_available = 0
                
        
    @pyqtSlot()
    def kill_scanThread_meth(self):
        # called by kill thread button, and directly by some functions
        
        print('in kill_scanThread_meth !!!', self.scan_thread_available)
        
        if self.scan_thread_available == 0: # 0 important
            self.cancel_inline_meth() # cancel_scan or job
            time.sleep(1) # # otherwise too fast (tested)
            
            # # if self.set_new_scan < 2: # it's not necessary for the very first scan            
            # kill current scan worker if exist
            self.scan_thread_available = -1 # this flag will be reset to 1 by func zhen finished
            self.queue_com_to_acq.put([-1]) # kill current acq processes of data_acquisition, and the qthread
            # for the galvo scan, it does kill the QThread
            # for stage scan, it just put outside function of scan
            print('GUI sent to acq process a poison-pill, in kill')
            # except: # if no scan was previously done
            #     pass # do nothing
            # will end the acq. function, so make the QThread responsive to new signals
            if self.set_new_scan == 0:        
                self.set_new_scan = 2 # whole new scan, acts as the very first scan
        elif self.scan_thread_available == -1: # this flag was not reset to 1 by func: scanThread never finished !
            if self.stage_scan_mode != 1: # not stage scn
                self.thread_scan.quit()
            else: # stage scan
                self.thread_stageXY.quit()
                self.thread_stageXY.wait(2) # sec
                self.setupThread_stageXY()
            # # self.setupThread_scan()
            self.scan_thread_available = 1
        else:
            print('nothing, because self.scan_thread_available is', self.scan_thread_available)
    
    @pyqtSlot()
    def scan_mode_changed(self):
        
        print('scan mode changed')
        
        self.stage_scan_mode = self.mode_scan_box.currentIndex() # 0 for dig. galvo, 1 for stage, 2 for static, 3 for anlg galvos
        
        if (self.stage_scan_mode_current != self.stage_scan_mode):
            
            self.kill_scanThread_meth()
            
            if self.pixell_offset_dir_spbox.value != 0: self.pixell_offset_dir_spbox.setValue(0)
            if self.pixell_offset_rev_spbox.value != 0: self.pixell_offset_rev_spbox.setValue(0)
                
            # # **********************************************    
            # # \\\\\\\\\\\\\\\ STAGE scan //////////////////
            # # **********************************************  
            
            if self.stage_scan_mode == 1: # STAGE scan
                self.update_rate_spnbx.setEnabled(False)
                self.applylive_params_stgscn_chck.setVisible(True)
                self.applylive_params_stgscn_lbl.setVisible(True)
                self.coupleaccnvel_stgscn_chck.setVisible(True)
                self.coupleaccnvel_stgscn_lbl.setVisible(True)
                self.stage_scn_block_stp_lbl.setVisible(True)
                self.stage_scn_block_stp_chck.setVisible(True)
                self.stagescn_wait_fast_chck.setVisible(True)
                self.stagescn_wait_fast_lbl.setVisible(True)
                self.square_img_chck.setChecked(False)
                self.stgscn_livechgX_chck.setVisible(True)
                self.stgscn_livechgY_chck.setVisible(True)
                # # self.profile_mode_cmbbx.currentIndexChanged.disconnect(self.scan_dependencies_changed)
                self.profile_mode_cmbbx.blockSignals(True)
                self.profile_mode_cmbbx.setCurrentIndex(self.profile_mode_stgXY_current - 1)
                self.profile_mode_cmbbx.blockSignals(False)
                # # self.profile_mode_cmbbx.currentIndexChanged.connect(self.scan_dependencies_changed) # reconnect
                
                self.after_profile_mode_stgscn_changed_meth() # allow to be called everytime, even if profile mode does not change
                # # print('self.jerk_stgXY_current ', self.jerk_stgXY_current
                
                print('scan stage selected')
                # # print('\n Don`t forget to connect the stage trigger wire to the DAQ, and verify that the galvo one is not plugged with it (even if galvos are turned off) !\n')
                
                # use of queue Queue, not multiprocessing
                self.queue_com_to_acq = self.queue_com_to_acq_stage
                self.queue_special_com_acq_stopline = self.queue_special_com_acqstage_stopline
                
                # # self.external_clock = 0 # internal clock of the DAQ, external trigger (stage)
                # self.duration_indic.textChanged.connect(self.dwell_time_change) #
                        
                # # self.bidirec_check.setVisible(True)
                self.xscan_radio.setVisible(True)
                self.yscan_radio.setVisible(True)
                self.acc_offset_spbox.setVisible(True)
                self.dec_offset_spbox.setVisible(True)
                # self.pixell_offset_dir_spbox.setVisible(True)
                # self.pixell_offset_rev_spbox.setVisible(True)
                # self.cancel_inline_button.setVisible(True)
                self.acc_offset_theo_lbl.setVisible(True)
                self.label_pixell_trans2.setVisible(True)
                # self.label_pixell_read.setVisible(True)
                # self.label_pixell_read2.setVisible(True)
                # self.label_pixell_read3.setVisible(True)
                self.pixell_offset_theo_lbl.setVisible(True)
                # # self.profile_mode_cmbbx.setVisible(True)
                # # self.profile_mode_lbl.setVisible(True)
                self.jerk_fast_lbl.setVisible(True)
                self.jerk_fast_spnbx.setVisible(True)
                self.label_pixell_trans3.setVisible(True)
                self.label_pixell_trans4.setVisible(True)
                self.lock_stage_scan_dep_chck.setVisible(True)
                
                try:
                    self.stepX_um_edt.valueChanged.disconnect(self.duration_change)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.stepY_um_edt.valueChanged.disconnect(self.duration_change)
                except TypeError: # nothing to disconnect
                    pass 
                self.stepX_um_edt.valueChanged.connect(self.exp_time_funcof_step_stgscn_meth)
                self.stepY_um_edt.valueChanged.connect(self.exp_time_funcof_step_stgscn_meth)
                
                self.profile_mode_cmbbx.currentIndexChanged.connect(self.stgscn_chg_primary_param_meth)
                
                self.pos_phshft0 = 0 # self.list_pos_wrt_origin = numpy.arange(0) ; 
                
                # can be already True if going from galvo to static for instance
                try:
                    self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.scan_dependencies_changed) 
                except TypeError: # nothing to disconnect
                    pass 
                
                self.stgscn_chg_primary_param_meth() # see above

                self.profile_mode_cmbbx.currentIndexChanged.connect(self.adjust_vel_wrt_size)
                
                self.specific_scan_params_tab_switch.setCurrentIndex(0)
                
                # # !!
                self.acc_max_motor_X_spinbox.blockSignals(True)
                self.acc_max_motor_Y_spinbox.blockSignals(True)
                self.speed_max_motor_X_spinbox.blockSignals(True)
                self.speed_max_motor_Y_spinbox.blockSignals(True)
                
                if self.yscan_radio.isChecked(): # yfast
                    sizeum_slow_spbx = self.sizeX_um_spbx # the full spinbox
                    sizeum_fast_spbx = self.sizeY_um_spbx # the full spinbox
                else:
                    sizeum_slow_spbx = self.sizeY_um_spbx # the full spinbox
                    sizeum_fast_spbx = self.sizeX_um_spbx # the full spinbox
                
                if (sizeum_fast_spbx.value() == self.dflt_sizeum_slow_stage): # ref for stage scan in other dir
                    sizeum_fast_spbx.setValue(self.size_um_dflt) # 400
                if (sizeum_slow_spbx.value() > self.too_much_sizeum_slow_stage): # ref for stage scan in other dir
                    sizeum_slow_spbx.setValue(self.dflt_sizeum_slow_stage)
                    
                self.acc_max_motor_X_spinbox.blockSignals(False)
                self.acc_max_motor_Y_spinbox.blockSignals(False)
                self.speed_max_motor_X_spinbox.blockSignals(False)
                self.speed_max_motor_Y_spinbox.blockSignals(False)
                if self.stage_scan_mode_current in (0, 3): # galvos before 
                    self.offsetX00_Galvos = self.offsetX_mm_spnbx.value()
                    self.offsetY00_Galvos = self.offsetY_mm_spnbx.value()
                self.offsetX_mm_spnbx.setValue(0)
                self.offsetY_mm_spnbx.setValue(0)
                self.offsetX_mm_spnbx.setValue( self.offsetX00_stgscn)
                self.offsetY_mm_spnbx.setValue( self.offsetY00_stgscn)
            
                if (self.stepX_um_edt.value() != self.step_ref_val_stage or self.stepY_um_edt.value() == self.step_ref_val_stage):
                    self.stepX_um_edt.setValue(self.step_ref_val_stage)
                    self.stepY_um_edt.setValue(self.step_ref_val_stage) # default values
                    
                self.modeEasy_stgscn_cmbbx.setVisible(True)
                self.modeEasy_stgscn_cmbbx.currentIndexChanged.emit(1) # fake a change
                self.modeEasy_stgscn_cmbbx.currentIndexChanged.emit(0) # fake a change
            
            # # **********************************************    
            # # \\\\\\\\\\ GALVOS scan or static /////////////
            # # **********************************************  
                
            else: # GALVOS scan or static acq.
                self.update_rate_spnbx.setEnabled(True)
                self.applylive_params_stgscn_chck.setVisible(False)
                self.applylive_params_stgscn_lbl.setVisible(False)
                self.coupleaccnvel_stgscn_chck.setVisible(False)
                self.coupleaccnvel_stgscn_lbl.setVisible(False)
                self.stage_scn_block_stp_lbl.setVisible(False)
                self.stage_scn_block_stp_chck.setVisible(False)
                self.stagescn_wait_fast_chck.setVisible(False)
                self.stagescn_wait_fast_lbl.setVisible(False)
                self.stgscn_livechgX_chck.setVisible(False)
                self.stgscn_livechgY_chck.setVisible(False)

                # can be already True if going from galvo to static for instance
                try:
                    self.profile_mode_cmbbx.currentIndexChanged.disconnect(self.stgscn_chg_primary_param_meth)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) 
                except TypeError: # nothing to disconnect
                    pass  
                try:
                    self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) 
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
                except TypeError: # nothing to disconnect
                    pass 
                try: # can be already disconnected because of lock scan dep
                    self.sizeX_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
                except TypeError: # nothing to disconnect
                    pass 
                try: # can be already disconnected because of lock scan dep
                    self.sizeY_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
                except TypeError: # nothing to disconnect
                    pass 
                try:    
                    self.profile_mode_cmbbx.currentIndexChanged.disconnect(self.adjust_vel_wrt_size)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.jerk_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
                except TypeError: # nothing to disconnect
                    pass 
                try: # can be already done by lock scan dep.
                    self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.stepX_um_edt.valueChanged.disconnect(self.exp_time_funcof_step_stgscn_meth)
                except TypeError: # no disconnect needed
                    pass
                try: # can be already done by lock scan dep.
                    self.stepY_um_edt.valueChanged.disconnect(self.exp_time_funcof_step_stgscn_meth)
                except TypeError: # no disconnect needed
                    pass
                try:
                    self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.scan_dependencies_changed)
                except TypeError: # nothing to disconnect
                    pass 
                try:
                    self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.scan_dependencies_changed) 
                except TypeError: # nothing to disconnect
                    pass 
                try: self.sizeY_um_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth)
                except TypeError: pass  # nothing to disconnect
                try: self.sizeX_um_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth)
                except TypeError: pass  # nothing to disconnect
                
                self.acc_max_motor_X_spinbox.valueChanged.connect(self.scan_dependencies_changed)
                self.acc_max_motor_Y_spinbox.valueChanged.connect(self.scan_dependencies_changed)
                self.speed_max_motor_X_spinbox.valueChanged.connect(self.scan_dependencies_changed)
                self.speed_max_motor_Y_spinbox.valueChanged.connect(self.scan_dependencies_changed) 
                
                self.stepX_um_edt.valueChanged.connect(self.duration_change)
                self.stepY_um_edt.valueChanged.connect(self.duration_change)
             
                # # self.profile_mode_cmbbx.currentIndexChanged.disconnect(self.scan_dependencies_changed) # reconnected after
                self.acc_max_motor_X_spinbox.blockSignals(True) # this values will be effectively changed by an explicit call to it
                self.acc_max_motor_Y_spinbox.blockSignals(True)
                self.speed_max_motor_X_spinbox.blockSignals(True)
                self.speed_max_motor_Y_spinbox.blockSignals(True)
                self.profile_mode_cmbbx.blockSignals(True)
                
                self.acc_max_motor_X_spinbox.setValue(self.acc_dflt)
                self.acc_max_motor_Y_spinbox.setValue(self.acc_dflt)
                self.speed_max_motor_X_spinbox.setValue(self.vel_dflt)
                self.speed_max_motor_Y_spinbox.setValue(self.vel_dflt) # call scan_dependencies_changed just once
                                
                self.profile_mode_cmbbx.blockSignals(True)                
                self.profile_mode_cmbbx.setCurrentIndex(param_ini.prof_mode_slow -1)
                self.profile_mode_cmbbx.blockSignals(False)
                self.jerk_fast_spnbx.setValue(param_ini.jerk_mms3_slow)
                
                # # self.profile_mode_cmbbx.currentIndexChanged.connect(self.scan_dependencies_changed) # reconnect
                self.profile_mode_cmbbx.blockSignals(False)
                self.acc_max_motor_X_spinbox.blockSignals(False)
                self.acc_max_motor_Y_spinbox.blockSignals(False)
                self.speed_max_motor_X_spinbox.blockSignals(False)
                self.speed_max_motor_Y_spinbox.blockSignals(False)

                if self.yscan_radio.isChecked(): # yfast, to define if stage_scan parameters or not !
                    size_um_ref = self.sizeX_um_spbx.value() # um
                    
                else:
                    size_um_ref = self.sizeY_um_spbx.value() # um
                
                if (size_um_ref == self.dflt_sizeum_slow_stage): # ref for stage scan, not applicable here because galvo
                    if self.yscan_radio.isChecked(): # yfast, to define if stage_scan parameters or not !
                        stp = self.stepX_um_edt
                        sz = self.sizeX_um_spbx
                        sz_um = self.sizeX_galvo_prev
                    else:
                        stp = self.stepY_um_edt
                        sz = self.sizeY_um_spbx
                        sz_um = self.sizeY_galvo_prev
                    stp_um = stp.value() # store
                    sz.setValue(sz_um) # um
                    stp.setValue(stp_um)  # rst
                    
                self.dwll_time_edt.setValue((param_ini.time_by_point*1e6))

                timescan_min_sec = 1 # sec  
                timescan_max_sec = 20 # sec  
                szmax_px = 1000

                if (self.sizeY_um_spbx.value() != self.sizeX_um_spbx.value() or self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6 < timescan_min_sec):
                    if (self.stepX_um_edt.value() != self.step_ref_val_galvo and self.stepY_um_edt.value() != self.step_ref_val_galvo):
                        if (self.step_ref_val_galvo*self.sizeX_um_spbx.value() >= szmax_px): # # will lead to a too big dflt tot time
                            self.sizeX_um_spbx.setValue(self.sizeX_galvo_prev*self.step_ref_val_galvo)
                        if self.step_ref_val_galvo*self.sizeY_um_spbx.value() >= szmax_px:
                            self.sizeY_um_spbx.setValue(self.sizeY_galvo_prev*self.step_ref_val_galvo)
                        self.stepX_um_edt.setValue(self.step_ref_val_galvo)
                        self.stepY_um_edt.setValue(self.step_ref_val_galvo) # default values
                        
                self.square_img_chck.setChecked(True)
                
                if self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6 > timescan_max_sec: self.sizeX_um_spbx.setValue(self.sizeX_galvo_prev*self.step_ref_val_galvo); self.stepX_um_edt.setValue(self.step_ref_val_galvo)

                self.queue_com_to_acq = self.queue_com_to_acq_process
                self.queue_special_com_acq_stopline = self.queue_special_com_acqGalvo_stopline # use of multiprocessing queues, not queue Queues
                            
                if self.stage_scan_mode == 2: # static acquisition, # intern clock of the DAQ, but without trigger
                
                    self.specific_scan_params_tab_switch.setCurrentIndex(1)
            
                    print('\nStatic acq selected : you can acquire without the galvos or stage turn on \n')
                    # # self.external_clock = 0 
                    if self.stage_scan_mode_current in (0, 3): # galvos before 
                        self.offsetX00_Galvos = self.offsetX_mm_spnbx.value()
                        self.offsetY00_Galvos = self.offsetY_mm_spnbx.value()
                    self.offsetX_mm_spnbx.setValue( self.offsetX00_stgscn)
                    self.offsetY_mm_spnbx.setValue( self.offsetY00_stgscn)
                    self.offsetX_pg_curr = self.offsetX00_stgscn
                    self.offsetY_pg_curr = self.offsetY00_stgscn
                                        
                else:# (digital or analog) GALVOS scan
                
                    self.specific_scan_params_tab_switch.setCurrentIndex(2)

                    print('scan galvos selected')
                    
                    self.y_fast = 0# # for now
                    self.pause_trig_sync_dig_galv_changed_meth(int(self.pause_trig_sync_dig_galv_chck.isChecked()))
                    # # print('\n Don`t forget to connect the galvo trigger wire to the DAQ (can be together with stage one) !\n')
                    
                    # # if self.stage_scan_mode == 0: # digital
                    # #     self.external_clock = 1 # external clock, external trigger (galvos)
                    # #     
                    # # elif self.stage_scan_mode == 3: # anlg galvos new
                    # #     self.external_clock = 0 
                    
                # self.launch_scan_button.clicked.disconnect(self.param_stage_scan_send)
              
                # try:
                #     self.duration_indic.textChanged.disconnect(self.dwell_time_change)
                # except:
                #     pass
                        
                # # self.bidirec_check.setVisible(False)
                self.xscan_radio.setVisible(False)
                self.yscan_radio.setVisible(False)
                self.acc_offset_spbox.setVisible(False)
                self.dec_offset_spbox.setVisible(False)
                # self.pixell_offset_dir_spbox.setVisible(False)
                # self.pixell_offset_rev_spbox.setVisible(False)
                # self.cancel_inline_button.setVisible(False)
                self.acc_offset_theo_lbl.setVisible(False)
                self.label_pixell_trans2.setVisible(False)
                # self.label_pixell_read.setVisible(False)
                # self.label_pixell_read2.setVisible(False)
                # self.label_pixell_read3.setVisible(False)
                self.pixell_offset_theo_lbl.setVisible(False)
                # # self.profile_mode_cmbbx.setVisible(False)
                # # self.profile_mode_lbl.setVisible(False)
                self.jerk_fast_lbl.setVisible(False)
                self.jerk_fast_spnbx.setVisible(False)
                self.label_pixell_trans3.setVisible(False)
                self.label_pixell_trans4.setVisible(False)
                self.lock_stage_scan_dep_chck.setVisible(False)
                self.modeEasy_stgscn_cmbbx.setVisible(False)
            
            if self.stage_scan_mode == 3: # anlg galvos
                self.acqline_galvo_mode_box.setCurrentIndex(1) # # callback default
                self.corr_sync_inPx_spnbx.setValue(0)
                try: self.update_rate_spnbx.valueChanged.disconnect(self.eff_new_galvos_adjustMax_meth)
                except TypeError: pass
                self.update_rate_spnbx.valueChanged.connect(self.eff_new_galvos_adjustMax_meth)
                
                self.jobs_window.set_anGalvo_pos_button.setEnabled(True)
                self.jobs_window.get_anGalvo_pos_button.setEnabled(True)
                self.jobs_window.fast_wantedPos_anlgGalvo_spbx.setEnabled(True)
                self.jobs_window.slow_wantedPos_anlgGalvo_spbx.setEnabled(True)
                self.jobs_window.off_fast00_anlgGalvo_spbx.setEnabled(True)
                self.jobs_window.off_slow00_anlgGalvo_spbx.setEnabled(True)
                self.jobs_window.jobs_tabWidget_2.setCurrentIndex(1)
                self.jobs_window.rst_fltr_imic.setChecked(False)
                if self.offsetX00_Galvos is None:
                    offsetX00_anlgGalvos = self.offsetX00_anlgGalvos
                else:
                    offsetX00_anlgGalvos = self.offsetX00_Galvos
                if self.offsetY00_Galvos is None:
                    offsetY00_anlgGalvos = self.offsetY00_anlgGalvos
                else:
                    offsetY00_anlgGalvos = self.offsetY00_Galvos
                self.offsetX_mm_spnbx.setValue( offsetX00_anlgGalvos)
                self.offsetY_mm_spnbx.setValue( offsetY00_anlgGalvos)
                self.offsetX_pg_curr = self.offsetX00_anlgGalvos
                self.offsetY_pg_curr = self.offsetY00_anlgGalvos
                self.use_preset_sync_dig_galv_chck.setVisible(False)
                self.load_scn_dig_galv_chck.setVisible(False)
                # self.corr_sync_inPx_spnbx.setVisible(False)
                self.fact_buffer_anlgGalvo_spbx.setVisible(True)
                self.eff_wvfrm_an_galvos_spnbx.setVisible(True)
                self.trig_safety_perc_spnbx.setVisible(True)
                self.hyst_perc_trig_spnbx.setVisible(True)
                
                # # self.sizeX_um_spbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)  # magn already trigger
                # # self.sizeY_um_spbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.frac_FOV_spn_bx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.offsetX_mm_spnbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.offsetY_mm_spnbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.yscan_radio.toggled.connect(self.up_volt_anlg_galvo_meth)
                self.jobs_window.off_fast00_anlgGalvo_spbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.jobs_window.off_slow00_anlgGalvo_spbx.valueChanged.connect(self.up_volt_anlg_galvo_meth)
                self.watch_triggalvos_dev_box.setCurrentIndex(param_ini.num_dev_watcherTrig) # #  # # Dev2
                self.anlgtriggalvos_dev_box.setVisible(True)  # # for anlg galvos
                self.aogalvos_dev_box.setVisible(True) # # for anlg galvos
                self.aogalvos_dev_box.setCurrentIndex(1) # # Dev2
                self.anlgtriggalvos_dev_box.setCurrentIndex(1) # # Dev2
                # # self.watch_triggalvos_dev_box.setCurrentIndex(1) # # Dev2
                self.up_volt_anlg_galvo_meth()
                    
            else: # NOT anlg galvos 
                self.acqline_galvo_mode_box.setCurrentIndex(0) # # readlinetime default
                try: self.update_rate_spnbx.valueChanged.disconnect(self.eff_new_galvos_adjustMax_meth)
                except TypeError: pass
                if self.stage_scan_mode != 1:
                    self.bidirec_check.setCurrentIndex(0) # bidirek
                self.jobs_window.set_anGalvo_pos_button.setEnabled(False)
                self.jobs_window.get_anGalvo_pos_button.setEnabled(False)
                self.jobs_window.fast_wantedPos_anlgGalvo_spbx.setEnabled(False)
                self.jobs_window.slow_wantedPos_anlgGalvo_spbx.setEnabled(False)
                self.jobs_window.off_fast00_anlgGalvo_spbx.setEnabled(False)
                self.jobs_window.off_slow00_anlgGalvo_spbx.setEnabled(False)
                self.jobs_window.jobs_tabWidget_2.setCurrentIndex(0)
                self.jobs_window.rst_fltr_imic.setChecked(True)
                self.eff_wvfrm_an_galvos_spnbx.setVisible(False)
                self.fact_buffer_anlgGalvo_spbx.setVisible(False)
                self.trig_safety_perc_spnbx.setVisible(False)
                self.hyst_perc_trig_spnbx.setVisible(False)
                self.watch_triggalvos_dev_box.setCurrentIndex(param_ini.numdev_watchTrig_diggalv) # # 
                self.anlgtriggalvos_dev_box.setVisible(False)  # # for anlg galvos
                self.aogalvos_dev_box.setVisible(False) # # for anlg galvos
                # # self.transXY_imgplane_anlggalv_chck.setVisible(False)

                if self.stage_scan_mode == 0:  # dig galvos
                    if self.offsetX00_Galvos is None:
                        offsetX00_digGalvos = self.offsetX00_digGalvos
                    else:
                        offsetX00_digGalvos = self.offsetX00_Galvos
                    if self.offsetY00_Galvos is None:
                        offsetY00_digGalvos = self.offsetY00_digGalvos
                    else:
                        offsetY00_digGalvos = self.offsetY00_Galvos
                    self.offsetX_mm_spnbx.setValue( offsetX00_digGalvos)
                    self.offsetY_mm_spnbx.setValue( offsetY00_digGalvos)
                    self.offsetX_pg_curr = self.offsetX00_digGalvos
                    self.offsetY_pg_curr = self.offsetY00_digGalvos
                    self.use_preset_sync_dig_galv_chck.setVisible(True)
                    self.load_scn_dig_galv_chck.setVisible(True)
                    # # self.corr_sync_inPx_spnbx.setVisible(True)
                
                try:   # only if previous alg galvo scan  
                    self.magn_obj_bx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth) 
                    # # self.sizeX_um_spbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)  # magn already trigger
                    # # self.sizeY_um_spbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                    self.frac_FOV_spn_bx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                    self.offsetX_mm_spnbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                    self.offsetY_mm_spnbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                    self.yscan_radio.toggled.disconnect(self.up_volt_anlg_galvo_meth)
                    self.jobs_window.off_fast00_anlgGalvo_spbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                    self.jobs_window.off_slow00_anlgGalvo_spbx.valueChanged.disconnect(self.up_volt_anlg_galvo_meth)
                except TypeError:
                    pass
                    
            
            if self.stage_scan_mode in (0, 3): # galvo
                self.bidirec_check.setCurrentIndex(1) # unidirek
                self.watch_triggalvos_dev_box.setVisible(True) 
                self.acqline_galvo_mode_box.setVisible(True) 
                self.dwll_time_edt.valueChanged.connect(self.dt_rate_ishg_match_meth)
                if not self.magn_init: # # false
                    self.launch_scan_button.setEnabled(False)
                    self.launch_scan_button_single.setEnabled(False)
                self.szarray_readAI_willchange_meth()
            else: # not galvos
                if not self.lock_uprate_chck.isChecked(): self.update_rate_spnbx.setValue(1/param_ini.update_time) # Hz
                self.watch_triggalvos_dev_box.setVisible(False) 
                self.acqline_galvo_mode_box.setVisible(False)
                try: self.dwll_time_edt.valueChanged.disconnect(self.dt_rate_ishg_match_meth)
                except TypeError: pass
                if not self.magn_init: # # false
                    self.launch_scan_button.setEnabled(True)
                    self.launch_scan_button_single.setEnabled(True)
            if self.stage_scan_mode == 0: # # dig galvos
                self.cancel_inline_button.setStyleSheet('font-size:5px;') # because not recommended
                self.pause_trig_sync_dig_galv_chck.setVisible(True) # only in dig. galvos
            else: # # not dig galvos
                self.cancel_inline_button.setStyleSheet('font-size:10px;')  
                self.pause_trig_sync_dig_galv_chck.setVisible(False) # only in dig. galvos          
            
            self.stage_scan_mode_before = self.stage_scan_mode_current                            
            self.stage_scan_mode_current = self.stage_scan_mode
            self.duration_change()
            # # self.duration_indic.editingFinished.emit()
            
    
    @pyqtSlot()    
    def duration_change(self):
        
        self.stage_scan_mode = self.mode_scan_box.currentIndex() # 0 for dig. galvo, 1 for stage, 2 for static, 3 for anlg galvos
        
        if self.stage_scan_mode == 1: # for stage, it depends on the speed of the fast motor

            # # stage scan
            dead_time_motor = 27.5/1000 # s
            dead_time_motorslow = 20/1000 # s
        
            if self.yscan_radio.isChecked(): # yfast
            
                # # size_slow_um = self.sizeX_um_spbx.value()
                step_fast_spnbx = self.stepY_um_edt # full spnbox
                step_slow_spnbx = self.stepX_um_edt # full spnbox
                speed_max = self.speed_max_motor_Y_spinbox.value() # mm/s
                acc_max = self.acc_max_motor_Y_spinbox.value() # mm/s2
                speed_slow_max = self.speed_max_motor_X_spinbox.value() # mm/s
                acc_slow = self.acc_max_motor_X_spinbox.value() # mm/s2
                
                nb_PX_fast = self.nbPX_Y_ind.value()
                nb_PX_slow = self.nbPX_X_ind.value()
                                
            else: # x-fast
            
                # # size_slow_um = self.sizeY_um_spbx.value()
                step_fast_spnbx = self.stepX_um_edt # full spnbox
                step_slow_spnbx = self.stepY_um_edt # full spnbox
                speed_max = self.speed_max_motor_X_spinbox.value() # mm/s
                acc_max = self.acc_max_motor_X_spinbox.value() # mm/s2
                speed_slow_max = self.speed_max_motor_Y_spinbox.value() # mm/s
                acc_slow = self.acc_max_motor_Y_spinbox.value() # mm/s2
                
                nb_PX_fast = self.nbPX_X_ind.value()
                nb_PX_slow = self.nbPX_Y_ind.value()
                
            cond_add_time_slow = int(step_slow_spnbx.value() != 0 and (self.bidirec_check.currentIndex()==0 or (self.bidirec_check.currentIndex()!=0 and param_ini.block_slow_stgXY_before_return))) # slow not stationnary and {bidirek, or Unidirek with blocking direct slow }
            
            cond_add_dead_time_unidirek = int(self.bidirec_check.currentIndex()!=0 and step_slow_spnbx.value() != 0) # slow not stationnary and unidirek (bidirek = index 0)
            
            cond_add_dead_time_bidirek = int(self.bidirec_check.currentIndex()==0 and step_slow_spnbx.value() != 0) # slow not stationnary and bidirek 
            
            dead_time_add_fast = nb_PX_slow*dead_time_motor  
            
            time_chline_slow = step_slow_spnbx.value()*1e-3/speed_slow_max + speed_slow_max/acc_slow # warning : slow must travel only a step each time
            time_chline_slow_TOT  = nb_PX_slow*(time_chline_slow*cond_add_time_slow + dead_time_motorslow*2)
            
            self.profile_mode_stgXY = self.profile_mode_cmbbx.currentIndex() + 1 # 1 for trapez, 2 for S-curve
            self.jerk_stgXY = self.jerk_fast_spnbx.value() # in mm/s3
            wait_fast_complete = (self.stagescn_wait_fast_chck.isChecked() or self.stage_scn_block_stp_chck.isChecked())

            time_acc_dec_add_fast = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(step_fast_spnbx.value()/1000, speed_max, acc_max, param_ini.trigout_maxvelreached, self.acc_offset_spbox.value(), self.dec_offset_spbox.value(), 1, 1, 1, 1, self.profile_mode_stgXY, self.jerk_stgXY)[9] # last params are not used
            
            subs_flyback = 0 # dflt
            # # \\\ calc flyback if not opt vel is used and too different fronm optimal ///// 
            if self.bidirec_check.currentIndex()!=0: # unidr
                szfst_um = step_fast_spnbx.value()*nb_PX_fast
                opt_acc_fast, opt_vel_fast, opt_vel_slow, opt_vel_fast_theo_scurve, opt_acc_fast_theo_scurve = calc_scan_param_stagescan_script.vel_acc_opt_stgscn_func(speed_max, self.jerk_fast_spnbx.value(), szfst_um, step_slow_spnbx.value(), acc_max, acc_slow) # zero parameters are not used 
                if self.profile_mode_stgXY == 1: vel_fast_opt = opt_vel_fast; accn_fast_opt = opt_acc_fast # 1 for trapez, 2 for S-curve
                else: vel_fast_opt = opt_vel_fast_theo_scurve; accn_fast_opt = opt_acc_fast_theo_scurve # Scurve
                if (abs(vel_fast_opt/speed_max - 1) > param_ini.tol_speed_flbck or abs(accn_fast_opt/acc_max - 1) > param_ini.tol_speed_flbck):
                    time_acc_dec_add_fast = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(step_fast_spnbx.value()/1000, speed_max, acc_max, param_ini.trigout_maxvelreached, None, None, 1, 1, 1, 1, self.profile_mode_stgXY, self.jerk_stgXY)[9]
                    subs_flyback = (nb_PX_fast*nb_PX_slow*self.dwll_time_edt.value()*1e-6 + time_acc_dec_add_fast*nb_PX_slow*0.5*(1+wait_fast_complete))*(1-1/nb_PX_slow) - ( (nb_PX_slow*szfst_um/1000/vel_fast_opt + time_acc_dec_add_fast*nb_PX_slow*0.5*(1+wait_fast_complete))*(1-1/nb_PX_slow) ) 
            # # print('l3407',  param_ini.tol_speed_flbck, subs_flyback) # vel_fast_opt,speed_max, accn_fast_opt, acc_max,

            # # print('time_acc_dec_add_fast ', time_acc_dec_add_fast)
                
            duration = ('%.3g' % ((nb_PX_fast*nb_PX_slow*self.dwll_time_edt.value()*1e-6 + time_acc_dec_add_fast*nb_PX_slow*0.5*(1+wait_fast_complete))*(1+(1-1/nb_PX_slow)*(1-(self.bidirec_check.currentIndex()==0))) + time_chline_slow_TOT + wait_fast_complete*(2 + 2*int(self.bidirec_check.currentIndex()!=0) + cond_add_dead_time_unidirek + 2*cond_add_dead_time_bidirek)*dead_time_add_fast - subs_flyback)) # 2 for acceleration and deceleration
            # # print('dead_f', wait_fast_complete*(2 + 2*int(self.bidirec_check.currentIndex()!=0) + cond_add_dead_time_unidirek + 2*cond_add_dead_time_bidirek)*dead_time_add_fast)
            # # print('slow', time_chline_slow_TOT )
            # # print('pixell', time_acc_dec_add_fast*nb_PX_slow*0.5*(1+wait_fast_complete)*(1+(1-1/nb_PX_slow)*(1-(self.bidirec_check.currentIndex()==0))))
   
        else: # galvo or static
            fact_trig = 1
            if (self.stage_scan_mode == 2 or self.bidirec_check.currentIndex() == 0): # # static, or bidirek
                eff_loss = 0
            else: # unidirek (non-static)
                if self.stage_scan_mode == 0: # # digital galvos
                    eff_loss = self.eff_loss_dig_galvos
                else: # # anlg galvos
                    eff_loss = 1-self.eff_wvfrm_an_galvos_spnbx.value()/100
                    fact_trig = self.trig_safety_perc_spnbx.value()/100
                    
            duration = ('%.3g' % (self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6/(1-eff_loss)*fact_trig))
            update_time=1/self.update_rate_spnbx.value() # sec
            lntime = float(duration)/self.nbPX_Y_ind.value()
            nblines_inpacket = round(update_time/lntime)
            self.update_rate_spnbx.setMaximum(1/lntime)# Hz
            if nblines_inpacket < 1: # # not even one line in packet !!
                self.update_rate_spnbx.setValue(1/lntime) # Hz
            elif (update_time > param_ini.update_time and not self.lock_uprate_chck.isChecked()): # previous long scan ?
                self.update_rate_spnbx.setValue(min(1/lntime, 1/param_ini.update_time))# Hz

        self.duration_indic.setText(duration)
        
        if (self.stage_scan_mode in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1): # # callback galvos
            self.szarray_readAI_willchange_meth()
   
    @pyqtSlot()    
    def exp_time_funcof_step_stgscn_meth(self):
        # called by change of stepX or stepY, in stage-scan
        print('exp_time_funcof_step_stgscn_meth')
        
        if self.stage_scan_mode == 1: # nothing for galvos or static
            if self.yscan_radio.isChecked(): # yfast
                step_fast = self.stepY_um_edt.value() # um
                speed_fast = self.speed_max_motor_Y_spinbox.value() # mm/s
            else: # x-fast
                step_fast = self.stepX_um_edt.value() # um
                speed_fast = self.speed_max_motor_X_spinbox.value() # mm/s
                
            dwll_time = (step_fast*1e-3)/(speed_fast)*1e6 # in us
            self.dwll_time_edt.blockSignals(True)
            self.dwll_time_edt.setValue(dwll_time) # us
            self.dwll_time_edt.blockSignals(False)
            
            self.duration_change() # is not called otherwise
        
        
    @pyqtSlot()    
    def exp_time_changed_meth(self):
        
        if not self.lock_smp_clk_chck.isChecked():
            self.read_sample_rate_spnbx.blockSignals(True)
            self.read_sample_rate_spnbx.setValue(param_ini.smp_rate_AI_dflt)
            self.read_sample_rate_spnbx.blockSignals(False)

        if self.stage_scan_mode == 1: # for stage, it depends on the speed of the fast motor
        
            if self.yscan_radio.isChecked(): # yfast
            
                speed_max_spnbx = self.speed_max_motor_Y_spinbox
                step_fast = self.stepY_um_edt.value()
            else: # x-fast
            
                speed_max_spnbx = self.speed_max_motor_X_spinbox
                step_fast = self.stepX_um_edt.value()
            
            speed_fast = (step_fast*1e-3)/(self.dwll_time_edt.value()*1e-6)
            # # print('\n in exp time meth \n : %.1f' % speed_fast)
            
            if speed_fast > self.max_vel_stage:

                # QtWidgets.QMessageBox
                
                print('\n Max val. of motor speed is %d but you asked for %.1f, I have to increase the exp. time to compensate ! \n' % (self.max_vel_stage, speed_fast)) 
                
                speed_fast = self.max_vel_stage
                
                self.exp_time = (step_fast*1e-3)/(self.max_vel_stage)*1e6 # in us
                
                self.dwll_time_edt.blockSignals(True)
                self.dwll_time_edt.setValue(self.exp_time)
                self.dwll_time_edt.blockSignals(False)
            
            speed_max_spnbx.blockSignals(True)    
            speed_max_spnbx.setValue(speed_fast)
            speed_max_spnbx.blockSignals(False)
            if self.profile_mode_cmbbx.currentIndex() +1  == 2: # s-curve
                self.adjust_vel_wrt_size() 
            else: # # trapez
                self.adjust_stage_scan_param()
            print('\n vel. value of motor fast changed only its disp value(set a vel. value or launch a scan to change it)\n')
        elif self.stage_scan_mode == 3: # for anlg new galvos
            self.eff_new_galvos_adjustMax_meth()

        self.exp_time = self.dwll_time_edt.value()
        
        self.duration_change() # direct to here for non-stage scans
            
    @pyqtSlot()    
    def adjust_steps_function_duration_time(self):
        
        
        if float(self.duration_indic.text()) == 0:
            self.duration_indic.setText('%.4g' % (2*2*param_ini.time_by_point))
        
        if self.stage_scan_mode != 1: # galvo scan or static acq
            self.nbPX_X_ind.setValue(round(math.sqrt(float(self.duration_indic.text())/float(self.dwll_time_edt.value())*1e6)))
            self.nbPX_Y_ind.setValue(round(math.sqrt(float(self.duration_indic.text())/float(self.dwll_time_edt.value())*1e6)))
            
        else: # stage scan
        
            self.duration_change() # forbidden to change the duration manually in stage scan
    
    def stgscn_chg_primary_param_meth(self):
        # is called whether by x or y scan changed, or scan mode changed
       
        print('in  stgscn_chg_primary_param_meth')
        self.acc_max_motor_X_spinbox.blockSignals(True)
        self.acc_max_motor_Y_spinbox.blockSignals(True)
        self.speed_max_motor_X_spinbox.blockSignals(True)
        self.speed_max_motor_Y_spinbox.blockSignals(True)
     
        if self.yscan_radio.isChecked(): # yfast

            speed_max_motor_fast_spinbox = self.speed_max_motor_Y_spinbox # the full spinbox
            speed_max_motor_slow_spinbox = self.speed_max_motor_X_spinbox # the full spinbox
            acc_max_motor_fast_spinbox = self.acc_max_motor_Y_spinbox # the full spinbox
            acc_max_motor_slow_spinbox = self.acc_max_motor_X_spinbox # the full spinbox
        
            sizeum_slow_spbx = self.sizeX_um_spbx # the full spinbox
            sizeum_fast_spbx = self.sizeY_um_spbx # the full spinbox
            
            # self.acc_max_motor_X_spinbox.setValue(self.acc_dflt)
            # # self.speed_max_motor_X_spinbox.setValue(self.vel_dflt)
            
        else:
            
            speed_max_motor_fast_spinbox = self.speed_max_motor_X_spinbox # the full spinbox
            speed_max_motor_slow_spinbox = self.speed_max_motor_Y_spinbox # the full spinbox
            acc_max_motor_fast_spinbox = self.acc_max_motor_X_spinbox # the full spinbox
            acc_max_motor_slow_spinbox = self.acc_max_motor_Y_spinbox # the full spinbox
            
            sizeum_slow_spbx = self.sizeY_um_spbx # the full spinbox
            sizeum_fast_spbx = self.sizeX_um_spbx # the full spinbox
            
            # # # self.acc_max_motor_Y_spinbox.setValue(self.acc_dflt)
            # # self.speed_max_motor_Y_spinbox.setValue(self.vel_dflt)

        # speed fast will be changed after
        if self.profile_mode_cmbbx.currentIndex() + 1 == 1: # trapez
            acc_max_motor_fast_spinbox.setValue(self.acc_max)
        elif self.profile_mode_cmbbx.currentIndex() +1  == 2: # s-curve
            # acc to set depends on size
            pass
        
        acc_max_motor_slow_spinbox.setValue(self.acc_max)
        
        # # *********************************************************
        # # \\\\\\\\\\ Connections to change of duration ////////////
        # # *********************************************************
        
        # # \\\\\\\ For speed to duration /////////
        
        try: # can be already done by lock scan dep.
            speed_max_motor_slow_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
        except TypeError: # no disconnect needed
            pass
        speed_max_motor_slow_spinbox.valueChanged.connect(self.duration_change) # connect the slow change in acc to duration
        try: # can be already done by lock scan dep.
            speed_max_motor_fast_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
        except TypeError: # no disconnect needed
            pass
        speed_max_motor_fast_spinbox.valueChanged.connect(self.duration_change)
        
        # # \\\\\\\ For acc. to duration /////////
        
        try: # can be already done by lock scan dep.
            acc_max_motor_slow_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
        except TypeError: # no disconnect needed
            pass
        acc_max_motor_slow_spinbox.valueChanged.connect(self.duration_change) # connect the slow change in acc to duration
        try: # can be already done by lock scan dep.
            acc_max_motor_fast_spinbox.valueChanged.disconnect(self.duration_change) # disconnect old 
        except TypeError: # no disconnect needed
            pass
        acc_max_motor_fast_spinbox.valueChanged.connect(self.duration_change) 
        # # 
        
        # # *******************************
        # # \\\\\\\\\\ trapez ////////////
        # # *******************************
        if self.profile_mode_cmbbx.currentIndex() + 1 == 1: # trapez
        # connect change of acceleration fast to change the speed fast
            try: # can be already done by lock scan dep.
                self.jerk_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            # # \\\\\\\\\\ acc. to adjust vel. ////////////
            
             # erase old S-curve case
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            # erase old S-curve case
            try: # can be already done by lock scan dep.
                speed_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: # no disconnect needed
                pass
            # # erase old S-curve Slow  case
            try: # can be already done by lock scan dep.
                speed_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase old Slow case
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            acc_max_motor_fast_spinbox.valueChanged.connect(self.adjust_vel_wrt_size) # connect the slow change in acc to duration
            
            # # \\\\\\\\\\ vel. to adjust acc-offset ////////////
            
            # erase old Slow cases
            try: # can be already done by lock scan dep.
                speed_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                speed_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase old trapez cases
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase old trapez Slow case
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            speed_max_motor_fast_spinbox.valueChanged.connect(self.adjust_stage_scan_param)
            
             # # \\\\\\\\\\ size to adjust vel, acc ////////////
             
            # erase case of S-curve
            try: # can be already done by lock scan dep.
                sizeum_slow_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                sizeum_fast_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            try: # can be already done by lock scan dep.
                sizeum_slow_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            try: # can be already done by lock scan dep.
                sizeum_fast_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase old Slow case
            try: # can be already done by lock scan dep.
                sizeum_slow_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                sizeum_fast_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            sizeum_fast_spbx.valueChanged.connect(self.adjust_vel_wrt_size)
            
            acc_max_motor_fast_spinbox.setValue(self.acc_max)
            
            # # *******************************
            # # \\\\\\\\\\ S-curve ////////////
            # # *******************************
        elif self.profile_mode_cmbbx.currentIndex() +1  == 2: # s-curve
        # connect change of speed fast to change the acceleration fast
        
            try: # can be already done by lock scan dep.
                self.jerk_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            self.jerk_fast_spnbx.valueChanged.connect(self.adjust_vel_wrt_size_scurve)
            
            # # \\\\\\\\\\ vel. to adjust acc. ////////////
            
            # erase trapez cases
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase other Slow case
            try: # can be already done by lock scan dep.
                speed_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                speed_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            speed_max_motor_fast_spinbox.valueChanged.connect(self.adjust_vel_wrt_size)
            
            # # \\\\\\\\\\ acc. to adjust vel. ////////////
            
            # erase previous Slow
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
            except TypeError: # no disconnect needed
                pass
            acc_max_motor_fast_spinbox.valueChanged.connect(self.adjust_vel_wrt_size_scurve)
            
            # # \\\\\\\\\\ acc. to adjust acc-offset ////////////
            
            # erase old trapez cases
            try: # can be already done by lock scan dep.
                speed_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            try: # can be already done by lock scan dep.
                speed_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # erase other Slow case
            try: # can be already done by lock scan dep.
                acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            # avoid double connections
            try: # can be already done by lock scan dep.
                acc_max_motor_fast_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param) # disconnect old 
            except TypeError: # no disconnect needed
                pass
            acc_max_motor_fast_spinbox.valueChanged.connect(self.adjust_stage_scan_param)

            # # \\\\\\\\\\ size to adjust vel, acc ////////////
           
            # erase old Slow case
            try: # can be already done by lock scan dep.
                sizeum_slow_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth) # disconnect old 
            except TypeError: pass # no disconnect needed
            # avoid double connections
            try: # can be already done by lock scan dep.
                sizeum_fast_spbx.valueChanged.disconnect(self.acc_vel_wrt_jerk_scurve_meth) # disconnect old 
            except TypeError: pass # no disconnect needed
                
            # erase case of trapez
            try: # can be already done by lock scan dep.
                sizeum_slow_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: pass # no disconnect needed
            try: # can be already done by lock scan dep.
                sizeum_fast_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
            except TypeError: pass # no disconnect needed
            sizeum_fast_spbx.valueChanged.connect(self.acc_vel_wrt_jerk_scurve_meth)
        
        # # *******************************
        # # \\\\\\\\\\ other ////////////
        # # *******************************
        
        # Fast is disconnected before, or connected on purpose !
        try: # can be already done by lock scan dep.
            acc_max_motor_slow_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size) # disconnect old 
        except TypeError: # no disconnect needed
            pass
        acc_max_motor_slow_spinbox.valueChanged.connect(self.adjust_vel_wrt_size)
        
        self.acc_max_motor_X_spinbox.blockSignals(False)
        self.acc_max_motor_Y_spinbox.blockSignals(False)
        self.speed_max_motor_X_spinbox.blockSignals(False)
        self.speed_max_motor_Y_spinbox.blockSignals(False)
    
        if self.profile_mode_cmbbx.currentIndex() + 1 == 1: # trapez    
            # apply all changes
            self.adjust_vel_wrt_size() # change parameters function of size

        elif self.profile_mode_cmbbx.currentIndex() +1  == 2: # s-curve
            self.acc_vel_wrt_jerk_scurve_meth() # change both values to optimal value
            
        self.scan_dependencies_changed(0) # -1 for forced
        
        self.duration_change()
    
    @pyqtSlot()    
    def x_or_y_scan_changed(self):
        # x or y scan fast in stage scan
        
        if self.stage_scan_mode == 1: # stage scan
        
            self.stgscn_chg_primary_param_meth() # see above
        
            print('\n Don`t forget to switch the wire for the DAQ in the Thorlabs back-end in the good (X or Y) slot ! \n')
    
    @pyqtSlot()        
    def adjust_vel_wrt_size(self):
        
        print('in adj vel\n')
        
        if self.stage_scan_mode == 1: # stage scan
        
            if self.yscan_radio.isChecked(): # yfast
                size_fast_um = self.sizeY_um_spbx.value() # um
                stp_slow_um = self.stepX_um_edt.value() # um
                speed_fast_spbx = self.speed_max_motor_Y_spinbox # the entire Object
                speed_slow_spbx = self.speed_max_motor_X_spinbox  # the entire Object
                acc_fast_spnbx = self.acc_max_motor_Y_spinbox # the entire Object
                acc_slow_spnbx = self.acc_max_motor_X_spinbox   # the entire Object
                pixel_size_fast_mm = self.stepY_um_edt.value()*1e-3
                
            else: # x-fast
                size_fast_um = self.sizeX_um_spbx.value() # um
                stp_slow_um = self.stepY_um_edt.value() # um
                speed_fast_spbx = self.speed_max_motor_X_spinbox  # the entire Object
                speed_slow_spbx = self.speed_max_motor_Y_spinbox  # the entire Object
                acc_fast_spnbx = self.acc_max_motor_X_spinbox   # the entire Object
                acc_slow_spnbx = self.acc_max_motor_Y_spinbox   # the entire Object
                pixel_size_fast_mm = self.stepX_um_edt.value()*1e-3 
            
            # self.speed_max_motor_Y_spinbox.setValue(0.321 + 9.782*size_fast_um*1e-3) # (in mm/s) # optimized speed, mm/s, with size_fast_um in um
            
            params = calc_scan_param_stagescan_script.vel_acc_opt_stgscn_func(speed_fast_spbx.value(), self.jerk_fast_spnbx.value(), size_fast_um, stp_slow_um, acc_fast_spnbx.value(), acc_slow_spnbx.value()) # zero parameters are not used
            # # opt_acc_fast, opt_vel_fast, opt_vel_slow, opt_vel_fast_theo_scurve, opt_acc_fast_theo_scurve 
            
            speed_slow_spbx.blockSignals(True)
            # # rounded to easily differentiate it's value from vel_fast one
            opt_vel_slow = params[2]
            speed_slow_spbx.setValue(opt_vel_slow)
            speed_slow_spbx.blockSignals(False)
            
            if self.profile_mode_cmbbx.currentIndex() +1  == 2: # s-curve
                
                if (not self.coupleaccnvel_stgscn_chck.isChecked() and self.sender() == speed_fast_spbx ):
                    print('vel accn fast decoupled')
                else: # # coupled
                    # # opt_acc_fast = (speed_fast_spbx.value()*self.jerk_fast_spnbx.value())**0.5
                    opt_acc_fast = params[0]
                    # acc_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size) # avoid infinite loops of changing
                    acc_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve) # avoid infinite loops of changing
                    acc_fast_spnbx.setValue(opt_acc_fast)
                    acc_fast_spnbx.valueChanged.connect(self.adjust_vel_wrt_size_scurve) # reconnect
                    # acc_fast_spnbx.valueChanged.connect(self.adjust_vel_wrt_size) # reconnect
                
            elif self.profile_mode_cmbbx.currentIndex() + 1 == 1: # trapez
                
                # speed_fast_spbx.valueChanged.disconnect(self.scan_dependencies_changed) # change only the disp value, no order sent to motor
                # # speed_fast_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
                # need to emit signal for change scan param
            
                # # opt_vel_fast =(size_fast_um*1e-3*acc_fast_spnbx.value()/2)**0.5
                if (not self.coupleaccnvel_stgscn_chck.isChecked() and self.sender() == acc_fast_spnbx ):
                    print('vel accn fast decoupled')
                else: # # coupled
                    opt_vel_fast = params[1]
                
                    # # # this will allow to have an integer value of oversampling
                    # # # can be dangerous because can lead to non simple offset_acceleration values
                    imposed_integer_oversampling = 0
                    if imposed_integer_oversampling:
                        opt_vel_fast_theo = opt_vel_fast
                       # time_by_px_theo = pixel_size_fast_mm/opt_vel_fast_theo # in s/pixel
                        opt_vel_fast = pixel_size_fast_mm/round(1e6*pixel_size_fast_mm/opt_vel_fast_theo)*1e6
                    # time_by_px = pixel_size_fast_mm/opt_vel_fast
                    speed_fast_spbx.setValue(opt_vel_fast) # optimized speed, mm/s, with size_fast_um in um
                    # 2 because there are acceleration and decceleration
                    # speed_fast_spbx.valueChanged.connect(self.scan_dependencies_changed)
                    # # speed_fast_spbx.valueChanged.connect(self.adjust_vel_wrt_size)

            if self.ct_adj_vel_size_msg < 1:
                
                self.ct_adj_vel_size_msg += 1
                print('\n I did not change the vel. value of motor fast for real, just the disp value (set a vel. value or launch a scan to change it)\n')
    
    @pyqtSlot()    
    def adjust_vel_wrt_size_scurve(self):
        # for S-curve only
        # is called directly by scan_depend_workerXY_togui_meth
        # signal callback jerk_fast_spnbx, jerk_slow_spnbx, acc_max_motor_fast_spinbox, acc_max_motor_slow_spinbox, sizeum_slow_spbx, sizeum_fast_spbx
        
        print('in adj vel S curve\n')
    
        if self.yscan_radio.isChecked(): # yfast
            size_fast_um = self.sizeY_um_spbx.value() # um
            acc_fast_spnbx = self.acc_max_motor_Y_spinbox   # the entire Object
            speed_fast_spbx = self.speed_max_motor_Y_spinbox # the entire Object
            
        else: # x-fast
            size_fast_um = self.sizeX_um_spbx.value() # um
            acc_fast_spnbx = self.acc_max_motor_X_spinbox   # the entire Object
            speed_fast_spbx = self.speed_max_motor_X_spinbox  # the entire Object
        
        if (not self.coupleaccnvel_stgscn_chck.isChecked() and self.sender() == acc_fast_spnbx ):
            print('vel accn fast decoupled')
        else: # # coupled
            # try:    
            #     speed_fast_spbx.valueChanged.disconnect(self.scan_dependencies_changed) # change only the disp value, no order sent to motor
            # except TypeError:
            #     pass
            try: speed_fast_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: pass
                    
            # # opt_vel_fast =(size_fast_um*1e-3*acc_fast_spnbx.value()/2)**0.5
            opt_vel_fast = calc_scan_param_stagescan_script.vel_acc_opt_stgscn_func(0, 0, size_fast_um, 0, acc_fast_spnbx.value(), 0)[1] # zero paremeters are not used
        
            speed_fast_spbx.setValue(opt_vel_fast) # optimized speed, mm/s, with size_fast_um in um
            
            # speed_fast_spbx.valueChanged.connect(self.scan_dependencies_changed) 
            speed_fast_spbx.valueChanged.connect(self.adjust_vel_wrt_size)
      
    def acc_vel_wrt_jerk_scurve_meth(self):
        # theo value optimal
        # this function is called ONLY by stgscn_chg_primary_param_meth
        # print('in adj vel wrt jerk\n')

        
        if self.yscan_radio.isChecked(): # yfast
            size_fast_um = self.sizeY_um_spbx.value() # um
            acc_fast_spnbx = self.acc_max_motor_Y_spinbox   # the entire Object
            speed_fast_spbx = self.speed_max_motor_Y_spinbox # the entire Object
            
        else: # x-fast
            size_fast_um = self.sizeX_um_spbx.value() # um
            acc_fast_spnbx = self.acc_max_motor_X_spinbox   # the entire Object
            speed_fast_spbx = self.speed_max_motor_X_spinbox  # the entire Object
           

        speed_fast_spbx.blockSignals(True)
        # acc_fast_spnbx.blockSignals(True)
        try: # can be already done by lock scan dep.
            acc_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size_scurve)
        except TypeError: # no disconnect needed
            pass
        
        # # opt_vel_fast = ((size_fast_um*1e-3)**2*self.jerk_fast_spnbx.value()/4)**(1/3)
        # # opt_acc_fast = (opt_vel_fast*self.jerk_fast_spnbx.value())**0.5
        params = calc_scan_param_stagescan_script.vel_acc_opt_stgscn_func(0, self.jerk_fast_spnbx.value(), size_fast_um, 0, 0, 0) # zero paremeters are not used
        
        opt_vel_fast = params[3]
        opt_acc_fast = params[4]
        
        print('in adj wrt jerk', opt_acc_fast, opt_vel_fast)
         
        speed_fast_spbx.setValue(opt_vel_fast)
        acc_fast_spnbx.setValue(opt_acc_fast)
        
        speed_fast_spbx.blockSignals(False)
        # acc_fast_spnbx.blockSignals(False)
        acc_fast_spnbx.valueChanged.connect(self.adjust_vel_wrt_size_scurve)

        
    @pyqtSlot()    
    def adjust_stage_scan_param(self):
        # called directl;y by easy_scn_chg
        # callback of acc_max_motor_fast_spinbox,acc_max_motor_slow_spinbox,  speed_max_motor_slow_spinbox
        print('adjust_stage_scan_param')
        
        if self.yscan_radio.isChecked(): # yfast
        
            step_fast = self.stepY_um_edt.value() # um/px
            speed_max = self.speed_max_motor_Y_spinbox.value() # mm/s
            acc_max = self.acc_max_motor_Y_spinbox.value() # mm/s2
            # size_fast_um = self.sizeY_um_spbx.value() # um
            
        else: # x-fast
                    
            step_fast = self.stepX_um_edt.value() # um/px
            speed_max = self.speed_max_motor_X_spinbox.value() # mm/s
            acc_max = self.acc_max_motor_X_spinbox.value() # mm/s2
            # size_fast_um = self.sizeX_um_spbx.value() # um
            
        self.profile_mode_stgXY = self.profile_mode_cmbbx.currentIndex() + 1 # 1 for trapez, 2 for S-curve
        self.jerk_stgXY = self.jerk_fast_spnbx.value() # in mm/s3
        
        self.trigout_stgXY_current = param_ini.trigout_maxvelreached
        self.trigout_stgXY = param_ini.trigout_maxvelreached
        
        calc_scan_param = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(step_fast/1000, speed_max, acc_max, self.trigout_stgXY, self.acc_offset_spbox.value(), 1, 1, 1, 1, 1, self.profile_mode_stgXY, self.jerk_stgXY) # last params are not used
        
        dwll_time = calc_scan_param[0]
        acceleration_offset_direct = calc_scan_param[1] 
        deceleration_offset_direct = calc_scan_param[2] 
        scan_stage_px_offset_direct = calc_scan_param[3] 
        # pixell_to_set = calc_scan_param[4] 
        # 5,6,7,8 are not used
        # acc_offset_recalc = calc_scan_param[5]
        # dec_offset_recalc = calc_scan_param[6]
        # pixell_direct_adjusted = calc_scan_param[7]
        # pixell_reverse_adjusted = calc_scan_param[8]

        # pixell_to_set = 0 # not used here
        
        self.dwll_time_edt.blockSignals(True)
        self.dwll_time_edt.setValue(dwll_time)
        self.dwll_time_edt.blockSignals(False)
        
        self.acc_offset_spbox.setValue(acceleration_offset_direct) # mm
        self.dec_offset_spbox.setValue(deceleration_offset_direct)
        
        self.acc_offset_theo_lbl.setText('%s%.5f mm)' % (self.acc_offset_theo_label_dflt, acceleration_offset_direct))
        # acceleration_offset_reverse = acceleration_offset_direct # mm        
        
        self.pixell_offset_dir_spbox.setValue(scan_stage_px_offset_direct) # in number of pixel
        
        # coeff_rev = 2.132 + 0.001*size_fast_um
        # self.pixell_offset_rev_spbox.setValue(scan_stage_px_offset_direct*coeff_rev) # avec size
        self.pixell_offset_rev_spbox.setValue(scan_stage_px_offset_direct) # in number of pixel
        
    @pyqtSlot()
    def buffer_read_change_wrt_acc_offset_meth(self):
        
        print('in adj buffer\n')
        
        self.dec_offset_spbox.setValue(self.acc_offset_spbox.value())
        
        if self.yscan_radio.isChecked(): # yfast
        
            step_fast = self.stepY_um_edt.value() # um
            speed_max = self.speed_max_motor_Y_spinbox.value() # mm/s
            acc_max = self.acc_max_motor_Y_spinbox.value() # mm/s2
            
        else: # x-fast
                    
            step_fast = self.stepX_um_edt.value() # um
            speed_max = self.speed_max_motor_X_spinbox.value() # mm/s
            acc_max = self.acc_max_motor_X_spinbox.value() # mm/s2
        
        
        self.profile_mode_stgXY = self.profile_mode_cmbbx.currentIndex() + 1 # 1 for trapez, 2 for S-curve
        self.jerk_stgXY = self.jerk_fast_spnbx.value() # in mm/s3

        pixell_to_set = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(step_fast/1000, speed_max, acc_max, param_ini.trigout_maxvelreached, self.acc_offset_spbox.value(), 1, 1, 1, 1, 1, self.profile_mode_stgXY, self.jerk_stgXY)[4] # last params are not used
    
        self.pixell_offset_dir_spbox.setValue(pixell_to_set) # in number of pixel
        
        self.pixell_offset_theo_lbl.setText('%s%.5f PX)' % (self.pixell_offset_theo_label_dflt, pixell_to_set))
        
        # # if self.bidirec_check.currentIndex() == 0: # bidirek scan
        self.pixell_offset_rev_spbox.setValue(pixell_to_set) # in number of pixel
    
    @pyqtSlot()
    def lock_stage_scan_dep_meth(self): 
    
        if self.lock_stage_scan_dep_chck.isChecked(): # lock dep. of stage scan
        
            self.acc_max_motor_X_spinbox.setEnabled(False)
            self.acc_max_motor_Y_spinbox.setEnabled(False)
            self.speed_max_motor_X_spinbox.setEnabled(False)
            self.speed_max_motor_Y_spinbox.setEnabled(False)
            self.xscan_radio.setEnabled(False)
            self.yscan_radio.setEnabled(False)
            self.bidirec_check.setEnabled(False)
            self.acc_offset_spbox.setEnabled(False)
            self.dec_offset_spbox.setEnabled(False)
            self.pixell_offset_dir_spbox.setEnabled(False)
            self.pixell_offset_rev_spbox.setEnabled(False)
            self.profile_mode_cmbbx.setEnabled(False)
            self.jerk_fast_spnbx.setEnabled(False)
            
            try:
                self.sizeX_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: # no disconnect needed
                pass
            try:
                self.sizeY_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: # no disconnect needed
                pass 
            # # self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
            # # self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
            # # self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param)
            # # self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param)
            # # self.jerk_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            
            
        else: # unlock dep. of stage scan
        
            self.acc_max_motor_X_spinbox.setEnabled(True)
            self.acc_max_motor_Y_spinbox.setEnabled(True)
            self.speed_max_motor_X_spinbox.setEnabled(True)
            self.speed_max_motor_Y_spinbox.setEnabled(True)
            self.xscan_radio.setEnabled(True)
            self.yscan_radio.setEnabled(True)
            self.bidirec_check.setEnabled(True)
            self.acc_offset_spbox.setEnabled(True)
            self.dec_offset_spbox.setEnabled(True)
            self.pixell_offset_dir_spbox.setEnabled(True)
            self.pixell_offset_rev_spbox.setEnabled(True)
            self.profile_mode_cmbbx.setEnabled(True)
            self.jerk_fast_spnbx.setEnabled(True)
            
            try:
                self.sizeX_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: # no disconnect needed
                pass
            self.sizeX_um_spbx.valueChanged.connect(self.adjust_vel_wrt_size)
            
            try:
                self.sizeY_um_spbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            except TypeError: # no disconnect needed
                pass 
            self.sizeY_um_spbx.valueChanged.connect(self.adjust_vel_wrt_size)
            
            # # try: # prevent multiple connections
            # #     self.jerk_fast_spnbx.valueChanged.disconnect(self.adjust_vel_wrt_size)
            # # except TypeError:
            # #     pass
            # # self.jerk_fast_spnbx.valueChanged.connect(self.adjust_vel_wrt_size)
            # # 
            # # try: # prevent multiple connections
            # #     self.acc_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
            # # except TypeError:
            # #     pass
            # # self.acc_max_motor_X_spinbox.valueChanged.connect(self.adjust_vel_wrt_size)
            # # 
            # # try: # prevent multiple connections
            # #     self.acc_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_vel_wrt_size)
            # # except TypeError:
            # #     pass
            # # self.acc_max_motor_Y_spinbox.valueChanged.connect(self.adjust_vel_wrt_size)
            # # 
            # # try: # prevent multiple connections
            # #     self.speed_max_motor_X_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param)
            # # except TypeError:
            # #     pass
            # # self.speed_max_motor_X_spinbox.valueChanged.connect(self.adjust_stage_scan_param)
            # # 
            # # try: # prevent multiple connections
            # #     self.speed_max_motor_Y_spinbox.valueChanged.disconnect(self.adjust_stage_scan_param)
            # # except TypeError:
            # #     pass
            # # self.speed_max_motor_Y_spinbox.valueChanged.connect(self.adjust_stage_scan_param)
    
    @pyqtSlot()
    def after_profile_mode_stgscn_changed_meth (self):
        
        if self.profile_mode_cmbbx.currentIndex() == 1: # S-curve
            self.jerk_fast_spnbx.setValue(self.jerk_stgXY_current)
        else: # trapez
            self.jerk_fast_spnbx.setValue(param_ini.jerk_mms3_trapez)

        print('Profile mode value is just indication, to effectively change it, launch a stg scan !')
        
    @pyqtSlot()
    def after_jerk_stgscn_changed_meth (self):

        print('Jerk value is just indication, to effectively change it, launch a stg scan !')
        
    @pyqtSlot()
    def set_th_res_meth(self): 
    
        self.th_xy_res_edt.setText('%.3f' % (2*(math.log(2))**(0.5)*0.325*self.lambda_bx.value()/(2**(0.5)*self.eff_na_bx.value()**0.91)))
        
        self.eff_na_bx.blockSignals(True)
        if self.eff_na_bx.value() > 1: #  # surely 40X
            self.eff_na_bx.setValue(self.eff_na_bx.value()*self.index_opt_bx.value()/1.33)
        
        elif self.index_opt_bx.value() < self.eff_na_bx.value():
            self.index_opt_bx.blockSignals(True)
            self.eff_na_bx.setValue(self.index_opt_bx.value())
            self.index_opt_bx.blockSignals(False)
        else:    
            self.th_z_res_edt.setText('%.3f' % (2*(math.log(2))**(0.5)*0.532*self.lambda_bx.value()/(2**(0.5))/(self.index_opt_bx.value()-(self.index_opt_bx.value()**2-self.eff_na_bx.value()**2)**0.5)))
        self.eff_na_bx.blockSignals(False)
        
    @pyqtSlot(float)        
    def scan_dependencies_changed(self, val):
        # # val == -1 for direct call force to change
        # # tell the worker to change vel, accn
        
        print('in scan dep., scan_thread_available =', self.scan_thread_available, '\n')
        
        if (self.stage_scan_mode !=1 or val == -1 or self.applylive_params_stgscn_chck.isChecked()): # scan Process not running
        # motorXY not in the process of stage scan, so available 
        # # for stage scan the change of parameters must not change in live the acc and vel, unless forced to.
        
            self.max_accn_x = self.acc_max_motor_X_spinbox.value()
            self.max_accn_y = self.acc_max_motor_Y_spinbox.value()
            self.max_vel_x = self.speed_max_motor_X_spinbox.value()
            self.max_vel_y = self.speed_max_motor_Y_spinbox.value()
            profile_mode_fast = self.profile_mode_cmbbx.currentIndex() + 1
            jerk_fast = self.jerk_fast_spnbx.value()
            lbl_mtr_fast = int(self.yscan_radio.isChecked()) + 1
            
            self.change_scan_dependencies_signal.emit(self.max_accn_x, self.max_accn_y, self.max_vel_x, self.max_vel_y, lbl_mtr_fast, profile_mode_fast, jerk_fast )
            # self.queue_scan_dependencies.put(self.scan_dependencies) # a list of speed, acceleration
        elif self.scan_thread_available != 1: # # 1 important    and STAGE SCAN      
            print('you can`t change scan dep. now, a scan is still running !')
            
    @pyqtSlot(float, float, float, float)        
    def scan_depend_workerXY_togui_meth(self, accn_motorX, accn_motorY, max_speed_motorX, max_speed_motorY ):
        # meth symmetrical to the next one, sent by 'change_scan_dependencies' in worker_XY,to disp in the GUI's boxes the real values effectivly set to acc and vel.
      
        self.max_accn_x = accn_motorX
        self.max_accn_y = accn_motorY
        self.max_vel_x = max_speed_motorX
        self.max_vel_y = max_speed_motorY
        
        self.vel_mtr_X_live.setText(str(round(max_speed_motorX,1)))
        self.vel_mtr_Y_live.setText(str(round(max_speed_motorY,1)))
        self.acc_mtr_X_live.setText(str(round(accn_motorX)))
        self.acc_mtr_Y_live.setText(str(round(accn_motorY)))
        
        if self.applylive_params_stgscn_chck.isChecked():
            self.acc_max_motor_X_spinbox.blockSignals(True)
            self.acc_max_motor_Y_spinbox.blockSignals(True)
            self.speed_max_motor_X_spinbox.blockSignals(True)
            self.speed_max_motor_Y_spinbox.blockSignals(True)
            self.acc_max_motor_X_spinbox.setValue(accn_motorX)
            self.acc_max_motor_Y_spinbox.setValue(accn_motorY)
            self.speed_max_motor_X_spinbox.setValue(max_speed_motorX)
            self.speed_max_motor_Y_spinbox.setValue(max_speed_motorY)
            self.acc_max_motor_X_spinbox.blockSignals(False)
            self.acc_max_motor_Y_spinbox.blockSignals(False)
            self.speed_max_motor_X_spinbox.blockSignals(False)
            self.speed_max_motor_Y_spinbox.blockSignals(False)
        
        # # if self.profile_mode_cmbbx.currentIndex() + 1 == 1: # trapez 
        # #     self.adjust_vel_wrt_size()
        # # elif self.profile_mode_cmbbx.currentIndex() + 1 == 2: # S-curve
        # #     self.adjust_vel_wrt_size_scurve()
 
    @pyqtSlot(float, float, float, float, float, float, float, float, float, int, float, tuple) 
    def calc_param_stgscan_workerXY_togui_meth(self, accn_x, accn_y, max_vel_x, max_vel_y, dwll_time, acceleration_offset_direct, acceleration_offset_reverse, offset_buffer_direct, offset_buffer_reverse, profile_mode_fast, jerk_fast, tuple_smp_rate_new ):
        # sent by the acq process in worker_XY, to change the GUI's boxes by the values effectively set of vel. and acc. during a stage scan with new parameters
        
        self.dwll_time_edt.blockSignals(True)
        self.acc_offset_spbox.blockSignals(True)
        self.dec_offset_spbox.blockSignals(True)
        self.pixell_offset_dir_spbox.blockSignals(True)
        self.pixell_offset_rev_spbox.blockSignals(True)
        self.profile_mode_cmbbx.blockSignals(True)
        self.jerk_fast_spnbx.blockSignals(True)
        
        self.dwll_time_edt.setValue(dwll_time)
        self.acc_offset_spbox.setValue(acceleration_offset_direct)
        self.dec_offset_spbox.setValue(acceleration_offset_reverse)
        self.pixell_offset_dir_spbox.setValue(offset_buffer_direct)
        self.pixell_offset_rev_spbox.setValue(offset_buffer_reverse)
        self.profile_mode_cmbbx.setCurrentIndex(profile_mode_fast - 1) # 1 (so index 0) for trapez, 2 (so index 1) for S-curve
        self.jerk_fast_spnbx.setValue(jerk_fast)
        
        self.profile_mode_cmbbx.blockSignals(False)
        self.jerk_fast_spnbx.blockSignals(False)
        self.dwll_time_edt.blockSignals(False)
        self.acc_offset_spbox.blockSignals(False)
        self.dec_offset_spbox.blockSignals(False)
        self.pixell_offset_dir_spbox.blockSignals(False)
        self.pixell_offset_rev_spbox.blockSignals(False)
        
        self.vel_mtr_X_live.setText(str(round(max_vel_x,1)))
        self.vel_mtr_Y_live.setText(str(round(max_vel_y,1)))
        self.acc_mtr_X_live.setText(str(round(accn_x)))
        self.acc_mtr_Y_live.setText(str(round(accn_y)))
        
        if len(tuple_smp_rate_new) > 0:  # # otherwise did not work
            self.read_sample_rate_spnbx.setValue(tuple_smp_rate_new[0]) # if not self.lock_smp_clk_chck.isChecked(): 
            if len(tuple_smp_rate_new) > 1: # for ISHG
                jobs_scripts.dt_ishg_setnewval_meth(self, tuple_smp_rate_new[1], tuple_smp_rate_new[2])
        
        if self.applylive_params_stgscn_chck.isChecked():
            self.acc_max_motor_X_spinbox.blockSignals(True)
            self.acc_max_motor_Y_spinbox.blockSignals(True)
            self.speed_max_motor_X_spinbox.blockSignals(True)
            self.speed_max_motor_Y_spinbox.blockSignals(True)
            self.acc_max_motor_X_spinbox.setValue(accn_x)
            self.acc_max_motor_Y_spinbox.setValue(accn_y)
            self.speed_max_motor_X_spinbox.setValue(max_vel_x)
            self.speed_max_motor_Y_spinbox.setValue(max_vel_y)
            self.acc_max_motor_X_spinbox.blockSignals(False)
            self.acc_max_motor_Y_spinbox.blockSignals(False)
            self.speed_max_motor_X_spinbox.blockSignals(False)
            self.speed_max_motor_Y_spinbox.blockSignals(False)
    
    @pyqtSlot(tuple) 
    def setnewparams_scan_meth(self, params):
    # # called by go_galvos_scan_func_mp after init, itself called by new_img_flag_queue.put(tuple) in data_acq 
    
        self.read_sample_rate_spnbx.setValue(params[0]) # verify it's ok if not self.lock_smp_clk_chck.isChecked(): 
        if params[1] is not None: # change in update time
            self.update_rate_spnbx.blockSignals(True)
            self.update_rate_spnbx.setValue(1/params[1]) # rate
            self.update_rate_spnbx.blockSignals(False)
        if len(params) > 2: # for ISHG
            jobs_scripts.dt_ishg_setnewval_meth(self, params[2], params[3])
            
    @pyqtSlot(float)    
    def dt_rate_ishg_match_meth(self, val):
        # # -1 for direct call
        
        exptime = self.dwll_time_edt.value()*1e-6 # us to sec
        # if self.sender() in (self.jobs_window.deadtimeEnd_us_EOMph_spbx, self.jobs_window.deadtimeBeg_us_EOMph_spbx):
        # print(self.sender().objectName())
        if self.sender() == self.read_sample_rate_spnbx:
            rate_fixed = True
            dtb_fixed = dte_fixed = expfixed = False
        elif (val ==-1 or self.sender() in (self.jobs_window.deadtimeEnd_us_EOMph_spbx, self.jobs_window.deadtimeBeg_us_EOMph_spbx)):#, -1 for direct call from other func
            rate_fixed = expfixed = False
            dtb_fixed = dte_fixed = True
            # # exptime = self.jobs_window.ramptime_us_EOMph_spbx.value() + self.ishg_EOM_AC[-2][1]+ self.ishg_EOM_AC[-2][2] # # fixed already
        if (self.sender() == self.dwll_time_edt or val ==-2): # # -2 for sent by acqmode_galvoline
            rate_fixed = False
            dtb_fixed = dte_fixed = expfixed = True # for them not to be changed
        if (self.ishg_EOM_AC[0] and val != -1): # # fast ISHG EOM, -1 will cause a loop infinite
            self.EOMph_params_ch_meth()
        # # print(self.sender(), not (self.ishg_EOM_AC[0]) ,val == -1, self.stage_scan_mode, self.pause_trig_sync_dig_galv_chck.isChecked(),  self.acqline_galvo_mode_box.currentIndex() )
        if (self.sender() in (self.read_sample_rate_spnbx, self.dwll_time_edt) and (not (self.ishg_EOM_AC[0]) or val == -1) and not (self.stage_scan_mode in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1)): return # # not fast ISHG EOM
        if self.dev_to_use_AI_box.currentIndex() == 0: # # 6110
            min_rate = 0.1e6  # Hz
            max_rate = param_ini.max_rate_multiRead_DAQ6110 # 
        else:
            min_rate = 0.1  # Hz
            max_rate = param_ini.max_rate_multiRead_DAQ6259 # 
        
        if self.lock_smp_clk_chck.isChecked(): rate_fixed=True
        rate0 = self.read_sample_rate_spnbx.value()
        dt0 = self.ishg_EOM_AC[-2]
        rate, self.ishg_EOM_AC, exptime = jobs_scripts.ishgEOM_adjdtvsrate_func(rate0, max_rate, min_rate, param_ini.master_rate_daq_normal, self.ishg_EOM_AC, exptime, rate_fixed, dtb_fixed, dte_fixed, expfixed) # # adjust if necessary rate or dead times to match
        str_sup= str(self.ishg_EOM_AC[-2]) + 'fixed rate dtb dte exptime '+'%r,%r,%r,%r '%(rate_fixed, dtb_fixed, dte_fixed, expfixed)+ self.sender().objectName() if self.ishg_EOM_AC[0] else ''
        print('%.1fHz, %fsec' % (rate, exptime), str_sup)
        
        if dt0 != self.ishg_EOM_AC[-2]:
            jobs_scripts.dt_ishg_setnewval_meth(self, self.ishg_EOM_AC[-2][1], self.ishg_EOM_AC[-2][2])
        
        if (not rate_fixed and (self.ishg_EOM_AC[0] or expfixed)):  
            if rate0 != rate: 
                self.read_sample_rate_spnbx.blockSignals(True)
                self.read_sample_rate_spnbx.setValue(rate)
                self.read_sample_rate_spnbx.blockSignals(False)
                print(' !! warning I changed rate to ', rate)
                
        if not expfixed:
            try: self.dwll_time_edt.valueChanged.disconnect(self.exp_time_changed_meth)
            except TypeError: pass
            try: self.dwll_time_edt.valueChanged.disconnect(self.dt_rate_ishg_match_meth)
            except TypeError: pass
            self.dwll_time_edt.setValue(exptime*1e6) # in us
            self.dwll_time_edt.valueChanged.connect(self.exp_time_changed_meth) # reconn
            self.dwll_time_edt.valueChanged.connect(self.dt_rate_ishg_match_meth)  # reconn
        
    @pyqtSlot()    
    def after_fov_perc_changed_meth(self):
         
        if self.stage_scan_mode_current == 0 or self.stage_scan_mode_current == 3: # # galvos
            self.sizeX_um_spbx.setValue(self.size_um_fov*self.frac_FOV_spn_bx.value()/100/(self.magn_obj_bx.value()/self.obj_mag))
            self.sizeY_um_spbx.setValue(self.size_um_fov*self.frac_FOV_spn_bx.value()/100/(self.magn_obj_bx.value()/self.obj_mag))
        
 
    def sizeXY_change_FOV_meth(self, condX):
        # # not a PyQtSlot
        
        # # self.frac_FOV_spn_bx.blockSignals(True) # avoid infinite loop on buttons
        self.frac_FOV_spn_bx.valueChanged.disconnect(self.after_fov_perc_changed_meth) # there is another signal useful
        
        if self.square_img_chck.isChecked(): # force square imgs
            
            size_um = (self.sizeX_um_spbx.value()*self.sizeY_um_spbx.value())**0.5
        else: # rect imgs
            if condX:
                size_um = self.sizeX_um_spbx.value()
            else:
                size_um = self.sizeY_um_spbx.value()
                
        if self.stage_scan_mode == 3: # anlg new galvo
            eff_val =self.eff_wfrm_anlggalv_dflt
            self.new_szX_um = self.sizeX_um_spbx.value() 
            # # \\\ empirical ////
            if self.new_szX_um >= 200: eff_val = 75 # %
            elif (self.new_szX_um < 200 and self.new_szX_um > 100): eff_val = 70 # %
            elif (self.new_szX_um <= 100 and self.new_szX_um > 70): eff_val = 65 # %
            elif self.new_szX_um <= 70: eff_val = 60 # %
            # self.eff_wvfrm_an_galvos_spnbx.blockSignals(True)
            self.eff_wvfrm_an_galvos_spnbx.valueChanged.disconnect(self.duration_change)
            self.eff_wvfrm_an_galvos_spnbx.setValue(eff_val)
            self.eff_wvfrm_an_galvos_spnbx.valueChanged.connect(self.duration_change)
            self.duration_change()
            
        self.frac_FOV_spn_bx.setValue(size_um/self.size_um_fov*(self.magn_obj_bx.value()/self.obj_mag)*100)
        
        # # self.frac_FOV_spn_bx.blockSignals(False) # avoid infinite loop on buttons
        self.frac_FOV_spn_bx.valueChanged.connect(self.after_fov_perc_changed_meth)
        
    @pyqtSlot()    
    def after_sizeX_um_changed_meth(self):
        
        if self.square_img_chck.isChecked(): # force square imgs
            self.sizeY_um_spbx.setValue(self.sizeX_um_spbx.value()) # # the other dir
            
        if (self.square_img_chck.isChecked() or self.xscan_radio.isChecked()): # force square imgs or yfast
            stp = self.sizeX_um_spbx.value()/self.nbPX_X_ind.value()
            self.stepX_um_edt.blockSignals(True)
            self.stepX_um_edt.setValue(stp)
            self.stepX_um_edt.blockSignals(False)
            if (self.square_px_chck.isChecked() and not self.square_img_chck.isChecked()): # force square pxs (and not imgs)
                # # self.stepX_um_edt.blockSignals(True)
                self.stepY_um_edt.setValue(self.stepX_um_edt.value())
                # # self.stepX_um_edt.blockSignals(False) # # otherwise it changes the nb of pixels
        else: # # xfast and not square img
        # # step is fixed by fast !
            self.nbPX_X_ind.setValue(self.sizeX_um_spbx.value()/self.stepX_um_edt.value())
            
            # # self.nbPX_Y_ind.blockSignals(True); self.nbPX_Y_ind.setValue(self.sizeY_um_spbx.value()/self.stepX_um_edt.value()) ; self.nbPX_Y_ind.blockSignals(False) # # it's normal that it seems "inverted", the sizeX change the nbpxY
            # # self.duration_change()
        
        self.sizeXY_change_FOV_meth(True) # see above
        
    @pyqtSlot()    
    def after_sizeY_um_changed_meth(self):
        
        if self.square_img_chck.isChecked(): # force square imgs
            self.sizeX_um_spbx.setValue(self.sizeY_um_spbx.value()) # # the other dir
            
        if (self.square_img_chck.isChecked() or self.yscan_radio.isChecked()): # force square imgs or yfast
            stp = self.sizeY_um_spbx.value()/self.nbPX_Y_ind.value()
            self.stepY_um_edt.blockSignals(True)
            self.stepY_um_edt.setValue(stp)
            self.stepY_um_edt.blockSignals(False)
            if (self.square_px_chck.isChecked() and not self.square_img_chck.isChecked()): # force square pxs (and not imgs)
                # # self.stepX_um_edt.blockSignals(True)
                self.stepX_um_edt.setValue(self.stepY_um_edt.value())
                # # self.stepX_um_edt.blockSignals(False) # # otherwise it changes the nb of pixels
        else: # # xfast and not square img
        # # step is fixed by fast !
            self.nbPX_Y_ind.setValue(self.sizeY_um_spbx.value()/self.stepY_um_edt.value())
            
            # # self.nbPX_X_ind.blockSignals(True); self.nbPX_X_ind.setValue(self.sizeX_um_spbx.value()/self.stepY_um_edt.value()) ; self.nbPX_X_ind.blockSignals(False)   # # it's normal that it seems "inverted", the sizeY change the nbpxX
            # # self.duration_change()
        
        self.sizeXY_change_FOV_meth(False) # see above
        
    @pyqtSlot()
    def sampling_changed_meth(self): 
    
        self.nbPX_X_ind.valueChanged.disconnect(self.nb_px_xy_to_sampling_meth) # protection against infinite loops
        self.nbPX_Y_ind.valueChanged.disconnect(self.nb_px_xy_to_sampling_meth) # protection against infinite loops
    
        # pixel_objective_20X = 1.4 # to be controlled !
        if self.sampling_bx.value() != 0:
            stepx = self.sizeX_um_spbx.value()/self.size_um_fov/self.sampling_bx.value()
            stepy = self.sizeY_um_spbx.value()/self.size_um_fov/self.sampling_bx.value()
        else:
            stepx = 0
            stepy = 0
        
        self.stepX_um_edt.setValue(stepx)
        self.stepY_um_edt.setValue(stepy)
        
        self.nbPX_X_ind.valueChanged.connect(self.nb_px_xy_to_sampling_meth) # protection against infinite loops
        self.nbPX_Y_ind.valueChanged.connect(self.nb_px_xy_to_sampling_meth) # protection against infinite loops
        
    @pyqtSlot()
    def stepX_um_changed_meth(self): 
    
        if self.stepX_um_edt.value() != 0:
            self.nbPX_X_ind.setValue(self.sizeX_um_spbx.value()/self.stepX_um_edt.value()) # has to be an int
            
            if self.square_px_chck.isChecked(): # force square pxs
                self.stepY_um_edt.setValue(self.stepX_um_edt.value())
                
            if (self.mode_scan_box.currentIndex() == 1 and not self.xscan_radio.isChecked()): # yfast, so X slow
                self.adjust_vel_wrt_size() # adjust velocity
            
        else:
            self.nbPX_X_ind.setValue(self.sizeX_um_spbx.value())  # allows you to do a scan in Y, with a stationnary scan in X
        
    @pyqtSlot()
    def stepY_um_changed_meth(self): 
    
        if self.stepY_um_edt.value() != 0:
            self.nbPX_Y_ind.setValue(self.sizeY_um_spbx.value()/self.stepY_um_edt.value())
            
            if self.square_px_chck.isChecked(): # force square pxs
                self.stepX_um_edt.setValue(self.stepY_um_edt.value())
                
            if (self.mode_scan_box.currentIndex() == 1 and self.xscan_radio.isChecked()): # Xfast, so y slow
                self.adjust_vel_wrt_size() # adjust velocity
        else:
            self.nbPX_Y_ind.setValue(self.sizeY_um_spbx.value()) # allows you to do a scan in X, with a stationnary scan in Y
    
    @pyqtSlot()
    def nb_px_x_changed_meth(self):
        
        self.stepX_um_edt.blockSignals(True)
        if self.nbPX_X_ind.value() != 0:
            self.stepX_um_edt.setValue(self.sizeX_um_spbx.value()/self.nbPX_X_ind.value()) # has to be an int
            if self.square_img_chck.isChecked(): # force square imgs
                self.nbPX_Y_ind.setValue(self.nbPX_X_ind.value())
            elif (self.square_px_chck.isChecked() and self.stepY_um_edt.value() != self.stepX_um_edt.value()): # force square pxs (and not imgs)
                self.stepY_um_edt.setValue(self.stepX_um_edt.value())
            # # elif self.square_px_chck.isChecked(): # force square pxs
            # #     self.nbPX_Y_ind.setValue(self.sizeY_um_spbx.value()/self.stepX_um_edt.value())
                
        else:
            self.stepX_um_edt.setValue(0)
        self.stepX_um_edt.blockSignals(False)
        
        if self.stage_scan_mode == 3: # for anlg new galvos
            self.eff_new_galvos_adjustMax_meth()
            
    @pyqtSlot()
    def nb_px_y_changed_meth(self):
        
        self.stepY_um_edt.blockSignals(True)
        if self.nbPX_Y_ind.value() != 0:
            self.stepY_um_edt.setValue(self.sizeY_um_spbx.value()/self.nbPX_Y_ind.value())
            if self.square_img_chck.isChecked(): # force square imgs
                self.nbPX_X_ind.setValue(self.nbPX_Y_ind.value())
            elif (self.square_px_chck.isChecked() and self.stepY_um_edt.value() != self.stepX_um_edt.value()): # force square pxs (and not imgs)
                self.stepX_um_edt.setValue(self.stepY_um_edt.value())
            # # elif self.square_px_chck.isChecked(): # force square pxs
            # #     self.nbPX_X_ind.setValue(self.sizeX_um_spbx.value()/self.stepY_um_edt.value())

        else:
            self.stepY_um_edt.setValue(0)
        self.stepY_um_edt.blockSignals(False)
        
        if self.stage_scan_mode == 3: # for anlg new galvos
            self.eff_new_galvos_adjustMax_meth()
            
    def nb_px_xy_to_sampling_meth(self):
        
        self.sampling_bx.blockSignals(True)
        if self.stepY_um_edt.value() != 0:
            self.sampling_bx.setValue((self.sizeX_um_spbx.value()*self.sizeY_um_spbx.value())**0.5/self.size_um_fov/(self.stepX_um_edt.value()*self.stepY_um_edt.value())**0.5)
        else:
            self.sampling_bx.setValue(0)
        
        self.sampling_bx.blockSignals(False)
            
    @pyqtSlot()        
    def nyquist_slider_changed_meth(self):
        
        step_to_set = ((self.nyquist_slider.value()/50)**(1/0.4)*(float(self.th_xy_res_edt.text()))/2)
        
        self.stepX_um_edt.blockSignals(True)
        self.stepY_um_edt.blockSignals(True)
        self.stepX_um_edt.setValue(step_to_set) 
        self.stepY_um_edt.setValue(step_to_set) 
        self.stepX_um_changed_meth() # it's not done otherwise
        self.stepY_um_changed_meth() # it's not done otherwise
        self.stepX_um_edt.blockSignals(False)
        self.stepY_um_edt.blockSignals(False)
        
    @pyqtSlot()        
    def nyquist_slider_finished_meth(self):
        
        step_to_set = ((self.nyquist_slider.value()/50)**(1/0.4)*(float(self.th_xy_res_edt.text()))/2)
        # print(step_to_set)
        self.stepX_um_edt.setValue(step_to_set) 
        self.stepY_um_edt.setValue(step_to_set) 
        
        # self.nbPX_X_ind.setValue(round(
        # self.nbPX_Y_ind.setValue(step_to_set)
        
    @pyqtSlot()        
    def change_nyquist_meth(self):
        # law in **0.4 because linear is too violent
        
        self.nyquist_slider.blockSignals(True)
        real_val = float(self.th_xy_res_edt.text())/2/((self.stepX_um_edt.value()*self.stepY_um_edt.value())**0.5)
        val = round(50*(real_val)**0.4)
        # from 0% to 50% , **0.4 to have a non-linear scale
        # print(val)
        self.nyquist_slider.setValue(val )
        self.nyquist_slider.blockSignals(False)
        
        self.nyquist_real_spbx.setText('%.1f' % real_val)
        
    @pyqtSlot(float)        
    def read_sample_rate_changed_meth(self, sample_rate):
                
        if self.sample_rate_current != sample_rate:
            max_rate_multiRead_DAQCard = param_ini.max_rate_multiRead_DAQ6110 if self.dev_to_use_AI_box.currentIndex() == 0 else param_ini.max_rate_multiRead_DAQ6259
            if sample_rate > max_rate_multiRead_DAQCard:
                sample_rate = max_rate_multiRead_DAQCard
            
            if self.stage_scan_mode == 0: # digital galvos
                
                if (self.timebase_ext_diggalvo_chck.isChecked() and sample_rate > param_ini.clock_galvo_digital/param_ini.min_timebase_div): # max rate
                # implictly assume that param_ini.clock_galvo_digital/param_ini.min_timebase_div < max_rate_multiRead_DAQCard, otherwise no problem
                    sample_rate = param_ini.clock_galvo_digital/param_ini.min_timebase_div
                    
                if sample_rate > 1/param_ini.SM_cycle: #most cases
                    if sample_rate % 1/param_ini.SM_cycle: # not a multiple
                        sample_rate -= (sample_rate % 1/param_ini.SM_cycle)
                else:
                    r = 1/param_ini.SM_cycle % sample_rate
                    if r: # not a multiple
                        sample_rate = param_ini.SM_cycle/math.ceil(param_ini.SM_cycle/r)
            
            if sample_rate < 1/(self.dwll_time_edt.value()*1e-6): # not even one point per pixel
                sample_rate = 1/(self.dwll_time_edt.value()*1e-6)
            if sample_rate < param_ini.master_rate_daq_normal/param_ini.max_divider_master_rate_daq: # minimal rate in theory
                sample_rate = param_ini.master_rate_daq_normal/param_ini.max_divider_master_rate_daq
            
            self.read_sample_rate_spnbx.blockSignals(True)
            self.read_sample_rate_spnbx.setValue(sample_rate)
            self.read_sample_rate_spnbx.blockSignals(False)
            
            self.sample_rate_current = sample_rate
            if (self.stage_scan_mode in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1): # # callback galvos
                self.szarray_readAI_willchange_meth()
        
    @pyqtSlot()        
    def square_img_changed_meth(self):
        # force square img or not
        
        if self.square_img_chck.isChecked(): # force square img
            self.old_rect_sizeXum = self.sizeX_um_spbx.value()
            self.old_rect_sizeYum = self.sizeY_um_spbx.value()
            
            if self.old_rect_sizeXum != self.old_rect_sizeYum:
                self.sizeY_um_spbx.blockSignals(True)
                self.sizeY_um_spbx.setValue(self.old_rect_sizeXum) # X dictates the square size in um
                self.sizeY_um_spbx.blockSignals(False)
                self.nbPX_Y_ind.blockSignals(True)
                self.nbPX_Y_ind.setValue(self.nbPX_X_ind.value()) # X dictates the square size in um
                self.nbPX_Y_ind.blockSignals(False)
                self.sizeY_um_spbx.valueChanged.emit(self.sizeY_um_spbx.value())
        
        else: # do not force square img
            self.sizeX_um_spbx.setValue(self.old_rect_sizeXum)
            self.sizeY_um_spbx.setValue(self.old_rect_sizeYum)
            
        self.square_px_changed_meth()
            
    @pyqtSlot()        
    def square_px_changed_meth(self):
        # force square px or not
        
        if self.square_px_chck.isChecked(): # force square px
            if self.stepX_um_edt.value() > self.stepY_um_edt.value():
                self.stepY_um_edt.setValue(self.stepX_um_edt.value()) # X dictates the square size in um
            elif self.stepX_um_edt.value() < self.stepY_um_edt.value():
                self.stepX_um_edt.setValue(self.stepY_um_edt.value()) # Y dictates the square size in um
    
    @pyqtSlot()        
    def stgscn_Easymode_changed_meth(self): 
    
   #    #   print('In da club')
   
        if self.xscan_radio.isChecked(): # xfast
            acc_slow_spnbx = self.acc_max_motor_Y_spinbox
        else: # Yfast
            acc_slow_spnbx = self.acc_max_motor_X_spinbox
        acc_slow_spnbx.blockSignals(True)
        acc_slow_spnbx.setValue(self.acc_max) # # ready for scan
        acc_slow_spnbx.blockSignals(False)

        if self.modeEasy_stgscn_cmbbx.currentIndex() == 0: # fastest : bidirek trapez dflt
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:coral;')
            self.profile_mode_cmbbx.setCurrentIndex(0) # trapez
            self.bidirec_check.setCurrentIndex(0) # unidirek
            self.adjust_stage_scan_param()
        elif self.modeEasy_stgscn_cmbbx.currentIndex() == 1: # super fast : unidirek trapez dflt
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:darksalmon;')
            self.profile_mode_cmbbx.setCurrentIndex(0) # trapez
            self.bidirec_check.setCurrentIndex(1) # unidirek
            self.adjust_stage_scan_param()
            
        elif self.modeEasy_stgscn_cmbbx.currentIndex() == 2: # safe slow
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:gold;')
            self.profile_mode_cmbbx.setCurrentIndex(1) # S-curve
            self.bidirec_check.setCurrentIndex(0) # bidirek
            self.adjust_stage_scan_param()
            
        elif self.modeEasy_stgscn_cmbbx.currentIndex() == 3: # safest
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:lightgreen;') # lightgreen # greenyellow
            self.profile_mode_cmbbx.setCurrentIndex(1) # S-curve
            self.bidirec_check.setCurrentIndex(1) # unidirek
            self.adjust_stage_scan_param()
            
        elif self.modeEasy_stgscn_cmbbx.currentIndex() == 4: # add. mode
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:skyblue;')
            self.profile_mode_cmbbx.setCurrentIndex(0) # trapez
            self.bidirec_check.setCurrentIndex(1) # unidirek
            self.adjust_stage_scan_param()
            self.acc_offset_spbox.setValue(6*self.acc_offset_spbox.value()) # max(self.sizeX_um_spbx.value()/1000/2, 6*self.acc_offset_spbox.value()))
            
        elif self.modeEasy_stgscn_cmbbx.currentIndex() == 5: # add. mode 2
            self.modeEasy_stgscn_cmbbx.setStyleSheet('background-color:lightsteelblue;')
            self.profile_mode_cmbbx.setCurrentIndex(0) # trapez
            self.bidirec_check.setCurrentIndex(0) # bidirek
            self.adjust_stage_scan_param()
            offs00 = self.acc_offset_spbox.value()
            self.acc_offset_spbox.setValue(6*offs00) # max(self.sizeX_um_spbx.value()/1000/2, 6*offs00))
            self.dec_offset_spbox.setValue(self.dec_offset_spbox.value() + offs00/10) # empirical # max(self.sizeX_um_spbx.value()/1000/2, self.dec_offset_spbox.value() + offs00/10))
        
        if self.profile_mode_cmbbx.currentIndex()  == 0: # # trapez
            self.adjust_vel_wrt_size()
        elif self.profile_mode_cmbbx.currentIndex() == 1: # # Scurve
            self.adjust_vel_wrt_size_scurve()
        
    
    @pyqtSlot(int)    
    def stage_scn_block_stp_chg_meth(self, v):    
        if not v: # not checked #self.stage_scn_block_stp_chck.isChecked()
            self.stagescn_wait_fast_chck.setEnabled(True)
        else:
            self.stagescn_wait_fast_chck.setChecked(True)
            self.stagescn_wait_fast_chck.setEnabled(False) # no modif anymore
        self.duration_change()
    
    @pyqtSlot(int)    
    def stgscn_block_ornot_meth(self, v):
        if v == 0: # trapez
            self.stage_scn_block_stp_chck.setChecked(False)
            self.stagescn_wait_fast_chck.setChecked(False)
        else: # s-curve
            self.stage_scn_block_stp_chck.setChecked(True)
            self.stagescn_wait_fast_chck.setChecked(True)
        
    
        ## scan definition
    
    @pyqtSlot()    
    def cancel_scan_meth(self):
        
        if self.sender() == self.cancel_scan_button:
            bef = '\n --- User '; aft =  ' ! --- \n'
        else:
            bef = ''; aft =''
        
        print('%scanceled %s' % (bef, aft))
                
        self.number_img_done = self.nb_img_max
        
        if not(self.count_avg_job is None): # job scan, not a classic scan
            jobs_scripts.cancel_meth(self)
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = self.wait_flag_apt_current    
        
        try:# empty the order queue
            while True:
                self.queue_com_to_acq.get_nowait() # empty the queue
        except queue.Empty: # if empty, it raises an error (or if worker scan undefined)
            pass
            
        # if not ((self.connect_new_img_to_move_trans or self.connect_end_z_to_move_trans) or (self.connect_new_img_to_move_Z_obj or self.connect_end_ps_to_move_Z)):
        #     self.queue_com_to_acq.put([0]) # poison-pill to exit the process of acquisition_data, the latter will kill other processes via their pipes
        #     
        if self.count_avg_job is not None: # job scan, not a classic scan
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = self.wait_flag_apt_current    
        # else: # not a job, normal scan
        # # self.queue_com_to_acq.put([0]) # just order to stop acq.
        
        self.acq_name_edt.setText(self.job_name_previous)
        
        if self.use_shutter_combo.currentIndex(): # only if job finished, and shutter used
            self.shutter_outScan_mode()
    
    @pyqtSlot()    
    def cancel_inline_meth(self):
        # normal cancel ALREADY called on click button
        
        if self.sender() == self.cancel_inline_button:
            bef = '\n --- User '; aft =  ' ! --- \n'
        else:
            bef = ''; aft =''
        
        print('%scanceled (in-line)%s' % (bef, aft))
        
        if self.count_avg_job is not None: # job scan, not a classic scan
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = self.wait_flag_apt_current    

        self.number_img_done = self.nb_img_max
        # # keep it in case of cancel meth too late
        
        # jobs_scripts.cancel_meth(self)
        
        # # if self.stage_scan_mode == 1: # is 2 for static acq
        # # self.cancel_scan_meth() # cancel classic
        # already called on click button
        
        self.queue_special_com_acq_stopline.put('stop')  # for scan stage mode, cancel during acquisition

     
    @pyqtSlot()        
    def force_single_scan_meth(self): 
    
        self.force_single_scan = 1
        
        self.define_if_new_scan()
            
    @pyqtSlot()        
    def define_if_new_scan(self):
        # # for galvo or stage scan
        
        if self.sender() ==  self.launch_scan_button: # not single
            self.count_avg_job = None # not a job
        
        if self.stage_scan_mode == 0:
            
            msg_scan = 'new galvo digital scan'
        elif self.stage_scan_mode == 1: # stage scan
            if (self.chck_homed == 0 and not self.debug_mode_stgscn):
                print(param_ini.notXY_homed_msg)
                return # outside this function
            msg_scan = 'stage scan'
            
            self.reset_prev_vel_acc_scnstg_meth() # # put prev vel and acc
            # # was useful when there was only one indicator for acc and vel., and self.vel_acc_X_reset_by_move = True at each scan end
            
        elif self.stage_scan_mode == 2:
            msg_scan = 'static scan'
        elif self.stage_scan_mode == 3:
            msg_scan = 'galvo ANLG scan'
            
        print()
        print(' --- new %s ---' % msg_scan)
        print()
        
        if self.imic_was_init_var:
            if self.filter_bottom_choice.currentIndex() == param_ini.block_bottom_slider_pos: # block
                self.filter_bottom_choice.setCurrentIndex(self.filter_bot_choice_curr_index) # empty
                time.sleep(param_ini.wait_time_chg_filter_sec) # sec
                                
            if self.stage_scan_mode == 0: # dig galvos, path of the bottom
                if self.filter_bottom_choice.currentIndex() == param_ini.mirrordirect_bottom_slider_pos: # mirror silver
                    self.filter_bottom_choice.setCurrentIndex(self.diggalv_bottom_slider_pos) # empty
                    time.sleep(param_ini.wait_time_chg_filter_sec) # sec
                    
            elif (self.stage_scan_mode == 1 or self.stage_scan_mode == 3): # stage path of anlg galvos
                if self.filter_bottom_choice.currentIndex() == param_ini.empty_bottom_slider_pos: # empty
                    pos = self.anlggalv_bottom_slider_pos if self.stage_scan_mode == 3 else self.stgscn_bottom_slider_pos
                    self.filter_bottom_choice.setCurrentIndex(pos) # mirror silver
                    time.sleep(param_ini.wait_time_chg_filter_sec) # sec
         
        if self.force_single_scan:
            self.nb_img_max = 1
            self.force_single_scan = 0
        else:
            self.nb_img_max = self.nb_img_max_box.value()
        
        self.number_img_done = 0
        
        self.obj_mag = self.magn_obj_bx.value()
        self.external_clock = self.ext_smp_clk_chck.isChecked()
        self.exp_time = self.dwll_time_edt.value() # us 
        self.new_szX_um = self.sizeX_um_spbx.value() 
        self.new_szY_um = self.sizeY_um_spbx.value()
        self.px_sz_x = self.stepX_um_edt.value()
        self.px_sz_y = self.stepY_um_edt.value()
        self.nb_px_x = round(self.nbPX_X_ind.value())
        self.nb_px_y = round(self.nbPX_Y_ind.value())
        self.nb_bins_hist = self.nb_bins_hist_box.value()
        self.center_x = self.offsetX_mm_spnbx.value() # in mm !
        self.center_y = self.offsetY_mm_spnbx.value() # in mm !
        self.real_time_disp = self.real_time_disp_chck.isChecked()
        self.unidirectional = self.bidirec_check.currentIndex() # unidirec is 1 or 2, 0 for bidirek
        self.y_fast = self.yscan_radio.isChecked() # y fast
        self.update_time = 1/self.update_rate_spnbx.value() # sec # param_ini.update_time # for now
        self.time_base_ext = self.timebase_ext_diggalvo_chck.isChecked()
        # self.clrmap_nb = 
        sampleRateRead = self.read_sample_rate_spnbx.value()
        self.nb_accum = self.nb_packet_acc_spnbx.value()
        self.scan_xz = self.scan_xz_chck.isChecked()
        DSP_scan_list = []
        self.read_buffer_offset_direct = self.pixell_offset_dir_spbox.value() # in PX
        self.read_buffer_offset_reverse = self.pixell_offset_rev_spbox.value() # in PX
        self.currentDevice_AI = self.dev_to_use_AI_box.currentIndex() # # 0 for 6110, 1 for 6259
        self.eff_wvfrm_an_galvos = self.eff_wvfrm_an_galvos_spnbx.value() # # in % # efficiency of the ramp, taking into account non-linear parts of the ramp
        self.mult_trig_fact_anlg_galv = self.trig_safety_perc_spnbx.value()/100 # # percent/100
        self.trig_perc_hyst = self.hyst_perc_trig_spnbx.value()
        self.off_fast_anlgGalvo = self.jobs_window.off_fast00_anlgGalvo_spbx.value()
        self.off_slow_anlgGalvo = self.jobs_window.off_slow00_anlgGalvo_spbx.value()
        self.fact_buffer_anlgGalvo = round(self.fact_buffer_anlgGalvo_spbx.value())
        self.autoscalelive_plt = self.jobs_window.autoscalelive_plt_cmb.currentIndex() # # 1 for Live, 0 for 10 1st lines, 2 for X% range
        self.lock_smprate = self.lock_smp_clk_chck.isChecked()
        self.lock_uptime = self.lock_uprate_chck.isChecked()
        if self.autoscalelive_plt == self.jobs_window.autoscalelive_plt_cmb.count()-1: # last one
            a=self.jobs_window.autoscalelive_plt_cmb.currentText()
            a=a.split('%')[0][1:-1].split(',')
            a1 = int(a[0]) if a[0].isdigit() else 0
            a2 = int(a[1]) if a[1].isdigit() else 100
            self.autoscalelive_plt = (a1, a2) # will be the range of autoscale
        else: self.autoscalelive_plt = True
        #dur_sec = float(self.duration_indic.text())
#        if (self.stage_scan_mode == 0 or self.stage_scan_mode == 2):  # # digital galvos or static       
#            ind_max = math.ceil(self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6/self.update_time)
#        else: # stage scan, or new anlg galvo
#            ind_max = math.ceil(dur_sec/self.update_time)
            
        # # if ind_max <= 1: # # already done in worker
        # #     # # ind_max = math.ceil(self.nbPX_X_ind.value()*self.nbPX_Y_ind.value()*self.dwll_time_edt.value()*1e-6/self.update_time)
        # #     self.real_time_disp = 0 # no disp if one buffer
            
        if self.stage_scan_mode == 1: # stage scan
            self.scan_mode_str = 'stage scan'

            self.dist_offset = self.acc_offset_spbox.value()
            self.dist_offset_rev = self.dec_offset_spbox.value()
                        # # self.dist_offset_rev = self.dist_offset # in um
            self.max_vel_x = self.speed_max_motor_X_spinbox.value()
            self.max_vel_y = self.speed_max_motor_Y_spinbox.value()
            
            if self.y_fast:
                self.max_accn_y = self.acc_max_motor_Y_spinbox.value()
                self.max_accn_x = max(param_ini.min_speedslow,  self.acc_max_motor_X_spinbox.value()) # # ok it can make the scan longer, but a priori the stage does not reach the full speed if small steps, and if the user wants to move big steps it avoids 
            else: # xfast classical
                self.max_accn_y = self.acc_max_motor_Y_spinbox.value()
                self.max_accn_x = max(param_ini.min_speedslow,  self.acc_max_motor_X_spinbox.value()) # # ok it can make the scan longer, but a priori the stage does not reach the full speed if small steps, and if the user wants to move big steps it avoids
                
            self.profile_mode_stgXY = self.profile_mode_cmbbx.currentIndex() + 1 # 1 for trapez, 2 for S-curve
            self.jerk_stgXY = self.jerk_fast_spnbx.value() # in mm/s3
            self.invDir_slow = self.invDir_slow_chck.isChecked()
            self.force_reinit_AI_eachimg = self.force_reinit_AI_eachimg_chck.isChecked()
            self.stage_scn_block_moves = self.stage_scn_block_stp_chck.isChecked()
            self.stagescn_wait_fast = self.stagescn_wait_fast_chck.isChecked()
        
        elif self.stage_scan_mode == 0: # digital galvo scan
            self.scan_mode_str = 'diggalvo scan'

            if self.use_preset_sync_dig_galv_chck.isChecked(): # na value set
                if self.timebase_ext_diggalvo_chck.isChecked(): # timebase from galvo controller
                    if (self.new_szX_um == 400 and self.new_szY_um == 400 and self.px_sz_x == 1 and self.px_sz_y == 1 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(2.75)
                    elif (self.new_szX_um == 200 and self.new_szY_um == 200 and self.px_sz_x == 0.5 and self.px_sz_y == 0.5 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(2.0)
                    elif (self.new_szX_um == 300 and self.new_szY_um == 300 and self.px_sz_x == 0.75 and self.px_sz_y == 0.75 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(2.0)
                    elif (self.new_szX_um == 100 and self.new_szY_um == 100 and self.px_sz_x == 0.25 and self.px_sz_y == 0.25 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(1.5)
                    elif (self.new_szX_um == 50 and self.new_szY_um == 50 and self.px_sz_x == 0.15 and self.px_sz_y == 0.15 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(1.0)
                    elif (self.new_szX_um == 200 and self.new_szY_um == 200 and self.px_sz_x == 0.5 and self.px_sz_y == 0.5 and self.exp_time == 200):
                        self.corr_sync_inPx_spnbx.setValue(1.0)
                        
                # put here other values measured
                else: # timebase internal
                    if (self.new_szX_um == 200 and self.new_szY_um == 200 and self.px_sz_x == 0.5 and self.px_sz_y == 0.5 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(2) # is divided by 10 after
                    elif (self.new_szX_um == 20 and self.new_szY_um == 20 and self.px_sz_x == 0.06 and self.px_sz_y == 0.06 and self.exp_time == 20):
                        self.corr_sync_inPx_spnbx.setValue(-5) # is divided by 10 after
            
            if self.load_scn_dig_galv_chck.isChecked():
                fname = r'%s\code Labview microscopy\MultiPHOTON - Copie\2Photon\Variables\scan.txt' % os.path.abspath(self.path_computer + '/../')
                
                with open(fname) as f:
                    DSP_scan_list = f.read().splitlines()
                
            if self.center_x > param_ini.max_offset_x_digGalvo:
                print('Caution offset X in galvo mode is too high (max 0.2 mm) : set to 0.2')
                self.center_x = 0.2
                self.offsetX_mm_spnbx.setValue(self.center_x)
            # elif self.center_x == 0:
            #     self.center_x = param_ini.center_x # as in labview
                
            if self.center_y > param_ini.max_offset_y_digGalvo:
                print('Caution offset Y in galvo mode is too high (max 0.2 mm) : set to 0.2')
                self.center_y = 0.2
                self.offsetY_mm_spnbx.setValue(self.center_y)
            # elif self.center_y == 0:
            #     self.center_y = param_ini.center_y # as in labview
        # # else: self.isec_proc_forishgfill = False # static or anlg galvos
        
            
        if self.stage_scan_mode in (0, 3): # # digital or analog galvo scan
            self.acqline_galvo_mode = self.acqline_galvo_mode_box.currentIndex() # # 0 for linetime meas., 1 for callback each line
            self.method_watch = 7 if self.acqline_galvo_mode == 0 else min(6, param_ini.method_watch) # acqline_galvo_mode
            # # for it not to be 7, which would mean 1 contrary to order
        
        send_new_params = False # init
        
        pause_trig_diggalvo = self.pause_trig_sync_dig_galv_chck.isChecked()
        corr_sync_inPx = self.corr_sync_inPx_spnbx.value() # number of px shift between lines
        
        device_used_AIread = self.dev_to_use_AI_box.currentIndex() + 1
        if device_used_AIread == 1: # 6110
            self.max_value_pixel = param_ini.max_value_pixel_6110
        elif device_used_AIread == 2: # 6259
            self.max_value_pixel = param_ini.max_value_pixel_6259
        
        self.num_dev_watcherTrig = self.watch_triggalvos_dev_box.currentIndex()
        self.num_dev_anlgTrig = self.anlgtriggalvos_dev_box.currentIndex()  # # for anlg galvos
        self.num_dev_AO = self.aogalvos_dev_box.currentIndex() # # for anlg galvos
        
        if self.ishg_EOM_AC[0]: self.isec_proc_forishgfill = self.jobs_window.scndProcfill_EOMph_chck.isChecked()  #dur_sec < 20 else param_ini.sec_proc_forishgfill # # no need if scan too small ??
            
        # # print('wlhh l4264', self.stage_scan_mode,  (self.isec_proc_forishgfill and self.ishg_EOM_AC[0] == 1 and self.stage_scan_mode == 1 and self.ishg_EOM_AC[0] == 1 and not self.ishg_EOM_AC_current[0] and self.set_new_scan == 0))
        if (self.stage_scan_mode == 1 and self.ishg_EOM_AC[0] == 1 and not self.ishg_EOM_AC_current[0] and self.set_new_scan == 0 and self.isec_proc_forishgfill): # stage scan and ishgfast was not set before in running QThread scn but is set now, and sec. wrkr for ISHG
            self.set_new_scan = 1 # # because will have to start a new Process for fill ishg
        
        if self.use_shutter_combo.currentIndex(): # # use at all the imgs
            self.waitTime_shutter_00 = time.time()
            
        if self.set_new_scan == 0: # not a whole new_scan...
        
            print('Not a new scan')
            
            # # print(self.pmt_channel_list_current , self.pmt_channel_list)
            
            if (self.new_szX_um_current != self.new_szX_um or self.new_szY_um_current != self.new_szY_um or self.px_sz_x_current != self.px_sz_x or self.px_sz_y_current != self.px_sz_y or self.nb_px_x_current != self.nb_px_x or self.nb_px_y_current != self.nb_px_y or self.nb_bins_hist_current != self.nb_bins_hist or self.center_x != self.center_x_current or self.center_y != self.center_y_current or self.force_whole_new_scan or self.real_time_disp_current != self.real_time_disp or self.pmt_channel_list_current != self.pmt_channel_list or self.sampleRateRead_current != sampleRateRead or self.update_time_current != self.update_time or self.nb_img_max_current != self.nb_img_max or self.y_fast_current != self.y_fast or self.unidirectional_current != self.unidirectional or self.clrmap_nb_current != self.clrmap_nb or self.delete_px_fast_begin_current != self.delete_px_fast_begin or self.delete_px_fast_end_current != self.delete_px_fast_end or self.delete_px_slow_begin_current != self.delete_px_slow_begin or self.delete_px_slow_end_current != self.delete_px_slow_end or self.nb_accum != self.nb_accum_current or self.external_clock_current != self.external_clock or self.scan_xz_current != self.scan_xz or self.exp_time_current != self.exp_time or self.read_buffer_offset_direct_current != self.read_buffer_offset_direct or self.read_buffer_offset_reverse_current != self.read_buffer_offset_reverse or self.currentDevice_AI != self.currentDevice_AI_current or self.ishg_EOM_AC_current != self.ishg_EOM_AC or self.autoscalelive_plt_current != self.autoscalelive_plt or self.lock_smprate_current != self.lock_smprate or self.lock_uptime_current != self.lock_uptime):
                # # print('here1 !!!!!!')
                
                send_new_params = True
                
            else: # specific to some scan meth
                if ((self.stage_scan_mode == 0 or self.stage_scan_mode == 3) and (self.obj_mag_current!= self.obj_mag or self.pause_trig_diggalvo_current != pause_trig_diggalvo or self.acqline_galvo_mode_current != self.acqline_galvo_mode)): # # any galvos
                    # # print('here2 !!!!')

                    send_new_params = True
                    
                elif (self.stage_scan_mode == 3 and (self.eff_wvfrm_an_galvos != self.eff_wvfrm_an_galvos_current or self.write_scan_before_anlg != self.write_scan_before_anlg_current or self.mult_trig_fact_anlg_galv_current != self.mult_trig_fact_anlg_galv or self.trig_perc_hyst_current != self.trig_perc_hyst or self.off_fast_anlgGalvo != self.off_fast_anlgGalvo_current or self.off_slow_anlgGalvo != self.off_slow_anlgGalvo_current or self.corr_sync_inPx_current != corr_sync_inPx)): # new alng galvo scan
                    send_new_params = True
                    # # print('here3 !!!!')
                    
                elif (self.stage_scan_mode == 0 and (self.corr_sync_inPx_current != corr_sync_inPx or self.time_base_ext_current != self.time_base_ext)): # digital galvo scan
                    send_new_params = True
                    
                elif (self.stage_scan_mode == 1 and (self.dist_offset_current != self.dist_offset or self.dist_offset_rev_current != self.dist_offset_rev or self.max_vel_x_current/self.max_vel_x > self.tolerance_speed_accn_diff_real_value or self.max_vel_y_current/self.max_vel_y > self.tolerance_speed_accn_diff_real_value or self.max_accn_x_current/self.max_accn_x > self.tolerance_speed_accn_diff_real_value or self.max_accn_y_current/self.max_accn_y > self.tolerance_speed_accn_diff_real_value or self.profile_mode_stgXY_current != self.profile_mode_stgXY or self.jerk_stgXY_current != self.jerk_stgXY or self.trigout_stgXY_current != self.trigout_stgXY or self.invDir_slow != self.invDir_slow_current or self.force_reinit_AI_eachimg_current != self.force_reinit_AI_eachimg or self.stage_scn_block_moves != self.stage_scn_block_moves_current or self.stagescn_wait_fast != self.stagescn_wait_fast_current )): # stage scan
                    # # print('here3b !!!!')
                    send_new_params = True
                    
                else: send_new_params = False # init
        
        else: # new scan # if self.set_new_scan > 0
            # # print('here44 !!!!')
            send_new_params = True
            if self.set_new_scan == 1: # because is set to 2 if it's the very first scan
                # print('trying to end thread scan for a new scan ...')
                
                self.kill_scanThread_meth()
                # for the galvo scan, it does kill the QThread
                # for stage scan, it just put outside function of scan
            
            if self.scan_thread_available:
                if self.stage_scan_mode == 1: # stage scan
                    self.worker_stageXY.new_scan_stage_signal.emit( self.debug_mode_stgscn, self.stage_scan_mode - 1, self.min_val_volt_list, self.max_val_volt_list, device_used_AIread, (self.isec_proc_forishgfill and self.ishg_EOM_AC[0] in (1, 11)), (param_ini.limitwait_move_time, param_ini.vel_dflt, param_ini.acc_dflt, param_ini.tol_speed_flbck, self.method_fast_stgscn), self.real_time_disp ) # start new scan from scratch
                else: # not stage scan
                    if (not hasattr(self, 'thread_scan') or self.thread_scan is None): # thread_scan was not defined
                        self.setupThread_scan() # start Qthread of scan
                
                    self.scan_galvo_launch_processes_signal.emit(1-self.mode_scan_box.currentIndex(), self.real_time_disp, self.min_val_volt_list, self.max_val_volt_list, device_used_AIread, self.write_scan_before_anlg, self.num_dev_anlgTrig, self.num_dev_watcherTrig, self.num_dev_AO, self.isec_proc_forishgfill and self.ishg_EOM_AC[0], self.path_computer)
                
        if send_new_params:
            if self.stage_scan_mode == 1: # stage scan
                # # print('list1', self.max_vel_x, self.max_vel_y, self.max_accn_x, self.max_accn_y)
                self.list_scan_params = [self.new_szX_um, self.new_szY_um, self.px_sz_x, self.px_sz_y, self.y_fast, self.unidirectional, self.pmt_channel_list, self.dist_offset, self.dist_offset_rev, self.read_buffer_offset_direct, self.read_buffer_offset_reverse , self.nb_bins_hist, self.max_vel_x, self.max_vel_y, self.max_accn_x, self.max_accn_y, self.center_x, self.center_y, self.delete_px_fast_begin, self.delete_px_fast_end, self.delete_px_slow_begin, self.delete_px_slow_end, self.real_time_disp, self.profile_mode_stgXY, self.jerk_stgXY, self.trigout_stgXY, sampleRateRead, self.scan_xz, self.external_clock, [self.invDir_slow, self.force_reinit_AI_eachimg, (self.lock_smprate, self.lock_uptime)], self.stage_scn_block_moves, self.stagescn_wait_fast, self.clrmap_nb, self.autoscalelive_plt, list(self.ishg_EOM_AC) ]
            
            else: # galvo (dig or anlg) or static acq.
                self.list_scan_params = [self.pmt_channel_list, sampleRateRead, self.exp_time*1e-6, self.update_time, self.obj_mag , self.center_x, self.center_y, self.new_szX_um, self.new_szY_um, self.nb_px_x, self.nb_px_y, self.nb_img_max, self.unidirectional, self.y_fast, self.nb_bins_hist, self.real_time_disp, self.clrmap_nb , self.delete_px_fast_begin, self.delete_px_fast_end, self.delete_px_slow_begin, self.delete_px_slow_end, [corr_sync_inPx, pause_trig_diggalvo, self.acqline_galvo_mode], DSP_scan_list, self.nb_accum, self.scan_xz, self.external_clock, self.time_base_ext, [self.read_buffer_offset_direct, self.read_buffer_offset_reverse], self.autoscalelive_plt, (self.lock_smprate, self.lock_uptime), [self.eff_wvfrm_an_galvos, self.mult_trig_fact_anlg_galv, self.trig_perc_hyst, self.off_fast_anlgGalvo, self.off_slow_anlgGalvo, self.fact_buffer_anlgGalvo], list(self.ishg_EOM_AC)]
            
            print('New scan with new parameters will be sent by signal !')
            # # print('accY', self.max_accn_y)
                        
        else:
            print('No new parameters')
            self.list_scan_params = []
        
        # # # will distinguish if you use shutter or not 
        # # print('set_new_scan', self.set_new_scan)
        if self.set_new_scan != 3: # #  2 if new scan
        # # launch scan is here !!
            self.empty_queue_send_reset_scan(True) # # see later
  
        self.pmt_channel_list_current = self.pmt_channel_list
        self.new_szX_um_current = self.new_szX_um 
        self.new_szY_um_current = self.new_szY_um
        self.px_sz_x_current = self.px_sz_x
        self.px_sz_y_current = self.px_sz_y
        self.nb_px_x_current = round(self.nb_px_x)
        self.nb_px_y_current = round(self.nb_px_y)
        self.nb_bins_hist_current = self.nb_bins_hist
        self.center_x_current = self.center_x
        self.center_y_current = self.center_y
        self.real_time_disp_current = self.real_time_disp
        self.clrmap_nb_current = self.clrmap_nb; self.delete_px_fast_begin_current = self.delete_px_fast_begin; self.delete_px_fast_end_current = self.delete_px_fast_end; self.delete_px_slow_begin_current = self.delete_px_slow_begin; self.delete_px_slow_end_current = self.delete_px_slow_end; self.sampleRateRead_current = sampleRateRead; self.update_time_current = self.update_time ; self.nb_img_max_current = self.nb_img_max
        self.nb_accum_current = self.nb_accum
        self.external_clock_current = self.external_clock
        self.scan_xz_current = self.scan_xz
        self.exp_time_current = self.exp_time
        self.time_base_ext_current = self.time_base_ext
        self.currentDevice_AI_current = self.currentDevice_AI
        self.read_buffer_offset_direct_current = self.read_buffer_offset_direct
        self.read_buffer_offset_reverse_current = self.read_buffer_offset_reverse
        self.unidirectional_current = self.unidirectional
        self.ishg_EOM_AC_current = list(self.ishg_EOM_AC) # otherwise does not create a copy, but same object !!
        self.y_fast_current = self.y_fast
        self.autoscalelive_plt_current = self.autoscalelive_plt
        self.lock_smprate_current = self.lock_smprate
        self.lock_uptime_current = self.lock_uptime
        
        if self.stage_scan_mode == 1: # stage scan
            self.dist_offset_current = self.dist_offset; self.dist_offset_rev_current = self.dist_offset_rev; self.max_vel_x_current = self.max_vel_x; self.max_vel_y_current = self.max_vel_y; self.max_accn_x_current = self.max_accn_x; self.max_accn_y_current = self.max_accn_y 
            self.profile_mode_stgXY_current = self.profile_mode_stgXY; self.jerk_stgXY_current = self.jerk_stgXY; self.trigout_stgXY_current = self.trigout_stgXY; self.stage_scn_block_moves_current = self.stage_scn_block_moves; self.stagescn_wait_fast_current = self.stagescn_wait_fast; self.invDir_slow_current = self.invDir_slow ; self.force_reinit_AI_eachimg_current = self.force_reinit_AI_eachimg
                 
        elif self.stage_scan_mode != 1: # not a stage scan
            if self.stage_scan_mode == 2:  # # static acq.
                self.scan_mode_str = 'static acq.'

            self.sizeX_galvo_prev = self.sizeX_um_spbx.value() # just the default value when galvo scan
            self.sizeY_galvo_prev = self.sizeY_um_spbx.value()
            self.step_ref_val_galvo = self.stepX_um_edt.value()
            if (self.stage_scan_mode == 0 or self.stage_scan_mode == 3): # galvo (any)  
                self.obj_mag_current = self.obj_mag
                self.pause_trig_diggalvo_current = pause_trig_diggalvo
                self.acqline_galvo_mode_current = self.acqline_galvo_mode # # acqline_galvo_mode_box
            # # if self.stage_scan_mode == 0: # galvo digital  
                self.corr_sync_inPx_current = corr_sync_inPx
                if self.stage_scan_mode == 3: # galvo anlg new
                    self.scan_mode_str = 'Anlggalvo scan'
                    self.eff_wvfrm_an_galvos_current = self.eff_wvfrm_an_galvos
                    self.write_scan_before_anlg_current = self.write_scan_before_anlg
                    self.mult_trig_fact_anlg_galv_current = self.mult_trig_fact_anlg_galv
                    self.trig_perc_hyst_current = self.trig_perc_hyst
                    self.off_fast_anlgGalvo_current = self.off_fast_anlgGalvo
                    self.off_slow_anlgGalvo_current = self.off_slow_anlgGalvo
                    self.fact_buffer_anlgGalvo_current = self.fact_buffer_anlgGalvo
        
        # # print('\n I`m here \n')
        
        self.force_whole_new_scan = 0
        
        if len(self.list_scan_params) > 0:
            self.list_scan_params_full = self.list_scan_params # always full
                
        if self.use_shutter_combo.currentIndex() == 1: # # use at all the imgs
            self.shutter_closed_chck.setEnabled(False) # prevent user from using the button
    
    def empty_queue_send_reset_scan(self, direct):
        # # calle by define_new_scan direct
        # do NOT put it after the order of image !!
        
        print('direct', direct)
        
        try:# empty the order queue
            while not self.queue_com_to_acq.empty():
                self.queue_com_to_acq.get_nowait() # empty the queue
        except queue.Empty: # if empty, it raises an error (or if worker scan undefined)
            pass
            
        try:  # empty the cancel in-line queue
            while not self.queue_special_com_acq_stopline.empty(): 
                self.queue_special_com_acq_stopline.get_nowait() # raise queueEmpty error if empty, otherwise continue                     
        except queue.Empty:
            pass
        self.send_new_img_to_acq(100) # tell the acq process to start with no changes
         # # 101 for direct call
        # # otherwise will be sent by the kill_method itself
        self.set_new_scan = 0 # re-init set_new_scan 
     
    @pyqtSlot(int)        
    def worker_scan_set_reload_meth(self, bb): 
        # # called by reload_scan_worker_signal in stage Worker
        
        self.set_new_scan = 1

        if bb > 0:
            self.thread_stageXY.quit()
            self.thread_stageXY.wait(5) # sec
            runst = self.thread_stageXY.isRunning()
            print('thread', self.thread_stageXY.currentThreadId(), runst)
            if not runst:
                self.setupThread_stageXY()
        ## display methods    
            
    @pyqtSlot()    
    def display_img_gui(self):
        
        print('received signal new img in display_img_gui')
        
        if self.use_shutter_combo.currentIndex() == 1: # # use at all the imgs
            self.shutter_send_close()
            self.waitTime_shutter_00 = time.time()
        
        try: paquet_received_all = self.queue_list_arrays.get(timeout = param_ini.time_out)
        except queue.Empty: print('ERR: received new img flag, but queue is empty !!'); return # out of func
        # # print('paquet_received', paquet_received_all)
        sat_value_list = paquet_received_all[1]
        paquet_received = paquet_received_all[0] # this paquet is received from a queue defined at init and filled by fill_array process
        # the rest are the params to disp
        
        array_ishg_4d = array_ctr_3d = arrlist = None
        if (self.ishg_EOM_AC): # # ishg EOM fast
            if type(paquet_received) == list: # normal
                if len(paquet_received) > 2: # # filled array in ishg
                    if paquet_received[1] is not None: array_ctr_3d = paquet_received[1]
                    array_ishg_4d = paquet_received[2]
                    if array_ishg_4d is None: print('received array_ishg_4d None !!')
                    if len(paquet_received) > 3: # # treated arrays + whole_lists
                        if (type(paquet_received[3]) == int and paquet_received[3]==1): # # normally 1
                            # # arrlist = paquet_received[3]
                            try: arrlist = self.queue_list_arrays.get(timeout = param_ini.time_out)
                            except queue.Empty: print('did not receiv buffers ISHG in list as expected !!')
                else:  # # special for saving whole array
                    arrlist = paquet_received[1]
                    
                paquet_received = paquet_received[0]    # # is array_3d, the normal image   
            else: print('did not receive list paquet for ishg fast as expected !\n')
        
        pg_plot_scripts.display_save_img_gui_util (self, datetime, numpy, shutil, glob, QtWidgets, PIL, os, param_ini, jobs_scripts, img_hist_plot_mp, paquet_received, sat_value_list, array_ishg_4d, array_ctr_3d, arrlist, [True])  # # True for add new img (full func)
        # # datetime, numpy, shutil, glob, QtWidgets, PIL, os, param_ini, jobs_scripts, img_hist_plot_mp, paquet_received, sat_value_list, array_ishg_4d, array_ctr_3d, arrlist, add_new_img)
        
        self.number_img_done +=1 # increment number of image done
        
        self.curr_row_img = len(self.list_arrays)-1
        self.list_scan_params = [] # very important to avoid re-defining the task all the time
        end = False # dflt

        if not(self.count_avg_job is None): # a job is running and not a classic scan 
        
            if self.count_avg_job == -1: # # cal fast ps
                self.send_move_to_worker_phshft() # will call end
                self.count_avg_job = None # None means no job is running
                
                jobs_scripts.disp_autoco_frog_meth(self, sys, glob, os, numpy, False, paquet_received[0, :, :])
                
            # # eq_infs_1mm_mtr = eq_infs_1mm_calci*nb_pass = (1/self.vg1 - 1/self.vg2)*1e12*self.nb_pass_calcites, in fs/mm
            if (self.row_jobs_current is not None and self.jobs_window.table_jobs.columnCount() is not None):  
                nb_average_job = int(self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.average_posWrtEnd_jobTable).text())
            else: # job erased
                nb_average_job = 1
            
            # # print('\n self.count_avg_job < nb_average_job', self.count_avg_job ,nb_average_job)
            if (nb_average_job > 1 and self.count_avg_job > 0 and self.count_avg_job < nb_average_job): # if average is asked AND iteration of avg is not at max
                self.send_new_img_to_acq(101) # tell the acq process to continue the job
                 # # 101 for direct call
                self.count_avg_job += 1 # iteration
                
            else: # iteration of AVG is at max (or average is not asked)
                if self.iterationInCurrentJob is not None: # # job is not cancelled
                    self.count_avg_job = 1 # reset
                else:
                    self.count_avg_job = None # job canceled
                    
                self.queue_com_to_acq.put([0]) # put in stand-by the acq process
                if self.connect_new_img_to_move_Z_obj:
                    self.send_move_to_worker_imic_obj_Z()
                
                elif self.connect_new_img_to_move_phshft: # even if Z_ps job, it's the end of Z job that leads to move p-s
                    self.send_move_to_worker_phshft()
                    
                elif self.connect_new_img_to_move_polar: # even if Z_ps job, it's the end of Z job that leads to move p-s
                    self.send_move_to_worker_polar()
                elif self.connect_new_img_to_move_XY:
                    self.send_move_to_XYmos_job()
                elif self.connect_new_img_to_single: # no mtr
                    self.send_move_to_single()
                    
                if self.use_shutter_combo.currentIndex() == 1:  # at end
                    self.shutter_outScan_mode() # # just for display

                # # print('self.connect_new_img_to_move_polar', self.connect_new_img_to_move_polar)
        
        else:  # not a job, classic scan
        
            print('In GUI : acq # %d received/ %d acq. programmed' % (self.number_img_done, self.nb_img_max))
            if self.number_img_done < self.nb_img_max: # still some image to acquire
            
                self.send_new_img_to_acq(101) # tell the acq process to continue
                 # # 101 for direct call
                
            else: # enough images acquired
                self.queue_com_to_acq.put([0]) # put in stand-by the acq process
            
                if self.use_shutter_combo.currentIndex(): # # use at all the imgs
                    self.shutter_outScan_mode() # # just for display
                    if self.use_shutter_combo.currentIndex() == 2:  # at end
                        self.shutter_send_close() # ordr to close it (before for == 1)

        self.filter_top_choice_curr_index = self.filter_top_choice.currentIndex()   
        
        '''
        # temporary
        if (self.stage_scan_mode != 0 and self.imic_was_init_var): # stage scan or static ACQ
        # imic init, allow to use the scan with imic OFF not to lose the previous Z position
            self.filter_top_choice_curr_index = self.filter_top_choice.currentIndex()
            self.filter_top_choice.setCurrentIndex(param_ini.mddle_top_slider_pos) # enough to call self.fltr_top_changed() # 
            # shutter for the poor
        '''
    
    @pyqtSlot()    
    def display_img_selected(self):
        # display acquired image by selecting a line in the GUI widget table
        
        curr_row_img = self.name_img_table.currentRow() + self.offset_table_img
        
        if curr_row_img < 0:
            print('curr_row_img', curr_row_img, ' wrong row!')
            if self.name_img_table.rowCount() > 0: curr_row_img = self.name_img_table.rowCount() - 1
            else: return
            
        # else:
        lintable_cond = int(self.name_img_table.item(curr_row_img , 1).text()) == 2
        caller = self.sender()
        if caller == self.name_img_table:
            cond1 = curr_row_img != self.curr_row_img
        elif caller == self.swappg_img_button:
            cond1 = True
            lintable_cond = not lintable_cond
                        
        if cond1:
        
            self.curr_row_img = curr_row_img
            # print('self.offset_table_img is ', self.offset_table_img)
            # print(curr_row_img)
            # print(len(self.list_arrays))
            
            paquet_received = self.list_arrays[self.curr_row_img]
                        
            # set PMT value
            
            if lintable_cond: # see before
                
                img_item_pg = self.img_item_pg_2
                hist = self.hist_2
                LUT = self.LUT_2
            else:
                img_item_pg  = self.img_item_pg
                hist = self.hist_1
                LUT = self.LUT
            
            #img_hist_plot_mp.plot_img_hist(self.fig_main, self.canvas_main, self.canvas_hist, paquet_received, nb_bins_hist, self.ax1f1, self.ax2f1)
            img_hist_plot_mp.plot_img_hist(numpy, LUT, paquet_received, img_item_pg, hist, self.isoLine_pg)
            self.updateClrmap_meth(-1) # -1 to tell its not a slot call
            
            self.sat_val_spbx.setValue(int(self.name_img_table.item(curr_row_img, param_ini.posSat_wrt0_tablemain).text()))
     
    # # def satval_upld_meth(self, row):
        # not a slot
    
        # # obj_card_str = self.name_img_table.item( row, 13).text().split('MHz')
        # # rate = float(obj_card_str[0][2:]) # MHz   # self.name_img_table.currentRow()
        # # exptime = self.name_img_table.item(row , 3).text().split('us')[0][2:] # us
        # # bit = param_ini.max_value_pixel_6110 if obj_card_str[1].split(', ')[1] == "'%s'" % self.dev_to_use_AI_box.itemText(0) else param_ini.max_value_pixel_6259
        # # exptime*rate
                
    @pyqtSlot()
    def load_disp_img_from_file_meth(self):
                
        file_full_path_chosen = QtWidgets.QFileDialog.getOpenFileName(None, 'Load file ...', r'%s\Desktop' % os.path.abspath(self.path_computer + '/../' + '/../'), '*.tif', '*.tif')
        
        # # print(file_full_path_chosen)
        self.disp_img_loaded_meth(file_full_path_chosen)

    def disp_img_loaded_meth(self, path):
         # # not pyqtslot
        if (isinstance(path, list) or isinstance(path, tuple)):
            path1 = path[0]
        else:
            path1 = path
        
        print(path)
        arr = numpy.array(PIL.Image.open(path1))
                
        use_second = 0
        if use_second:
            
            img_item_pg = self.img_item_pg_2
            hist = self.hist_2
            LUT = self.LUT_2
        else:
            img_item_pg  = self.img_item_pg
            hist = self.hist_1
            LUT = self.LUT
        
        img_hist_plot_mp.plot_img_hist(numpy, LUT, arr, img_item_pg, hist, self.isoLine_pg)
        self.updateClrmap_meth(-1) # -1 to tell its not a slot call
        # 
        
        if (isinstance(path, list) or isinstance(path, tuple)):
        
            self.list_arrays.append(arr)

            rowPosition = self.name_img_table.rowCount()
            self.name_img_table.insertRow(rowPosition)
            
            self.name_img_table.setItem(rowPosition , 1, QtWidgets.QTableWidgetItem('1'))
            self.name_img_table.setItem(rowPosition , 2, QtWidgets.QTableWidgetItem(path[0]))
            self.offset_save_img += 1
            # max_arr = round(numpy.max(arr))
            # # # print(max_arr)
            # useScale = [0, max_arr ]
            # img_item_pg.setImage(arr[::-1, :].T, autoLevels=False, levels=useScale, lut=self.LUT, autoDownsample=0)
            # hist.setLevels(round(numpy.min(arr)), round(numpy.max(arr)))
            
        #  # useScale = [0, round(numpy.max(arr))]
        #  # win = pyqtgraph.GraphicsWindow()#GraphicsWindow() #QtGui.QMainWindow()
        #  # win.resize(800,800)
        #  # 
        #  # vb = win.addViewBox(row=0, col=0)
        #  # vb = win.addPlot(row=0, col=0, rowspan=1, colspan=1)
        #  # vb.setAspectLocked()
        #  # # vb2 = win.addViewBox(row=1, col=0)
        #  # # vb3 = win.addViewBox(row=2, col=0)S
        #  # 
        #  # imv = pyqtgraph.ImageItem()
        #  # vb.addItem(imv)
        #  # vb.autoRange()
        #  # hist_1 = pyqtgraph.HistogramLUTItem()
        #  # hist_1.setImageItem(imv)
        #  # win.addItem(hist_1,row=0, col=1)
    
        # #   # #   imv.setImage(arr[::-1, :].T, autoLevels=False, levels=useScale, lut=self.LUT, autoDownsample=0)
        #  # hist_1.setLevels(round(numpy.min(arr)), round(numpy.max(arr)))
        #  # 
        #  # hist_1.gradient.setColorMap(self.cmap_fire_pg)
        #  # imv.setLookupTable(self.LUT)
        #  #     
        #  # win.show()
        #  # err
    
    @pyqtSlot()
    def save_img_stack(self):

        save_meth = 1 # save selected items
        self.save_util_meth(save_meth)                        
    
    @pyqtSlot()            
    def save_last_meth(self):
            
        save_meth = 2 # save a specified number of images
        # # self.path_save is defined AT THE TOP OF THIS SCRIP
        self.save_util_meth(save_meth)
    
    def save_util_meth(self, save_meth): 
    
        list_row_selected = self.name_img_table.selectedItems() # return a 1D list with all the cells after each other (#, # PMT, etc.)
        if len(list_row_selected) == 0: list_row_selected =  self.name_img_table.findItems('',QtCore.Qt.MatchContains)
        
        savefromRAM = self.savefromRAM_chck.isChecked()
        # # print('aa2', self.name_img_table.currentRow() , self.offset_table_img)

        pack_saveRAM= (savefromRAM, pg_plot_scripts, datetime, numpy, PIL, param_ini, self.name_img_table.currentRow() + self.offset_table_img, self.list_arrays, self) if savefromRAM else [False]
        
        nb_field_table = self.name_img_table.columnCount()
        self.offset_save_img = self.off_table_spbx.value()
        
        if save_meth == 1 and (len(list_row_selected) % nb_field_table): # if len(list_row_selected) is not a multiple of param_ini.nb_field_table
            msg = QtWidgets.QMessageBox()
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setText('Wrong selection of rows in the table')
            msg.setInformativeText('You have to check the whole lines, not just one column')
            msg.setWindowTitle('Warning')
            msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
            
        else:
            # print('colco', self.name_img_table.columnCount())
            # print('len(list_row_selected)/param_ini.nb_field_table*2', len(list_row_selected)/param_ini.nb_field_table*2)
            flnmtxt = list_row_selected[2].text()
            a = '' if flnmtxt[22]=='_' else flnmtxt[22] # # remove ms
            flnmtxt =flnmtxt[:15] +a+flnmtxt[22:]
            file_full_path_chosen = QtWidgets.QFileDialog.getSaveFileName(None, 'Save file in folder ...', (r'%s\Desktop\%s.tif' % (os.path.abspath(self.path_computer + '/../' + '/../'), flnmtxt)), '*.tif', '*.tif') # round(len(list_row_selected)/nb_field_table*2)
            # # name of full path of destination
                                    
            print('file_full_path_chosen', file_full_path_chosen)
            # # self.path_save is defined AT THE TOP OF THIS SCRIPT
            
            if save_meth == 1: # sel.
                pmt_ll = list_row_selected[1::nb_field_table] # # number of the PMTs in a list
                    
            else: # last img
                list_row_selected = [0, 0]
                curr_row = self.name_img_table.currentRow() if self.name_img_table.currentRow() !=-1 else self.name_img_table.rowCount() - 1
                list_row_selected[0] = max(0, curr_row - self.save_nb_img_last.value())+1
                list_row_selected[1] = self.save_nb_img_last.value()
                pmt_ll= []
                for i in range(list_row_selected[1]):
                    pmt_ll.append(self.name_img_table.item(list_row_selected[0]+i, 1))
            # # for ii in range(len(pmt_ll)):
            # #     print(pmt_ll[ii].text())
            # # print(pmt_ll)
    
        if file_full_path_chosen[0]:
            # if not(self.count_avg_job is None): # a job is running and not a classic scan 
            jobn = list_row_selected[2].text()
            jobn = jobn[11:11+15]
            # else:
            #     jobn = ''
            pmt_txt_all = [el.text() for el in pmt_ll]
            # try: 
            save_img_tiff_script2.save_img_tiff2(os, subproc_call, self.path_save, list_row_selected, file_full_path_chosen, nb_field_table, save_meth, self.offset_table_img+self.offset_save_img, pmt_txt_all, jobn, pack_saveRAM, shutil)
            # except IndexError: # pb with # of line
            #     print('off', self.offset_table_img, 'pmt_len', len(pmt_ll), 'pmt_len', round(len(list_row_selected)/nb_field_table))
            #     QtWidgets.QMessageBox.critical(None, "Error in saving", "index retrieval of files failed: saving is only partial !!")   
                        
    @pyqtSlot()            
    def erase_last_meth(self):
        
        erase_num = min(self.name_img_table.rowCount(), self.count_erase_spbx.value())
        # print(self.name_img_table.currentRow())
        if QtWidgets.QMessageBox.question(None, 'erase imgs ??', "Are you sure you want to erase %d imgs?" % erase_num,
                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                            QtWidgets.QMessageBox.No) == QtWidgets.QMessageBox.No:
            return
        
        current_row = self.name_img_table.currentRow()
        if current_row == -1: # no row selected
            current_row = self.name_img_table.rowCount() - 1
            
        # print('self.name_img_table.rowCount() is ' , self.name_img_table.rowCount() )
        
        files = glob.glob(('%s/tmp/*' % self.path_save))
            
        ct = 0
        for ii in range(erase_num ):
            self.name_img_table.removeRow(current_row - ii)
            del self.list_arrays[current_row- ii]
            # # os.remove(files[current_row- ii])
            shutil.copy2(files[current_row- ii], self.path_recycle)
            ct+=1
            
        # self.offset_table_img = self.offset_table_img + ct
        self.offset_save_img = self.offset_save_img + ct
        self.off_table_spbx.setValue(self.offset_save_img)
    
    @pyqtSlot()    
    def shift_reg_xcorr_meth(self):
        '''
        that one is cheap. For precise use DipImage in matlab.
        '''
        
        curr_row_img = self.name_img_table.currentRow() + self.offset_table_img
        if curr_row_img < 0:
            print('curr_row_img', curr_row_img, ' wrong row!')
            if self.name_img_table.rowCount() > 0: curr_row_img = self.name_img_table.rowCount() - 1
            else: return
        
        if not 'skimage.feature' in sys.modules:
            import skimage.feature as sk
        else: sk=sys.modules['skimage.feature']
        
        arr = numpy.array(self.list_arrays[self.curr_row_img]) # defines another one
        ci = self.name_img_table.item(curr_row_img , 3)
        if (ci is not None and ci.text().split(',')[3] == " 'Yfast'"):
            if numpy.size(arr, 1)%2: arr = arr[:, :-1] # # odd number of lines 
            xfast = 0
            arr1 = arr[:, ::2]; arr2 = arr[ :, 1::2]
        else: # xfast, classic
            if numpy.size(arr, 0)%2: arr = arr[:-1, :] # # odd number of lines 
            xfast = 1
            arr1 = arr[::2, :]; arr2 = arr[1::2, :]
        # # plt.close()
        # # plt.subplot(2,1,1)
        # # plt.imshow(arr[::2, :])
        # # plt.subplot(2,1,2)
        # # plt.imshow(arr[1::2, :])
        # # plt.show(False)
        # # plt.figure();plt.imshow(arr); plt.show(False)
        
        shift, _, _ = sk.register_translation(arr1, arr2) #, 100) # # calculate shift between odd and even # of lines in img (xfast)
        print('calc. shift in reg:', shift, 'that one is cheap. For precise use DipImage in matlab (reg_shift_advanced.m).')
        
        if xfast: sh = shift[1]
        else: sh = shift[0]
        if sh > 0: self.pixell_offset_dir_spbox.setValue(sh) 
        elif sh < 0: self.pixell_offset_rev_spbox.setValue(sh) 
    
        ## jobs methods
    
    @pyqtSlot(int)        
    def gather_calib_ps(self, v):
        # # used only in FAST calib ishg AC
        if self.gather_calib_flag is not None:
            if self.gather_calib_flag:
                self.end_job_apt_suite(0)
            else:
                self.gather_calib_flag = True # # next is good
                # # if v == 0: # # comes from end of acq.
                # v == 2 comes from and mtr trans move
            
    @pyqtSlot(int)
    def end_job_apt(self, motor):
        # !! for calib AND ps job !!
        # called by signal
        
        self.motor_temp = motor if motor > -1 else 1 # # -1 = calib, 1 will put it to ps
        
        print('motor', motor, self.motor_temp, self.connect_end_ps_to_move_polar, self.worker_apt.wait_flag, self.wait_flag_apt_current)
        
        if (hasattr(self, 'worker_apt') and self.worker_apt is not None and (motor < -1)): self.worker_apt.wait_flag = self.wait_flag_apt_current
        
        if self.motor_temp == 1:   # ps job
            print('Ending p-s job ...')
            if hasattr(self, 'mtr_phshft_finishedmove_sgnl'):
                while True:
                    try:
                        self.mtr_phshft_finishedmove_sgnl.disconnect() # disconnects all, if connection there is
                    except TypeError: # if had no connection
                        break # outside infinite 'while' loop
            
            if motor == -2: # # end of job FAST calib
                self.gather_calib_ps(0)
                if self.divider_lines_calib_fast is None: # # FROG not autoco
                    jobs_scripts.disp_autoco_frog_meth(self, sys, glob, os, numpy, True, None) # # FROG, paquet
            
            if self.connect_new_img_to_move_phshft: # ps is only job or the primary job inside a bigger one
                print('Disconnecting the step of motor phshft from the new img received')
                self.connect_new_img_to_move_phshft = 0
                
            # else: # ps is secondary job with z-stack as primary
            cond1 = (self.connect_end_ps_to_move_polar or motor > -1)  # # not calib self.connect_end_polar_to_move_ps or 
            # self.change_phshft_sgnl.emit(self.pos_phshft0, True) # must be a float, has to be in mm, not um # re-init motor phshft
            if self.connect_end_polar_to_move_ps: self.motor_temp = 2
            elif cond1: signal_considered = self.mtr_phshft_finishedmove_sgnl

            if cond1: # self.connect_end_ps_to_move_polar
                signal_considered.connect(self.end_job_apt_suite) # 
            if (self.mtrreturninitposjob or cond1 or self.connect_end_apt_to_move_Z): # # always done if ps job inside bigger one
                jobs_scripts.pos_init_motor_phshft_meth(self) # # Move phshft origin
                if (hasattr(self, 'name_instr_ps') and self.name_instr_ps == param_ini.name_trans): # # name_rot
                    self.jobs_window.pos_motor_trans_edt.blockSignals(True); self.jobs_window.pos_motor_trans_edt.setText('%.1f' % self.pos_phshft0); self.jobs_window.pos_motor_trans_edt.blockSignals(False)
            
            if (self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text() == param_ini.calib_ps_name_job): # # calib fast
                self.square_img_chck.setChecked(True)
                current_row = self.jobs_window.table_jobs.currentRow()
                if current_row == -1: current_row = self.jobs_window.table_jobs.rowCount() - 1 # no row selected
                if (self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0] == 'DC' and type(self.list_scan_params[-2]) == float ): # # calib of EOMph voltage
                    self.list_scan_params[-2] = [0]*6 # reset
                self.jobs_window.table_jobs.removeRow(current_row)
                if self.jobs_window.table_jobs.rowCount() == 0: self.row_jobs_current = None
                self.jobs_window.cal_ps_button.setText(self.cal_ps_button_txt00)
                self.jobs_window.cal_ps_button.setStyleSheet('color: black')
                if self.use_shutter_combo.currentIndex(): # only if job finished, and shutter used
                    self.shutter_outScan_mode() # # just for display
                self.dwll_time_edt.setValue(param_ini.time_by_point*1e6)
                self.stepX_um_edt.setValue(param_ini.step_ref_val_galvo)

        # # independent        
        if self.motor_temp == 2:   # polar job
            print('Ending polar job ...')
            if self.list_polar.ndim == 1: # one WP
                signal_considered = self.worker_apt.motor_polar_finished_move_signal
            else: # 2 WPs
                signal_considered = self.both_polars_finished_move_signal
            while True:
                try:
                    signal_considered.disconnect() # disconnects all, if connection there is
                except TypeError: # if had no connection
                    break # outside infinite 'while' loop
                
            signal_considered.connect(self.end_job_apt_suite) # 
            
            if self.connect_new_img_to_move_polar: # polar is only job or the primary job inside a bigger one
                print('Disconnecting the step of motor polar from the new img received')
                self.connect_new_img_to_move_polar = 0
  
            self.tl_ready = 0 ; self.newport_ready = 0
            jobs_scripts.pos_init_motor_polar_meth(self) # to have the print
            self.angle_polar_setVal_meth( 1, self.pos_polar0)
            if self.list_polar.ndim == 2: # 2 WPs
                self.move_motor_newport_signal.emit(self.pos_polar0b)  # # 2nd col
        elif motor <= -1: # # calib
            jobs_scripts.no_job_running_meth(self)
            self.acq_name_edt.setText(self.name0) # calib or name previous
            if not self.real_time_disp_chck.isChecked(): self.real_time_disp_chck.setChecked(True)
        
    @pyqtSlot(int)
    def end_job_apt_suite(self, v):
        # in all cases
        # v is useless, but keep it
        if self.motor_temp == 1:   # ps job
            try: self.mtr_phshft_finishedmove_sgnl.disconnect(self.end_job_apt_suite) # disconnect itself, because no need anymore
            except TypeError: pass
            self.count_job_ps = 0  # re-init 
            
        elif self.motor_temp == 2:   # polar job 
            if self.list_polar.ndim == 1: # one WP
                signal_considered = self.worker_apt.motor_polar_finished_move_signal
            else: # 2 WPs
                signal_considered = self.both_polars_finished_move_signal 
                self.worker_apt.motor_polar_finished_move_signal.disconnect() # disconnects all, if connection there is
                self.worker_newport.motor_newport_finished_move_signal.disconnect() # disconnects all, if connection there is
            signal_considered.disconnect(self.end_job_apt_suite) # disconnect itself, because no need anymore
            self.count_job_polar = 0  # re-init  
    
        if self.connect_end_apt_to_move_Z: # z-stack as secondary job, not the end now
        
            # they will be redefined if necessary
            self.connect_end_apt_to_move_Z = 0
            
            # print('\n Move Z # %d/%d \n' % (self.count_job_Z_stack+1, len(self.list_pos_Z_to_move_piezo_or_motorZ)+1))
            # print('self.count_job_Z_stack ,len(self.list_pos_Z_to_move_piezo_or_motorZ) = ', self.count_job_Z_stack , len(self.list_pos_Z_to_move_piezo_or_motorZ))
            
            if self.count_job_Z_stack < len(self.list_pos_Z_to_move_piezo_or_motorZ): # scan z-stack NOT finished
                self.send_move_to_worker_imic_obj_Z() # # call another method of GUI
                # self.count_job_Z_stack += 1  # iter.
                
            else: # scan z-stack finished
                self.jobs_window.strt_job_button.setEnabled(True) # re-activate the start job button
                print('sent signal to end stack Z job, in end_job_apt')
                self.end_job_stackZ_signal.emit() # send to a function in the GUI
    
        else:  # ps scan as secondary job OR  # polar as sec. job OR the end        
            jobs_scripts.ps_polar_jobs_end_util(self)

    @pyqtSlot()
    def end_job_stack_Z(self):
        
        print('Ending z-stack job ...')
            
        jobs_scripts.ZstckEnd_reconnectNormal_meth(self)
        
        if self.connect_new_img_to_move_Z_obj:
            print('Disconnecting the step of obj. Z from the new img received')
            self.connect_new_img_to_move_Z_obj = 0
            
        # else: # z-stack is secondary job with ps job as primary 
        
        self.count_job_Z_stack = 0  # re-init 
        
        jobs_scripts.ps_polar_jobs_end_util(self)
        
    @pyqtSlot()
    def end_job_mosaic(self):
        
        print('Ending mosaic job ...')
            
        try:
            self.worker_stageXY.home_ok.disconnect() # signal just used to see if motor is available after X or Y
        except TypeError: # nothing
            pass
        self.worker_stageXY.home_ok.connect(self.has_been_homed)  # normal
        
        if self.Zplane_mosaic_um_r is not None:
            jobs_scripts.ZstckEnd_reconnectNormal_meth(self)
        
        if self.connect_new_img_to_move_XY:
            print('Disconnecting the step of XY from the new img received')
            self.connect_new_img_to_move_XY = 0
        
        # pos00    
        self.posX_edt.setValue(self.list_pos_job_mosXY[0][0]) # X, mm
        self.posY_edt.setValue(self.list_pos_job_mosXY[1][0]) # Y, mm
        time.sleep(0.5)  # # essential, if not orders superimposed
    
    @pyqtSlot()
    def list_pos_job_def_util(self):
        if (self.jobs_window.ps_mtr_trans_radio.isChecked() or self.jobs_window.ps_mtr_dcvolt_radio.isChecked()): # set calib by displacement of motor phshft (special), use motor trans or DC
            num_frames = self.jobs_window.num_frame_calib_phshft_spbx.value() # number of frames to use for calibration
            # # it's because the motor trans has a linear variation of phase-shift vs motor displacemen
            eq_deg_um_theo = self.jobs_window.eq_deg_unit_test_spnbx.value() # eq_deg_um to use for calibration
            # # can be a deg to volt if this mode chosen
            max_angle_calib = self.jobs_window.max_angle_calib_phshft_spbx.value() # max angle to use for calibration
            if self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # # max not in °, but V
                max_angle_calib = max_angle_calib*eq_deg_um_theo # is now in V*°/V = °
            
            add_modulo_2pi = param_ini.add_modulo_2pi_calib_ps
            if self.jobs_window.ps_fast_radio.isChecked(): # # fast
                add_modulo_2pi = False # # used before for mtr trans to ensure steps are high enough
                num_frames = 2
            self.list_pos_wrt_origin = jobs_scripts.list_calib_motor_phshft_func(numpy, num_frames, eq_deg_um_theo, max_angle_calib, add_modulo_2pi) # # can be a list of DC volt if this mode chosen
            
            # # offset init
            self.offset_pos_motor_ps = float(self.jobs_window.trans_pos_live_lbl.text()) if self.jobs_window.ps_mtr_trans_radio.isChecked() else self.jobs_window.valHV_EOMph_spbx.value()  # # calib starts at the current value, um 
            
        elif self.jobs_window.ps_mtr_rot_radio.isChecked(): # set calib by angles, use motor rot
            strt_calib_pos = self.jobs_window.st_calib_phshft_spnbx.value() # start position of motor phshft
            step_calib_pos = self.jobs_window.step_calib_phshft_spnbx.value() # step of motor phshft
            end_calib_pos = self.jobs_window.end_calib_phshft_spnbx.value() # end position of motor phshft
            
            self.list_pos_wrt_origin = numpy.linspace(strt_calib_pos*1000, end_calib_pos*1000,  math.ceil((end_calib_pos-strt_calib_pos)/step_calib_pos) + 1)
            # self.list_pos_wrt_origin = numpy.arange(strt_calib_pos*1000, end_calib_pos*1000, step_calib_pos*1000)  # in um
            # self.list_pos_wrt_origin = numpy.append(self.list_pos_wrt_origin, self.list_pos_wrt_origin[len(self.list_pos_wrt_origin)-1]+step_calib_pos*1000)
        # # print(self.sender(), isinstance(self.sender(), QtWidgets.QPushButton))
        if isinstance(self.sender(), QtWidgets.QPushButton):
            print('simu ps list', self.list_pos_wrt_origin   ) 
            
    # is not a pyqtSlot   
    def cal_ps_meth(self):
        # # calibration of phase-shift
        
        # # self.name0 = 'calib'
        if self.jobs_window.ps_mtr_trans_radio.isChecked(): # # trans
            self.pos_phshft0 = float(self.jobs_window.trans_pos_live_lbl.text())/1000 # has to be in mm, not um
        elif self.jobs_window.ps_mtr_rot_radio.isChecked(): # # rot
            self.pos_phshft0 = float(self.jobs_window.gp_pos_live_lbl.text())/1000 # has to be in mm, not um
        elif self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # # DC volt
            self.pos_phshft0 =  self.jobs_window.valHV_EOMph_spbx.value()/1000 # has to be in mV not V

        self.list_pos_job_def_util() # # see above
        # # self.list_pos_wrt_origin is defined here
        
        if self.jobs_window.ps_fast_radio.isChecked(): # # fast
            self.count_job_ps = 2 # ending
            if self.mode_scan_box.currentIndex() != 2: self.mode_scan_box.setCurrentIndex(2) #not static acq., now ok
            if self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC': # # calib EOM with AC # EOM cal # AC calib
                linetime_us= self.jobs_window.ramptime_us_EOMph_spbx.value() if self.jobs_window.stmode_EOMph_cbBx.isEnabled() == True else 2000
                self.vel_mtr_phsft  = t_line = t_tot = target_begin = target_end = self.off_acc_mm = self.res_theo_mm_mtr = 0
                self.nb_px_line_fastcal = round((self.jobs_window.max_angle_calib_phshft_spbx.value()/self.jobs_window.restheo_fastcalib_spbx.value()))
                self.exp_time_real_calib_sec = linetime_us*1e-6/self.nb_px_line_fastcal
                self.nb_pass_calcites = 0
                self.list_pos_wrt_origin = [] 

            else:  # trans
                val = self.jobs_window.restheo_fastcalib_spbx.value()
                if val>0: self.res_theo_deg = val
                self.vel_mtr_phsft, self.exp_time_real_calib_sec, self.nb_px_line_fastcal, t_line, t_tot, target_begin, target_end, self.off_acc_mm, self.res_theo_mm_mtr = jobs_scripts.calib_fast_calc(math, self.res_theo_deg, self.alpha_calc_deg, self.min_exp_time_calibfast_sec, self.vel_mtr_phsft, self.accn_mtr_phsft, self.list_pos_wrt_origin[-1]/1000, self.lambda_shg_um*1e-6, self.vg1, self.vg2, self.list_pos_wrt_origin[0]/1000, self.jobs_window.inv_order_chck.isChecked(), self.nb_pass_calcites)
            self.jobs_window.exptime_fastcalib_vallbl.setText('%.3f' % (self.exp_time_real_calib_sec*1000))
            if self.jobs_window.inv_order_chck.isChecked(): # # invert order for doing reverse autoco
                self.list_pos_wrt_origin[-1] = self.list_pos_wrt_origin[0] - self.list_pos_wrt_origin[-1]
            print('fast mode for calib p-s !', 'time tot', round(t_tot, 2), 'with only', round(t_line, 2), 'sec in movement')
            self.offset_pos_motor_ps += -self.off_acc_mm*1000 # #self.list_pos_wrt_origin[0] = target_begin*1000 # in um
            # # self.list_pos_wrt_origin[-1] = target_end*1000 # in um
            time_str =  '%.2f' % (t_tot/60) # #in min 
            
            if self.jobs_window.autoco_frog_pushButton.text() == 'FROG':
                self.spectro_connected = 2 if self.spectro_connected else -2
                # # time.sleep(1) # # if spectro is started
                self.spectro_conn_disconn_push_meth()
                # # if param_ini.fast_acq_frog:
                # #     time.sleep(1) # # the spectro acq. will be started if spectro was not connected
                # # # # self.spectro_acq_flag_queue.put([1])
                # # # # self.acquire_spectrum_continuous_signal.emit(0) # mode normal
                # #     self.spectro_acq_flag_queue.put([-3]) # # stop
                # # time.sleep(0.5) # # the spectro acq. will be started if spectro was not connected
                # # empty queue
                # # if not self.spectro_acq_flag_queue.empty(): 
                # #     qsz = self.spectro_acq_flag_queue.qsize(); ind_queue = 0
                # #     while ind_queue < qsz:
                # #         try:
                # #             msg = self.spectro_acq_flag_queue.get_nowait()
                # #         except queue.Empty:
                # #             break
               
                if param_ini.fast_acq_frog:
                    try:
                        self.acquire_spectrum_continuous_signal.disconnect(self.worker_spectro.acquire_spectrum_continuous_meth)  # # safety
                    except TypeError:
                        pass
                    var = self.jobs_window.nblinesimg_fastcalib_spbx.value() if param_ini.fast_acq_frog else 1e6*self.exp_time_real_calib_sec/self.jobs_window.nblinesimg_fastcalib_spbx.value()
                    self.spectro_acq_flag_queue.put([1, [self.lower_bound_shgjob , self.upper_bound_shgjob , self.lwr_bound_exp_shgjob, self.upr_bound_exp_shgjob, var, self.exp_time_real_calib_sec, self.save_live_frog_calib, self.save_big_frog_calib, self.path_frog, self.res_theo_mm_mtr, (1/self.vg1 - 1/self.vg2)/0.000000001*self.nb_pass_calcites, self.vel_mtr_phsft, self.save_excel_frog_calib, int(self.nb_px_line_fastcal) , self.keep_wlth_frog]]) # last is save_excel
                    # # [lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, nb_avg, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, save_excel, nb_px_line_fastcal]
                    # # eq_inps_1mm_mtr = eq_inps_1mm_calci*nb_pass = (1/self.vg1 - 1/self.vg2)/0.000000001*self.nb_pass_calcites, in ps/mm
                    
                    self.divider_lines_calib_fast = None # # is used by plot to detect a FROG, not autoco

            else: # # autoco
                divider_lines_calib_fast = self.divider_lines_calib_fast = self.jobs_window.nblinesimg_fastcalib_spbx.value()
                divider_lines_calib_fast += math.ceil((self.nb_px_line_fastcal%self.divider_lines_calib_fast)/self.nb_px_line_fastcal)
                # # print('div', int(self.nb_px_line_fastcal/self.divider_lines_calib_fast), divider_lines_calib_fast) 
                self.square_img_chck.setChecked(False); self.square_px_chck.setChecked(False)
                self.stepY_um_edt.blockSignals(True); self.stepX_um_edt.blockSignals(True)
                self.nbPX_Y_ind.setValue(divider_lines_calib_fast); self.nbPX_X_ind.setValue(int(self.nb_px_line_fastcal/self.divider_lines_calib_fast))
                self.stepY_um_edt.blockSignals(False);  self.stepX_um_edt.blockSignals(False)
                self.square_px_chck.blockSignals(True); self.square_px_chck.setChecked(True); self.square_px_chck.blockSignals(False); 
                self.dwll_time_edt.setValue(self.exp_time_real_calib_sec*1e6) # # us
                # if self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC': self.duration_indic.setText( str(linetime_us*1e-6))

                # # will just start the Process
                
                self.set_new_scan = 3 # # will kill the current, start a new
                self.define_if_new_scan() # # will start the Thread
                # # time.sleep(1) # # the time for self.list_scan_params to be set
                self.queue_com_to_acq.put([2, self.list_scan_params_full])  # # 2 for just start the buffer etc. but no acq.
            # # time.sleep(0.5)
            bb = False # don't emit finished move
            print('fast mode: start the job manually please')
            self.jobs_window.strt_job_button.setEnabled(True)
            
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = False # watch in live the move
            
        else: # # slow
            
            list_str = param_ini.list_ps_separator.join(str(x) for x in self.list_pos_wrt_origin)
            self.jobs_window.table_jobs.setItem(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(list_str)) # ps job params
            bb = True
            if hasattr(self, 'mtr_phshft_finishedmove_sgnl'):
                try:
                    self.mtr_phshft_finishedmove_sgnl.disconnect(self.cal_ps_meth_suite)
                except TypeError:
                    pass
                self.mtr_phshft_finishedmove_sgnl.connect(self.cal_ps_meth_suite)
            
            dur_mtr = self.jobs_window.step_calib_phshft_spnbx.value()/self.vel_mtr_job if not self.jobs_window.ps_mtr_dcvolt_radio.isChecked() else 1
            time_str = '%.2f' % (len(self.list_pos_wrt_origin)*(dur_mtr+float(self.duration_indic.text()))/60) # #in min
            self.offset_pos_motor_ps = 0 # important !!
            
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = True # has to block the move before doing something else, otherwise it is too fast
        
        if (self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC'): return # # fast calib of modulator using AC
        else:
            pos = self.list_pos_wrt_origin[0]/1000 + self.offset_pos_motor_ps/1000
            if not self.jobs_window.offsetalreadyhere_fastcalib_chck.isChecked():
                self.change_phshft_sgnl.emit(pos, bb) # # can be DC volt set as well if this mode is chosen
                numtr= 2 if self.jobs_window.ps_mtr_trans_radio.isChecked() else 1
                self.pos_ps_setxt(numtr, '%.3f' % (pos*1000)) # # 2 for not live trans
            self.jobs_window.time_job_ind_bx.setText(time_str)
            
            print('pos', self.list_pos_wrt_origin,  self.offset_pos_motor_ps)

    @pyqtSlot(int)    
    def cal_ps_meth_suite(self, v):
        # calibration of phase-shift (suite)
        # v is useless, but keep it for signals
        print('(in cal. suite)', v)
        if v != -1: # # not direct call
            self.mtr_phshft_finishedmove_sgnl.disconnect(self.cal_ps_meth_suite) # disconnect itself, because it's only for first pos
        unitstr = 'V' if self.jobs_window.ps_mtr_dcvolt_radio.isChecked() else 'um' 
        if not self.jobs_window.ps_fast_radio.isChecked(): # # slow
            self.count_job_ps = 1  # init 
        
            # # if self.stage_scan_mode != 1: # is not stage scan # 3 ???
            # # I need this for stg scan at least for DC volt slow
            try:
                self.mtr_phshft_finishedmove_sgnl.disconnect(self.send_new_img_to_acq)
            except TypeError: # if had no connection
                pass
            self.mtr_phshft_finishedmove_sgnl.connect(self.send_new_img_to_acq)
        
            # print(self.list_pos_wrt_origin)
            # return
            
            self.connect_new_img_to_move_phshft = 1
            print('Connecting the step of motor phshft from the new img received')
            print('calib pos are :', self.list_pos_wrt_origin) # ok
            job_name = ('calib_step%.3f%s' % (self.jobs_window.step_calib_phshft_spnbx.value(), unitstr))
            
            if float(self.duration_indic.text()) <= 1.0: #sec
                self.real_time_disp_chck.setChecked(False)
                self.kill_scanThread_meth() # # have to reset the Process for using this feature
            
        else: # # fast
            job_name = ('calib_fast_%.3f%s' % (self.jobs_window.num_frame_calib_phshft_spbx.value(), unitstr)) # # last el.
            if self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] != 'DC': # # calib fast ishg AC
                self.gather_calib_flag = False # # init
                if hasattr(self, 'mtr_phshft_finishedmove_sgnl'): self.mtr_phshft_finishedmove_sgnl.connect(self.gather_calib_ps)
        self.name0 = self.acq_name_edt.text()
        self.acq_name_edt.setText(job_name)
        self.job_name = job_name
        
        if (self.jobs_window.ps_fast_radio.isChecked() and self.change_phshft_sgnl is not None and len(self.list_pos_wrt_origin) > 0): # # fast
        
            pos_mm = self.list_pos_wrt_origin[-1]/1000 + self.offset_pos_motor_ps/1000 + 2*self.off_acc_mm
            # # if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
            # #     self.worker_apt.wait_flag = True
            self.change_phshft_sgnl.emit(pos_mm, False) # # False  for no send
            self.pos_ps_setxt(2, '%.3f' % (pos_mm*1000)) # # 2 for not live trans
            # # self.mtr_phshft_finishedmove_sgnl.connect(
        
        if (v == -1 and self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.autoco_frog_pushButton.text() == 'FROG'): # # v=-1 is calib fast
            print('-- FROG --')
            if self.use_shutter_combo.currentIndex():
                self.send_new_img_to_acq(-1) # # will just open shutter if needed
                time.sleep(self.waitTime_shutter_00 + self.shutter_duration_ms_spnbx.value()/1000)
            if not param_ini.fast_acq_frog: # # slow function in spectro (but not step by step)
                self.spectro_acq_flag_queue.put([1, [self.lower_bound_shgjob , self.upper_bound_shgjob , self.lwr_bound_exp_shgjob, self.upr_bound_exp_shgjob, 1e6*self.exp_time_real_calib_sec/self.jobs_window.nblinesimg_fastcalib_spbx.value(), self.exp_time_real_calib_sec, self.save_live_frog_calib, self.save_big_frog_calib, self.path_frog, self.res_theo_mm_mtr, (1/self.vg1 - 1/self.vg2)/0.000000001*self.nb_pass_calcites, self.save_excel_frog_calib, int(self.nb_px_line_fastcal), self.keep_wlth_frog]]) # last is save_excel
                # # [lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, integration_time_spectro_us, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, save_excel, nb_px_line_fastcal]
                # # eq_inps_1mm_mtr = eq_inps_1mm_calci*nb_pass = (1/self.vg1 - 1/self.vg2)/0.000000001*self.nb_pass_calcites, in ps/mm
                self.acquire_spectrum_continuous_signal.emit(1)
            else:
                self.spectro_acq_flag_queue.put([1]) # # 1 is start

        else: # # normal, slow calib or fast autoco
            if self.jobs_window.ps_fast_radio.isChecked():  # # fast autoco
                print('-- Autoco --')
                if self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC':
                    # if len(self.list_scan_params) >= 2: self.list_scan_params=
                    if len(self.list_scan_params) >= 2: self.list_scan_params[-2] = 0.0 # has to be a float, to set mtr out but not retriggerable
                self.empty_queue_send_reset_scan(True)
            else:   # # normal, slow calib
                self.num_experiment+= 1
                jobs_scripts.launch_job_general(self) # # animateclick launch scan, with nb_img = 1
        
        if self.jobs_window.ps_fast_radio.isChecked(): # # fast
            self.jobs_window.table_jobs.setItem(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem('1'))
            # # if not (self.jobs_window.autoco_frog_pushButton.text() == 'FROG'): # # autoco
                # self.set_new_scan = 0

            self.count_avg_job = -1 # # for finishing
            # # self.cal_ps_button_txt00 = self.jobs_window.cal_ps_button.text()
            self.jobs_window.cal_ps_button.setText(self.cal_ps_button_stop00)
            self.jobs_window.cal_ps_button.setStyleSheet('color: red')

    
    def job_apt_meth(self):
        # for phase-shift jobs or polar jobs
        # called directly by start_job_after_meth_suite
        
        print('Inside job_apt_meth')
        
        # eq_deg_um = self.jobs_window.eq_deg_unit_test_spnbx.value() # eq_um_deg to use for job
        # step_phase_shift = self.jobs_window.step_phase_shift_spbx.value() # phase step to use for job
        
        # if (type_job_str == param_ini.z_ps_name_job or type_job_str == param_ini.polar_ps_name_job or type_job_str == param_ini.ps_name_job or type_job_str == ps_zstck_name_job):
        
        # print(self.list_pos_wrt_origin)
        try:
            self.mtr_phshft_finishedmove_sgnl.disconnect() # disconnects all, if connection there is
        except TypeError: # if had no connection
            pass
        try:
            if hasattr(self, 'worker_apt'):
                self.worker_apt.motor_polar_finished_move_signal.disconnect() # disconnects all, if connection there is
        except TypeError: # if had no connection
            pass
        
        # # might be defined for nopthing if no p-s, but does not matter
        
        type_job_str = self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()
        
        if (type_job_str == param_ini.z_ps_name_job or type_job_str == param_ini.polar_ps_name_job or type_job_str == param_ini.z_polar_name_job or type_job_str == param_ini.ps_polar_name_job): # # two intricated jobs
        
            if type_job_str == param_ini.z_ps_name_job: #self.jobs_window.job_choice_combobx.currentIndex() == 13: # secondary job = ps, and primary = z-stack
                self.connect_end_z_to_move_phshft = 1  # # so the move of ps will start a new Z serie
                meth_associated = self.init_job_z_stack
                signal_considered = self.mtr_phshft_finishedmove_sgnl
                
            elif type_job_str == param_ini.z_polar_name_job:
                self.connect_end_z_to_move_polar = 1 # # so the move of polar will start a new Z serie
                meth_associated = self.init_job_z_stack
                if self.list_polar.ndim == 1: # one WP
                    signal_considered = self.worker_apt.motor_polar_finished_move_signal
                else: # 2 WPs
                    signal_considered = self.both_polars_finished_move_signal
                    self.twomotors_wp_util() 
                    
            elif type_job_str == param_ini.polar_ps_name_job: # polar in bigger ps
                self.connect_end_polar_to_move_ps = 1  # # so the move of ps will start a new polar serie
                signal_considered = self.mtr_phshft_finishedmove_sgnl
                meth_associated = self.job_apt_meth # !!!
                
            elif type_job_str == param_ini.ps_polar_name_job: # ps in bigger polar
                self.connect_end_ps_to_move_polar = 1  # # so the move of ps will start a new polar serie
                meth_associated = self.job_apt_meth 
                if self.list_polar.ndim == 1: # one WP
                    signal_considered = self.worker_apt.motor_polar_finished_move_signal
                else: # 2 WPs
                    signal_considered = self.both_polars_finished_move_signal
                    self.twomotors_wp_util() 
            try:
                signal_considered.disconnect(meth_associated)
            except TypeError: # if had no connection
                pass
            signal_considered.connect(meth_associated) #lambda: init_job_z_stack(self)) # connects end of move to next action
                
            if self.connect_end_z_to_move_phshft:
                meth_associated() # see few lines before
        
        # # self.wait_flag_apt_current = self.worker_apt.wait_flag
            
        if (type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.ps_name_job or type_job_str == param_ini.ps_polar_name_job or type_job_str == param_ini.polar_name_job or type_job_str == param_ini.polar_zstck_name_job or type_job_str == param_ini.polar_ps_name_job): # apt job is called multiple times : ps or polar is primary job inside a bigger job (secondary), or is primary (or secondary) alone
            
            if (type_job_str == param_ini.polar_name_job or type_job_str == param_ini.polar_zstck_name_job or type_job_str == param_ini.polar_ps_name_job): # polar involved
                self.connect_new_img_to_move_polar = 1

            else: # ps
            # if self.stage_scan_mode != 1: # is not stage scan
                self.connect_new_img_to_move_phshft = 1
                print('Connecting the step of motor phshft from the new img received')
                
            if (self.count_job_polar == 0 and (type_job_str == param_ini.polar_ps_name_job or type_job_str == param_ini.polar_name_job or type_job_str == param_ini.polar_zstck_name_job or type_job_str == param_ini.ps_polar_name_job)):
                self.count_job_polar = 1  # init
            if (self.count_job_ps == 0 and (type_job_str == param_ini.ps_polar_name_job or type_job_str == param_ini.ps_name_job or type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.polar_ps_name_job)):
                self.count_job_ps = 1  # init 

            if (type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.polar_zstck_name_job): # self.jobs_window.job_choice_combobx.currentIndex() == 4: # secondary job = z-stack, and primary = ps
                self.connect_end_apt_to_move_Z = 1
            # # elif type_job_str == param_ini.ps_polar_name_job: # self.jobs_window.job_choice_combobx.currentIndex() == 4: # secondary job = z-stack, and primary = ps
            # #     self.connect_end_ps_to_move_polar = 1
            # # # # elif type_job_str == param_ini.polar_zstck_name_job: # self.jobs_window.job_choice_combobx.currentIndex() == 4: # secondary job = z-stack, and primary = ps
            # # # #     self.connect_end_polar_to_move_Z = 1
            # # elif type_job_str == param_ini.polar_ps_name_job: # self.jobs_window.job_choice_combobx.currentIndex() == 4: # secondary job = z-stack, and primary = ps
            # #     self.connect_end_polar_to_move_ps = 1
            
            # if self.connect_new_img_to_move_phshft:
            jobs_scripts.launch_job_general(self)
                
            # else: # stage scan
            #     jobs_scripts.launch_job_general_stage(self)
            
            if (type_job_str == param_ini.polar_name_job or type_job_str == param_ini.polar_zstck_name_job or type_job_str == param_ini.polar_ps_name_job): # polar involved
                if self.list_polar.ndim == 1: # one WP
                    apt_signal_assoc = self.worker_apt.motor_polar_finished_move_signal
                else: # 2 WPs
                    apt_signal_assoc = self.both_polars_finished_move_signal
                    self.twomotors_wp_util() # # already made

            else: #if type_job_str == param_ini.ps_name_job: # p-s
                apt_signal_assoc = self.mtr_phshft_finishedmove_sgnl
            try:
                apt_signal_assoc.disconnect(self.send_new_img_to_acq)
            except TypeError: # if had no connection
                pass
            apt_signal_assoc.connect(self.send_new_img_to_acq) # connects phshft move to new acq.
    
    def twomotors_wp_util(self):
        self.tl_ready = 0 
        self.newport_ready = 0
        try:
            self.worker_apt.motor_polar_finished_move_signal.disconnect(self.wp_polar_ready_meth )
        except TypeError: # if had no connection
            pass
        self.worker_apt.motor_polar_finished_move_signal.connect(self.wp_polar_ready_meth )
        try:
            self.worker_newport.motor_newport_finished_move_signal.disconnect(self.wp_polar_ready_meth )
        except TypeError: # if had no connection
            pass
        self.worker_newport.motor_newport_finished_move_signal.connect(self.wp_polar_ready_meth )
                                
    @pyqtSlot()    
    def init_job_z_stack(self):
        # not for stage scan
        
        onlymtr = self.jobs_window.only_motorZ_chck.isChecked()
        # read here the list of Z from table
        # # print('\n self.row_jobs_current \n ', self.row_jobs_current)
        list_Z_abs = [float(i) for i in self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.zstck_posWrtEnd_jobTable).text().split(param_ini.list_Z_separator)]
        range = list_Z_abs[-1] - list_Z_abs[0]
        if (not onlymtr and range > param_ini.max_range_piezoZ): # mm, scan Z cannot be made using only the piezo, so the piezo won't be used
            if QtWidgets.QMessageBox.question(None, 're-def. Zrange ?', "Zrange too high for piezo: st job using mtr Z anyway ?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes) == QtWidgets.QMessageBox.No:
                return # outside this func
 
        print('\n Z stack job starting ...\n')
        
        # print('self.connect_end_z_to_move_phshft = ', self.connect_end_z_to_move_phshft

        #currentZ_motor = self.posZ_motor_edt.value()
        #currentZ_piezo = self.posZ_piezo_edt.value()/1000 # piezo is in um
        
        self.piezo_ready = 0
        self.count_job_Z_stack = 0
        
        # disconnect the button to change Z
        try:
            self.posZ_motor_edt_1.valueChanged.disconnect(self.z_motor_edt1_changed) # to make changed in Z value
            self.posZ_motor_edt_2.valueChanged.disconnect(self.z_motor_edt2_changed) # to make changed in Z value
            self.posZ_motor_edt_3.valueChanged.disconnect(self.z_motor_edt3_changed) # to make changed in Z value
            self.posZ_piezo_edt_1.valueChanged.disconnect(self.z_piezo_edt1_changed)
            self.posZ_piezo_edt_2.valueChanged.disconnect(self.z_piezo_edt2_changed)
            self.posZ_piezo_edt_3.valueChanged.disconnect(self.z_piezo_edt3_changed)
            self.posZ_piezo_edt_4.valueChanged.disconnect(self.z_piezo_edt4_changed)
            self.posZ_piezo_edt_5.valueChanged.disconnect(self.z_piezo_edt5_changed)
        except TypeError: # if had no connection
            pass
        
        while True:    
            try:
                self.progress_piezo_signal.disconnect(self.piezo_ready_meth)
            except TypeError: # if had no connection
                break
        if (self.imic_was_init_var and self.worker_imic is not None): 
            self.motorZ_ready = 0 # will check
            while True:  
                try:
                    self.worker_imic.progress_motor_signal.disconnect(self.motorZ_ready_meth) 
                except TypeError: # if had no connection
                    break
            self.worker_imic.progress_motor_signal.connect(self.motorZ_ready_meth) # each time the pos Z is moved, signal to take a new img sent
        else: self.motorZ_ready = 1 # # no use of mtr, because not here
        if not onlymtr:
            self.progress_piezo_signal.connect(self.piezo_ready_meth)
        
        self.list_pos_Z_to_move_piezo_or_motorZ, self.use_piezo_for_Z_stack, motor_Z_to_set, piezo_Z_to_set = jobs_scripts.z_defmoveList_meth(onlymtr, numpy, list_Z_abs) # defines the list to move by piezo or mtorZ, that will remains the same until a new initJobZ
         # however it prevents user from changing Z list via table
         # it's because the split between motorZ and piezoZ is heavy and is done done all the time
        
        type_job_str = self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()
        
        if (type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.polar_zstck_name_job): # self.jobs_window.job_choice_combobx.currentIndex() == 4: # secondary job = z-stack, and primary = ps
            self.connect_end_apt_to_move_Z = 1
            
        else: # init_job_z is called multiple times : z-stack is primary job inside a bigger job of ps (secondary), or is primary (or secondary) alone
            
            self.connect_new_img_to_move_Z_obj = 1
            print('Connecting the step of obj. in Z from the new img received')
 
            if type_job_str == param_ini.z_ps_name_job: #self.jobs_window.job_choice_combobx.currentIndex() == 13: #(self.jobs_window.ps_job_sec_radio.isChecked() and self.jobs_window.z_job_prim_radio.isChecked()): # secondary job = ps, and primary = z-stack
            
                self.connect_end_z_to_move_phshft = 1
                
            elif type_job_str == param_ini.z_polar_name_job: # 
                self.connect_end_Z_to_move_polar = 1
                
        if self.jobs_window.inv_order_chck.isChecked():
            self.list_pos_Z_to_move_piezo_or_motorZ = self.list_pos_Z_to_move_piezo_or_motorZ[::-1] # reverse order
            motor_Z_to_set = self.list_pos_Z_to_move_piezo_or_motorZ[-1]
        # # if not self.jobs_window.only_motorZ_chck.isChecked():    
        # #     self.list_pos_Z_to_move_piezo_or_motorZ = self.list_pos_Z_to_move_piezo_or_motorZ[1:]
        print('\n List of Z-pos to do (with 1st):', self.list_pos_Z_to_move_piezo_or_motorZ)
        
        # print('self.connect_new_img_to_move_phshft = ', self.connect_new_img_to_move_phshft)
        # print('list_pos_Z_to_move_piezo_or_motorZ = ' , self.list_pos_Z_to_move_piezo_or_motorZ)
        self.motorZ_move_signal.emit(motor_Z_to_set) # mm
        # self.posZ_motor_edt.setValue(motor_Z_to_set)
        self.motorZ_changeDispValue_signal.emit(motor_Z_to_set) # mm
        
        self.piezoZ_move_signal.emit(piezo_Z_to_set) # in mm
        self.piezoZ_changeDispValue_signal.emit(piezo_Z_to_set) # mm
        self.count_job_Z_stack += 1

        # print('piezo_Z_to_set', piezo_Z_to_set)
        # self.posZ_piezo_edt.setValue(piezo_Z_to_set)
        
    @pyqtSlot()    
    def send_move_to_worker_phshft(self):
        # is called each time a new image has been sent to the GUI, or directly
        
        pos_phshft0 = 0 # not a relative but absolute position
        
        if self.jobs_window.table_jobs.rowCount() >= 1: # # some row
            str_list = self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)
        else: return
        if self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()[:5] == param_ini.calib_ps_name_job[:5]: #not str_list[0].replace('.','',1).isdigit(): # # e.g. calib ps
            list_ps = self.list_pos_wrt_origin
            em_str = -2 if (self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC') else -1  # #  -2 if fast calibISHG_AC else autoco or calib ps
            # calib
        else: # # normal phsft job
            list_ps = [float(i) for i in str_list]
            pos_phshft0 = 0 # # self.pos_phshft0
            em_str = 1 # # normal
        
        # if self.jobs_window.ps_mtr_rot_radio.isChecked(): # use motor rot.
        
        # # print('In send_move_to_worker_phshft : self.connect_new_img_to_move_phshft = ', self.connect_new_img_to_move_phshft)
                
        if self.count_job_ps < len(list_ps): # job not finished
            
            print('\n Move phshft # %d/%d \n' % (self.count_job_ps+1, len(list_ps)))

            # if self.stage_scan_mode != 1: # is not stage scan
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None): self.worker_apt.wait_flag = True
            self.change_phshft_sgnl.emit(list_ps[self.count_job_ps]/1000 + pos_phshft0 + self.offset_pos_motor_ps/1000, True) # must be a float, has to be in mm, not um
            # True for send when finished
            # else: # stage scan
            self.count_job_ps += 1
                
        else:  # scan ps finished
        
            print('sent signal to end job, in send_phshft_meth')
            self.end_job_apt_signal.emit(em_str) # send to a function in the GUI # -1 for calib, 1 for normal
            # 1 for ps
            self.count_job_ps = 0
            
        
    @pyqtSlot()    
    def send_move_to_worker_polar(self):
        
        print('\n Move polar # %d/%d \n' % (self.count_job_polar+1, len(self.list_polar)))
                
        if self.count_job_polar < len(self.list_polar): # not finished
        
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = True  # # otherwise too fast !
                
            if self.list_polar.ndim == 1: # # 1 dim
                ppl = self.list_polar[self.count_job_polar]
            else: # # 2 dim
                self.tl_ready = 0 
                self.newport_ready = 0
                ppl = self.list_polar[self.count_job_polar, 0] # 1st col
                self.move_motor_newport_signal.emit(self.list_polar[self.count_job_polar, 1])  # QWP

            self.move_motor_rot_polar_signal.emit(ppl)  # HWP
            self.count_job_polar += 1  # iter.

        else:  # scan polar finished
            
            print('sent signal to end polar job, in send_move_polar because ', self.count_job_polar, '/ ', len(self.list_polar))
            self.end_job_apt_signal.emit(2) # send to a function in the GUI
            # 2 for ps
            self.count_job_polar = 0 
        
    @pyqtSlot()    
    def send_move_to_worker_imic_obj_Z(self):
        
        print('\n Move Z # %d/%d in jobZ\n' % (self.count_job_Z_stack+1, len(self.list_pos_Z_to_move_piezo_or_motorZ)))
        if (self.count_job_Z_stack < len(self.list_pos_Z_to_move_piezo_or_motorZ) or len(self.Z_to_set_tmp)>0): # not finished, or not a job
        
            # print('useppiezo =', self.use_piezo_for_Z_stack)
        
            if (self.use_piezo_for_Z_stack or len(self.Z_to_set_tmp)>0): # use piezo, or not a job
                if len(self.Z_to_set_tmp)>0:
                    piezo_Z_to_set = self.Z_to_set_tmp[1]
                else:
                    piezo_Z_to_set = self.list_pos_Z_to_move_piezo_or_motorZ[self.count_job_Z_stack]
                self.piezoZ_move_signal.emit(piezo_Z_to_set) # in mm # for simplicity
                # self.posZ_piezo_edt.setValue(piezo_Z_to_set)
                                
            if (not self.use_piezo_for_Z_stack or len(self.Z_to_set_tmp)>0): # use motorZ, or not a job
                if len(self.Z_to_set_tmp)>0:
                    motor_Z_to_set = self.Z_to_set_tmp[0]
                else:
                    motor_Z_to_set = self.list_pos_Z_to_move_piezo_or_motorZ[self.count_job_Z_stack]
                self.motorZ_move_signal.emit(motor_Z_to_set)
                # # self.mtrZ_setVal_util(motor_Z_to_set)
            self.count_job_Z_stack += 1  # iter.

        else:  # scan z-stack finished
            
            print('sent signal to end stack Z job, in send_move_Z')
            self.end_job_stackZ_signal.emit() # send to a function in the GUI
            self.count_job_Z_stack = 0
    
    @pyqtSlot()    
    def send_move_to_XYmos_job(self):
        # # self.list_pos_job_mosXY is defined in jobs_scripts
        
        print('\n Move XY mos # %d/%d \n' % (self.count_job_mosXY+1, len(self.list_pos_job_mosXY[0])))
        if self.count_job_mosXY < len(self.list_pos_job_mosXY[0]): # not finished
            self.Z_ready_mos = False; self.stageXY_ready_mos = False # # only for Z correc°
            if self.Zplane_mosaic_um_r is not None: # # some Z correct° for mosaic
                Z_rel_um = self.Zplane_mosaic_um_r[int((self.count_job_mosXY-(self.count_job_mosXY%(self.nbStMosFast+1)))/(self.nbStMosFast+1)), int(self.count_job_mosXY%(self.nbStMosFast+1))] # # indexing (Y,X) if X then Y, otherwise (X,Y), in um
                if self.usePZ_mos: # # use piezo
                    self.piezoZ_move_signal.emit(self.mos_Z0_pz+Z_rel_um/1000) # in mm # for simplicity
                    # # self.piezoZ_setVal_util(self.mos_Z0_pz+Z_rel_um/1000) # call piezo 
                else:
                    self.motorZ_move_signal.emit(self.mos_Z0+Z_rel_um/1000)
                    # # self.mtrZ_setVal_util(self.mos_Z0+Z_rel_um/1000) # or motor

            self.posX_edt.setValue(self.list_pos_job_mosXY[0][self.count_job_mosXY]) # X, mm
            self.posY_edt.setValue(self.list_pos_job_mosXY[1][self.count_job_mosXY]) # Y, mm
            time.sleep(0.5)  # essential, if not orders superimposed
            
            # works even in stage scn normally, as the order is considered at beginning of scan
            self.count_job_mosXY += 1
            self.worker_stageXY.control_if_thread_stage_avail_meth() # see if motor available, the home_ok signal will trigger the new img
        else:  # XY mosaic finished
            print('sent signal to end mosaic job, in send_move_toXYmos')
            self.count_job_mosXY = 1
            self.end_job_mosaic()
    
    def send_move_to_single(self):
        self.count_job_singlenomtr += 1
        nb_fr_s = self.jobs_window.table_jobs.item(self.row_jobs_current, param_ini.nbfr_posWrt0_jobTable).text()
        nb_fr = int(nb_fr_s) if nb_fr_s.replace('.','',1).isdigit() else self.nbmax00
        print('\n No mtr job # %d/%d \n' % (self.count_job_singlenomtr,nb_fr))

        if self.count_job_singlenomtr <= nb_fr: # count 1, 2, ... nb_fr 
            self.send_new_img_to_acq(101) # tell the acq process to continue
        else: # over
            print('Disconnecting the singlescn from the new img received')
            self.connect_new_img_to_single = 0
            self.count_job_singlenomtr = 0  
            jobs_scripts.ps_polar_jobs_end_util(self) # general purpose, will go to job_manager_meth for shutter and ctl jobs

            
    @pyqtSlot(int) 
    def wp_polar_ready_meth(self, id_motor):
        
        if id_motor == 1: # TL
            self.tl_ready = 1 
            print('TL ready')
        elif id_motor == 2: # newport
            self.newport_ready = 1
            print('newport ready')
            
        if (self.newport_ready and self.tl_ready): # both ready
            self.both_polars_finished_move_signal.emit(1) # tell to continue because both polars have been set
            
    # is not pyQtSlot  
    def shutter_send_close(self):
        
        if self.use_shutter_combo.currentIndex(): # use shutter or not
            self.open_close_shutter_signal.emit(1) # tell the shutter worker to CLOSE shutter
                
    @pyqtSlot(int)    
    def send_new_img_to_acq(self, v):
        # is called each time the motor phshft (in the worker) has finished to move
        # perhaps it could be replace by a lambda function
        # v is useless, but introduced in case a signal with an arg is linked
        # # print('send_new_img_to_acq' , v)
        self.was_in_send_new_img_func = bool(v > -1)  # # otherwise special
        if v < 100:  # # > 100 for direct call
            if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
                self.worker_apt.wait_flag = self.wait_flag_apt_current # # re-init flag
        
        if (self.stage_scan_mode == 1 and self.imic_was_init_var): # stage scan
        # imic init, allow to use the scan with imic OFF not to lose the previous Z position
            self.filter_top_choice.setCurrentIndex(self.filter_top_choice_curr_index)  
        
        if (self.use_shutter_combo.currentIndex() ==1 or (self.use_shutter_combo.currentIndex() ==2 and v == 100)): # use shutter or not
            if v == 100: diff_time = 0 # # first launch of scan set
            else:
                diff_time = - (time.time() - self.waitTime_shutter_00) - (param_ini.t_understand_order + param_ini.t_shutter_trans)/1000
                if not self.out_scan: # in scan, wait (contrary is was out of scan, no wait)
                    diff_time += self.shutter_duration_ms_spnbx.value()/1000
            
            # because the app will wait (param_ini.t_understand_order + param_ini.t_shutter_trans)/1000 anyway after
            if diff_time > 0: # the waiting time for shutter was reached
                self.waitin_shutter_signal.emit(diff_time)
                # #time.sleep(diff_time) # will block the GUI
                # I calculated that the lower time I can sleep is 10ms 
            else: # no wait 
                self.open_close_shutter_signal.emit(0) # tell the shutter worker to OPEN shutter
        else: # not use shutter
            self.send_new_img_to_acq_suite(0) # 0 to simulate a shutter open
            
        self.out_scan = False
        
    @pyqtSlot(int)    
    def send_new_img_to_acq_suite(self, bool_shutter):
        #is called by shutter worker, or directly by previous meth if no shutter

        if self.was_in_send_new_img_func: # otherwise is called for nothing
            self.was_in_send_new_img_func = 0
            if not bool_shutter: # 0 for OPEN
                if len(self.list_scan_params) == 0: # no change of parameters
                    paquet = [1] # no change of parameter
                else: # change of scan parameters
                    paquet = [1, self.list_scan_params]
                print('\n send_new_img_to_acq is sending a new acq. order \n')
                self.queue_com_to_acq.put(paquet) # tell the acq process to acq. a new image
                
    @pyqtSlot()    
    def piezo_ready_meth(self):
        
        self.piezo_ready = 1
        if self.motorZ_ready:
            self.motorZ_ready = 0
            self.piezo_ready = 0
            print('piezoZ was ready in last')
            jobs_scripts.launch_job_z_stack_meth(self) 
    
    @pyqtSlot()    
    def motorZ_ready_meth(self):
        
        self.motorZ_ready = 1
        if (self.jobs_window.only_motorZ_chck.isChecked() or self.piezo_ready):
            
            if self.piezo_ready:
                self.piezo_ready = 0
            print('motorZ was ready in last')
            self.motorZ_ready = 0
            jobs_scripts.launch_job_z_stack_meth(self)
    
    
    @pyqtSlot()     
    def job_manager_meth(self):
        
        if (self.shutter_is_here and self.use_shutter_combo.currentIndex() == 2):  # # close shutter only at end of job
            self.shutter_send_close() # ordr to close it (before for == 1)
            self.shutter_outScan_mode() # display closed            
        
        self.mtrreturninitposjob = self.jobs_window.mtrreturninitposjob_chck.isChecked()
        st_job = 1
        frst_el_item = self.jobs_window.table_jobs.item(0, 0)
        self.path_tmp_job = None
        
        if frst_el_item is None: # no row
            st_job = 0
        
        if (st_job and self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.rowCount() - 1, 3).text() == param_ini.calib_ps_name_job and int(frst_el_item.text()) >= 1): # calib fast
            self.cal_ps_meth_suite(-1) # -1 for direct
            return # no need to do something else
                    
        # # print('self.iterationInCurrentJob', self.iterationInCurrentJob)
        self.Z_to_set_tmp = []
        
        if not (self.iterationInCurrentJob is None or self.row_jobs_current is None): # a job has been started at some point (second condition is for safety)

            if self.iterationInCurrentJob < int(self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount() - 1-1).text()): # job not finished all repetition
            # one before last element
                self.iterationInCurrentJob += 1
                self.start_job_after_meth()
                return # exit this function
                
            else: # job finished (all repetition)
            # one before last element 
                disp_done = '1'
                self.jobs_window.table_jobs.setItem(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem(disp_done))
                self.iterationInCurrentJob = None
                self.acq_name_edt.setText(self.name0) # calib or name previous
                self.jobs_window.remove_done_jobs_button.setEnabled(True)
        
        if frst_el_item is not None: # no row: # at least one row
        
            frst_row = None # ct = 0; 
            for ii in range(self.jobs_window.table_jobs.rowCount()):
                
                alr_done = self.jobs_window.table_jobs.item(ii, self.jobs_window.table_jobs.columnCount()-1).text()
                if (alr_done is None or int(alr_done) < 1): # not already done
                    frst_row = ii
                    break # outside 'for' loop
                
            if frst_row is None:  # no job to start
                if self.count_avg_job is None: # None means no job is running
                    if QtWidgets.QMessageBox.question(None, 'st 1st job ?', "No job to start : start 1st job anyway ?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes) == QtWidgets.QMessageBox.Yes:
                        st_job = 1
                        frst_row = self.jobs_window.table_jobs.rowCount() - 1
                    else:
                        st_job = 0
                else: # a job was running, don't ask to start another one yet
                    st_job = 0
            
            else: # at least one job to start   

                # # print(frst_el_item.text())
                
                frst_el_item = self.jobs_window.table_jobs.item(frst_row, 0)
                
                if int(frst_el_item.text()) < 1:
                    if QtWidgets.QMessageBox.question(None, '1st job no autostart', "First job in the list is not set to autostart : start anyway ?", QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes) == QtWidgets.QMessageBox.No:
                        st_job = 0
        
        # # print('frst_row', frst_row, self.jobs_window.table_jobs.rowCount(),alr_done )
        
        if (self.row_jobs_current is not None and int(self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1).text()) == -1): # # was canceled
            self.jobs_window.table_jobs.setItem(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem('0'))
            st_job = 0
        # # else: # no job started yet
                
        if st_job: # start a job
            mode_t = int(self.jobs_window.table_jobs.item(frst_row, param_ini.mode_posWrt0_jobTable).text())
            if (mode_t==1 and self.chck_homed == 0):
                print(param_ini.notXY_homed_msg)
                return
            self.iterationInCurrentJob = 1
            
            if mode_t != self.mode_scan_box.currentIndex():
                self.mode_scan_box.setCurrentIndex(mode_t)
                
            type_job_str = self.jobs_window.table_jobs.item(frst_row, 3).text()
            
            # # print(self.jobs_window.table_jobs.item(frst_row, param_ini.centerX_posWrt0_jobTable), frst_row, param_ini.centerX_posWrt0_jobTable)
            x_txt = self.jobs_window.table_jobs.item(frst_row, param_ini.centerX_posWrt0_jobTable).text()
            if x_txt.replace('.','',1).isdigit(): # is a float inside string
                self.posX00 = float(x_txt)
                self.posX_edt.setValue(self.posX00) # X center, in mm
            y_txt = self.jobs_window.table_jobs.item(frst_row, param_ini.centerY_posWrt0_jobTable).text()
            if y_txt.replace('.','',1).isdigit(): # is a float inside string
                self.posY00 = float(y_txt)
                self.posY_edt.setValue(self.posY00) # Y center, in mm

            self.dwll_time_edt.setValue(float(self.jobs_window.table_jobs.item(frst_row, param_ini.dwllTime_posWrt0_jobTable).text())) # dwll_time, us
            self.sizeX_um_spbx.setValue(float(self.jobs_window.table_jobs.item(frst_row, param_ini.szX_posWrt0_jobTable).text())) # um
            self.sizeY_um_spbx.setValue(float(self.jobs_window.table_jobs.item(frst_row, param_ini.szY_posWrt0_jobTable).text())) # um
            self.stepX_um_edt.setValue(float(self.jobs_window.table_jobs.item(frst_row, param_ini.stX_posWrt0_jobTable).text())) # um
            self.stepY_um_edt.setValue(float(self.jobs_window.table_jobs.item(frst_row, param_ini.stY_posWrt0_jobTable).text())) # um
            
            if (self.jobs_window.pos_motor_trans_edt.isEnabled() or self.jobs_window.angle_polar_bx.isEnabled() or self.jobs_window.newport_polar_bx.isEnabled()) : self.worker_apt.wait_flag = True # will be reset after
            
            self.use_shutter_combo.setCurrentIndex(int(self.jobs_window.table_jobs.item(frst_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.shutteruse_posWrtEnd_jobTable).text()))
            
            ishgfastuse = (self.jobs_window.table_jobs.item(frst_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.ishgfastuse_posWrtEnd_jobTable).text()).split(param_ini.list_ishgfast_separator)
            row1 = self.row_jobs_current if self.row_jobs_current is not None else 0
            if (not self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.table_jobs.item(row1 , self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] != 'DC' and (len(ishgfastuse) > 1 and ishgfastuse[0].isdigit() and int(ishgfastuse[0]))): # # use ishg fast
            # # [False, rmp_time_sec_dflt, 31, 260, 1360, 1, (0, beg_dt_sec_dflt, end_dt_sec_dflt, line_dt_us_dflt), (flag_impose_ramptime_as_exptime, 0)]  +  [ self.jobs_window.scndProcfill_EOMph_chck.isChecked(), self.jobs_window.mode_EOM_ramps_spec_AC_cb.currentIndex()]
                self.jobs_window.mode_EOM_ramps_AC_chk.setChecked(True)
                self.jobs_window.voltmax_EOMph_spbx.setValue(float(ishgfastuse[4]))
                self.jobs_window.voltpi_EOMph_spbx.setValue(float(ishgfastuse[3]))
                self.jobs_window.steptheo_EOMph_spbx.setValue(float(ishgfastuse[2]))
                rmp = float(ishgfastuse[1])*1e6 # # in us
                self.jobs_window.ramptime_us_EOMph_spbx.setValue(rmp)
                dttm_l = ishgfastuse[6][1:-1].split(', ')
                tup = ishgfastuse[7][1:-1].split(', ')
                self.jobs_window.deadtimeBeg_us_EOMph_spbx.setValue(float(dttm_l[1])*1e6)
                self.jobs_window.deadtimeEnd_us_EOMph_spbx.setValue(float(dttm_l[2])*1e6)
                self.jobs_window.deadtimeLine_us_EOMph_spbx.setValue(float(dttm_l[3])*1e6)
                self.jobs_window.impose_rmptime_exptime_EOMph_chck.setChecked(tup[0] == 'True')
                self.jobs_window.scndProcfill_EOMph_chck.setChecked(ishgfastuse[8] == 'True')
                self.jobs_window.mode_EOM_ramps_spec_AC_cb.setCurrentIndex(float(ishgfastuse[9]))
                if self.jobs_window.close_EOMph_button.isEnabled(): # worker eom here
                    if self.jobs_window.stmode_EOMph_cbBx.currentIndex() != 0: # # one mode is current
                        self.jobs_window.stop_EOMph_button.animateClick()
                    if rmp == 2000: # us
                        self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(1)
                    elif rmp in (200, 220): # us
                        self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(2)
                    elif rmp in (20, 22): # us
                        self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(3)
            # !

            if self.jobs_window.pos_motor_trans_edt.isEnabled(): # set pos trans
                self.jobs_window.pos_motor_trans_edt.setText((self.jobs_window.table_jobs.item(frst_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.transmtrs_posWrtEnd_jobTable ).text())) # # um
            list_mtrpola = (self.jobs_window.table_jobs.item(frst_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.polarmtrs_posWrtEnd_jobTable ).text()).split(param_ini.list_polar_separator) # # deg
            # # TODO: to  test
            if (len(list_mtrpola) > 1 or len(list_mtrpola[0]) > 0):
                if (list_mtrpola[0].replace('.','',1).isdigit()): # HWP
                    pola_hwp = float(list_mtrpola[0])
                    self.jobs_window.mtr_tl_chck.setChecked(True)
                    if self.jobs_window.angle_polar_bx.value() != pola_hwp: self.jobs_window.angle_polar_bx.setValue(pola_hwp)
                else: self.jobs_window.mtr_tl_chck.setChecked(False)
                if (list_mtrpola[1].replace('.','',1).isdigit()): # QWP
                    pola_qwp = float(list_mtrpola[1])
                    self.jobs_window.mtr_newport_chck.setChecked(True)
                    if self.jobs_window.newport_polar_bx.value() != pola_qwp: self.jobs_window.newport_polar_bx.setValue(pola_qwp)
                else: self.jobs_window.mtr_newport_chck.setChecked(False)
            
            l_pm = list(self.jobs_window.table_jobs.item(frst_row, param_ini.pmts_posWrt0_jobTable).text())
            pm_list = [self.pmt1_chck, self.pmt2_chck, self.pmt3_chck, self.pmt4_chck]
            for ii in range(len(l_pm)):
                if bool(int(l_pm[ii])):
                    pm_list[ii].setChecked(True)
                else: # 0
                    pm_list[ii].setChecked(False)
            
            if ((self.imic_was_init_var == 1 and not self.use_piezo_for_Z_stack) or (self.use_piezo_for_Z_stack and ((self.PI_here and self.use_PI_notimic) or (not self.use_PI_notimic and self.imic_was_init_var == 1)))):
                
                if not (type_job_str == param_ini.zstck_name_job or type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.polar_zstck_name_job or type_job_str == param_ini.z_ps_name_job or type_job_str == param_ini.z_polar_name_job): # not Z involved (but here), will be defined later anyway
                    zstr = self.jobs_window.table_jobs.item(frst_row, param_ini.mtrZ_posWrt0_jobTable).text()
                    if not zstr.replace('.','',1).isdigit(): zstr = '0'
                    self.Z_to_set_tmp.append(float(zstr)) # mm
                    pzstr = self.jobs_window.table_jobs.item(frst_row, param_ini.pzZ_posWrt0_jobTable).text()
                    if not pzstr.replace('.','',1).isdigit(): pzstr = '0'
                    self.Z_to_set_tmp.append(float(pzstr)/1000) # mm
                    self.send_move_to_worker_imic_obj_Z()
                
                self.Z_to_set_tmp = []
                listiMic_params = self.jobs_window.table_jobs.item(frst_row, param_ini.imicOther_posWrt0_jobTable).text().split(param_ini.list_stgscn_separator) # [obj # ; filter btm ; filter top]
                
                self.objective_choice.setCurrentIndex(int(listiMic_params[0])) 
                self.filter_bottom_choice.setCurrentIndex(int(listiMic_params[1])) 
                self.filter_top_choice.setCurrentIndex(int(listiMic_params[2])) 
                
            self.nbstXmos = int(float(self.jobs_window.table_jobs.item(frst_row, param_ini.nbstXmos_posWrt0_jobTable).text()))
            self.nbstYmos = int(float(self.jobs_window.table_jobs.item(frst_row, param_ini.nbstYmos_posWrt0_jobTable).text()))
            self.bstXmos = int(float(self.jobs_window.table_jobs.item(frst_row, param_ini.bstXmos_posWrt0_jobTable).text()))
            self.bstYmos = int(float(self.jobs_window.table_jobs.item(frst_row, param_ini.bstYmos_posWrt0_jobTable).text()))
                                
            if self.stage_scan_mode == 1: # scan stage
                listStgScan_params = self.jobs_window.table_jobs.item(frst_row, param_ini.listStgScan_posWrt0_jobTable).text().split(param_ini.list_stgscn_separator)  
                self.xscan_radio.setChecked(bool(listStgScan_params[0]))
                self.bidirec_check.setCurrentIndex(int(listStgScan_params[1]))
                self.modeEasy_stgscn_cmbbx.setCurrentIndex(int(listStgScan_params[2]))
                self.profile_mode_cmbbx.setCurrentIndex(int(listStgScan_params[3]))
                self.acc_max_motor_X_spinbox.setValue(float(listStgScan_params[4]))
                self.acc_max_motor_Y_spinbox.setValue(float(listStgScan_params[5]))
                self.speed_max_motor_X_spinbox.setValue(float(listStgScan_params[6]))
                self.speed_max_motor_Y_spinbox.setValue(float(listStgScan_params[7]))
                self.jerk_fast_spnbx.setValue(float(listStgScan_params[8]))
                self.acc_offset_spbox.setValue(float(listStgScan_params[9]))
                self.dec_offset_spbox.setValue(float(listStgScan_params[10]))
                self.pixell_offset_dir_spbox.setValue(float(listStgScan_params[11])) # acc offset (mm)
                self.pixell_offset_rev_spbox.setValue(float(listStgScan_params[12])) # acc offset (mm)
        
            # # for ii in range(self.jobs_window.table_jobs.columnCount()): 
            # #     self.job_parameter_list_current.append(self.jobs_window.table_jobs.item(0, ii).text())
            
            # # print(self.job_parameter_list_current)
            self.count_avg_job = 1 # reset to init
            self.row_jobs_current = frst_row
            self.num_experiment+= 1
            self.start_job_after_meth()
            
        else: # don't start a job
            print('\n No job to start \n')
            jobs_scripts.no_job_running_meth(self)
            
    @pyqtSlot(int)         
    def after_apt_posini_2other_apt_meth(self, v):
        # # transition method to init 2nd apt motor after 1st one is ok in a job
        # # for polar + ps
        # v is useless but here because some arg signal can be linked
    
        type_job_str = self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()
        
        if self.list_polar.ndim == 1: # one WP
            signal_considered = self.worker_apt.motor_polar_finished_move_signal
        else: # 2 WPs
            signal_considered = self.both_polars_finished_move_signal
            # # self.twomotors_wp_util() # # already made
    
        if type_job_str == param_ini.polar_ps_name_job: # # polar + ph-shft
            
            signal_considered.disconnect(self.after_apt_posini_2other_apt_meth) # # 
            self.mtr_phshft_finishedmove_sgnl.connect(self.start_job_after_meth_suite) # connect to the following of the method
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 1) # 1 for ps
            
        elif type_job_str == param_ini.ps_polar_name_job: # # ph-shft + polar 
            
            self.mtr_phshft_finishedmove_sgnl.disconnect(self.after_apt_posini_2other_apt_meth) # # 
            signal_considered.connect(self.start_job_after_meth_suite) # connect to the following of the method
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 2) # 2 for polar
      
    # is not a pyqtSlot   
    def start_job_after_meth(self):
        
        type_jb = self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()
    
        self.nb_img_max_box.setValue(1) #int(self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1-1).text()))
        self.nb_img_max = 1
        self.count_job_Z_stack = 0  # reinit
        self.count_job_ps = 0
        self.count_job_polar = 0
        self.count_job_mosXY = 1
        self.count_job_singlenomtr = 0
        
        # # in case of polar
        if len(self.list_polar) > 0:
            if self.list_polar.ndim == 1: # one WP
                signal_considered = self.worker_apt.motor_polar_finished_move_signal
                self.pos_polar0 = self.list_polar[0]
                nb = 1

            else: # 2 WPs
                signal_considered = self.both_polars_finished_move_signal
                self.twomotors_wp_util() # # connect TL + newport to both_signal
                self.pos_polar0 = self.list_polar[0][0]
                self.pos_polar0b = self.list_polar[0][1]
                nb = 2
            print('in st_job: %d WP will be involved' % nb)
        
        self.name_instr_ps = self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0]
        
        if (type_jb == param_ini.z_ps_name_job or type_jb == param_ini.polar_ps_name_job or type_jb == param_ini.ps_zstck_name_job or type_jb == param_ini.ps_polar_name_job or type_jb == param_ini.ps_name_job): # # ps involved
            
            if self.name_instr_ps == param_ini.name_dcvolt: # # DC volt
                self.mtr_phshft_finishedmove_sgnl = self.worker_EOMph.mdltr_voltSet_signal
                self.change_phshft_sgnl = self.worker_EOMph.EOMph_setHV_signal if not(self.jobs_window.ps_fast_radio.isChecked() and self.jobs_window.table_jobs.item(self.row_jobs_current, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable).text().split(param_ini.list_ps_separator)[0][:2] == 'DC') else None
            elif self.name_instr_ps == param_ini.name_rot: # # rot gp mtr self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # motor trans or rot.
                self.mtr_phshft_finishedmove_sgnl = self.worker_apt.motor_phshft_finished_move_signal
                self.change_phshft_sgnl = self.move_motor_phshft_signal
            elif self.name_instr_ps == param_ini.name_trans: # # trans mtr self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # motor trans or rot.
                self.mtr_phshft_finishedmove_sgnl = self.worker_apt.motor_trans_finished_move_signal
                self.change_phshft_sgnl = self.move_motor_trans_signal
        
        if (type_jb == param_ini.ps_name_job or type_jb == param_ini.z_ps_name_job or type_jb == param_ini.ps_zstck_name_job):#self.jobs_window.job_choice_combobx.currentIndex() == 2: #(((self.jobs_window.ps_job_prim_radio.isChecked() or self.jobs_window.ps_job_sec_radio.isChecked()))):
            '''
            if (self.stage_scan_mode == 1 and self.set_new_scan == 0):  # stage scan, but not considered as'new'
                self.queue_com_to_acq.put([-1]) # kill current acq processes of data_acquisition, and the qthread
                print('GUI sent to acq process a poison-pill')
                # except: # if no scan was previously done
                #     pass # do nothing
                        
                self.set_new_scan = 2 # whole new scan, acts as the very first scan
            '''   
            
            self.mtr_phshft_finishedmove_sgnl.connect(self.start_job_after_meth_suite) # connect to the following of the method 
            
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 1) # 1 for ps

        elif (type_jb == param_ini.polar_name_job or type_jb == param_ini.z_polar_name_job or type_jb == param_ini.polar_zstck_name_job): # polar involved
        
            signal_considered.connect(self.start_job_after_meth_suite) # connect to the following of the method
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 2) # 2 for polar
            if self.list_polar.ndim == 2: # 2 WPs
                jobs_scripts.frst_ini_apt_job_def_list_meth(self, 3)
            
        elif type_jb == param_ini.polar_ps_name_job: # # polar + ph-shft
            
            signal_considered.connect(self.after_apt_posini_2other_apt_meth) # # connect to the following of the method
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 2) # 2 for polar
            if self.list_polar.ndim == 2: # 2 WPs
                jobs_scripts.frst_ini_apt_job_def_list_meth(self, 3)
            
        elif type_jb == param_ini.ps_polar_name_job: # # ph-shft + polar 
            
            self.mtr_phshft_finishedmove_sgnl.connect(self.after_apt_posini_2other_apt_meth) # # connect to the following of the method
            jobs_scripts.frst_ini_apt_job_def_list_meth(self, 1) # 1 for ps
            
        # # elif type_jb == param_ini.XYmosaic_name_job: # # mosaic XY
        
            
        else: # # no mtr for instance, or no polar or no ps
            self.start_job_after_meth_suite(0) # v is useless, but to match the signal we need it
    
                
    @pyqtSlot(int)     
    def start_job_after_meth_suite(self, v): 
    # v is useless, but to match the signal we need it
                
        type_job_str = self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text()
        self.job_name_previous = name0 = self.acq_name_edt.text()
        if (hasattr(self, 'name_instr_ps') and self.jobs_window.pos_motor_phshft_edt.isEnabled()):
            self.pos_phshft0 = float(self.jobs_window.pos_motor_phshft_edt.text())/1000 # has to be in mm not um
        self.name0 = name0
        if name0 == param_ini.name_dflt00:
            name0 = ''
        
        if (type_job_str in (param_ini.polar_name_job, param_ini.z_polar_name_job, param_ini.ps_polar_name_job, param_ini.polar_ps_name_job, param_ini.polar_zstck_name_job, param_ini.z_ps_name_job)): # # it's normal if polar and ps are inverted in the combined case because the secondary calls this function
            if ((type(self.list_polar) == numpy.ndarray and self.list_polar.ndim == 1)): # one WP
                signal_considered = self.worker_apt.motor_polar_finished_move_signal
                if self.jobs_window.mode_wp_polar_cmb.currentIndex() == 0: # dflt
                    name_fol_pol = 'HWP%s..%s..%sdeg' % (str(self.jobs_window.strt_polar_angle_spnbx.value()), str(self.jobs_window.step_polar_angle_spnbx.value()), str(self.jobs_window.stop_polar_angle_spnbx.value()))
                else: # custom
                    name_fol_pol = 'HWP%.1f..%.1fdeg' % (self.list_polar[0],self.list_polar[-1])
            elif (type(self.list_polar) == numpy.ndarray and self.list_polar.ndim == 2): # 2 WPs
                signal_considered = self.both_polars_finished_move_signal
                # # self.twomotors_wp_util() # # already made
                name_fol_pol = 'HWPQWP%.1f..%.1f_%.1f..%.1fdeg' % (self.list_polar[0][0],self.list_polar[0][-1], self.list_polar[1][0], self.list_polar[1][-1])
            
                
        if (type_job_str in (param_ini.ps_name_job, param_ini.z_ps_name_job, param_ini.ps_zstck_name_job)): # ps and other non-apt job
            signal_considered = self.mtr_phshft_finishedmove_sgnl
            
        if 'signal_considered' in locals():
            try:
                signal_considered.disconnect(self.start_job_after_meth_suite) # disconnect itself, because temporary
            except TypeError:
                pass
        
        if (type_job_str == param_ini.ps_name_job or type_job_str == param_ini.z_ps_name_job or type_job_str == param_ini.polar_ps_name_job or type_job_str == param_ini.polar_name_job or type_job_str == param_ini.z_polar_name_job or type_job_str == param_ini.ps_polar_name_job): #(self.jobs_window.job_choice_combobx.currentIndex() == 2 or self.jobs_window.job_choice_combobx.currentIndex() == 13): #(((self.jobs_window.ps_job_prim_radio.isChecked() or self.jobs_window.ps_job_sec_radio.isChecked()) and not self.jobs_window.z_job_sec_radio.isChecked()) or (self.jobs_window.ps_job_sec_radio.isChecked() and self.jobs_window.z_job_prim_radio.isChecked())): # phase-shifts or polar defined as primary or secondary job, and no z-stack secondary job OR phase-shifts defined as secondary job, and z-stack as primary job
            
            # if (type_job_str == param_ini.ps_name_job or type_job_str == param_ini.z_ps_name_job or type_job_str == param_ini.polar_ps_name_job): # # it's normal if polar and ps are inverted in the combined case because the secondary calls this function

            self.job_apt_meth()  
        
            if type_job_str == param_ini.z_ps_name_job: # z-stack as primary job, ps as secondary
           
                rep = ('Z=%s..%s..%smm_every_%.1f deg' % (str(self.jobs_window.strt_Z_stack_spnbx.value()), str(self.jobs_window.stp_Z_stack_spnbx.value()), str(self.jobs_window.end_Z_stack_spnbx.value()), self.jobs_window.step_phase_shift_spbx.value()))
                
            elif type_job_str == param_ini.polar_ps_name_job: # polar as primary job, ps as secondary
            
                rep = ('%s_every_%.1f deg' % (name_fol_pol, self.jobs_window.step_phase_shift_spbx.value()))
                
            elif type_job_str == param_ini.z_polar_name_job: # z-stack as primary job, polar as secondary
            
                rep = ('Z=%s..%s..%smm_every_%d deg' % ( str(self.jobs_window.strt_Z_stack_spnbx.value()), str(self.jobs_window.stp_Z_stack_spnbx.value()), str(self.jobs_window.end_Z_stack_spnbx.value()), self.jobs_window.step_polar_angle_spnbx.value()))
                
            elif type_job_str == param_ini.ps_polar_name_job: # ps as primary job, polar as secondary
            
                rep = ('%dphshfts_every_%.1f deg' % ( self.jobs_window.nb_frame_phase_shift_spbx.value(), self.jobs_window.step_polar_angle_spnbx.value()))
             
            elif type_job_str == param_ini.polar_name_job: # polar as primary job
            
                rep = ('%s' % (name_fol_pol))
            
            elif type_job_str == param_ini.ps_name_job:  # ps as primary job
                rep = ('%dphshfts' % ( self.jobs_window.nb_frame_phase_shift_spbx.value()))
        
        elif (type_job_str == param_ini.zstck_name_job or type_job_str == param_ini.ps_zstck_name_job or type_job_str == param_ini.polar_zstck_name_job):#(self.jobs_window.job_choice_combobx.currentIndex() == 1 or self.jobs_window.job_choice_combobx.currentIndex() == 4):#(((self.jobs_window.z_job_prim_radio.isChecked() or self.jobs_window.z_job_sec_radio.isChecked()) and not self.jobs_window.ps_job_sec_radio.isChecked()) or (self.jobs_window.z_job_sec_radio.isChecked() and self.jobs_window.ps_job_prim_radio.isChecked())): # z-stack defined as primary or secondary job, and no phase-shifts secondary job OR z-stack defined as secondary job, and phase-shifts as primary job
            self.init_job_z_stack() 

            if type_job_str == param_ini.ps_zstck_name_job: #self.jobs_window.job_choice_combobx.currentIndex() == 4: # p-s as primary job
           
                rep = ('ps_step_%d deg_every%.1f_mm_Z' % (self.jobs_window.step_phase_shift_spbx.value(), self.jobs_window.stp_Z_stack_spnbx.value() ))
                
            elif type_job_str == param_ini.polar_zstck_name_job:
                
                rep = ('%s_every_%.1f_mm_Z' % (name_fol_pol, self.jobs_window.stp_Z_stack_spnbx.value()))
                
            else: # only z-stack
                rep = ('Z=%s..%s..%smm' % (str(self.jobs_window.strt_Z_stack_spnbx.value()), str(self.jobs_window.stp_Z_stack_spnbx.value()), str(self.jobs_window.end_Z_stack_spnbx.value())))
                
        elif (type_job_str == param_ini.XYmosaic_name_job): # # Mosaic
                        
            rep = ('mos_%dX%d_steps_%.1fX%.1fum' % (self.nbstXmos, self.nbstYmos, self.bstXmos, self.bstYmos))
            jobs_scripts.mosaic_job_ini(self, param_ini, numpy) # ini
        elif type_job_str == param_ini.nomtr_name_job: # no mtr
            rep = 'nomtr'
        # # ct = 1
        # # while True: 
        # rep = job_name[len(name0):]
        job_name =  name0 + rep
        if self.jobs_window.table_jobs.item(self.row_jobs_current, 3).text() != param_ini.calib_ps_name_job:  
            if self.acq_name_edt.text() == job_name:
                if job_name[len(job_name)-5:len(job_name)-4] == '_': # already numbered
                    num = int(job_name[len(job_name)-4:len(job_name)]) + 1
                    num_str = str(num).zfill(4)
                    job_name = job_name[:len(job_name)-5]
                else:
                    num_str = '0001'
                job_name = ('%s_%s' % (job_name, num_str))
            
            job_name[:-job_name.count(rep)*len(rep)]
            self.job_name = job_name
            self.acq_name_edt.setText(self.job_name)
        
        # self.jobs_window.strt_job_button.setEnabled(False)
        
        if type_job_str == param_ini.nomtr_name_job: # no mtr
            self.connect_new_img_to_single = 1
            self.count_job_singlenomtr += 1 # set to 0 in prev func
            jobs_scripts.launch_job_general(self) # just launch a single scan, no apt in there
            
    @pyqtSlot(int)
    def mosaic_after_move(self, v):
        
        if v == 0: # # stage XY
            self.stageXY_ready_mos = True
        else: # Z pos
            self.Z_ready_mos = True
        
        if (self.Zplane_mosaic_um_r is None or (self.Z_ready_mos and self.stageXY_ready_mos)): # # no Z correc°
            # # print('in mosaic sent move !!!!')
            self.send_new_img_to_acq(101) # # 101 for direct call
    
    @pyqtSlot(int)
    def groupBox_mosaic_visible_meth(self, bb):       
        if bb: # checked
            self.jobs_window.groupBox_mosaic.setVisible(True)
        else: # unchecked
            self.jobs_window.groupBox_mosaic.setVisible(False)
    
        ## jobs buttons, 2nd window
    
    @pyqtSlot(float)
    def mtrps_def_vel_accn_meth(self, val): 
    
        # # if self.jobs_window.ps_fast_radio.isChecked(): # # fast
        # #     jobs_scripts.calib_disttot_mtr_set_val_util(self)
        
        res = self.jobs_window.restheo_fastcalib_spbx.value()
        num = 0
        widg = self.sender()
        if widg == self.jobs_window.mtrps_velset_spbx: # # vel
            self.vel_mtr_job = vel = val
            accn = self.jobs_window.mtrps_accnset_spbx.value() # # mm/sec2
        elif widg == self.jobs_window.mtrps_accnset_spbx: # # accn
            vel = self.jobs_window.mtrps_velset_spbx.value()
            accn = val # # mm/sec2
        else:
            vel = self.jobs_window.mtrps_velset_spbx.value()
            num = -1
            if widg == self.jobs_window.restheo_fastcalib_spbx:
                res = val
        if num != -1:
            if self.motorTransIsHere:
                num = 2
            elif self.motorPhshftIsHere00:
                num = 1 
            else:
                num = -1
        
        exptime_msec = jobs_scripts.res_theo(res, 1e-6*self.lambda_shg_um, self.vg1, self.vg2, self.alpha_calc_deg, self.nb_pass_calcites, math)/vel*1000
        self.jobs_window.exptime_fastcalib_vallbl.setText('%.3f' % exptime_msec)
        if (self.jobs_window.autoco_frog_pushButton.text() == 'FROG' and exptime_msec < self.min_exptime_msec):
            self.jobs_window.exptime_fastcalib_vallbl.setStyleSheet('color: red')
        else:
            self.jobs_window.exptime_fastcalib_vallbl.setStyleSheet('color: black')
            
        if num == -1:           
            # # print('error, I returned (mtrps_def_vel_accn_meth)')
            return
        else:
            self.worker_apt.vel_acc_bounds_signal.emit(num, accn, vel)
    
    def currZ_util(self):
        # not a Slot
        
        return self.posZ_motor_edt_1.value() + self.posZ_motor_edt_2.value()/10 + self.posZ_motor_edt_3.value()/100 + self.posZ_motor_edt_4.value()/1000, self.posZ_piezo_edt_1.value()/1000 + self.posZ_piezo_edt_2.value()/1000/10 + self.posZ_piezo_edt_3.value()/1000/100 + self.posZ_piezo_edt_4.value()/1000/1000 + self.posZ_piezo_edt_5.value()/1000/10000 # piezo was in um, now in mm
                
    @pyqtSlot()
    def get_Z_start_from_indic_meth(self):
        
        currentZ = self.currZ_util(); currentZ = currentZ[0]+currentZ[1] # # mtr + piezo
        self.jobs_window.strt_Z_stack_spnbx.setValue(currentZ)
        self.start_Z_current = currentZ
        
    
    @pyqtSlot()
    def get_diffZ_from_indic_meth(self):
        
        currentZ = self.currZ_util(); currentZ = currentZ[0]+currentZ[1] # # mtr + piezo
        
        stp_to_set = currentZ-self.start_Z_current
        if stp_to_set == 0:
            stp_to_set = 0.000010
            
        self.jobs_window.stp_Z_stack_spnbx.setValue(stp_to_set)
        
    @pyqtSlot()    
    def get_Z_end_from_indic_meth(self):
        
        currentZ = self.currZ_util(); currentZ = currentZ[0]+currentZ[1] # # mtr + piezo
        self.jobs_window.end_Z_stack_spnbx.setValue(currentZ)
        
    @pyqtSlot()
    def get_polar_start_from_indic_meth(self):
        
        currentpolar = 2*self.jobs_window.angle_polar_bx.value() # factor of 2 between HWP and polar angles
        self.jobs_window.strt_polar_angle_spnbx.setValue(currentpolar)
        self.start_polar_current = currentpolar
    
    @pyqtSlot()
    def get_diffpolar_from_indic_meth(self):
        
        currentpolar = 2*self.jobs_window.angle_polar_bx.value() # factor of 2 between HWP and polar angles
        stp_to_set = currentpolar - self.start_polar_current
        if stp_to_set == 0:
            stp_to_set = 0.000010
            
        self.jobs_window.step_polar_angle_spnbx.setValue(stp_to_set)
        
    @pyqtSlot()    
    def get_polar_end_from_indic_meth(self):
        
        currentpolar = 2*self.jobs_window.angle_polar_bx.value() # factor of 2 between HWP and polar angles
        self.jobs_window.stop_polar_angle_spnbx.setValue(currentpolar)
     
    @pyqtSlot()
    def after_nbFrame_Zstck_chg_meth(self): 
    # # called by nb_frame_Z_stck button
    
        self.jobs_window.stp_Z_stack_spnbx.blockSignals(True)
        if self.jobs_window.nb_frame_Z_job_spbx.value() > 1:
            stp = (self.jobs_window.end_Z_stack_spnbx.value() - self.jobs_window.strt_Z_stack_spnbx.value())/(self.jobs_window.nb_frame_Z_job_spbx.value() - 1)
        else:
            stp = 0
            
        self.jobs_window.stp_Z_stack_spnbx.setValue(stp)
        
        self.jobs_window.stp_Z_stack_spnbx.blockSignals(False)
        self.change_nb_frame_Z_stack()
        
    @pyqtSlot()
    def after_nbFrame_polar_chg_meth(self): 
    # # called by nb_frame_polar button
    
        self.jobs_window.step_polar_angle_spnbx.blockSignals(True)
        if self.jobs_window.nb_frame_polar_job_spbx.value() > 1:
            strt_polar = self.jobs_window.strt_polar_angle_spnbx.value()
            if strt_polar > 180: # deg
                strt_polar -= 360 
            stp = (self.jobs_window.stop_polar_angle_spnbx.value() - strt_polar)/(self.jobs_window.nb_frame_polar_job_spbx.value() - 1)
        else:
            stp = 0
            
        self.jobs_window.step_polar_angle_spnbx.setValue(stp)
        
        self.jobs_window.step_polar_angle_spnbx.blockSignals(False)
        self.change_nb_frame_polar_meth()
    
        
    @pyqtSlot()
    def change_nb_frame_Z_stack(self):
        # # called by a change in spnbx nb_ps, or directly by after_nbFrame_ps_chg_meth
        
        self.jobs_window.nb_frame_Z_job_spbx.blockSignals(True)
        
        strt_Z_stack = self.jobs_window.strt_Z_stack_spnbx.value()
        self.start_Z_current = strt_Z_stack
        step_Z_stack = self.jobs_window.stp_Z_stack_spnbx.value()
        end_Z_stack = self.jobs_window.end_Z_stack_spnbx.value()
        
        if (round(end_Z_stack, 7) >= round(strt_Z_stack + step_Z_stack, 7) and step_Z_stack > 0): # valid values entered
            # print('Z stack bounds valid')
            nb_frame_stack = self.jobs_window.nb_frame_Z_job_spbx.value()
            if nb_frame_stack == self.nb_frame_stack_current: # start, step or end Z have changed, not nb frame
                nb_frame_stack = 0
            #     change_step = 0
            # else: # nb frame has changed, not start, step or end Z
            #     change_step = 1
            
            self.list_pos_Z_stack_abs, nb_frame_stack, step_calc = jobs_scripts.list_steps_stack_func(numpy, strt_Z_stack, step_Z_stack, end_Z_stack, nb_frame_stack)
            
            # if change_step: # nb frame has changed, not start, step or end Z : need to reset step
            self.jobs_window.stp_Z_stack_spnbx.setValue(step_calc) 
                
        else: # invalid values
            
            nb_frame_stack = 1
            currentZ = self.posZ_motor_edt_1.value() + self.posZ_motor_edt_2.value()/10 + self.posZ_motor_edt_3.value()/100 + self.posZ_piezo_edt_1.value()/1000 + self.posZ_piezo_edt_2.value()/1000/10 + self.posZ_piezo_edt_3.value()/1000/100 # piezo is in um
            self.list_pos_Z_stack_abs = [currentZ]
        
        self.jobs_window.nb_frame_Z_job_spbx.setValue(nb_frame_stack)    
        self.nb_frame_stack_current = nb_frame_stack
        
        # print('self.list_pos_Z_stack_abs' , self.list_pos_Z_stack_abs)
        # print(len(self.list_pos_Z_stack_abs))
    
        self.jobs_window.nb_frame_Z_job_spbx.blockSignals(False)
    
    @pyqtSlot()
    def change_nb_frame_polar_meth(self):
        # # called by a change in spnbx nb_polar, or directly by after_nbFrame_polar_chg_meth
        
        self.jobs_window.nb_frame_polar_job_spbx.blockSignals(True)
        
        strt_polar = self.jobs_window.strt_polar_angle_spnbx.value()
        step_polar = self.jobs_window.step_polar_angle_spnbx.value()
        end_polar = self.jobs_window.stop_polar_angle_spnbx.value()
        
        if (step_polar == 0 or (end_polar == strt_polar and step_polar!=0)):
            # # self.jobs_window.load_polar_xls_button.setEnabled(False)
            return
        else:
            self.jobs_window.load_polar_xls_button.setEnabled(True)
    
        if (round(end_polar, 7) >= round(strt_polar + step_polar, 7) and step_polar > 0): # valid values entered
            # print('Z stack bounds valid')
            if strt_polar>360: # deg
                strt_polar -= 360
                end_polar -= 360 
            nb_frame = abs(round((end_polar - strt_polar)/step_polar))+1
            self.jobs_window.nb_frame_polar_job_spbx.setValue(nb_frame)
            self.list_polar= (self.jobs_window.strt_polar_angle_spnbx.value() )*numpy.ones((nb_frame,)) + numpy.arange(nb_frame*1.0)*step_polar
            # # the motor is smart, it will move the right distance even if it's over 360deg
            # # the pos are set w.r.t. to the offset 
            
            print(self.list_polar)
                
        else: # invalid values
            nb_frame = 1

        self.jobs_window.nb_frame_polar_job_spbx.blockSignals(False)
        
    @pyqtSlot()
    def load_ps_list_meth(self):
        
        loaded_list = jobs_scripts.load_ps_list_func(QtWidgets, numpy)*1000
        
        if loaded_list is not None: 
            self.list_pos_wrt_origin = loaded_list
            self.new_ps_list_flag = 1
            # # self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1-4, QtWidgets.QTableWidgetItem()) # ps job params
            
            self.jobs_window.nb_frame_phase_shift_spbx.blockSignals(True)
            self.jobs_window.nb_frame_phase_shift_spbx.setValue(len(self.list_pos_wrt_origin))
            self.jobs_window.nb_frame_phase_shift_spbx.blockSignals(False)
            self.jobs_window.ps_job_load_radio.setChecked(True)
    
    @pyqtSlot()
    def change_nb_frame_ps_meth(self):
        
        # # print('in change_nb_frame_ps_meth')
        step_phase_shift = self.jobs_window.step_phase_shift_spbx.value()
        nb_frame_phase_shift = self.jobs_window.nb_frame_phase_shift_spbx.value()
        eq_deg_um = self.jobs_window.eq_deg_um_spnbx.value()
        nb_fr_stp = self.jobs_window.nb_fr_stp_ps_spbx.value() # # nb of frame per ps step (3 classic)
        
        for k in range(2):    
            if nb_frame_phase_shift != self.nb_frame_phase_shift_current: # 
                if self.sender() != self.jobs_window.step_phase_shift_spbx:
                    step_phase_shift = round(360/nb_frame_phase_shift*nb_fr_stp/2)
            else: # no prob
                if k>1:
                    break
            self.nb_frame_phase_shift_current = nb_frame_phase_shift
                     
            self.list_pos_wrt_origin, nb_frame_phase_shift = jobs_scripts.list_steps_motor_phshft_func(numpy, eq_deg_um, step_phase_shift, nb_fr_stp, self.jobs_window.force_incr_ps_chckbx.isChecked())
            
        self.jobs_window.nb_frame_phase_shift_spbx.blockSignals(True)
        self.jobs_window.nb_frame_phase_shift_spbx.setValue(nb_frame_phase_shift)
        self.jobs_window.nb_frame_phase_shift_spbx.blockSignals(False)
        
        self.jobs_window.step_phase_shift_spbx.blockSignals(True)
        self.jobs_window.step_phase_shift_spbx.setValue(step_phase_shift)
        self.jobs_window.step_phase_shift_spbx.blockSignals(False)
        
        print('list_pos_wrt_origin', self.list_pos_wrt_origin)
        
    @pyqtSlot()
    def change_nb_frame_calibps_meth(self):
        
        # # print(self.jobs_window.end_calib_phshft_spnbx.value() , self.jobs_window.st_calib_phshft_spnbx.value(), self.jobs_window.step_calib_phshft_spnbx.value())
        
        if self.jobs_window.step_calib_phshft_spnbx.value() > 0:
            nb_frame = math.ceil((self.jobs_window.end_calib_phshft_spnbx.value() - self.jobs_window.st_calib_phshft_spnbx.value())/self.jobs_window.step_calib_phshft_spnbx.value()) + 1
        else: # = 0
            nb_frame = 1
            
        self.jobs_window.num_frame_calib_phshft_spbx.blockSignals(True)
        self.jobs_window.num_frame_calib_phshft_spbx.setValue(nb_frame)
        self.jobs_window.num_frame_calib_phshft_spbx.blockSignals(False)
        
    @pyqtSlot()
    def change_step_calibps_meth(self):
        
        widg =  self.sender()
        
        if widg in (self.jobs_window.num_frame_calib_phshft_spbx, self.jobs_window.eq_deg_unit_test_spnbx, self.jobs_window.restheo_fastcalib_spbx): #  # num frames calib
            # # if widg == self.jobs_window.num_frame_calib_phshft_spbx:  # nb frame or total mtr dist for FAST
            # # fast
            if (not self.jobs_window.ps_fast_radio.isChecked()): # slow
                val = self.jobs_window.restheo_fastcalib_spbx.value()
                if self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # DC volt
                    val = val/self.jobs_window.eq_deg_unit_test_spnbx.value()
            else: # fast autoco or frog
            # # !! num frame is dist tot if fast !!
                val = self.jobs_window.eq_deg_unit_test_spnbx.value()
            self.jobs_window.max_angle_calib_phshft_spbx.blockSignals(True)
            self.jobs_window.max_angle_calib_phshft_spbx.setValue(round(val*self.jobs_window.num_frame_calib_phshft_spbx.value())) # # !! num frame is dist tot if fast !!
            self.jobs_window.max_angle_calib_phshft_spbx.blockSignals(False)
            # # print(self.jobs_window.max_angle_calib_phshft_spbx.value() , self.jobs_window.max_angle_calib_phshft_spbx.maximum())
            if self.jobs_window.max_angle_calib_phshft_spbx.value() == self.jobs_window.max_angle_calib_phshft_spbx.maximum(): self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('color: red')
            else: self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('color: black')
        
            step = (self.jobs_window.end_calib_phshft_spnbx.value()-self.jobs_window.st_calib_phshft_spnbx.value())/(self.jobs_window.num_frame_calib_phshft_spbx.value()-1) if self.jobs_window.num_frame_calib_phshft_spbx.value() > 1 else self.jobs_window.end_calib_phshft_spnbx.value()
            
            self.jobs_window.step_calib_phshft_spnbx.blockSignals(True)
            self.jobs_window.step_calib_phshft_spnbx.setValue(step)
            self.jobs_window.step_calib_phshft_spnbx.blockSignals(False)
        
        if widg in (self.jobs_window.restheo_fastcalib_spbx, self.jobs_window.max_angle_calib_phshft_spbx): # # slow mode, steps
            jobs_scripts.calib_disttot_mtr_set_val_util(self)

        if not self.jobs_window.ps_slow_radio.isChecked(): # # FAST , self.jobs_window.exptime_fastcalib_vallbl
            self.jobs_window.time_job_ind_bx.setText('%.2f' % (self.jobs_window.max_angle_calib_phshft_spbx.value()/self.jobs_window.restheo_fastcalib_spbx.value()*float(self.jobs_window.exptime_fastcalib_vallbl.text())/1000/60))
                    
    @pyqtSlot()
    def after_toggled_choice_ps_instr(self):
        
        time.sleep(0.2)
        
        ps_mtr_rot_chck = self.jobs_window.ps_mtr_rot_radio.isChecked()
        if (not self.jobs_window.ps_mtr_trans_radio.isChecked() and not self.jobs_window.ps_mtr_dcvolt_radio.isChecked()):
            ps_mtr_rot_chck =  True # dflt, to avoid problems
        
        if (self.jobs_window.ps_mtr_trans_radio.isChecked() or self.jobs_window.ps_mtr_dcvolt_radio.isChecked()): # set calib by displacement of motor phshft (special)
        
            self.jobs_window.eq_deg_unit_test_spnbx.setEnabled(True)
            self.jobs_window.max_angle_calib_phshft_spbx.setEnabled(True)
            self.jobs_window.st_calib_phshft_spnbx.setEnabled(False)
            self.jobs_window.step_calib_phshft_spnbx.setEnabled(False)
            self.jobs_window.end_calib_phshft_spnbx.setEnabled(False)
            # # try:
            # #     self.jobs_window.step_phase_shift_spbx.valueChanged.disconnect(self.change_nb_frame_ps_meth)
            # #     self.jobs_window.nb_frame_phase_shift_spbx.valueChanged.disconnect(self.change_nb_frame_ps_meth)
            # # except TypeError: # if had no connection
            # #     pass
            # #     
        elif ps_mtr_rot_chck: # ALSO means use motor phshft. rot
            
            self.jobs_window.eq_deg_unit_test_spnbx.setEnabled(False)
            self.jobs_window.max_angle_calib_phshft_spbx.setEnabled(False)
            self.jobs_window.st_calib_phshft_spnbx.setEnabled(True)
            self.jobs_window.step_calib_phshft_spnbx.setEnabled(True)
            self.jobs_window.end_calib_phshft_spnbx.setEnabled(True)
         
        namemax = 'Max angle (°)'
        if (ps_mtr_rot_chck or self.jobs_window.ps_mtr_trans_radio.isChecked()): # ps mtr
            self.jobs_window.cal_unit_name_lbl.setText('Calibration (°/um)')
            self.jobs_window.cal_exp_name_lbl.setText('Cal. expected (°/um)')
            self.jobs_window.eq_deg_unit_test_spnbx.setMaximum(9999)
            if ps_mtr_rot_chck:
                max_phase = 1000 # deg
            elif self.jobs_window.ps_mtr_trans_radio.isChecked():
                max_phase = self.bound_mtr_trans*1000*self.jobs_window.eq_deg_unit_test_spnbx.value() # deg
            self.jobs_window.max_angle_calib_phshft_spbx.setMaximum(max_phase)
            if ps_mtr_rot_chck: # gp
                if hasattr(self, 'worker_apt'):
                    self.mtr_phshft_finishedmove_sgnl = self.worker_apt.motor_phshft_finished_move_signal
                self.change_phshft_sgnl = self.move_motor_phshft_signal
                self.motorPhshftIsHere = True if self.motorPhshftIsHere00 else False
                self.jobs_window.max_angle_calib_phshft_spbx.setValue(720)
            else: # trans
                if hasattr(self, 'worker_apt'):
                    self.mtr_phshft_finishedmove_sgnl = self.worker_apt.motor_trans_finished_move_signal
                self.change_phshft_sgnl = self.move_motor_trans_signal
                self.motorPhshftIsHere = True if self.motorTransIsHere else False
                rg = self.rg_autoco_dflt_um if self.jobs_window.ps_fast_radio.isChecked() else 50  # um
                self.jobs_window.max_angle_calib_phshft_spbx.setValue(round(self.jobs_window.eq_deg_unit_test_spnbx.value()*rg))
            
            self.jobs_window.eq_deg_unit_test_spnbx.setValue(2*180*(3e8/self.lambda_shg_um)*(1/self.vg1-1/self.vg2)*math.sin(self.alpha_calc_deg /180*3.14)*abs(self.nb_pass_calcites))
            
            if self.motorPhshftIsHere: self.jobs_window.cal_ps_button.setEnabled(True) 
            else: self.jobs_window.cal_ps_button.setEnabled(False)
            self.jobs_window.max_angle_calib_phshft_spbx.setSingleStep(10) 
            
            if (ps_mtr_rot_chck and self.jobs_window.ps_fast_radio.isChecked()): self.jobs_window.cal_ps_button.setEnabled(False)


        else: # # DC voltage
            if hasattr(self, 'worker_EOMph'):
                self.mtr_phshft_finishedmove_sgnl = self.worker_EOMph.mdltr_voltSet_signal
                self.change_phshft_sgnl = self.worker_EOMph.EOMph_setHV_signal if not(self.jobs_window.ps_fast_radio.isChecked()) else None
                self.offset_pos_motor_ps = 0 # important !!
            self.jobs_window.cal_unit_name_lbl.setText('Calibration (°/V)')
            self.jobs_window.cal_exp_name_lbl.setText('Cal. expected (°/V)')
            self.jobs_window.eq_deg_unit_test_spnbx.setMaximum(2); self.jobs_window.eq_deg_unit_test_spnbx.setValue(0.7)
            self.jobs_window.eq_deg_unit_test_spnbx.setValue(180/param_ini.ishg_EOM_AC_dflt[3]) # # °/V
            self.motorPhshftIsHere = True if self.EOMph_is_connected else False
            self.jobs_window.max_angle_calib_phshft_spbx.setMaximum(param_ini.ishg_EOM_AC_dflt[4]) # 1400
            self.jobs_window.max_angle_calib_phshft_spbx.setSingleStep(1) 
            if self.EOMph_is_connected: self.jobs_window.cal_ps_button.setEnabled(True) 
            else: self.jobs_window.cal_ps_button.setEnabled(False)
            if self.jobs_window.ps_slow_radio.isChecked(): namemax = 'Max voltage (V)' # # not for fast
            
        self.jobs_window.max_val_calib_lbl.setText(namemax)
            
        self.jobs_window.eq_deg_um_spnbx.setMaximum(self.jobs_window.eq_deg_unit_test_spnbx.maximum())
        if self.jobs_window.max_angle_calib_phshft_spbx.value() == self.jobs_window.max_angle_calib_phshft_spbx.maximum(): self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('color: red')
        else: self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('color: black')
        
        if (self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and self.jobs_window.ps_fast_radio.isChecked()): # # DC volt fast
            self.jobs_window.nb_fr_or_dist_calib_lbl.setVisible(False)
            self.jobs_window.num_frame_calib_phshft_spbx.setVisible(False)
            self.calib_eom_fast_meth()
            # self.change_step_calibps_meth() #self.eq_deg_unit_test_spnbx action
            # # \\\ trick to make the change considered
            eq_1=self.jobs_window.eq_deg_unit_test_spnbx.value()
            self.jobs_window.eq_deg_unit_test_spnbx.valueChanged.emit(eq_1)
            # self.jobs_window.eq_deg_unit_test_spnbx.setValue(eq_1*1.1)
            # time.sleep(0.2)
            # self.change_step_calibps_meth()
            # self.jobs_window.eq_deg_unit_test_spnbx.setValue(eq_1)
        else: # # trans or rot    , or slow
            self.jobs_window.nb_fr_or_dist_calib_lbl.setVisible(True)
            self.jobs_window.num_frame_calib_phshft_spbx.setVisible(True)     
        
        self.vlmtrjob_def_util() # useful even if no motor !
        
    def calib_eom_fast_meth(self):
        
        self.jobs_window.max_angle_calib_phshft_spbx.setValue( self.jobs_window.voltmax_EOMph_spbx.value()/self.jobs_window.voltpi_EOMph_spbx.value()*180) # # °
        self.jobs_window.restheo_fastcalib_spbx.setValue(9) # # °
        
    def vlmtrjob_def_util(self): 
        if (self.motorTransIsHere and self.jobs_window.ps_mtr_trans_radio.isChecked()):
            self.vel_mtr_phsft = self.jobs_window.mtrps_velset_spbx.value()
        elif (self.motorPhshftIsHere00 and self.jobs_window.ps_mtr_rot_radio.isChecked()): # # mtr rot ps
            if self.motorTransIsHere:
                self.vel_mtr_phsft = param_ini.max_vel_TC_dflt
            else:
                self.vel_mtr_phsft = self.jobs_window.mtrps_velset_spbx.value()
        else:
            self.vel_mtr_phsft = 1
    
    # # @pyqtSlot()     
    # # def get_current_pos_mot_ps_as_offset_meth(self):
    # # 
    # #     self.jobs_window.offset_pos_motor_ps_edt.setText(str(self.jobs_window.pos_motor_phshft_edt.text()))
    # #     self.offset_pos_motor_ps = float(self.jobs_window.pos_motor_phshft_edt.text())
    
    @pyqtSlot()     
    def acq_name_changed_meth(self):
        
        self.job_name_previous = self.acq_name_edt.text() # change the default name of acq. to the new name entered
     
    @pyqtSlot()     
    def offset_pos_mot_ps_def_meth(self):
    
        self.offset_pos_motor_ps = float(self.jobs_window.offset_pos_motor_ps_edt.text())
    
    @pyqtSlot(int, float)     
    def angle_polar_setVal_meth(self, wp, angle_polar_toset):
        # # is toggled by a reading of the actual value in apt worker
        # # 1 TL spnbx, 2 NP spnbx
        # # 11 TL lbl live, 22 NP lbl live
        
        if wp in (1, 11): # # TL
            polar_bx = self.jobs_window.angle_polar_bx
            home_wp = self.jobs_window.home_tl_rot_button
            polar_live = self.jobs_window.angle_polar_live_lbl
        elif wp in (2, 22): # # newport
            polar_bx = self.jobs_window.newport_polar_bx
            home_wp = self.jobs_window.home_newport_rot_button
        else: return

        try: cond = polar_bx.isEnabled()
        except RuntimeError: return
        
        if not cond: 
            polar_bx.setEnabled(True)
            home_wp.setEnabled(True)
        
        if wp < 11: # # update spinbx
            polar_bx.blockSignals(True)
            polar_bx.setValue(angle_polar_toset)
            polar_bx.blockSignals(False)
        else: # # update label, disp only
            polar_live.setText('%.1f°' % angle_polar_toset)
    
    @pyqtSlot(int)     
    def single_polar_useloaded_ch_meth(self, bb):
        
        if bb: # checked()
            self.jobs_window.lbl_hwp_pos.setText('angle \npolar(°)') #  special, use load array so this is angle polar
            self.jobs_window.lbl_hwp_pos.setStyleSheet('color: magenta')
        else: # standard
            self.jobs_window.lbl_hwp_pos.setText('angle \nHWP(°)') #  standard, angle of motor
            self.jobs_window.lbl_hwp_pos.setStyleSheet('color: black')
        
    @pyqtSlot(float)     
    def after_angle_polar_changed_meth(self):
        # toggled by a change of value
        
        widget_caller = self.sender()
        # if isinstance(widget_caller, QtWidgets.QDoubleSpinBox):
        name = widget_caller.objectName()
        if name == 'angle_polar_bx': # # HWP
            sign_mov = self.move_motor_rot_polar_signal
            bx = self.jobs_window.angle_polar_bx
            if not self.jobs_window.mtr_tl_chck.isChecked(): self.jobs_window.mtr_tl_chck.setChecked(True) # # if this WP is used, it means it's on the laser path, no ?
            
        elif name == 'newport_polar_bx':
            sign_mov = self.move_motor_newport_signal
            bx = self.jobs_window.newport_polar_bx
            if not self.jobs_window.mtr_newport_chck.isChecked(): self.jobs_window.mtr_newport_chck.setChecked(True) # # if this WP is used, it means it's on the laser path, no ?
 
        if bx.value() < 0:
            bx.setValue(360 + bx.value()) # will return in the function
            return
        elif bx.value() >= 360:
            bx.setValue(bx.value() - 360) # will return in the function
            return
        
        #  #TODO: test this part !    
        if (name == 'angle_polar_bx' and self.jobs_window.single_polar_useloaded_chck.isChecked()): # # use values from xls file !!
        # # HWP only
            hwp_angle, qwp_angle = jobs_scripts.find_angle_polar_array(numpy, numpy.vstack((self.polar_numberswanted_list, self.polars_xls[:,0], self.polars_xls[:,1])), bx.value(), len(self.polars_xls[0]) == 2) # # here the value of the HWP is considered as the wanted_polar/2
            # self.polars_xls[0] # # correct angles of polar
            # # self.polars_xls is 1st col HWP and 2nd col QWP
            self.move_motor_rot_polar_signal.emit(hwp_angle)
            
            if (len(self.polars_xls) == 2 and self.esp_here): # # 2 WPs
                self.move_motor_newport_signal.emit(qwp_angle)
            
        else: # normal
            sign_mov.emit(bx.value())
        
    @pyqtSlot()     
    def after_job_choice_chg_meth(self):
        
        if self.jobs_window.job_choice_combobx.currentIndex() > 0: # a job was selected
        
            self.jobs_window.add_job_button.setEnabled(True)
            if (self.jobs_window.job_choice_combobx.currentIndex() == 1 or self.jobs_window.job_choice_combobx.currentIndex() == 4 or self.jobs_window.job_choice_combobx.currentIndex() == 5 or self.jobs_window.job_choice_combobx.currentIndex() == 12 or self.jobs_window.job_choice_combobx.currentIndex() == 13 or self.jobs_window.job_choice_combobx.currentIndex() == 14 or self.jobs_window.job_choice_combobx.currentIndex() == 15): # a job with Z
                if self.imic_was_init_var:
                    self.jobs_window.strt_job_button.setEnabled(True)
                else:
                    self.jobs_window.strt_job_button.setEnabled(False)
            if (self.jobs_window.job_choice_combobx.currentIndex() == 2 or self.jobs_window.job_choice_combobx.currentIndex() == 4 or self.jobs_window.job_choice_combobx.currentIndex() == 8 or self.jobs_window.job_choice_combobx.currentIndex() == 10 or self.jobs_window.job_choice_combobx.currentIndex() == 13 or self.jobs_window.job_choice_combobx.currentIndex() == 14 or self.jobs_window.job_choice_combobx.currentIndex() == 15): # a job with p-s
                if self.motorPhshftIsHere:
                    self.jobs_window.strt_job_button.setEnabled(True)
                else:
                    self.jobs_window.strt_job_button.setEnabled(False)
            if (self.jobs_window.job_choice_combobx.currentIndex() == 3 or self.jobs_window.job_choice_combobx.currentIndex() == 5 or self.jobs_window.job_choice_combobx.currentIndex() == 9 or self.jobs_window.job_choice_combobx.currentIndex() == 11 or self.jobs_window.job_choice_combobx.currentIndex() == 12 or self.jobs_window.job_choice_combobx.currentIndex() == 14 or self.jobs_window.job_choice_combobx.currentIndex() == 15): # a job with polar
                if self.motorRotIsHere:
                    self.jobs_window.strt_job_button.setEnabled(True)
                else:
                    self.jobs_window.strt_job_button.setEnabled(False)
            
            if (self.jobs_window.job_choice_combobx.currentIndex() in (param_ini.mosaic_job_num, self.jobs_window.job_choice_combobx.count() - 1 - param_ini.nomtr_job_num_wrtend)):
                self.jobs_window.strt_job_button.setEnabled(True)
            
        if self.jobs_window.job_choice_combobx.currentIndex() == 1: # only Z
            self.jobs_window.z_job_prim_radio.setChecked(True)
            self.jobs_window.ps_job_off_radio.setChecked(True)
            self.jobs_window.polar_off_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 2: # only ph-shft
            self.jobs_window.z_job_off_radio.setChecked(True)
            self.jobs_window.ps_job_prim_radio.setChecked(True)
            self.jobs_window.polar_off_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 3: # only polar
            self.jobs_window.z_job_off_radio.setChecked(True)
            self.jobs_window.ps_job_off_radio.setChecked(True)
            self.jobs_window.polar_prim_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 4: # prim ph-shft, sec Z
            self.jobs_window.z_job_sec_radio.setChecked(True)
            self.jobs_window.ps_job_prim_radio.setChecked(True)
            self.jobs_window.polar_off_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 5: # prim polar, sec Z
            self.jobs_window.z_job_sec_radio.setChecked(True)
            self.jobs_window.ps_job_off_radio.setChecked(True)
            self.jobs_window.polar_prim_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 12: # prim Z, sec. polar (unusual)
            self.jobs_window.z_job_prim_radio.setChecked(True)
            self.jobs_window.ps_job_off_radio.setChecked(True)
            self.jobs_window.polar_sec_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 13: # prim Z, sec. ph shft (unusual)
        
            self.jobs_window.z_job_prim_radio.setChecked(True)
            self.jobs_window.ps_job_sec_radio.setChecked(True)
            self.jobs_window.polar_off_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 14: # prim phi ps, sec polar
            self.jobs_window.z_job_off_radio.setChecked(True)
            self.jobs_window.ps_job_prim_radio.setChecked(True)
            self.jobs_window.polar_sec_job_radio.setChecked(True)
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 15: # prim polar, sec phi
            self.jobs_window.z_job_off_radio.setChecked(True)
            self.jobs_window.ps_job_sec_radio.setChecked(True)
            self.jobs_window.polar_prim_job_radio.setChecked(True)
            
            
        elif self.jobs_window.job_choice_combobx.currentIndex() == 0: # no job 
            self.jobs_window.strt_job_button.setEnabled(False)
            self.jobs_window.add_job_button.setEnabled(False)
     
     
    @pyqtSlot()     
    def add_job2list_meth(self):
        
        z_concerned = 0; ps_concerned = 0; polar_concerned = 0
        self.list_ps_str = 'N/A' # for now, it will be defined after
        list_z_str = 'N/A' # for now, it will be defined after
        list_polar_str = 'N/A' # for now, it will be defined after
        
        # # print('wala', ps_concerned , self.calib_job, self.motorPhshftIsHere)
        if ((self.calib_job) and self.motorPhshftIsHere):
            # # self.jobs_window.strt_job_button.setEnabled(True)
            pass # for now
                    
        if self.calib_job:
            
            ps_concerned = 1
            job_type_current_str = param_ini.calib_ps_name_job
            nb_images_tot = 1 if (self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and self.jobs_window.ps_fast_radio.isChecked()) else round((self.jobs_window.end_calib_phshft_spnbx.value() - self.jobs_window.st_calib_phshft_spnbx.value())/self.jobs_window.step_calib_phshft_spnbx.value())+1 # # AC calib EOM, else normal
            
        else: # not a p-s calib job
            job_type_current_str = self.jobs_window.job_choice_combobx.currentText()
            if self.jobs_window.job_choice_combobx.currentIndex() == 1: # only Z
                z_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 2: # only ph-shft
                ps_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 3: # only polar
                polar_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 4: # prim ph-shft, sec Z
                ps_concerned = 1
                z_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 5: # prim polar, sec Z
                polar_concerned = 1
                z_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 12: # prim Z, sec. polar (unusual)
                polar_concerned = 1
                z_concerned = 1
            elif self.jobs_window.job_choice_combobx.currentIndex() == 13: # prim Z, sec. ph shft (unusual)
                ps_concerned = 1
                z_concerned = 1
            elif (self.jobs_window.job_choice_combobx.currentIndex() == 14 or self.jobs_window.job_choice_combobx.currentIndex() == 15): #  ph shft +  polar 
                ps_concerned = 1
                polar_concerned = 1

            if ps_concerned:
                if self.motorPhshftIsHere: # can be mtr or DC
                    self.jobs_window.strt_job_button.setEnabled(True)
                
                if self.jobs_window.ps_job_load_radio.isChecked():
                    if self.new_ps_list_flag is None: # because the p-s list is loaded so it can be changed
                        QtWidgets.QMessageBox.warning(None, '', "Load a p-s list file first" )
                        return # outside_func = 1
                    else: # a list of ps has been loaded
                        if self.new_ps_list_flag < 1: # no new ps list
                            
                            if QtWidgets.QMessageBox.question(None, 'p-s old', "P-s list is the old one :%s. Add anyway ?" % self.list_ps_str[:30], QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes) == QtWidgets.QMessageBox.No:
                                return# outside_func = 1
                            # # else:
                            # outside_func = 0
                if len(self.list_pos_wrt_origin) == 0: #not hasattr(self, 'list_pos_wrt_origin'):
                    QtWidgets.QMessageBox.warning(None, '', "You do not have any active p-s list : impossible to add a p-s job")
                    return
                
                if self.jobs_window.inv_order_chck.isChecked():
                    self.list_pos_wrt_origin = self.list_pos_wrt_origin[::-1] # reverse order
                self.list_ps_str = param_ini.list_ps_separator.join(str(x) for x in self.list_pos_wrt_origin) # is defined by load of p-s txt file
            if z_concerned:
                if self.imic_was_init: # imic was init
                    self.jobs_window.strt_job_button.setEnabled(True)
                # first element will be flag if piezo is used or not
                if not hasattr(self, 'list_pos_Z_stack_abs'):
                    self.list_pos_Z_stack_abs = jobs_scripts.list_steps_stack_func(numpy, self.jobs_window.strt_Z_stack_spnbx.value(), self.jobs_window.stp_Z_stack_spnbx.value(), self.jobs_window.end_Z_stack_spnbx.value(), self.jobs_window.nb_frame_Z_job_spbx.value())[0] 
                    
                
                list_z_str = param_ini.list_Z_separator.join(str(x) for x in self.list_pos_Z_stack_abs) # is defined by change of parameters
            
            if polar_concerned:
                if self.jobs_window.mode_wp_polar_cmb.currentIndex() == 0: # default, not loaded angles
                    self.list_polar = jobs_scripts.list_steps_stack_func(numpy, self.jobs_window.strt_polar_angle_spnbx.value(), self.jobs_window.step_polar_angle_spnbx.value(), self.jobs_window.stop_polar_angle_spnbx.value(), self.jobs_window.nb_frame_polar_job_spbx.value())[0]
                    self.list_polar = numpy.round(self.list_polar/2, 2)  # # because the HWP varies as twice the HWP angle
                    if self.jobs_window.inv_order_chck.isChecked():
                        self.list_polar = self.list_polar[::-1] # reverse order
                    list_polar_str = param_ini.list_polar_separator.join(str(x) for x in self.list_polar) # is defined by change of parameters
                else: # custom angles
                    self.list_polar = self.polars_xls # # self.polars_xls is 1st col HWP and 2nd col QWP
                    list_polar_str = param_ini.list_polar_separator.join(str(x) for x in self.list_polar.flatten())
                    
        cond_mosaic = (self.jobs_window.job_choice_combobx.currentIndex() >= 6 and self.jobs_window.job_choice_combobx.currentIndex() <= 11)
            
        if not self.calib_job: nb_images_tot = self.jobs_window.nb_average_job_spbx.value()*(max(self.jobs_window.nb_frame_Z_job_spbx.value()*z_concerned, 1)*max(self.jobs_window.nb_frame_phase_shift_spbx.value()*ps_concerned, 1)*max(self.jobs_window.nb_frame_polar_job_spbx.value()*polar_concerned, 1))*((self.jobs_window.nb_step_X_mosaic_spbx.value()+1)*(self.jobs_window.nb_step_Y_mosaic_spbx.value()+1))**(cond_mosaic)
        
        if self.use_shutter_combo.currentIndex() == 1: time_pause_shutter = self.shutter_duration_ms_spnbx.value()/1000 # sec
        else: time_pause_shutter = 0
        
        tot_time_str = ('%.2f' % (((float(self.duration_indic.text()) + time_pause_shutter)*nb_images_tot + max(param_ini.time_change_Z*z_concerned + param_ini.time_change_ps*ps_concerned + param_ini.time_change_polar*polar_concerned, 1)*(nb_images_tot/self.jobs_window.nb_average_job_spbx.value()-1))/60)*self.jobs_window.nb_repeat_job_spbx.value()) if not(self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and self.jobs_window.ps_fast_radio.isChecked()) else '%f' % (self.jobs_window.ramptime_us_EOMph_spbx.value()/1e3) # in minutes, or in ms for calib AC EOM
        
        self.jobs_window.nb_frame_tot_job_spbx.setValue(nb_images_tot)
        self.jobs_window.time_job_ind_bx.setText(tot_time_str)
        
        if self.stage_scan_mode == 1: # stage scan
            list_stg_scan = []; list_stg_scan.append(int(self.xscan_radio.isChecked())) # x or y-scan
            list_stg_scan.append(self.bidirec_check.currentIndex()) # bidirek or not
            list_stg_scan.append(self.modeEasy_stgscn_cmbbx.currentIndex()) # easy mode scan stage
            list_stg_scan.append(self.profile_mode_cmbbx.currentIndex()) # profile scan
            list_stg_scan.append(self.acc_max_motor_X_spinbox.value()) # accX
            list_stg_scan.append(self.acc_max_motor_Y_spinbox.value()) # accY
            list_stg_scan.append(self.speed_max_motor_X_spinbox.value()) # velX
            list_stg_scan.append(self.speed_max_motor_Y_spinbox.value()) # velY
            list_stg_scan.append(self.jerk_fast_spnbx.value()) # jerk
            list_stg_scan.append(self.acc_offset_spbox.value()) # acc offset (mm)
            list_stg_scan.append(self.dec_offset_spbox.value()) # acc offset (mm)
            list_stg_scan.append(self.pixell_offset_dir_spbox.value()) # acc offset (mm)
            list_stg_scan.append(self.pixell_offset_rev_spbox.value()) # acc offset (mm)
            list_stg_scan_param_str = param_ini.list_stgscn_separator.join(str(x) for x in list_stg_scan)
        else: # galvos or static acq.
            list_stg_scan_param_str = 'N/A'
        
        rowPosition = self.jobs_window.table_jobs.rowCount()
        
        # # if rowPosition > 0:
        self.jobs_window.table_jobs.insertRow(rowPosition)
        
        self.jobs_window.table_jobs.setItem(rowPosition, 0, QtWidgets.QTableWidgetItem(str(1))) # default auto-start is 0
        self.jobs_window.table_jobs.setItem(rowPosition, 1, QtWidgets.QTableWidgetItem(str(rowPosition+1))) # number of job, starts at 0
        combobx_currentText = self.jobs_window.job_choice_combobx.currentText()
        self.jobs_window.table_jobs.setItem(rowPosition, 2, QtWidgets.QTableWidgetItem('%s-unt.' % combobx_currentText[0:max(7, len(combobx_currentText))])) # name of job
        self.jobs_window.table_jobs.setItem(rowPosition, 3, QtWidgets.QTableWidgetItem(job_type_current_str)) # type of job
        
        self.nbmax00 = self.nb_img_max_box.value()
        
        nb_im = self.nbmax00 if job_type_current_str == param_ini.nomtr_name_job else nb_images_tot # no mt or not
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.nbfr_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(nb_im))) # nb of frames
        
        pmts = '%d%d%d%d' % (int(self.pmt1_chck.isChecked()), int(self.pmt2_chck.isChecked()), int(self.pmt3_chck.isChecked()), int(self.pmt4_chck.isChecked()))
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.pmts_posWrt0_jobTable, QtWidgets.QTableWidgetItem(pmts)) # PMTs
        imic_str = param_ini.list_stgscn_separator.join(str(x) for x in [self.objective_choice.currentIndex(), self.filter_bottom_choice.currentIndex(), self.filter_top_choice.currentIndex()])
        
        mosaic_str = param_ini.list_stgscn_separator.join(str(x) for x in [self.jobs_window.dir_mosaic_cbbx.currentIndex(), 1-2*int(self.jobs_window.invX_mosaic_chck.isChecked()), 1-2*int(self.jobs_window.invY_mosaic_chck.isChecked()), self.jobs_window.mos_Zdiff_um_Xmax_spnbx.value(), self.jobs_window.mos_Zdiff_um_Ymax_spnbx.value()]) # # X then Y (0, inv 1) ; invX == 1 if not, -1 if yes ; same for Y; Z diff in um for Xmax, Ymax
        
        if (self.stageXY_is_here and self.chck_homed):
            posX_str = str(self.posX_edt.value())
            posY_str = str(self.posY_edt.value())
        else:
            posX_str = posY_str = 'N/A'
        
        if self.imic_was_init_var:
            posZ_motor_str = str(self.posZ_motor)
        else:
            posZ_motor_str = 'N/A'
            
        if ((self.use_PI_notimic and self.PI_here) or (not self.use_PI_notimic and self.imic_was_init_var)): posZ_pz_str = '%.4f' % (self.posZ_piezo*1000) # # is in mm, has to be in um# use PI
        else: posZ_pz_str = 'N/A'

        mode_str = str(self.mode_scan_box.currentIndex())
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.mode_posWrt0_jobTable, QtWidgets.QTableWidgetItem(mode_str)) 

        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.mtrZ_posWrt0_jobTable, QtWidgets.QTableWidgetItem(posZ_motor_str)) # self.posZ_motor is defined when motorZ changed
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.pzZ_posWrt0_jobTable, QtWidgets.QTableWidgetItem(posZ_pz_str))
        
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.szX_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.sizeX_um_spbx.value())))
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.szY_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.sizeY_um_spbx.value())))
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.stX_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.stepX_um_edt.value())))
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.stY_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.stepY_um_edt.value()))) # # step Y um, for the image
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.nbstXmos_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.nb_step_X_mosaic_spbx.value()))) # # nb step X mosaic
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.nbstYmos_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.nb_step_Y_mosaic_spbx.value()))) # # nb step Y mosaic
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.bstXmos_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.sz_um_Xstp_mosaic_spbx.value()))) # # big step X mosaic
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.bstYmos_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.sz_um_Ystp_mosaic_spbx.value()))) # # big step Y mosaic
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.mosaic_posWrt0_jobTable, QtWidgets.QTableWidgetItem(mosaic_str)) # # params mosaic
        
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.centerX_posWrt0_jobTable, QtWidgets.QTableWidgetItem(posX_str)) # X center, in mm
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.centerY_posWrt0_jobTable, QtWidgets.QTableWidgetItem(posY_str)) # Y center, in mm
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.dwllTime_posWrt0_jobTable, QtWidgets.QTableWidgetItem(str(self.dwll_time_edt.value()))) # exp. time, in us
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.listStgScan_posWrt0_jobTable, QtWidgets.QTableWidgetItem(list_stg_scan_param_str)) # stg scan parameters
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.totTime_posWrt0_jobTable, QtWidgets.QTableWidgetItem(tot_time_str)) # total time, in minutes
        self.jobs_window.table_jobs.setItem(rowPosition, param_ini.imicOther_posWrt0_jobTable, QtWidgets.QTableWidgetItem(imic_str))
        
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem('0')) # 0 for not done yet, keep this one always the last !
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.repeat_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.nb_repeat_job_spbx.value()))) # nb repeat
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.average_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(str(self.jobs_window.nb_average_job_spbx.value()))) # nb average
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.zstck_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(list_z_str)) # Z stack job params
        # #'[%f, %f, %f]' % (self.strt_Z_stack_spnbx.value(), self.stp_Z_stack_spnbx.value(), self.end_Z_stack_spnbx.value())
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(self.list_ps_str)) # ps job params
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.polar_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(list_polar_str)) # polar job params
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.shutteruse_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(str(self.use_shutter_combo.currentIndex())))
        
        if self.ishg_EOM_AC[0]:
            ishgfastuse = self.ishg_EOM_AC + [ self.jobs_window.scndProcfill_EOMph_chck.isChecked(), self.jobs_window.mode_EOM_ramps_spec_AC_cb.currentIndex()]
            ishgfastuse_str = param_ini.list_ishgfast_separator.join(str(x) for x in ishgfastuse)
        else: ishgfastuse_str = 'N/A'
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.ishgfastuse_posWrtEnd_jobTable,  QtWidgets.QTableWidgetItem(ishgfastuse_str))
        
        trans_str = self.jobs_window.pos_motor_trans_edt.text() if self.jobs_window.pos_motor_trans_edt.isEnabled() else 'N/A' # um
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.transmtrs_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(trans_str))
        mtr_polar = ['','']
        mtr_polar[0] = self.jobs_window.angle_polar_bx.value() if (self.jobs_window.angle_polar_bx.isEnabled() and self.jobs_window.mtr_tl_chck.isChecked()) else 'N/A' # # HWP
        mtr_polar[1] = self.jobs_window.newport_polar_bx.value() if (self.jobs_window.newport_polar_bx.isEnabled() and self.jobs_window.mtr_newport_chck.isChecked()) else 'N/A' # # QWP
        mtr_polar_str = param_ini.list_polar_separator.join(str(x) for x in mtr_polar)
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.polarmtrs_posWrtEnd_jobTable , QtWidgets.QTableWidgetItem(mtr_polar_str)) # mtr polars
         
        if ps_concerned:
            if self.jobs_window.ps_mtr_trans_radio.isChecked(): # trans 
                name_mtr = 'trans'
            elif self.jobs_window.ps_mtr_rot_radio.isChecked(): # rot.
                name_mtr = 'rot.'
            elif self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): # # DC volt
                name_mtr = param_ini.name_dcvolt
        else: name_mtr = 'N/A'
        valmtrps = self.jobs_window.pos_motor_phshft_edt.text() if self.jobs_window.pos_motor_phshft_edt.isEnabled() else 'N/A'  # um
        name_mtr_c = param_ini.list_ps_separator.join(x for x in [name_mtr, valmtrps])
        self.jobs_window.table_jobs.setItem(rowPosition, self.jobs_window.table_jobs.columnCount()-1+param_ini.psmtr_posWrtEnd_jobTable, QtWidgets.QTableWidgetItem(name_mtr_c))
            
        self.new_ps_list_flag = 0
        
        if not self.jobs_window.del_job_button.isEnabled():
            self.jobs_window.del_job_button.setEnabled(True)
        if not self.jobs_window.ascendSelJob_button.isEnabled():
            self.jobs_window.ascendSelJob_button.setEnabled(True)
        if not self.jobs_window.descendSelJob_button.isEnabled():
            self.jobs_window.descendSelJob_button.setEnabled(True)
        
        if self.calib_job:
            self.calib_job = False # unlock the flag
            self.count_avg_job = 1 # reset to init
            self.row_jobs_current = self.jobs_window.table_jobs.rowCount()-1
            self.iterationInCurrentJob = 1
            self.cal_ps_meth() # call the calib p-s function
        
    @pyqtSlot()     
    def del_jobFromlist_meth(self):
        
        current_row = self.jobs_window.table_jobs.currentRow()
        
        if current_row == -1: # no row selected
            current_row = self.jobs_window.table_jobs.rowCount() - 1

        self.jobs_window.table_jobs.removeRow(current_row)
        
        if self.jobs_window.table_jobs.rowCount() < 1: # no row anymore
            self.row_jobs_current = None
            self.jobs_window.del_job_button.setEnabled(False)
            self.after_reset_jobFlags_meth()
    
    @pyqtSlot()     
    def after_cal_button_meth(self):
        # # because for now, calibration of p-s is still special
        
        if (self.count_avg_job == -1 and self.jobs_window.cal_ps_button.text() == self.cal_ps_button_stop00): # # calib running
            self.jobs_window.cal_ps_button.setText(self.cal_ps_button_txt00);  self.jobs_window.cal_ps_button.setStyleSheet('color: black')
            self.jobs_window.stop_apt_push.animateClick()
            if self.jobs_window.autoco_frog_pushButton.text() == 'FROG':
                self.spectro_acq_flag_queue.put([-2])
            else: # # autoco
                self.cancel_inline_meth()
        else: # # not started
            if ((self.motorPhshftIsHere and not self.jobs_window.ps_mtr_dcvolt_radio.isChecked()) or (self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and self.EOMph_is_connected)) : # if ps motor is connected ...
                print('calibration of phase-shift')
                if (self.spectro_toggled_forfastscan and self.jobs_window.autoco_frog_pushButton.text() == 'FROG'): # # will start a new
                    self.spectro_acq_flag_queue.put([-2])
                current_row = self.jobs_window.table_jobs.currentRow()
                if current_row == -1: # no row selected
                    current_row = self.jobs_window.table_jobs.rowCount() - 1
                if (self.jobs_window.table_jobs.rowCount() > 0 and self.jobs_window.table_jobs.item(current_row, 3).text() == param_ini.calib_ps_name_job): # already one
                    self.jobs_window.table_jobs.removeRow(current_row)
                    
                self.calib_job = True
                if self.jobs_window.mode_EOM_ramps_AC_chk.isChecked(): self.jobs_window.mode_EOM_ramps_AC_chk.setChecked(False) # a priori, not a interferograms  acquisition
                self.add_job2list_meth()
            else:
                print('no mtr corresp. for calib')
     
    @pyqtSlot()     
    def after_reset_jobFlags_meth(self):
        # called by button click
        
        self.number_img_done = 0
        self.path_tmp_job = None
        self.nbmax00 = param_ini.nb_img_cont_dflt
        self.pos_phshft0=0
        self.offset_pos_motor_ps = 0 # important !!
        jobs_scripts.no_job_running_meth(self)
        if self.jobs_window.table_jobs.rowCount() >= 1: # some row 
            self.jobs_window.table_jobs.setItem(0, self.jobs_window.table_jobs.columnCount()-1, QtWidgets.QTableWidgetItem('0')) # first row of jobs is set to undone
        self.force_single_scan = False
        # # self.set_new_scan = 1
        self.jobs_window.cal_ps_button.setText(self.cal_ps_button_txt00); self.jobs_window.cal_ps_button.setStyleSheet('color: black')
        if (hasattr(self, 'worker_apt') and self.worker_apt is not None):
            self.worker_apt.wait_flag = False # re-init        
       
    @pyqtSlot()     
    def remove_jobs_done_meth(self):
        # called by button click
        
        ct = 0
        for ii in range(self.jobs_window.table_jobs.rowCount()):
            
            if int(self.jobs_window.table_jobs.item(ii-ct, self.jobs_window.table_jobs.columnCount()-1).text()) > 0: # already done
                self.jobs_window.table_jobs.removeRow(ii-ct)
                ct += 1 # a row has been erased ...
        
        self.jobs_window.remove_done_jobs_button.setEnabled(False)
        if self.jobs_window.table_jobs.rowCount() < 1: # no row anymore
            self.row_jobs_current = None
                
    @pyqtSlot()     
    def ascendSelJob_meth(self):
        
        if self.jobs_window.table_jobs.currentRow() is None: # no selection
            QtWidgets.QMessageBox.warning(None, '', "No row selected")
        else: # row selected
            if self.jobs_window.table_jobs.currentRow() > 0: # not first row reached
                for jj in range(self.jobs_window.table_jobs.columnCount()):
                    item_memory = self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow()-1, jj).text() # it's a minus sign because going down means increase row
                    self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow()-1, jj, QtWidgets.QTableWidgetItem(self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow(), jj).text()))
                    self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow(), jj, QtWidgets.QTableWidgetItem(item_memory))
                # # self.jobs_window.table_jobs.insertRow(self.jobs_window.table_jobs.currentRow()+1)
                # # for jj in range(self.jobs_window.table_jobs.columnCount()):
                # #     item_memory = self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow()+2, jj)
                # #     
                # #     self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow()+1, jj, self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow(), jj))
                # #     self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow(), jj, item_memory)
        
    @pyqtSlot()     
    def descendSelJob_meth(self): 
    
        if self.jobs_window.table_jobs.currentRow() is None: # no selection
            QtWidgets.QMessageBox.warning(None, '', "No row selected")
        else: # row selected
            if self.jobs_window.table_jobs.currentRow() < self.jobs_window.table_jobs.rowCount()-1: # not last row reached
                for jj in range(self.jobs_window.table_jobs.columnCount()):
                    item_memory = self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow()+1, jj).text()
                    self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow()+1, jj, QtWidgets.QTableWidgetItem(self.jobs_window.table_jobs.item(self.jobs_window.table_jobs.currentRow(), jj).text()))
                    self.jobs_window.table_jobs.setItem(self.jobs_window.table_jobs.currentRow(), jj, QtWidgets.QTableWidgetItem(item_memory))
    
    @pyqtSlot()     
    def load_polar_xls_meth(self):
        
        file_full_path_chosen = QtWidgets.QFileDialog.getOpenFileName(None, 'Open xls(x) file or polars ...', r'%s\Desktop\bb.xlsx' % os.path.abspath(self.path_computer + '/../' + '/../'), '*.xlsx', '*.xlsx')
        
        if file_full_path_chosen[0]:
        
            if not 'pandas' in locals():
                import pandas
                
            st = self.jobs_window.strt_polar_angle_spnbx.value()
            step = self.jobs_window.step_polar_angle_spnbx.value()
            lst = self.jobs_window.stop_polar_angle_spnbx.value()
            
            if step == 0: self.jobs_window.step_polar_angle_spnbx.setValue(1); step = 1
            if lst == 0: self.jobs_window.stop_polar_angle_spnbx.setValue(1); lst = step
            nb_polar = self.jobs_window.nb_frame_polar_job_spbx.value()
            
            # # self.polars_xls is 1st col HWP and 2nd col QWP
            self.polars_xls, self.polar_numberswanted_list = jobs_scripts.ld_xls_to_polar_lists(file_full_path_chosen[0], numpy, pandas, st, step, lst, nb_polar)
            self.jobs_window.mode_wp_polar_cmb.setEnabled(True)
            print(self.polars_xls)
            # # if len(self.polars_xls[0]) == 2: # nb col
            nb_wps = len(self.polars_xls[0])
            self.jobs_window.mode_wp_polar_cmb.setCurrentIndex(nb_wps)
            self.jobs_window.nb_frame_polar_job_spbx.setValue(len(self.polars_xls))
            if (nb_wps ==2 and self.esp_here):
                self.jobs_window.mtr_newport_chck.setChecked(True)
            else:
                self.jobs_window.mtr_newport_chck.setChecked(False)
    
    @pyqtSlot(int)     
    def nbpass_calcite_changed_meth(self, ind):
        self.nb_pass_calcites = ind
        print('re-choose the correct mode to make the change of passes !')
    
    @pyqtSlot()     
    def jobs_avg_repeat_changed_meth(self):
        
        avg_job = self.jobs_window.nb_average_job_spbx.value()
        repeat_job = self.jobs_window.nb_repeat_job_spbx.value()
        tm_j = self.jobs_window.time_job_ind_bx.text()
        if tm_j:
            time_minutes = float(self.jobs_window.time_job_ind_bx.text())
        else:
            time_minutes = 0
        self.jobs_window.time_job_ind_bx.setText('%.2f' % (time_minutes*repeat_job/self.repeat_job_prev*avg_job/self.avg_job_prev))
        self.repeat_job_prev = repeat_job
        self.avg_job_prev = avg_job
        
    @pyqtSlot()     
    def update_time_job_meth(self):
        
        if self.jobs_window.table_jobs.rowCount() > 0: # at least one row
        
            curr_row = self.jobs_window.table_jobs.currentRow()
            if self.jobs_window.table_jobs.currentRow() == -1: # no selection
                curr_row = self.jobs_window.table_jobs.rowCount()-1
        
            if self.jobs_window.table_jobs.item(curr_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.zstck_posWrtEnd_jobTable).text() == 'N/A': # Z stack job params
                z_concerned = 0
            else:
                z_concerned = 1
            if self.jobs_window.table_jobs.item(curr_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.ps_posWrtEnd_jobTable).text() == 'N/A': # ps job params
                ps_concerned = 0
            else:
                ps_concerned = 1
            if self.jobs_window.table_jobs.item(curr_row, self.jobs_window.table_jobs.columnCount()-1+param_ini.polar_posWrtEnd_jobTable).text() == 'N/A': # polar job params
                polar_concerned = 0
            else:
                polar_concerned = 1
            
            nb_images_tot = self.jobs_window.nb_frame_tot_job_spbx.value()
            
            if self.use_shutter_combo.currentIndex()==1: time_pause_shutter = self.shutter_duration_ms_spnbx.value()/1000 # sec
            else: time_pause_shutter = 0
            
            tot_time_str = ('%.2f' % (((float(self.duration_indic.text()) + time_pause_shutter)*nb_images_tot + max(param_ini.time_change_Z*z_concerned + param_ini.time_change_ps*ps_concerned + param_ini.time_change_polar*polar_concerned, 1)*(nb_images_tot/self.jobs_window.nb_average_job_spbx.value()-1))/60)*self.jobs_window.nb_repeat_job_spbx.value()) # in minutes
            
            self.jobs_window.time_job_ind_bx.setText(tot_time_str)
        
    @pyqtSlot(int)     
    def mtr_tl_chck_meth(self, val):
        
        if val: # mtr Tl checked
            self.jobs_window.angle_polar_bx.setEnabled(True)
        else:
            self.jobs_window.angle_polar_bx.setEnabled(False)
        
    @pyqtSlot(int)     
    def mtr_newport_chck_meth(self, val):
        
        if val: # mtr newport checked
            self.jobs_window.newport_polar_bx.setEnabled(True)
        else:
            self.jobs_window.newport_polar_bx.setEnabled(False)
    
    @pyqtSlot()        
    def mos_Z_XorYmax_get(self):
    # # self.mos_Z_Xmax_get_push.
        widget_caller = self.sender()
        name = widget_caller.objectName()
        if name[6] == 'X':
            spbx = self.jobs_window.mos_Zdiff_um_Xmax_spnbx
        elif name[6] == 'Y': 
            spbx = self.jobs_window.mos_Zdiff_um_Ymax_spnbx
        currentZ = self.currZ_util(); currentZ = currentZ[0]+currentZ[1] # # mtr + piezo
        spbx.setValue((currentZ - self.jobs_window.strt_Z_stack_spnbx.value())*1000)
    
    @pyqtSlot(int, str)        
    def pos_ps_setxt(self, bb, postr):
        
        if bb == 1: # # (bb in (1, 11)): # # phsft rot.
            widg = self.jobs_window.pos_motor_phshft_edt #.setText(postr)
        elif bb == 11: # # live
            widg = self.jobs_window.gp_pos_live_lbl # .setText(postr)
        elif bb == 2: # #  bb in (2, 22): # # trans
            widg = self.jobs_window.pos_motor_trans_edt # .setText(postr)
        elif bb == 22: # # live
            widg = self.jobs_window.trans_pos_live_lbl
        else:
            return # # anormal
        
        try:    
            widg.blockSignals(True)
            widg.setText(postr)
            widg.blockSignals(False)
        except RuntimeError: pass
        
    @pyqtSlot(bool)        
    def ps_slowfast_toggled_meth(self, chck): # check is ps_slow check
        if self.jobs_window.ps_slow_radio.isChecked(): # # slow
            # # self.jobs_window.restheo_fastcalib_spbx.setVisible(False)
            self.jobs_window.restheo_fastcalib_spbx.setValue(30)
            self.jobs_window.nblinesimg_fastcalib_spbx.setVisible(False)
            # # self.jobs_window.restheo_fastcalib_lbl.setVisible(False)
            self.jobs_window.nblinesimg_fastcalib_lbl.setVisible(False)
            # # self.jobs_window.num_frame_calib_phshft_spbx.setEnabled(True)
            self.jobs_window.num_frame_calib_phshft_spbx.setMaximum(9999999)
            self.jobs_window.nb_fr_or_dist_calib_lbl.setText('Nbr of frames')
            self.jobs_window.autoco_frog_pushButton.setVisible(False)
            self.jobs_window.exptime_fastcalib_lbl.setVisible(False)
            self.jobs_window.exptime_fastcalib_vallbl.setVisible(False)
            self.jobs_window.mtrreturninitposjob_chck.setChecked(self.mtrreturninitposjob_set) # # preferable not
            mm = 500 # um
            if self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): self.change_phshft_sgnl = self.worker_EOMph.EOMph_setHV_signal if (hasattr(self, 'worker_EOMph') and self.worker_EOMph is not None) else None
            else: self.change_phshft_sgnl = self.move_motor_phshft_signal if self.jobs_window.ps_mtr_rot_radio.isChecked() else self.move_motor_trans_signal
            if self.motorPhshftIsHere: self.jobs_window.cal_ps_button.setEnabled(True) 

        elif self.jobs_window.ps_fast_radio.isChecked(): # # fast
            # # self.jobs_window.restheo_fastcalib_spbx.setVisible(True)
            self.jobs_window.nblinesimg_fastcalib_spbx.setVisible(True)
            # # self.jobs_window.restheo_fastcalib_lbl.setVisible(True)
            self.jobs_window.restheo_fastcalib_spbx.setValue(9)
            self.jobs_window.nblinesimg_fastcalib_lbl.setVisible(True)
            # # self.jobs_window.num_frame_calib_phshft_spbx.setEnabled(False)
            self.jobs_window.num_frame_calib_phshft_spbx.setMaximum(param_ini.pos_max_phshft_um)
            self.jobs_window.nb_fr_or_dist_calib_lbl.setText('dist_mtr (um)')
            self.jobs_window.autoco_frog_pushButton.setVisible(True)
            self.jobs_window.exptime_fastcalib_lbl.setVisible(True)
            self.jobs_window.exptime_fastcalib_vallbl.setVisible(True)
            self.mtrreturninitposjob_set = self.jobs_window.mtrreturninitposjob_chck.isChecked()
            self.jobs_window.mtrreturninitposjob_chck.setChecked(False) # # preferable not
            if self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): self.change_phshft_sgnl = None # # fast + DC
            if self.jobs_window.ps_mtr_rot_radio.isChecked(): self.jobs_window.cal_ps_button.setEnabled(False) # # does not exist for now
            elif self.motorPhshftIsHere: self.jobs_window.cal_ps_button.setEnabled(True) 
            
            mm = param_ini.pos_max_phshft_um
            print('use `invert order` checkbox in jobs to do the fast calib backward, and uncheck the box for return to 0 the motor')
        if self.jobs_window.ps_mtr_trans_radio.isChecked(): # # trans
            self.jobs_window.max_angle_calib_phshft_spbx.setValue(mm/param_ini.nb_pass_calcites/2*self.jobs_window.eq_deg_unit_test_spnbx.value())
            if self.jobs_window.max_angle_calib_phshft_spbx.value() == self.jobs_window.max_angle_calib_phshft_spbx.maximum(): self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('{ color: red;}')
            else: self.jobs_window.max_angle_calib_phshft_spbx.setStyleSheet('{ color: black;}')
        if (self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and self.jobs_window.ps_fast_radio.isChecked()): # # DC volt fast
            self.jobs_window.nb_fr_or_dist_calib_lbl.setVisible(False)
            self.jobs_window.num_frame_calib_phshft_spbx.setVisible(False)
        else: # # trans or rot    
            self.jobs_window.nb_fr_or_dist_calib_lbl.setVisible(True)
            self.jobs_window.num_frame_calib_phshft_spbx.setVisible(True)     
        jobs_scripts.calib_disttot_mtr_set_val_util(self)
        self.jobs_window.mtrps_velset_spbx.valueChanged.emit(self.jobs_window.mtrps_velset_spbx.value())
        if (self.jobs_window.ps_mtr_dcvolt_radio.isChecked() and not chck): # # DC(AC) volt fast (AC)
            # # \\\ trick to make the change considered
            # # print('fewr')
            # eq_1=self.jobs_window.eq_deg_unit_test_spnbx.value()
            # self.jobs_window.eq_deg_unit_test_spnbx.valueChanged.emit(eq_1)
            
            # self.jobs_window.eq_deg_unit_test_spnbx.setValue(eq_1*1.1)
            # time.sleep(1)
            # self.change_step_calibps_meth()
            # time.sleep(1)
            # self.jobs_window.eq_deg_unit_test_spnbx.setValue(eq_1)
            # time.sleep(0.2)
            self.calib_eom_fast_meth()
        self.jobs_window.ps_mtr_trans_radio.toggled.emit(self.jobs_window.ps_mtr_trans_radio.isChecked()) # just for validate values
        
    @pyqtSlot()        
    def autocofrog_toggled_meth(self ):   
        if self.jobs_window.autoco_frog_pushButton.text() == 'FROG': # # switch to autoco
            strss = 'background-color:lightblue;'
            name = 'Autoco'
            # # self.jobs_window.nblinesimg_fastcalib_spbx.setVisible(True)
            nbline_str = 'Nlines'
            nbln_dflt = param_ini.divider_lines_calib_fast
        else:
            strss = 'background-color:lightpink;'
            name = 'FROG'
            # # self.jobs_window.nblinesimg_fastcalib_spbx.setVisible(False)
            nbline_str = 'Avg'  
            nbln_dflt = 3
        self.jobs_window.autoco_frog_pushButton.setStyleSheet(strss)
        self.jobs_window.autoco_frog_pushButton.setText(name)
        self.jobs_window.nblinesimg_fastcalib_lbl.setText(nbline_str) # # setVisible(True)
        self.jobs_window.nblinesimg_fastcalib_spbx.setValue(nbln_dflt)
        
        self.mtrps_def_vel_accn_meth(param_ini.max_vel_TC_dflt)
        self.jobs_window.mtrps_velset_spbx.valueChanged.emit(self.jobs_window.mtrps_velset_spbx.value())
    
    @pyqtSlot()        
    def load_pltfig_pkl_after(self ): 
    
        # # r'%s\Desktop' % (os.path.abspath(path_computer + '/../' + '/../'))
        self.pathwalk = jobs_scripts.save_pltfig_pkl_meth(sys, os, '', self.pathwalk, False)   # False for load
    
    @pyqtSlot()        
    def save_pltfig_pkl_after(self ): 
    
        # # if QtWidgets.qApp.mouseButtons() & QtCore.Qt.RightButton:
        # #     
        # # print(QtWidgets.qApp.mouseButtons()== QtCore.Qt.RightButton, 'ok')
    
        self.pathwalk = jobs_scripts.save_pltfig_pkl_meth(sys, os, self.acq_name_edt.text(), self.pathwalk, True)   # true for save
    
    @pyqtSlot(int)        
    def mode_EOMph_changed_meth(self, val):
    # # called by a checkbx
        if val: # mode_EOMph ramps checked 
            self.ishg_EOM_AC[0] = 1 # flag
        else: # not checked
            self.ishg_EOM_AC[0] = 0 # flag
        # # TODO: logging Processes ??
    
    @pyqtSlot()        
    def EOMph_params_ch_meth(self):
        # # called by the EOM widgets
        widg = self.sender() 
        rmp_time_us = self.jobs_window.ramptime_us_EOMph_spbx.value()
        eom_cycles_times_tr = list(map(list, zip(*param_ini.eom_cycles_times))) # transpose of list
        if not (rmp_time_us in eom_cycles_times_tr[0]): 
            if widg == self.jobs_window.ramptime_us_EOMph_spbx:
                print('ERROR: unsupported ramp time !')
        else: # # rmp ok
            if not (widg in (self.jobs_window.deadtimeBeg_us_EOMph_spbx, self.jobs_window.deadtimeEnd_us_EOMph_spbx, self.jobs_window.deadtimeLine_us_EOMph_spbx)):
                self.jobs_window.deadtimeBeg_us_EOMph_spbx.valueChanged.disconnect(self.EOMph_params_ch_meth) #self.jobs_window.deadtimeBeg_us_EOMph_spbx.blockSignals(True)
                self.jobs_window.deadtimeEnd_us_EOMph_spbx.valueChanged.disconnect(self.EOMph_params_ch_meth) #
                
                ind = eom_cycles_times_tr[0].index(rmp_time_us)
                dead_t_beg_us = param_ini.eom_cycles_times[ind][1]
                dead_t_end_us = param_ini.eom_cycles_times[ind][2]
                self.jobs_window.deadtimeBeg_us_EOMph_spbx.setValue(dead_t_beg_us)
                self.jobs_window.deadtimeEnd_us_EOMph_spbx.setValue(dead_t_end_us)
                self.jobs_window.deadtimeBeg_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth) #
                self.jobs_window.deadtimeEnd_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth) # 
                if widg == self.jobs_window.ramptime_us_EOMph_spbx:
                    self.jobs_window.deadtimeLine_us_EOMph_spbx.valueChanged.disconnect(self.EOMph_params_ch_meth)
                    dead_tline_us = param_ini.eom_cycles_times[ind][3]
                    self.jobs_window.deadtimeLine_us_EOMph_spbx.setValue(dead_tline_us)
                    self.jobs_window.deadtimeLine_us_EOMph_spbx.valueChanged.connect(self.EOMph_params_ch_meth)          
            ind_spec = int(self.jobs_window.mode_EOM_ramps_spec_AC_cb.currentIndex())
            if ind_spec == 2:  # # both saving
                mode =  11
            else:
                mode = max(int(self.jobs_window.mode_EOM_ramps_AC_chk.isChecked()), 2*ind_spec)
            
            sprate = self.read_sample_rate_spnbx.value()
            lis_dt=[0, self.jobs_window.deadtimeBeg_us_EOMph_spbx.value()*1e-6, self.jobs_window.deadtimeEnd_us_EOMph_spbx.value()*1e-6, self.jobs_window.deadtimeLine_us_EOMph_spbx.value()*1e-6]
            for i in range(len(lis_dt)):
                if abs(round(lis_dt[i]*1e6)-lis_dt[i]*1e6) < 1/sprate: # # avoid values like 79.9999999999999999999999999999
                    lis_dt[i] = float(jobs_scripts.truncate(lis_dt[i], 6)) ##round(lis_dt[i]*1e6)*1e-6
                    
            self.ishg_EOM_AC = [mode, round(rmp_time_us*1e-6, 7), self.jobs_window.steptheo_EOMph_spbx.value(), self.jobs_window.voltpi_EOMph_spbx.value(), self.jobs_window.voltmax_EOMph_spbx.value(), 1, tuple(lis_dt), (self.jobs_window.impose_rmptime_exptime_EOMph_chck.isChecked(), 0) ]
            # # [False, rmp_time_sec_dflt, 30, 300, 1400, 1, [0, beg_dt_us_dflt, end_dt_us_dflt], flag_impose_ramptime_as_exptime] # flag, ramp time sec00, step theo(deg), Vpi, VMax, nb_samps_perphsft, task_mtrtrigger_out, offset_samps, flag_impose_ramptime_as_exptime
            
            if not self.jobs_window.mode_EOM_ramps_AC_chk.isChecked(): # # not iSHG
                self.mode_EOMph_changed_meth(False)
            
            widg_send = self.sender()
            if widg_send == self.jobs_window.steptheo_EOMph_spbx: # # change of phase step
                nb = round(self.ishg_EOM_AC[4]/self.ishg_EOM_AC[3]*180/self.ishg_EOM_AC[2])
                print('A priori number of phase-shifts = ', nb)
                self.jobs_window.msg_EOMph_pltxtedt.appendPlainText('nb ps %d' % nb)
            elif widg_send == self.jobs_window.ramptime_us_EOMph_spbx:
                self.jobs_window.steptheo_EOMph_spbx.setMinimum(self.ishg_EOM_AC[4]/self.ishg_EOM_AC[3]*180/round(sprate*rmp_time_us*1e-6))
        if widg == self.jobs_window.mode_EOM_ramps_AC_chk: # check
            self.dt_rate_ishg_match_meth(-1) #-1 for float, do not call this func again !!!
            
    @pyqtSlot(int)        
    def impose_rmptime_exptime_EOMph_meth(self, bb):
        # # called by chck impose_rmptime_exptime_EOMph stateChanged
        
        if bb: # checked
            self.dwll_time_edt.setValue(self.jobs_window.ramptime_us_EOMph_spbx.value() + self.jobs_window.deadtimeBeg_us_EOMph_spbx.value() + self.jobs_window.deadtimeEnd_us_EOMph_spbx.value())
        else: # not checked
            if self.stage_scan_mode == 1: # stage scn
                # # self.dwll_time_edt.setValue
                self.sizeX_um_spbx.valueChanged.emit(self.sizeX_um_spbx.value())
            else: # # galvo or static
                self.dwll_time_edt.setValue(param_ini.time_by_point*1e6) # classic

    @pyqtSlot()
    def EOMph_simulate_params_meth(self):
        importlib.reload(param_ini)
        print('\n \\ simu params //')
        ishg_EOM_AC_insamps = jobs_scripts.EOMph_nb_samps_phpixel_meth(self.read_sample_rate_spnbx.value(), list(self.ishg_EOM_AC), param_ini.tolerance_change_nbphsft, param_ini.exploit_all_acqsamps, param_ini.ps_step_closest_possible_so_lstsamps_inddtime, param_ini.add_nb_ps)
        print('in samps', ishg_EOM_AC_insamps)
    
        ## EOM phase Axis
        
    @pyqtSlot()        
    def frstini_EOMph_meth(self):
        # # called by 1st EOM COM call
        try: self.jobs_window.com_EOMph_button.clicked.disconnect(self.frstini_EOMph_meth)
        except TypeError: pass
        if (not hasattr(self, 'thread_EOMph') or self.thread_EOMph is None): # # never started
            self.setupThread_EOMph()
        
    @pyqtSlot()        
    def setHV_EOMph_meth(self):
        # # called by EOM set HV button
        self.jobs_window.getstatHV_EOMph_button.animateClick() # get
        securit = False
        if not securit: self.jobs_window.onoffHV_EOMph_chck.blockSignals(True)
        self.jobs_window.onoffHV_EOMph_chck.setChecked(True)
        if not securit: self.jobs_window.onoffHV_EOMph_chck.blockSignals(False)
        self.worker_EOMph.EOMph_setHV_signal.emit(self.jobs_window.valHV_EOMph_spbx.value(), False) # # False for no job
    
    @pyqtSlot(int)
    def EOMph_afterhere_meth(self, here):
        
        if self.jobs_window.ps_mtr_dcvolt_radio.isChecked(): self.jobs_window.cal_ps_button.setEnabled(here) 

        if here:
            try:
                self.jobs_window.com_EOMph_button.clicked.disconnect() # everything
            except TypeError:
                pass
            self.EOMph_is_connected = True
            self.jobs_window.close_EOMph_button.setEnabled(True)
            self.jobs_window.stop_EOMph_button.setEnabled(True)
            self.jobs_window.stmode_EOMph_cbBx.setEnabled(True)
            self.jobs_window.getstatHV_EOMph_button.setEnabled(True)
            self.jobs_window.valHV_EOMph_spbx.setEnabled(True)
            self.jobs_window.setHV_EOMph_button.setEnabled(True)
            self.jobs_window.onoffHV_EOMph_chck.setEnabled(True)
            self.jobs_window.com_EOMph_button.clicked.connect(self.worker_EOMph.get_status_modulator) # get
            
        else: # not here
            if (hasattr(self, 'worker_EOMph') and self.thread_EOMph is not None): # # never started
                try:
                    self.jobs_window.com_EOMph_button.clicked.disconnect() # everything
                except TypeError:
                    pass
                self.jobs_window.com_EOMph_button.clicked.connect(self.worker_EOMph.connect_modulator)
            self.EOMph_is_connected = False
            self.jobs_window.close_EOMph_button.setEnabled(False)
            self.jobs_window.stop_EOMph_button.setEnabled(False)
            self.jobs_window.stmode_EOMph_cbBx.setEnabled(False)
            self.jobs_window.getstatHV_EOMph_button.setEnabled(False)
            self.jobs_window.valHV_EOMph_spbx.setEnabled(False)
            self.jobs_window.setHV_EOMph_button.setEnabled(False)
            self.jobs_window.onoffHV_EOMph_chck.setEnabled(False)
            self.jobs_window.stmode_EOMph_cbBx.blockSignals(True); self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(0); self.jobs_window.stmode_EOMph_cbBx.blockSignals(False)
            
    @pyqtSlot(int)
    def expert_EOMph_chck_meth(self, chck):
        
        if chck: # expert
            # # self.jobs_window.stop_EOMph_button.setVisible(True)
            self.jobs_window.getstatHV_EOMph_button.setVisible(True)
            self.jobs_window.valHV_EOMph_spbx.setVisible(True)
            self.jobs_window.setHV_EOMph_button.setVisible(True)
            self.jobs_window.onoffHV_EOMph_chck.setVisible(True)
        else: # normal
            # # self.jobs_window.stop_EOMph_button.setVisible(False)
            self.jobs_window.getstatHV_EOMph_button.setVisible(False)
            self.jobs_window.valHV_EOMph_spbx.setVisible(False)
            self.jobs_window.setHV_EOMph_button.setVisible(False)
            self.jobs_window.onoffHV_EOMph_chck.setVisible(False)
    
    @pyqtSlot(int)
    def on_off_voltage_eom_meth(self, val):
        self.jobs_window.stmode_EOMph_cbBx.blockSignals(True)
        self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(4) # # DC
        self.jobs_window.stmode_EOMph_cbBx.blockSignals(False)
        self.eomph_send_onoff_signal.emit(val)
    
    @pyqtSlot(int)
    def stmode_EOMph_after_meth(self, val):
        if val > 0:
            if val == 1: # # 2000us
                rmptime = param_ini.ramptime_EOMph_0
            elif val == 2: # # 200us
                rmptime = param_ini.ramptime_EOMph_1
            elif val == 3: # # 20us
                rmptime = param_ini.ramptime_EOMph_2
            else: # # DC
                rmptime = None
            if rmptime is not None:
                self.jobs_window.ramptime_us_EOMph_spbx.setValue(rmptime)
                self.eomph_stmodeAC_signal.emit(val) # mode
            else: # DC
                self.eomph_send_onoff_signal.emit(1) # ON
        else: #val == 0
            self.jobs_window.stop_EOMph_button.clicked.emit()  # # will stop the mode
                
    @pyqtSlot()
    def stop_modulatorEOMph_meth(self):
        if self.jobs_window.onoffHV_EOMph_chck.isChecked():
            self.jobs_window.onoffHV_EOMph_chck.blockSignals(True); self.jobs_window.onoffHV_EOMph_chck.setChecked(False); self.jobs_window.onoffHV_EOMph_chck.blockSignals(False)
        self.jobs_window.stmode_EOMph_cbBx.blockSignals(True)
        self.jobs_window.stmode_EOMph_cbBx.setCurrentIndex(0)
        self.jobs_window.stmode_EOMph_cbBx.blockSignals(False)
    
    # # @pyqtSlot(int)    
    # # def mdltr_voltset_dispval_meth(self, val):
    
    @pyqtSlot(int)       
    def treatmatlab_chck_after(self, state):
        if state: jobs_scripts.matlab_treat_ishg_call(self, sys, QThread, None, None, None, None) # start engine
        
    @pyqtSlot(int)    
    def matlab_cmb_meth(self, val):
        if val == 1: # # instance
            if (hasattr(self, 'worker_matlab') and self.thread_matlab is not None):
                print('should show instance of matlab now')
            else: self.treatmatlab_chck_after(True) # start matlab
            self.worker_matlab.show_instance_signal.emit()
        elif val == 2: # # treat last
            pp=os.getcwd()        
            os.chdir('%s/tmp' % self.path_save)
            fldrnm=sorted(filter(os.path.isdir, os.listdir('.')), key=os.path.getmtime)
            os.chdir(pp)
            if len(fldrnm) > 0:  # otherwise no folder
                fldrnm=fldrnm[-1]
                if fldrnm is not None:  # otherwise just start the engine and prog 
                    if self.jobs_window.mode_EOM_ramps_AC_chk.isChecked(): incr_ordr = 1; nb_slice_per_step =5; ctr_mult=8; # fast ISHG
                    else: incr_ordr = 0; nb_slice_per_step =3; ctr_mult=2; # st ISHG
                    self.worker_matlab.matlabGUI_treatphase_signal.emit(incr_ordr, nb_slice_per_step, ctr_mult, fldrnm)
            else: print('\n no folder to treat !!')
        elif val == 3: # # quit matlab
            self.worker_matlab.engmatlab.quit()
            del self.worker_matlab.engmatlab
        
        if val in (1,2,3): 
            self.jobs_window.matlab_cmb.blockSignals(True)
            self.jobs_window.matlab_cmb.setCurrentIndex(0)
            self.jobs_window.matlab_cmb.blockSignals(False)

           
        ## spectro methods
    
    @pyqtSlot(int, str, str)
    def spectro_display_val_meth(self, val, spectro_wlth_str, spectro_fwhm_str):
         # # val = 0 means outside acq., 1 = continuous normal acq., 2 = before scan fast, 3 = during scan fast
        self.spectro_toggled_forfastscan = bool(val == 2)
        # print('received spectro values')
        self.wlth_spectro_edt.setText(spectro_wlth_str)
        self.fwhm_spectro_edt.setText(spectro_fwhm_str)
    
    @pyqtSlot(int)
    def spectro_msg_handler_meth(self, msg):
        # method is called if success connected or disconnected
                
        if msg == -1: # # QThread killed
            self.thread_spectro = None # re-init
            
        else: # # standard
            self.spectro_connected = not self.spectro_connected # self.spectro_connected change of state
            print('spectro connected is confirmed: ', self.spectro_connected)
            if self.spectro_connected: # spectro connected
                if msg != -2:
                    self.spectro_acq_flag_queue.put([1])
                    self.acquire_spectrum_continuous_signal.emit(0) # mode normal
                elif msg == -2:
                    self.worker_spectro.acqsave_fast_spect_scan_signal.emit(1) # # will start acqsave_fast_spect_scan_meth       
                
                self.spectro_link_button.setText('Discon. spectro')
                self.spectro_link_button.setStyleSheet('QPushButton { color: red;}')
                
            else:# spectro disconnected
                if msg <= -2: # # frog fast # # -22 if success full, -2 if aborted
                    if msg != -4: # # end job
                        self.send_move_to_worker_phshft() # # will end the job calib FROG fast  
                        print('frog fast disconn. detected, will reconnect the usual signal')
                        try:
                            self.acquire_spectrum_continuous_signal.disconnect(self.worker_spectro.acquire_spectrum_continuous_meth)  # # safety
                        except TypeError:
                            pass
                        self.acquire_spectrum_continuous_signal.connect(self.worker_spectro.acquire_spectrum_continuous_meth) 
                    else: # # -4 = acq normnal has been disconnected, scan save not started
                        # # self.spectro_connect_signal.emit(-2)  
                        self.spectro_connected = -2; self.spectro_link_button.clicked.emit() # # will call spectro_conn_disconn_push_meth
                self.spectro_link_button.setText('Con. spectro')
                self.spectro_link_button.setStyleSheet('QPushButton { color: #5555ff;}')
        
    @pyqtSlot()
    def spectro_conn_disconn_push_meth(self):    
        # conn/disconn spectro push button toggles this method
        
        # # print('self.spectro_connected', self.spectro_connected)
        if (not hasattr(self, 'thread_spectro') or self.thread_spectro is None): # never started
            self.setupThread_spectro() ##  starts the spectro worker
            # # the handler will start a spect acq.
            
        if self.spectro_connected in (1, 2): # spectro already connected (2 for cal fast)
            if (self.spectro_connected==1 and self.count_avg_job != -1): 
                pck = [0] 
            elif (self.spectro_connected==2 and self.count_avg_job != -1): # #  fast calib, but start not end
                pck = [-4] 
            elif (self.count_avg_job == -1): # # fast calib frog, end
                self.count_avg_job = None
                pck = [-3] if self.jobs_window.saveiferr_fastcalib_chck.isChecked() else [-2]
            self.spectro_acq_flag_queue.put(pck) # stop spectro
        elif self.spectro_connected in (0, -2): # spectro not connected
            self.spectro_connect_signal.emit(self.spectro_connected)
            self.spectro_connected = 0 # # will be modified after
        else:
            print('self.spectro_connected', self.spectro_connected )
    
    @pyqtSlot(float)
    def lambda_center_chg_meth(self, val):
        
        if (hasattr(self, 'worker_spectro') and self.worker_spectro is not None): 
            self.worker_spectro.central_wvlgth = val*1000 # nm
        
    
        ## Dig. galvos meth
    
    @pyqtSlot()        
    def szarray_readAI_willchange_meth(self):
        
        callbacks = (self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1)
        if callbacks: # # callback
            if self.xscan_radio.isChecked(): nbpxfast = self.nbPX_X_ind.value(); nbpxslow = self.nbPX_Y_ind.value()
            else: nbpxfast = self.nbPX_Y_ind.value(); nbpxslow = self.nbPX_X_ind.value()
            if self.bidirec_check.currentIndex(): # # unidirek
                eff_unid = param_ini.eff_unid_diggalvos if self.stage_scan_mode == 0 else self.eff_wvfrm_an_galvos_spnbx.value()/100
            else: eff_unid = 1
            duration_one_line_real = self.dwll_time_edt.value()*1e-6*nbpxfast/eff_unid
            nb_lines_inpacket, maxSmp_paquet = daq_control_mp2.nb_linespacket_meth(numpy, self.stage_scan_mode == 0, param_ini.last_buff_smallest_poss, param_ini.lvl_trigger_not_win, param_ini.add_nb_lines_safe, callbacks, self.read_sample_rate_spnbx.value(), nbpxslow , param_ini.update_time, float(self.duration_indic.text()), duration_one_line_real, param_ini.settling_time_galvo_us*1e-6)
            
            szarray_readAI_callbk = round(sum(self.pmt_channel_list)*maxSmp_paquet*nb_lines_inpacket*param_ini.fact_data)
            
            if szarray_readAI_callbk > 0: #param_ini.max_szarray_readAI_callbk:
                uptime = min(param_ini.update_time, max(duration_one_line_real, param_ini.update_time*param_ini.max_szarray_readAI_callbk/szarray_readAI_callbk))
            # else: uptime = param_ini.update_time
                if uptime>0: self.update_rate_spnbx.setValue(1/uptime)
                # # print(szarray_readAI_callbk, maxSmp_paquet, nb_lines_inpacket, duration_one_line_real)
        
    @pyqtSlot(int)        
    def ext_smp_clk_changed_meth(self, val):
        
        self.timebase_ext_diggalvo_chck.blockSignals(True)
        if val: # checked
            if self.dev_to_use_AI_box.currentIndex() == 0: # 6110
                print('Be careful not to use Dev1 6110 with a rate < 0.1MHz !')
            else: # 6259
                print('Be careful not to use Dev2 6259 with a rate > 1/nb_chan MHz !')
            
            self.timebase_ext_diggalvo_chck.setChecked(False)
            self.timebase_ext_diggalvo_chck.setEnabled(False)
            
        else: # unchecked
        
            self.timebase_ext_diggalvo_chck.setEnabled(True)
            
        self.timebase_ext_diggalvo_chck.blockSignals(False)
            
    @pyqtSlot(int)        
    def preset_sync_dig_galv_changed_meth(self, val):
        
        if val:  # checkedx
            self.corr_sync_inPx_spnbx.setEnabled(False)
        else: # unchecked
            self.corr_sync_inPx_spnbx.setEnabled(True)
            
    @pyqtSlot(int)        
    def pause_trig_sync_dig_galv_changed_meth(self, val):
        
        self.use_preset_sync_dig_galv_chck.blockSignals(True)
        if val:  # checked
            # self.corr_sync_inPx_spnbx.setEnabled(False)
            self.acqline_galvo_mode_box.setVisible(True)
            self.watch_triggalvos_dev_box.setVisible(True)
            self.use_preset_sync_dig_galv_chck.setEnabled(False)
            self.use_preset_sync_dig_galv_chck.setChecked(False)
            if self.acqline_galvo_mode_box.currentIndex() == 0: # # meas. line time
                self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_pausetrig_measline_dflt)
            else: self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_pausetrig_measline_dflt) # # callback
        else: # unchecked
            self.acqline_galvo_mode_box.setVisible(False)
            self.watch_triggalvos_dev_box.setVisible(False)
            # self.corr_sync_inPx_spnbx.setEnabled(True)
            self.use_preset_sync_dig_galv_chck.setEnabled(True)
            self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_recaststtrig_dflt)
        
        self.use_preset_sync_dig_galv_chck.blockSignals(False)
        if (self.stage_scan_mode in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1): # # callback galvos
            self.szarray_readAI_willchange_meth()
        
    @pyqtSlot(int)        
    def timebase_ext_diggalvo_changed_meth(self, val):
        
        if self.mode_scan_box.currentIndex() == 0: # dig. galvo
            self.ext_smp_clk_chck.blockSignals(True)
            
            if val:  # checked
                self.ext_smp_clk_chck.setEnabled(False)
                self.ext_smp_clk_chck.setChecked(False)
            else: # unchecked
                self.ext_smp_clk_chck.setEnabled(True)
            
            self.ext_smp_clk_chck.blockSignals(False)

    @pyqtSlot()        
    def magn_init_meth(self): 
    # # called by EDITING spnbx mag
    
        if not self.magn_init: # #  = False
            self.magn_init = True # # magnif. has been set
        # # print('ok')
            
            self.launch_scan_button.setEnabled(True)
            self.launch_scan_button_single.setEnabled(True)
        
        if self.magn_obj_bx.value() == 20:
            self.objective_name = 'Obj 1'
            # self.NA_obj = 0.8
            self.eff_na_bx.setValue(param_ini.eff_na_20X)
            self.size_um_fov = param_ini.size_um_fov_20X # um
    
        elif self.magn_obj_bx.value() == 40:
            self.objective_name = 'Obj 2'
            self.eff_na_bx.setValue(param_ini.eff_na_40X)
            self.size_um_fov = param_ini.size_um_fov_40X # um

    @pyqtSlot(int)    
    def acqline_galvo_mode_changed_meth(self, v):
        if self.stage_scan_mode == 0: # # dig galvos
            if self.pause_trig_sync_dig_galv_chck.isChecked():
                if v == 0: # # meas line time
                    self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_pausetrig_measline_dflt)
                else: # # callback
                    self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_pausetrig_callback_dflt)
            else:  self.corr_sync_inPx_spnbx.setValue(param_ini.nb_skip_sync_dig_recaststtrig_dflt) # # use start trig and sync by calc (standard labview, dig galvos)
        
        if (self.stage_scan_mode in (0,3) and self.pause_trig_sync_dig_galv_chck.isChecked() and self.acqline_galvo_mode_box.currentIndex() == 1): # # callback galvos
            self.dt_rate_ishg_match_meth(-2) # # adjust sample rate
            self.szarray_readAI_willchange_meth()

        ## Ang galvos methods
    
    def send_anlgGlvo_def_meth(self, def_task):
        
        self.num_dev_watcherTrig = self.watch_triggalvos_dev_box.currentIndex()
        self.num_dev_anlgTrig = self.anlgtriggalvos_dev_box.currentIndex()  # # for anlg galvos
        self.num_dev_AO = self.aogalvos_dev_box.currentIndex() # # for anlg galvos
        
        if (not hasattr(self, 'thread_scan') or self.thread_scan is None): # thread_scan was not defined: # thread_scan was not defined
            self.setupThread_scan() # start Qthread of scan
            
        device_used_AIread = self.dev_to_use_AI_box.currentIndex() + 1
        self.scan_galvo_launch_processes_signal.emit(1-self.mode_scan_box.currentIndex(), self.real_time_disp, self.min_val_volt_list, self.max_val_volt_list, device_used_AIread, self.write_scan_before_anlg, self.num_dev_anlgTrig, self.num_dev_watcherTrig, self.num_dev_AO, self.isec_proc_forishgfill and self.ishg_EOM_AC[0], self.path_computer)
        self.unidirectional = self.bidirec_check.currentIndex() # 1 or 2 for unidirec

        if def_task:
            list_scan_params = [[1,0,0,0], 4e6, 20e-6, 0.33, self.obj_mag, self.center_x, self.center_y, 200,200,400,400,1, 1,0,100,1,1,0,0,0,0,[0,0,0], [],0,0,0,0,[0, 0], 0, (False, False), [80, 1.15, 90, self.off_fast_anlgGalvo_current, self.off_slow_anlgGalvo_current, 4], list(self.ishg_EOM_AC)]#[self.pmt_channel_list, self.read_sample_rate_spnbx.value(), self.exp_time*1e-6, self.update_time, self.obj_mag , self.center_x, self.center_y, self.new_szX_um, self.new_szY_um, self.nb_px_x, self.nb_px_y, self.nb_img_max, self.unidirectional, self.y_fast, self.nb_bins_hist, self.real_time_disp, self.clrmap_nb , self.delete_px_fast_begin, self.delete_px_fast_end, self.delete_px_slow_begin, self.delete_px_slow_end, [0,0,0], [], self.nb_accum, self.scan_xz, self.external_clock, self.time_base_ext, [self.read_buffer_offset_direct, self.read_buffer_offset_reverse], self.autoscalelive_plt, (self.lock_smprate, self.lock_uptime), [self.eff_wvfrm_an_galvos, self.mult_trig_fact_anlg_galv, self.trig_perc_hyst, self.off_fast_anlgGalvo_current, self.off_slow_anlgGalvo_current, self.fact_buffer_anlgGalvo_current], list(self.ishg_EOM_AC)]
            # # default !!
        
            paquet = [2, list_scan_params]
            self.queue_com_to_acq.put(paquet) # tell the acq process to define write Task
            self.scan_thread_available = 0 # scan is running
            # # self.set_new_scan = 0
            
    @pyqtSlot()
    def send_anlgGlvo_pos_static_meth(self):
        # # called by a button   
         
        if self.scan_thread_available == 1: # scan Process not running
        # 1 important
            self.send_anlgGlvo_def_meth(True) # 1 for def_task
        
        paquet = [7, [self.jobs_window.fast_wantedPos_anlgGalvo_spbx.value(), self.jobs_window.slow_wantedPos_anlgGalvo_spbx.value()]]
        self.queue_com_to_acq.put(paquet) # tell the acq process to move pos
        
        self.write_scan_before_anlg_current = not(self.write_scan_before_anlg) # # faking a new send of parameters to rewrite the scan correctly at any new acq.

    @pyqtSlot()
    def get_anlgGlvo_pos_stat_meth(self):
        # # called by a button    

        if self.scan_thread_available == 1: # scan Process not running
        # 1 important
            self.send_anlgGlvo_def_meth(True) # 0 for NOT def_task
        
        dev = self.dev_to_use_AI_box.currentText()
        msg = "Connect the fast trigger to %s/%s and slow to %s/%s" % (dev, self.ai_readposX_anlggalvo, dev, self.ai_readposY_anlggalvo)
        QtWidgets.QMessageBox.information(None, 'Connections', msg, QtWidgets.QMessageBox.Ok) #, QMessageBox::StandardButton defaultButton = NoButton)
        print(msg)
        
        self.queue_com_to_acq.put([6]) # tell the acq process to get pos
        
        try:
            [fast_pos, slow_pos] = self.queue_special_com_acqGalvo_stopline.get(block = True, timeout = 5) # blocking
        except queue.Empty:
            print('no results for get anlg galvos pos')
        else:
            print([fast_pos, slow_pos])
            self.jobs_window.fast_wantedPos_anlgGalvo_spbx.setValue(fast_pos*self.factor_trigger_chan)
            self.jobs_window.slow_wantedPos_anlgGalvo_spbx.setValue(slow_pos*self.factor_trigger_chan)
            
        self.write_scan_before_anlg_current = not(self.write_scan_before_anlg) # # faking a new send of parameters to rewrite the scan correctly at any new acq.
    
    @pyqtSlot()    
    def eff_new_galvos_adjustMax_meth(self):
        # # called directly most of the times, except by update_rate
        
        # # set the maximum only !!
        self.eff_wvfrm_an_galvos_spnbx.setMaximum(100/(1+param_ini.settling_time_galvo_us/(max(1,self.nbPX_X_ind.value())*self.dwll_time_edt.value()))) # # all in us
        if self.eff_wvfrm_an_galvos_spnbx.value() < self.eff_wfrm_anlggalv_dflt*0.5: self.eff_wvfrm_an_galvos_spnbx.setValue(self.eff_wfrm_anlggalv_dflt)
        f=26/4
        fact = param_ini.fact_buffer_anlgGalvo # # self.fact_buffer_anlgGalvo_spbx.value()
        nb_buff = self.dwll_time_edt.value()*1e-6*self.nbPX_X_ind.value()/(self.eff_wvfrm_an_galvos_spnbx.value()/100)*self.nbPX_Y_ind.value()*self.update_rate_spnbx.value()
        if nb_buff/fact > f: # # empirically, nb_buffers/fact_buffer too high
            self.fact_buffer_anlgGalvo_spbx.setValue(fact*round((nb_buff/f)**0.5))
        else: # # not too high
            self.fact_buffer_anlgGalvo_spbx.setValue(round((nb_buff/f)**0.5))
        # # print('fact*round((nb_buff/f)**0.5)', fact*round((nb_buff/f)**0.5))

    @pyqtSlot(int)
    def use_ini_val_galvo_anlg_meth(self, val):
        
        if val:
            self.jobs_window.fast_wantedPos_anlgGalvo_spbx.blockSignals(True)
            self.jobs_window.slow_wantedPos_anlgGalvo_spbx.blockSignals(True)
            self.jobs_window.fast_wantedPos_anlgGalvo_spbx.setValue(param_ini.offset_y_deg_00)
            self.jobs_window.slow_wantedPos_anlgGalvo_spbx.setValue(param_ini.offset_x_deg_00)
            self.jobs_window.fast_wantedPos_anlgGalvo_spbx.blockSignals(False)
            self.jobs_window.slow_wantedPos_anlgGalvo_spbx.blockSignals(False)
    
    @pyqtSlot()
    def pos_anlg_galvos_chg_after_meth(self): 
        self.jobs_window.use_ini_val_galvo_anlg_chck.blockSignals(True)
        self.jobs_window.use_ini_val_galvo_anlg_chck.setChecked(False)
        self.jobs_window.use_ini_val_galvo_anlg_chck.blockSignals(False)
        
    @pyqtSlot()
    def up_volt_anlg_galvo_meth(self): 
    
        # # print(self.hyst_perc_trig_spnbx.value())
        _, _, _, _, _, _, volt_pos_max_fast, volt_pos_min_fast, volt_pos_max_slow, volt_pos_min_slow, lvl_trig_top, lvl_trig_bottom, hyst_trig, _ = new_galvos_funcs.calc_max_min_volt_anlg_galvos(self.magn_obj_bx.value(), self.sizeX_um_spbx.value(), self.sizeY_um_spbx.value(), self.offsetX_mm_spnbx.value()*1000, self.offsetY_mm_spnbx.value()*1000, param_ini.scan_lens_mm, self.hyst_perc_trig_spnbx.value(), self.yscan_radio.isChecked(), self.jobs_window.off_fast00_anlgGalvo_spbx.value(), self.jobs_window.off_slow00_anlgGalvo_spbx.value(), None, None, self.factor_trigger, self.trig_safety_perc_spnbx.value()/100, param_ini.num_dev_anlgTrig, numpy, daq_control_mp2 , param_ini.safety_fact_chan_trig, param_ini.max_val_volt_galvos)
        
        txt_fast = 'Trlvl [%.3f, %.3f]V  trig [%.3f, %.3f]V' % (volt_pos_min_fast, volt_pos_max_fast, lvl_trig_bottom*self.factor_trigger, lvl_trig_top*self.factor_trigger)
        txt_fast2 = 'Trig btm = %.3fV (hyst = %.f mV)' % ((lvl_trig_bottom-hyst_trig)*self.factor_trigger, hyst_trig*self.factor_trigger*1000)
        if hyst_trig < param_ini.hyst_trig_min_advised:
            self.fast_anlgGalvo_disp_lbl_2.setStyleSheet('color: red')
        else:
            self.fast_anlgGalvo_disp_lbl_2.setStyleSheet('color: black')
        if (volt_pos_max_fast >= param_ini.max_val_volt_galvos or volt_pos_max_slow >= param_ini.max_val_volt_galvos or volt_pos_min_fast <= -param_ini.max_val_volt_galvos or volt_pos_min_slow <= -param_ini.max_val_volt_galvos):
            self.fast_anlgGalvo_disp_lbl.setStyleSheet('color: red')
        else:
            self.fast_anlgGalvo_disp_lbl.setStyleSheet('color: black')
        self.fast_anlgGalvo_disp_lbl.setText(txt_fast)
        self.fast_anlgGalvo_disp_lbl_2.setText(txt_fast2)
        txt_slow = 'Slow [%.3f, %.3f] V' % (volt_pos_min_slow, volt_pos_max_slow)
        self.slow_anlgGalvo_disp_lbl.setText(txt_slow)

        ## threads methods
    
    def setupThread_spectro(self):
        
        self.thread_spectro = QThread()
        
        spectro_pack = [self.lambda_bx.value()*1000, self.lower_bound_window , self.upper_bound_window, self.lwr_bound_expected, self.upper_bound_expected, self.integration_time_spectro_microsec, self.wait_time_spectro_seconds]
        
        self.worker_spectro = spectro_worker_script2.Worker_spectro(self.spectro_acq_flag_queue, self.queue_disconnections, queue.Empty, spectro_pack, numpy, time, datetime, param_ini.path_save_spectro, param_ini.min_exptime_msec, jobs_scripts, spectro_worker_script2.max_fwhm_util)
        
        self.worker_spectro.moveToThread(self.thread_spectro)  
        
        self.acquire_spectrum_continuous_signal.connect(self.worker_spectro.acquire_spectrum_continuous_meth)  
        self.spectro_connect_signal.connect(self.worker_spectro.connect_disconnect_spectro_meth)
        self.worker_spectro.spectro_msg_handler_signal.connect(self.spectro_msg_handler_meth)
        
        self.worker_spectro.spectro_values_display_signal.connect(self.spectro_display_val_meth)
        self.worker_spectro.acqsave_fast_spect_scan_signal.connect(self.worker_spectro.acqsave_fast_spect_scan_meth)
        
        self.thread_spectro.started.connect(self.worker_spectro.open_lib)
        
        try: self.lambda_bx.valueChanged.disconnect(self.lambda_center_chg_meth)
        except TypeError: pass # # no conn.
        self.lambda_bx.valueChanged.connect(self.lambda_center_chg_meth)
        
        # Start thread
        
        self.thread_spectro.start()
    
    def setupThread_stageXY(self):
        # only the stage XY, com by virtual COM port
        
        from modules import thorlabs_lowlvl_list
        self.thread_stageXY = QThread()
        
        self.worker_stageXY = stage_xy_worker_script.Worker_stageXY(time, self.queue_com_to_acq_stage, self.queue_special_com_acqstage_stopline, self.queue_list_arrays, self.queue_moveX_inscan, self.queue_moveY_inscan, self.queue_disconnections, self.stop_motorsXY_queue, self.scan_thread_available_signal, self.piezoZ_step_signal, stage_xy_worker_script.motor_blocking_meth,  param_ini.use_serial_not_ftdi, param_ini.XYstage_comport,  param_ini.time_out_stageXY, param_ini.motorXY_SN, param_ini.prof_mode , param_ini.prof_mode_slow, param_ini.jerk_mms3_slow, param_ini.PID_scn_lst, param_ini.PID_dflt_lst, self.acc_max, param_ini.block_slow_stgXY_before_return, param_ini.trigout_maxvelreached, param_ini.time_out, param_ini.trig_src_name_stgscan, param_ini.bnd_posXY_l,  param_ini.max_val_pxl_l, thorlabs_lowlvl_list, numpy )
        
        self.worker_stageXY.moveToThread(self.thread_stageXY)
        
        self.thread_stageXY.started.connect(self.worker_stageXY.open_lib)
        try: self.home_stage_button.clicked.disconnect(self.worker_stageXY.control_if_home_stage_necessary_meth)
        except TypeError: pass
        self.home_stage_button.clicked.connect(self.worker_stageXY.control_if_home_stage_necessary_meth) # if you call here a gui function, it will freeze the GUI
        try: self.worker_stageXY.home_ok.disconnect(self.has_been_homed)
        except TypeError: pass
        self.worker_stageXY.home_ok.connect(self.has_been_homed)
        try: self.worker_stageXY.ask_if_safe_pos_for_homing_signal.disconnect(self.ask_if_safe_pos_for_homing_meth)
        except TypeError: pass
        self.worker_stageXY.ask_if_safe_pos_for_homing_signal.connect(self.ask_if_safe_pos_for_homing_meth)
        try: self.do_force_stage_homing_signal.disconnect(self.worker_stageXY.home_stage_meth_forced)
        except TypeError: pass
        self.do_force_stage_homing_signal.connect(self.worker_stageXY.home_stage_meth_forced)
        try: self.move_motorX_signal.disconnect(self.worker_stageXY.move_motor_X)
        except TypeError: pass
        self.move_motorX_signal.connect(self.worker_stageXY.move_motor_X)
        try: self.move_motorY_signal.disconnect(self.worker_stageXY.move_motor_Y)
        except TypeError: pass
        self.move_motorY_signal.connect(self.worker_stageXY.move_motor_Y)
        try: self.change_scan_dependencies_signal.disconnect(self.worker_stageXY.change_scan_dependencies)
        except TypeError: pass
        self.change_scan_dependencies_signal.connect(self.worker_stageXY.change_scan_dependencies)
        try: self.worker_stageXY.new_scan_stage_signal.disconnect(self.worker_stageXY.scan_stage_meth)
        except TypeError: pass
        self.worker_stageXY.new_scan_stage_signal.connect(self.worker_stageXY.scan_stage_meth) # signal inside the worker because it facilitates use in standalone
        
        try: self.worker_stageXY.new_img_to_disp_signal.disconnect(self.display_img_gui)
        except TypeError: pass
        
        self.worker_stageXY.new_img_to_disp_signal.connect(self.display_img_gui)
        try: self.worker_stageXY.reload_scan_worker_signal.disconnect(self.worker_scan_set_reload_meth)
        except TypeError: pass
        self.worker_stageXY.reload_scan_worker_signal.connect(self.worker_scan_set_reload_meth)
        try: self.worker_stageXY.scan_depend_workerXY_togui_signal.disconnect(self.scan_depend_workerXY_togui_meth)
        except TypeError: pass
        self.worker_stageXY.scan_depend_workerXY_togui_signal.connect(self.scan_depend_workerXY_togui_meth)
        try: self.worker_stageXY.stageXY_is_imported_signal.disconnect(self.stageXY_imported_after_meth)
        except TypeError: pass
        self.worker_stageXY.stageXY_is_imported_signal.connect(self.stageXY_imported_after_meth)
        try: self.worker_stageXY.calc_param_scan_stg_signal.disconnect(self.calc_param_stgscan_workerXY_togui_meth)
        except TypeError: pass
        self.worker_stageXY.calc_param_scan_stg_signal.connect(self.calc_param_stgscan_workerXY_togui_meth)
        try: self.worker_stageXY.posX_indic_real_signal.disconnect(self.posX_indic_real)
        except TypeError: pass
        self.worker_stageXY.posX_indic_real_signal.connect(self.posX_indic_real)
        try: self.worker_stageXY.posY_indic_real_signal.disconnect(self.posY_indic_real)
        except TypeError: pass
        self.worker_stageXY.posY_indic_real_signal.connect(self.posY_indic_real)
        
        try: self.close_motorXY_signal.disconnect(self.worker_stageXY.close_motorXY)
        except TypeError: pass
        self.close_motorXY_signal.connect(self.worker_stageXY.close_motorXY)

        # Start thread
        
        self.thread_stageXY.start()
        
    def setupThread_apt(self):
        # thread for APT dll so not the XY stage but small K-cubes
    
        print('received signal apt')
        
        self.thread_apt = QThread()
        
        self.worker_apt = apt_worker_script2.Worker_apt( self.motor_phshft_ID, self.motor_rot_ID, self.motor_trans_ID, param_ini.motorX_ID, param_ini.motorY_ID, param_ini.dist_mm_typical_phshft, self.queue_disconnections, self.jobs_window, jobs_scripts, apt_worker_script2.params_mtr_set_func, time)
        
        self.worker_apt.moveToThread(self.thread_apt)
        
        self.thread_apt.started.connect(self.worker_apt.open_lib)
        
        self.worker_apt.pos_phshft_signal.connect(self.pos_ps_setxt)
        self.worker_apt.pos_trans_signal.connect(self.pos_ps_setxt)
        self.worker_apt.angle_rot_signal.connect(self.angle_polar_setVal_meth)
                
        self.home_motor_phshft_signal.connect(self.worker_apt.move_home_phshft)
        self.worker_apt.motor_phshft_homed_signal.connect(self.after_motor_phshft_homed_meth)
        self.worker_apt.motor_trans_homed_signal.connect(self.after_motor_trans_homed_meth)
        self.worker_apt.motor_polar_homed_signal.connect(self.after_motor_polar_homed_meth)
        
        self.move_motor_phshft_signal.connect(self.worker_apt.move_motor_phshft)
        self.move_motor_trans_signal.connect(self.worker_apt.move_motor_trans)
        self.move_motor_rot_polar_signal.connect(self.worker_apt.move_motor_rot_polar)
        
        self.worker_apt.apt_is_imported_signal.connect(self.apt_imported_after_meth)
        self.jobs_window.home_tl_rot_button.clicked.connect(self.worker_apt.move_home_polar)
        self.jobs_window.upld_tl_rot_button.clicked.connect(self.worker_apt.get_pos_polar)
        self.worker_apt.vel_acc_define_signal.connect(self.mtr_phsft_APT_def_velacc)
        self.worker_apt.vel_acc_bounds_signal.connect(self.worker_apt.vel_acc_set_func)
    
        # # self.worker_apt.get_bckg_signal.connect(self.worker_apt.background_get_func)
        # # self.worker_apt.buffer_signal.connect(self.worker_apt.buffer_wait_func)
        self.jobs_window.stop_apt_push.clicked.connect(self.worker_apt.stop_func)
        self.worker_apt.close_timer_sign.connect(self.worker_apt.close_timer)

        self.mtr_phshft_finishedmove_sgnl = self.worker_apt.motor_phshft_finished_move_signal
        self.change_phshft_sgnl = self.move_motor_phshft_signal
        
        # Start thread
        self.thread_apt.start()
        
        
    def setupThread_newport(self):
        # thread for newport motor(s)
        
        self.thread_newport = QThread()
        self.worker_newport = newport_worker_script.Worker_newport( self.queue_disconnections, self.jobs_window, param_ini.newportstage_comport, param_ini.motornewport_SN, jobs_scripts)
        self.worker_newport.moveToThread(self.thread_newport)
        self.thread_newport.started.connect(self.worker_newport.open_lib)
        self.jobs_window.home_newport_rot_button.clicked.connect(self.worker_newport.move_home_newport)
        self.worker_newport.esp_imported_signal.connect(self.esp_imported_after_meth)
        self.home_motor_newport_signal.connect(self.worker_newport.move_home_newport)
        self.move_motor_newport_signal.connect(self.worker_newport.move_motor_newport)
        self.close_newport_signal.connect(self.worker_newport.close_motor_newport)
        self.worker_newport.pos_newport_signal.connect(self.angle_polar_setVal_meth)
        self.jobs_window.upld_newport_rot_button.clicked.connect(self.worker_newport.get_pos_newport)

        # Start thread
        self.thread_newport.start()
        
    def setupThread_imic(self): # control of microscope basics : objectives etc.
                
        # QThread definition
        self.thread_imic = QThread()
        self.worker_imic = imic_worker_script2.Worker_imic(self.path_computer, self.queue_disconnections, self.motorZ_changeDispValue_signal, self.piezoZ_changeDispValue_signal, self.progress_piezo_signal,  param_ini.max_pos_Z_motor, param_ini.port_imic)
        self.worker_imic.moveToThread(self.thread_imic)
        
        self.thread_imic.started.connect(self.worker_imic.open_com) # because 2 imports in parallel was bugging
    
        self.worker_imic.progress_motor_signal.connect(self.posZ_slider.setValue)
        self.progress_piezo_signal.connect(self.posZ_slider_piezo.setValue)
        
        self.worker_imic.fltr_top_choice_set.connect(self.imic_fltr_top_changed_meth) # change the index in function of the index receive by the pyqtSignal
        self.worker_imic.fltr_bottom_choice_set.connect(self.imic_fltr_bottom_changed_meth)
        self.worker_imic.obj_choice_set.connect(self.imic_objTurret_changed_meth)
        
        self.worker_imic.posZ_mtr_str.connect(self.posZ_motor_edt_1.setValue)
        
        try:
            self.init_imic_button.clicked.disconnect()
        except TypeError: # if had no connection
            pass
        self.init_imic_button.clicked.connect(self.worker_imic.imic_ini)
        
        try:
            self.motorZ_move_signal.disconnect()
        except TypeError: # if had no connection
            pass
        self.motorZ_move_signal.connect(self.worker_imic.change_z_motor_meth)
        if not self.use_PI_notimic: # use imic
            self.worker_imic.posZ_piezo_str.connect(self.posZ_piezo_edt_1.setValue)

            try:
                self.piezoZ_move_signal.disconnect()
            except TypeError: # if had no connection
                pass
            self.piezoZ_move_signal.connect(self.worker_imic.change_z_piezo_meth)
            try:
                self.piezoZ_step_signal.disconnect()
            except TypeError: # if had no connection
                pass
            self.piezoZ_step_signal.connect(self.worker_imic.step_z_piezo_meth)
        
        try:
            self.obj_choice_signal.disconnect()
        except TypeError: # if had no connection
            pass
        self.obj_choice_signal.connect(self.worker_imic.obj_choice_meth)  
        try:
            self.fltr_top_ch_signal.disconnect()
        except TypeError: # if had no connection
            pass
        self.fltr_top_ch_signal.connect(self.worker_imic.filter_top_meth)
        try:
            self.fltr_bottom_ch_signal.disconnect()
        except TypeError: # if had no connection
            pass
        self.fltr_bottom_ch_signal.connect(self.worker_imic.filter_bottom_meth)
        try:
            self.update_Z_values_button.disconnect()
        except TypeError: # if had no connection
            pass
            
        self.worker_imic.imic_was_ini_signal.connect(self.imic_was_init)
        
        # Start thread
        self.thread_imic.start()
    
    def setupThread_scan(self): 
        # is recalled by define_if_new_scan
        
        # galvo mode
        # QThread definition
  
        self.thread_scan = QThread()
        self.worker_scan = scan_main_script.Worker_scan( self.queue_com_to_acq_process, self.queue_list_arrays, self.queue_disconnections, self.queue_special_com_acqGalvo_stopline, self.scan_thread_available_signal, self.piezoZ_step_signal )  # , EmittingStream, self.logger_window.normalOutputWritten
        
        self.worker_scan.moveToThread(self.thread_scan)
        
        # # self.thread_scan.started.connect(self.worker_scan.scan_galvos_meth)
        
        self.worker_scan.new_img_to_disp_signal.connect(self.display_img_gui)
        self.worker_scan.setnewparams_scan_signal.connect(self.setnewparams_scan_meth)
        self.kill_worker_scan_signal.connect(self.worker_scan.close_scanThread)
        self.scan_galvo_launch_processes_signal.connect(self.worker_scan.scan_galvos_meth)
                
        # Start QThread
        self.thread_scan.start()
        
    def setupThread_shutter(self):
        # is called in __init__
        
        # definition of thread
        self.thread_shutter = QThread()
        self.worker_shutter = shutter_worker_script2.Worker_shutter( queue.Empty, self.queue_disconnections, param_ini.read_termination_shutter, param_ini.write_termination_shutter, param_ini.ressource_shutter, param_ini.baud_rate_shutter_dflt, param_ini.baud_rate_shutter, param_ini.timeout_shutter, param_ini.t_understand_order, param_ini.t_shutter_trans)
        self.worker_shutter.moveToThread(self.thread_shutter)
        
        # connections
        self.thread_shutter.started.connect(self.worker_shutter.open_resource)
        
        self.open_close_shutter_signal.connect(self.worker_shutter.open_close_shutter_meth)
        self.worker_shutter.shutter_wasOpenClose_signal.connect(self.shutter_closed_chck.setChecked)
        self.worker_shutter.shutter_wasOpenClose_signal.connect(self.send_new_img_to_acq_suite)
        self.waitin_shutter_signal.connect(self.worker_shutter.waitin_shutter_meth)
        
        self.worker_shutter.shutter_here_signal.connect(self.shutter_here_meth)
        self.conn_instr_shutter_signal.connect(self.worker_shutter.set_instr)
        self.terminate_shutter_signal.connect(self.worker_shutter.terminate_shutter)
        
        # Start thread
        
        self.thread_shutter.start()
    
    def setupThread_PI(self):   
        # is called in __init__
        
        # definition of thread
        self.thread_PI = QThread()
        self.worker_PI = PI_worker_script.Worker_PI(self.queue_disconnections, self.jobs_window, self.progress_piezo_signal, self.piezoZ_changeDispValue_signal, param_ini.PI_pack)
        self.worker_PI.moveToThread(self.thread_PI)
        
        # connections
        self.thread_PI.started.connect(self.worker_PI.open_instr)
        self.worker_PI.PI_ishere_signal.connect(self.PI_imported_after_meth)
        self.close_PI_signal.connect(self.worker_PI.close_instr)
        
        if self.use_PI_notimic:
            # # self.worker_PI.posZ_piezo_str.connect(self.posZ_piezo_edt_1.setValue)
            try:
                self.piezoZ_move_signal.disconnect()
            except TypeError: # if had no connection
                pass
            self.piezoZ_move_signal.connect(self.worker_PI.move_motor_PI)
            try:
                self.piezoZ_step_signal.disconnect()
            except TypeError: # if had no connection
                pass
            self.piezoZ_step_signal.connect(self.worker_PI.step_motor_PI)

        # Start thread
        self.thread_PI.start()
        
    def setupThread_EOMph(self): 
    
        self.thread_EOMph = QThread()
        self.worker_EOMph = EOM_phase_ctrl_script.Worker_EOMph(self.queue_disconnections, param_ini.write_termination_EOMph, param_ini.EOMphAxis_comport, param_ini.EOMph_baudrate , param_ini.time_out_EOMph, param_ini.msg_getStatusEOM,  param_ini.code_resp_getstatus,  param_ini.msg_stopEOM, param_ini.code_resp_getHV,  param_ini.code_resp_getHVvar, param_ini.code_resp_getHVval, param_ini.code_resp_getHVval2, param_ini.code_resp_getHVval3, param_ini.msg_ONVoltageEOM , param_ini.msg_OFFVoltageEOM, param_ini.msg_SetVoltageEOM,  param_ini.msg_stModeEOM, param_ini.msg_getStatusVoltageEOM, param_ini.msg_ReadVoltageEOM, param_ini.code_resp_mode1, param_ini.code_resp_getHVon, time) # queue.Empty,  self.jobs_window
        self.worker_EOMph.moveToThread(self.thread_EOMph)
        
        self.worker_EOMph.EOMph_here_signal.connect(self.EOMph_afterhere_meth)
        # connections
        self.thread_EOMph.started.connect(self.worker_EOMph.connect_modulator)
        # # try:
        # #     self.jobs_window.com_EOMph_button.clicked.disconnect(self.worker_EOMph.get_status_modulator) # get
        # # except TypeError:
        # #     pass
        # # self.jobs_window.com_EOMph_button.clicked.connect(self.worker_EOMph.get_status_modulator) # get
        try:
            self.jobs_window.stop_EOMph_button.clicked.disconnect(self.worker_EOMph.stop_modulator) # stop
        except TypeError:
            pass
        self.jobs_window.stop_EOMph_button.clicked.connect(self.worker_EOMph.stop_modulator) # stop
        try:
            self.jobs_window.close_EOMph_button.clicked.disconnect(self.worker_EOMph.close_modulator) # close instr
        except TypeError:
            pass
        self.jobs_window.close_EOMph_button.clicked.connect(self.worker_EOMph.close_modulator) # close instr
        try:
            self.jobs_window.getstatHV_EOMph_button.clicked.disconnect(self.worker_EOMph.get_voltage_modulator) #  get HV
        except TypeError:
            pass
        self.jobs_window.getstatHV_EOMph_button.clicked.connect(self.worker_EOMph.get_voltage_modulator) #  get HV
        try:
            self.jobs_window.setHV_EOMph_button.clicked.disconnect(self.setHV_EOMph_meth) # set HV
        except TypeError:
            pass
        self.jobs_window.setHV_EOMph_button.clicked.connect(self.setHV_EOMph_meth) # set HV
        try:
            self.worker_EOMph.EOMph_setHV_signal.disconnect(self.worker_EOMph.set_voltage_modulator) # set HVsignal
        except TypeError:
            pass
        self.worker_EOMph.EOMph_setHV_signal.connect(self.worker_EOMph.set_voltage_modulator) # set HVsignal
        try:
            self.eomph_send_onoff_signal.disconnect(self.worker_EOMph.on_off_voltage_modulator) # if checked, ON
        except TypeError: pass
        self.eomph_send_onoff_signal.connect(self.worker_EOMph.on_off_voltage_modulator) # if checked, ON
        self.jobs_window.onoffHV_EOMph_chck.stateChanged.connect(self.on_off_voltage_eom_meth)
        try: self.eomph_stmodeAC_signal.disconnect(self.worker_EOMph.st_mode_modulator )
        except TypeError: pass
        self.eomph_stmodeAC_signal.connect(self.worker_EOMph.st_mode_modulator )
        try:
            self.jobs_window.stmode_EOMph_cbBx.currentIndexChanged.disconnect(self.stmode_EOMph_after_meth) # mode
        except TypeError:
            pass
        self.jobs_window.stmode_EOMph_cbBx.currentIndexChanged.connect(self.stmode_EOMph_after_meth) # mode
        try:
            self.worker_EOMph.EOMph_msg_signal.disconnect(self.jobs_window.msg_EOMph_pltxtedt.appendPlainText) # msg plain
        except TypeError:
            pass
        self.worker_EOMph.EOMph_msg_signal.connect(self.jobs_window.msg_EOMph_pltxtedt.appendPlainText)  # msg plain
        
        self.worker_EOMph.EOM_voltget_signal.connect(self.jobs_window.valHV_EOMph_spbx.setValue) # int
#self.mdltr_voltset_dispval_meth)
        
        # Start thread
        self.thread_EOMph.start()
        
        ## improve display img meth
  
    @pyqtSlot()        
    def roi_pg_after_meth(self):
        
        curr_row = self.name_img_table.currentRow() if self.name_img_table.currentRow() !=-1 else self.name_img_table.rowCount() - 1
        if int(self.name_img_table.item(curr_row , 1).text()) == 1: # first plot
            self.roi_pg_current = 0
            roi_pg = self.roi_left_pg
            vb_plot = self.vb_plot_img
            vb_pg = self.vb_real_pg[0]
     
        else:  # # 2nd plot
            self.roi_pg_current = 1
            roi_pg = self.roi_right_pg
            vb_plot = self.vb_plot_img_2
            vb_pg = self.vb_real_pg[1]
        
        pg_plot_scripts.roi_add(vb_plot, roi_pg, vb_pg, self.graph2TxtROI, pyqtgraph)
    
    def ext_step_func(self, curr_row):
        pb = 0
        try: stepX_um = stepY_um = float(self.name_img_table.item(curr_row , 4).text().split('_')[1].split('um')[0])
        except ValueError: pb=1
            # # ValueError: could not convert string to float: 'xxus'
        if pb:
            try: 
                step = self.name_img_table.item(curr_row , 4).text().split('_')[1].split('X') # # step not square
                stepX_um = float(step[0]); stepY_um = float(step[1][:-2])
            except ValueError:
                try: self.name_img_table.item(curr_row , 4).text().split('_'); stepX_um = stepY_um=1;
                except ValueError: print('select a row in the tableWidget of scan galvos !'); stepX_um= stepY_um =None
        return [stepX_um, stepY_um]
    
    @pyqtSlot()        
    def def_scan_roi_pg_meth(self):  
        if self.roi_pg_current == 0: # first plot
            roi_pg = self.roi_left_pg
            vb_pg = self.vb_real_pg[0]
     
        else:  # # 2nd plot
            roi_pg = self.roi_right_pg
            vb_pg = self.vb_real_pg[1]
            
        offX, offY, numPXx, numPXy, win_X, win_Y = pg_plot_scripts.roi_use(roi_pg, vb_pg, self.graph2TxtROI)
        
        curr_row = self.name_img_table.currentRow() if self.name_img_table.currentRow() !=-1 else self.name_img_table.rowCount() - 1
        
        a = self.ext_step_func( curr_row)
        if a[0] is not None: stepX_um, stepY_um = a
        else: return
            
        pb = 0    
        try: sizeX_um = sizeY_um = float(self.name_img_table.item(curr_row , 4).text().split('_')[0].split('um')[0])
        except ValueError:  pb=1
        if pb:
            try: 
                size = self.name_img_table.item(curr_row , 4).text().split('_')[0].split('X') # # size not square
                sizeX_um = float(size[0]); sizeY_um = float(size[1][:-2]) 
            except ValueError:
                # # ValueError: could not convert string to float: 'xxus'
                print('select a row in the tableWidget of scan galvos !')
                return
            
        # # sizeX_um = float(self.name_img_table.item(curr_row , 4).text().split('_')[0].split('X')[0])
        # # sizeY_um = self.name_img_table.item(curr_row , 4).text().split('_')[0].split('X')[1]
        # # sizeY_um = float(sizeY_um[:len(sizeY_um)-2])
        offsetX_mm = float(self.name_img_table.item(curr_row , param_ini.posoffXY_wrt0_tablemain).text().split('; ')[0])/1000
        offsetY_mm = float(self.name_img_table.item(curr_row , param_ini.posoffXY_wrt0_tablemain).text().split('; ')[1])/1000
        
        curr_row_img = curr_row + self.offset_table_img
        paquet_received = self.list_arrays[curr_row_img]
        [px_X, px_Y] = paquet_received.shape # # real size in PX because the disp img might be binned
        
        print(offX, offY, numPXx, numPXy, px_X, px_Y ) #
        if self.up_offset_pg:
            self.up_offset_pg = False
            oXt = (offX+self.offsetX_pg_curr)
            oYt = (offY+self.offsetY_pg_curr)
        else:
            oXt = offX
            oYt = offY
            
        if self.mode_scan_box.currentIndex() == 0: # dig galvos
            oX =  math.cos(self.rotate)*oXt + math.sin(self.rotate)*oYt #math.cos(self.rotate)*oXt + math.sin(self.rotate)*oYt
            oY = math.sin(self.rotate)*oXt - math.cos(self.rotate)*oYt #-math.sin(self.rotate)*oXt + math.cos(self.rotate)*oYt
        else:
            oX = oXt
            oY = oYt
        
        self.offsetX_mm_spnbx.setValue(offsetX_mm + oX*stepX_um/1000) # mm
        self.offsetY_mm_spnbx.setValue(offsetY_mm + oY*stepY_um/1000) # mm
        self.offsetX_pg_curr = offX
        self.offsetY_pg_curr = offY
        
        if numPXx/px_X*sizeX_um != numPXy/px_Y*sizeY_um:
            self.square_img_chck.setChecked(False)
        self.sizeX_um_spbx.setValue(numPXx/px_X*sizeX_um) # um 
        self.sizeY_um_spbx.setValue(numPXy/px_Y*sizeY_um) # um
        
        self.stepX_um_edt.setValue(stepX_um) # um
        self.stepY_um_edt.setValue(stepY_um) # um
            
    @pyqtSlot(int)        
    def updateClrmap_meth(self, clrmap_nb):
        # # slot clrmap_choice_combo.currentIndexChanged (see ini pg)
        # # or called directly
        
        if clrmap_nb >= 0: # # not called directly
            widget_caller = self.sender()
            # if isinstance(widget_caller, QtWidgets.QComboBox):
            name = widget_caller.objectName()
            # # clrmap_nb = widget_caller.currentIndex()
            if name == 'clrmap_choice_combo': # # left
            # update colormap on plot img 1 (pyqtgraph) 
                img_item_pg = self.img_item_pg
                hist = self.hist_1
                self.clrmap_nb = self.cmap_curr[0]= clrmap_nb
                #LUT = self.LUT
            else: # # right
                img_item_pg = self.img_item_pg_2
                hist = self.hist_2
                self.clrmap_nb_2 = self.cmap_curr[1] = clrmap_nb
                #LUT = self.LUT_2
            rg = 1 # # one update
        else: # # direct call
            rg = 2 # # both update
            img_item_pg = self.img_item_pg # # left first
            hist = self.hist_1
            clrmap_nb = self.clrmap_choice_combo.currentIndex()
            #LUT = self.LUT
        
        for k in range(rg):
            if k>0: # # both update
                img_item_pg = self.img_item_pg_2
                hist = self.hist_2
                clrmap_nb = self.clrmap2_choice_combo.currentIndex()
                #LUT = self.LUT_2

            if clrmap_nb == 0: # # grey
                img_item_pg.setLookupTable(self.lut_grey)
                hist.gradient.setColorMap(self.cmap_grey_pg)
                #LUT = self.lut_grey
                hist.autoHistogramRange()
                
            elif clrmap_nb == 1: # # fire
                img_item_pg.setLookupTable(self.lut_fire)
                hist.gradient.setColorMap(self.cmap_fire_pg)
                #LUT = self.lut_fire
                hist.autoHistogramRange()
            
            elif clrmap_nb == 2:
                hist.gradient.setColorMap(self.cmap_cubehelix_pg)
                img_item_pg.setLookupTable(self.lut_cubehelix)
                #LUT = self.lut_cubehelix
                
            elif clrmap_nb == 3: # ocean
                hist.gradient.setColorMap(self.cmap_ocean_pg)
                img_item_pg.setLookupTable(self.lut_ocean)
                #LUT = self.lut_ocean
            
            elif clrmap_nb == 4: # kryptonite
                hist.gradient.setColorMap(self.cmap_krypto_pg)
                img_item_pg.setLookupTable(self.lut_kryptonite)
                #LUT = self.lut_kryptonite
                
            elif clrmap_nb == 5: # PiYG
                hist.gradient.setColorMap(self.cmap_PiYG_pg)
                img_item_pg.setLookupTable(self.lut_PiYG)
                #LUT = self.lut_PiYG
            
    
    @pyqtSlot()        
    def updateIsocurve_meth(self):
        # update isoline on plot img 1 (pyqtgraph)
        # # print('in iso curve\n')
        # # global isoLine_pg, iso_pg
        self.iso_pg.setLevel(self.isoLine_pg.value())
        # # iso_pg.setLevel(isoLine_pg.value())
        # # print('iso', self.isoLine_pg.value())
    
    def mouse_util(self, pos):
    
        # # print(pos)
        scenePos = self.img_item_pg.mapFromScene(pos)
        scenePos2 = self.img_item_pg_2.mapFromScene(pos)
        disprow, dispcol = int(scenePos.y()), int(scenePos.x())
        
        # # print(scenePos.y(), scenePos.x())
        
        data = self.img_item_pg.image  # or use a self.data member
        
        if data is None: 
            nRows = 400; nCols = 400; value = 0
            
        else:
            nRows, nCols = data.shape
        
        row = dispcol # trnspose + inversion
        col =  disprow # trnspose + inversion
        condleft = (0 <= row < nRows) and (0 <= col < nCols)
        
        if condleft:
            r = row # trnspose + inversion
            c =  col # trnspose + inversion
            return 1, r, c, dispcol, disprow, data, nRows, nCols
        else: # perhaps right img (#2)
            disprow2, dispcol2 = int(scenePos2.y()), int(scenePos2.x())
            data_2 = self.img_item_pg_2.image  # or use a self.data member
            if data_2 is None: 
                nRows_2 = 400; nCols_2 = 400; value2 = 0
            else:
                nRows_2, nCols_2 = data_2.shape
            r = dispcol2 # trnspose + inversion
            c =  disprow2 # trnspose + inversion
            if not ((0 <= r < nRows_2) and (0 <= c < nCols_2)): return 0, 0,0,0,0,0,0,0
            else: return 2, r, c, dispcol2, disprow2, data_2, nRows_2, nCols_2
        
    
    # # @pyqtSlot(pyqtgraph.QtCore.QPointF) # @pyqtSlot(QtCore.QPointF)   
    def mouseMoved(self, pos):
        
        condleft, r, c, dispcol, disprow, data, _,_ = self.mouse_util( pos)
        
        if condleft==1:
            if not(data is None): 
                value = data[r, c]
                # # text = ("({:d}, {:d}), {!r}".format(row, col, value))
                intens = '%d' % round(value)

        elif condleft == 2: # perhaps right img (#2)
            if not(data is None): 
                value2 = data[r, c]
                intens = '%d' % round(value2)
        pos_txt = '(%d, %.d)' % (dispcol, disprow) # x, y
        
        if (not condleft or data is None):
            intens = "no data at cursor"
            pos_txt = "no data at cursor"
                
        self.graph1TxtMousePos.setText(intens, size = '9pt', bold=True, color = 'c') # one of: r, g, b, c, m, y, k, w, or RGB
        self.graph2TxtMousePos.setText(pos_txt, size = '9pt', bold=True, color = 'c')
        
    def mouseClicked(self, ev):
        # # left click
        # print(ev.pos(), ev.scenePos())
        if ev.button() == QtCore.Qt.LeftButton:
        
            try: cc, _, _, _, _, _, nbX, nbY = self.mouse_util(ev.pos())
            except AttributeError: return
            
            if cc >0:
                curr_row = self.name_img_table.currentRow() if self.name_img_table.currentRow() !=-1 else self.name_img_table.rowCount() - 1
                if curr_row == -1: return
                a = self.ext_step_func( curr_row)
                if a[0] is not None: stepX_um, stepY_um = a
                else: return 
                
                try: x, y = self.graph2TxtMousePos.text.split(',')
                except ValueError: return
                x=float(x[1:]); y=float(y[:-1]);
                # print(x,y)
                xrel = x-round(nbX/2)  
                yrel = y-round(nbY/2)
                
                bn_str = self.name_img_table.item(curr_row , param_ini.pos_reducnblinesdisp_wrt0_tablemain).text()
                # self.name_img_table.item(self.name_img_table.currentRow(), param_ini.pos_reducnblinesdisp_wrt0_tablemain).text()
                bn = 1/(1-1/int(bn_str)) if (bn_str.isdigit() and int(bn_str) > 1) else 1
                if self.stage_scan_mode==1: signX = 1;signY = -1 # stg
                else: signX =-1; signY = -1 # dig galv
                nbpxX=signX*int(round(max(1,bn )*xrel)); distX=nbpxX*stepX_um
                nbpxY=signY*int(round(max(1,bn )*yrel)); distY=nbpxY*stepY_um
                if self.stage_scan_mode==3: 
                    # signX =1/2**0.5; signY = 1/2**0.5 # anlg galv
                    stprot = (stepX_um**2+stepY_um**2)**0.5
                    nbpxX = -(math.cos(self.rotate)*nbpxX - math.sin(self.rotate)*nbpxY)
                    distX=nbpxX*stprot
                    nbpxY = math.sin(self.rotate)*nbpxX + math.cos(self.rotate)*nbpxY
                    distY=nbpxY*stprot
                print( 'TOT(%d, %d px, STP %.2fX%.2f_um/px, bin_disp %g)' % (nbX,  nbY, stepX_um, stepY_um, bn))
                print( 'YOU should do: dX = %.1fum (%dpx); dY = %.1fum (%dpx)' % ( distX, nbpxX, distY, nbpxY))
                
class Jobs_GUI(QSecondWindow, Ui_JobsWindow):
    """
    other small GUI for jobs
    """
    
    def __init__(self, parent=None):
        
        super(Jobs_GUI, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setupUi(self)
        
        # when you want to destroy the dialog set this to True
        self._want_to_close = False
        self.setWindowState(QtCore.Qt.WindowMinimized)
        
    def closeEvent(self, evnt): # method to overwrite the close event, because otherwise the object is no longer available
        if self._want_to_close:
            super(Jobs_GUI, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setWindowState(QtCore.Qt.WindowMinimized)
            
    
class QTextEditLogger(QtWidgets.QDialog, QtWidgets.QPlainTextEdit):
    def __init__(self, parent):
        super().__init__()
        self.setWindowTitle('Logger')
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)
        self._want_to_close = False
        # # color_palette = self.widget.palette()
        # # color_palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
        # # color_palette.setColor(QtGui.QPalette.Base, QtCore.Qt.black)
        # # self.widget.setPalette(color_palette)
        self.widget.setStyleSheet(
        """QPlainTextEdit {background-color: rgb(0, 0, 0);
                           color: rgb(255, 255, 255);
                           font-family: Courier;}""")
        
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)
        self.move(10, 10) # from left top corner (px)
        self.resize(500,900)

    # # def emit(self, record):
    # #     msg = self.format(record)
    # #     self.widget.appendPlainText(msg)
    
    def closeEvent(self, evnt): # method to overwrite the close event, because otherwise the object is no longer available
        if self._want_to_close:
            super(QTextEditLogger, self).closeEvent(evnt)
        else:
            evnt.ignore()
            self.setWindowState(QtCore.Qt.WindowMinimized)
        
    def normalOutputWritten(self, text):
        # for the logging 
        # # self.jobs_window.exec_code_edt.appendPlainText(text)
        plainTxtWidg = self.widget # # self.jobs_window.exec_code_edt
        cursor = plainTxtWidg.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        plainTxtWidg.setTextCursor(cursor)
        plainTxtWidg.ensureCursorVisible()
        
# import logging
# Uncomment below for terminal log messages
# logging.basicConfig(level=logging.DEBUG, format=' %(asctime)s - %(name)s - %(levelname)s - %(message)s')    


class EmittingStream(QtCore.QObject):

    textWritten = pyqtSignal(str)

    def write(self, text):
        self.textWritten.emit(str(text))



