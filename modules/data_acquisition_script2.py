# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

import multiprocessing

class acq_data(multiprocessing.Process):

    """Process acq with galvos"""

    def __init__(self, time_out, queue_acq_fill, min_val_volt_list, max_val_volt_list, delay_trig,  digGalvo_timebase_src_end, trig_src, time_out_sync, queue_com_to_acq_process, scan_mode, queue_special_com_acqGalvo_stopline, sideAcq_writeAcq_pipe, sideWrite_writeAcq_pipe, write_scan_before, piezoZ_step_signal, num_dev_anlgTrig, num_dev_watcherTrig, num_dev_AO, new_img_flag_queue, path_computer):

        multiprocessing.Process.__init__(self)

        self.time_out = time_out # for read AI
        self.queue_acq_fill = queue_acq_fill
        
        self.min_val_volt_list = min_val_volt_list; self.max_val_volt_list = max_val_volt_list

        self.delay_trig = delay_trig
        
        self.digGalvo_timebase_src_end = digGalvo_timebase_src_end; self.trig_src = trig_src
        self.time_out_sync = time_out_sync; 
        
        self.queue_com_to_acq_process = queue_com_to_acq_process
        
        self.scan_mode = scan_mode
        self.queue_special_com_acqGalvo_stopline = queue_special_com_acqGalvo_stopline
        self.sideAcq_writeAcq_pipe = sideAcq_writeAcq_pipe
        self.sideWrite_writeAcq_pipe = sideWrite_writeAcq_pipe
        self.write_scan_before = write_scan_before
        self.num_dev_anlgTrig = num_dev_anlgTrig ; self.num_dev_watcherTrig = num_dev_watcherTrig; self.num_dev_AO = num_dev_AO
        self.new_img_flag_queue = new_img_flag_queue # # just here to pass parameters to GUI
        self.path_computer = path_computer
     
    def run(self):

        def acqGalvo_stopline_meth(queue_special_com_acqGalvo_stopline, queue_acq_fill, queue_com_to_acq_process, queueEmpty, analog_output_daq_to_galvos, anlg_galvos):
            # # called inside this process
            
            send_stop_inline = ignore_watcher_undone = False # init
            try: # raises error if nothing to read
                msg = queue_special_com_acqGalvo_stopline.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
            except queueEmpty:
                pass # do nothing
                
            else: # received message
                if msg == 'stop':
                    print('stop signal in-line from the GUI (dataAcq.)') 
                    send_stop_inline = 1
            if send_stop_inline:
                queue_acq_fill.put([-2]) # communicate the stop in-line to fill_array process
                msg_list = [] # inside var
                if anlg_galvos:  # new anlg galvos
                    warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                    analog_output_daq_to_galvos.stop()
                    warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)
                    ignore_watcher_undone = True

                # #     # re-init the galvos
                # #     write_task.galvo_goToPos_byWrite(nidaqmx, analog_output_daq_to_galvos, meth_write, 4, y_fast, volt_begin_fast, volt_pos_min_slow, sample_rate_galvos, param_ini.min_val_volt_galvos, param_ini.max_val_volt_galvos, bits_write, param_ini.use_volt_not_raw_write, time, numpy)
                # #     write_task.write_arrays_AO(analog_output_daq_to_galvos, meth_write, write_scan_before, param_ini.use_velocity_trigger, unidirectional, param_ini.angle_rot_degree_new_galvos, cos_angle, sin_angle, one_scan_pattern_vect, line_slow_daq_vect, line_slow_daq_vect_last, correct_unidirektionnal, shape_reverse_movement, sample_rate_galvos, y_fast, nb_pts_daq_one_pattern, nb_line_prewrite, param_ini.tolerance_nb_write_to_stop, nidaqmx, numpy, time, sideWrite_writeAcq_pipe, param_ini.use_volt_not_raw_write, bits_write, daq_pos_max_slow, daq_pos_min_slow, nb_px_slow)
                try: # empty the order queue, in case there is an order of launch image remaining  
                    while True:
                        msg = queue_com_to_acq_process.get_nowait() # raise queueEmpty error if empty, otherwise continue
                        if msg[0] == -1:
                            msg_list.append(msg)
                            
                except queueEmpty: # when the queue is emptied
                    if len(msg_list) > 0: # a message of poison-pill has been read : re-put it in the queue
                        for msg in msg_list:
                            queue_com_to_acq_process.put(msg)
                            
            return send_stop_inline, ignore_watcher_undone
        
        try:
            
            from modules import daq_control_mp2, param_ini, galvos_util_scripts, master_trig_ctrl_scrpts, write_task, new_galvos_funcs
            # # new_galvos_funcs is used by anlg galvos, and dig galvos callbacks
            
            print('Importing NIDAQmx in data_acquisition...')
            import nidaqmx
            import nidaqmx.stream_readers, nidaqmx.system # mandatory if read_stream
            print('in worker_dataAcq. : NIDAQmx ok')
            
            import time, numpy, warnings
            from queue import Empty as queueEmpty
        
            system = nidaqmx.system.System.local()
            # # print(system.driver_version)
            i = 0; dev_list=[]
            for device in system.devices:
                dev_list.append(nidaqmx.system.Device(device.name))
                
            self.trig_src[0] = dev_list[self.trig_src[0]-1]  # the whole device
            # # self.trig_src is [device_used_AIread, param_ini.trig_src_name_dig_galvos], for digital galvos
            
            fct_incr = 1.05
            verbose = 0 # print or not
            analog_output_daq_to_galvos = None # init
            analog_input = None # init
            ai_trig_control = None # init
            anlgCompEvent_watcher_task = None # init
            ao_dumb = None # init
            name_list_AI_tasks = param_ini.name_list_AI_tasks
            name_list_trigctrl_tasks = param_ini.name_list_trigctrl_tasks
            name_list_AO_tasks = param_ini.name_list_AO_tasks
            name_list_watcher_tasks = param_ini.name_list_watcher_tasks
            name_list_wr_dumb_tasks = param_ini.name_list_wr_dumb_tasks
            device_to_use_AO = device_to_use_anlgTrig=device_to_use_watcherTrig= export_trigger = use_dig_fltr_onAlgCmpEv = mtr_trigout_cntr_task = nametask_mtr_trigout_list = min_pulse_width_digfltr_6259 = time_comp_fltr = meas_linetime_saved = None
            use_dig_galvos = clear_arr = break_here = disp_info_flag = False # disp info shift array on 1st acq
            read = 0 ; duration_one_line_real = method_watch = send_stop_inline = 0 # init
            
            msg_warning_ifstop_taskundone = param_ini.msg_warning_ifstop_taskundone
            if not param_ini.DI_parallel_watcher: # # used in callback galvos
                sender_read_to_trigger = receiver_trigger_to_read = trigWatcher_process = None
            # # otherwise you need to define it in go_scan_galvos (parent func)
                    #     receiver_read_to_trigger, sender_read_to_trigger

            if self.scan_mode == 1 : # digital galvo_Scan 
                print('Importing serial in data_acquisition...')
                import serial
                print('serial ok.')          
                if not param_ini.dll_diggalvos_timing: from scipy import optimize
                else: optimize = None
                
                dig_galvo, dll_tuple = galvos_util_scripts.init_dig_galvos(serial, param_ini.baud_rate_dig_galvos, param_ini.timeout_dig_galvos, param_ini.ressource_dig_galvos, param_ini.dll_diggalvos_timing, self.path_computer)
                
            elif self.scan_mode == -2 : # analog galvo_Scan
                dig_galvo = None
                    
            ## input galvo
            
            index_acq_current = 1 
            
            while True: #index_acq_current <= nb_img_max: 
            
                print('In data_acquisition galvos %d, reading for job if any ...' % self.scan_mode) 
                job = self.queue_com_to_acq_process.get() # blocking
                # job is a list of instruction
                
                if job[0] < 1: # do not continue
                
                    if job[0] == -1:
                        print('Poison-pill in data_acquisition') 
                        self.queue_acq_fill.put([-1]) # communicate the poison-pill to fill_array process
                        if (self.scan_mode == -2 and not self.write_scan_before): # new anlg galvos
                            self.sideAcq_writeAcq_pipe.send([-1])
                            
                        break # outside big while loop, end process
                        
                    else:
                        print('Order to stop detected in data_acquistion') # if = 0
                        if job[0] == 0:
                            self.queue_acq_fill.put([0]) # communicate the stop to fill_array process
                        elif job[0] == -2: # stop in-line (NOT USED NORMALLY)
                            send_stop_inline = 0
                            self.queue_acq_fill.put([-2]) # communicate the stop in-line to fill_array process
                        # do nothing
                        if (self.scan_mode == -2 and not self.write_scan_before): # new anlg galvos
                            self.sideAcq_writeAcq_pipe.send([job[0]])
                            
                        continue # to the beginning of 'while' loop
                        
                else: # 1 = continue scan normally
                    
                    # # len_list = 29
                    if (len(job) > 1 and job[0] != 7): # # and len(job[1]) == len_list): # scan with new parameters
                
                        list_param_scan = job[1]
                        
                        # # print('len(list_param_scan)',len(list_param_scan))
                        
                        pmt_channel_list = list_param_scan[0]
                        sample_rate_imposed = list_param_scan[1]
                        time_by_point = list_param_scan[2]
                        update_time =  list_param_scan[3] 
                        obj_mag = list_param_scan[4] 
                        center_x = list_param_scan[5]  
                        center_y = list_param_scan[6]  
                        new_sz_x_um =  list_param_scan[7] # new_szX in um !
                        new_sz_y_um = list_param_scan[8] 
                        nb_px_x = list_param_scan[9] 
                        nb_px_y = list_param_scan[10] 
                        nb_img_max =  list_param_scan[11] 
                        unidirectional =  list_param_scan[12] 
                        y_fast = list_param_scan[13]  
                        nb_bins_hist =  list_param_scan[14] 
                        real_time_disp =  list_param_scan[15] 
                        clrmap_nb = list_param_scan[16] 
                        delete_px_fast_begin = list_param_scan[17] 
                        delete_px_fast_end = list_param_scan[18] 
                        delete_px_slow_begin = list_param_scan[19] 
                        delete_px_slow_end = list_param_scan[20] 
                        skip_behavior = list_param_scan[21]
                        list_galvo_scan = list_param_scan[22]
                        nb_accum = list_param_scan[23]
                        scan_xz = list_param_scan[24]
                        external_clock =  list_param_scan[25]
                        time_base_ext = list_param_scan[26]
                        offset_scan_list = list_param_scan[27]
                        autoscalelive_plt = list_param_scan[28]
                        lock_timing = list_param_scan[29]
                        params_an_galvos = list_param_scan[-2]
                        ishg_EOM_AC = list_param_scan[-1][:] # be sure that's a new el.
                        
                        if ishg_EOM_AC[0]: from modules import jobs_scripts # # flag
                        else: jobs_scripts = None
                                       
                        pause_trigger_diggalvo = skip_behavior[1] if self.scan_mode == 1 else 0 # if dig galvos
                        self.method_watch = 7 if (skip_behavior[2] == 0 ) else min(6, param_ini.method_watch) # acqline_galvo_mode
                        method_watch = self.method_watch 
                        use_callbacks = False if self.method_watch == 7 else param_ini.use_callbacks
                        # # for it not to be 7, which would mean 1 contrary to order
                        oneline_calib = False # dflt
                        mtr_trigout_retriggerable = 1 # dflt
                        # # print('mag11', obj_mag)

                        if (not time_base_ext and not pause_trigger_diggalvo):
                            skip_behavior[0] = skip_behavior[0]/10 # nb_skip
                            # # adjust the nb_skip of digital galvos, because it's different if it uses the internal clock of the DSP or not
                        # # dig_galvos_use serves for dadcontrolmp2.trig_watcher_ctrl_def_galvoscn (both galvos)
                        if self.scan_mode == -1: # static acq.
                            dig_galvos_use = skip_behavior[1] =0 # 0 
                        elif (pause_trigger_diggalvo and skip_behavior[2] == 0 ):
                            dig_galvos_use = 2 # use pause trigger and line time meas.
                        elif (pause_trigger_diggalvo and skip_behavior[2] >= 1 ): 
                            dig_galvos_use = 1 # use callback (not fast enough?)
                            lvl_trig_not_win = 1 # # trigger not sent on flybacks for dig galvos
                            skip_behavior.append((unidirectional and not(lvl_trig_not_win)))
                        else:
                            dig_galvos_use = 0 # 0 for classic method (st trigger, preset skip sync)
                            
                        if (dig_galvos_use or self.scan_mode == -2): # dig_galvos_use was 2, or anlg galvos
                            # # dig_galvos_use = 0 # static OR classic dig galvos with start trigger
                            # # dig_galvos_use = 2 # use pause trigger meas. with dig galvos
                            # #   dig_galvos_use = 1 # use pause trigger that callbacks with dig galvos
                            nametask_mtr_trigout_list = param_ini.nametask_mtr_trigout_list # # for ishg fast
                        else: # # if self.scan_mode == -1: # static, or dig galvos classic
                            method_watch = 0
                            nametask_mtr_trigout_list = None

                        cond_read_counter_line_time = ((self.scan_mode == 1 and pause_trigger_diggalvo and dig_galvos_use == 2) or (self.scan_mode == -2 and method_watch == 7)) # # is a condition
                        
                        if not (type(params_an_galvos) in (float, int)): [eff_wvfrm_an_galvos, mult_trig_fact, trig_perc_hyst, off_fast_anlgGalvo, off_slow_anlgGalvo, fact_buffer] = params_an_galvos 
                        else: mtr_trigout_retriggerable = -1
                        
                        # # print('skip_behavior', skip_behavior, cond_read_counter_line_time, method_watch, dig_galvos_use)     
                        
                        if (self.scan_mode == 1 and time_base_ext): # # dig galvos
                            sample_rate = param_ini.clock_galvo_digital/max(param_ini.min_timebase_div, round(param_ini.clock_galvo_digital/sample_rate_imposed))
                        else: sample_rate = sample_rate_imposed
                        
                        if scan_xz:
                            step_Z_mm = new_sz_y_um*1000/nb_px_y
                            new_sz_y_um = 0 # acts as static
                        
                        fact_data = param_ini.fact_data
                        update_time00 = update_time
                        if (self.scan_mode == -1 or (self.scan_mode == 1 and (dig_galvos_use != 1 or method_watch in (0,7)))): # digital galvos (0) or static (-1), readlines or static
                            nb_loop_line = nb_px_slow = nb_px_y

                            analog_input, _, _, _, _, _, time_by_point, update_time, sample_rate, AI_bounds_list, meth_read, params_galvos, nb_px_fast, [ishg_EOM_AC_insamps, mtr_trigout_cntr_task, ishg_EOM_AC2, tuple_EOMph] = daq_control_mp2.init_daq(nidaqmx, pmt_channel_list, self.min_val_volt_list, self.max_val_volt_list, self.digGalvo_timebase_src_end, self.trig_src, self.delay_trig, self.scan_mode, sample_rate, time_by_point, time_by_point*nb_px_slow*nb_px_x, numpy, nb_px_x, 0, 0, 0, 0, dev_list, update_time, (None, nb_px_slow),  param_ini, external_clock, dig_galvos_use, time_base_ext, method_watch, analog_input, ai_trig_control, name_list_AI_tasks, name_list_trigctrl_tasks, ishg_EOM_AC, jobs_scripts, mtr_trigout_cntr_task, nametask_mtr_trigout_list, mtr_trigout_retriggerable, lock_timing) 
                            # sample_rate, time_by_px, time_expected_sec, numpy, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, dev_list, update_time
                            
                            duration_one_line_imposed = time_by_point*nb_px_x
                            callback=None; pack_params_new_galvos = [self.trig_src[0], self.trig_src[0], param_ini.num_ctrdflt]
                            
                        else: # analog new galvos OR dig galvos callback
                        
                            # # print('walla/n',self.num_dev_watcherTrig, self.num_dev_anlgTrig, dev_list)
                            device_to_use_AO, factor_trigger, trig_src_name_slave, samp_src_term_slave, trig_src_name_master, samp_src_term_master_toExp, ai_trig_src_name_master, sin_angle , cos_angle, duration_one_line_real, self.write_scan_before, nb_hysteresis_trig_subs, sample_rate_min, sample_rate_min_other, trig_src_end_master_toExp, time_expected_sec, duration_one_line_imposed, sample_rate_AO_wanted, nb_px_fast, nb_px_slow, nb_loop_line, nb_pts_daq_one_pattern, term_trig_other, term_trig_name, trig_src_end_chan, nb_AI_channels, export_smpclk, export_trigger, pack_params_new_galvos, min_val_volt_galvos, max_val_volt_galvos, one_scan_pattern_vect, line_slow_daq_vect, line_slow_daq_vect_last, daq_pos_max_slow, daq_pos_min_slow, init_pos_volt, time_comp_fltr, min_pulse_width_digfltr_6259, use_dig_fltr_onAlgCmpEv, skip_behavior  = new_galvos_funcs.params_newGalvos(sum(pmt_channel_list), unidirectional, self.num_dev_AO, self.trig_src[0], dev_list[self.num_dev_anlgTrig], dev_list[self.num_dev_watcherTrig], param_ini.correct_unidirektionnal, param_ini.export_smpclk, param_ini.export_trigger, param_ini.DO_parallel_trigger, self.write_scan_before, center_x*1000, center_y*1000, new_sz_x_um, new_sz_y_um, nb_px_x, nb_px_y, obj_mag, param_ini.scan_lens_mm, y_fast, time_by_point, galvos_util_scripts, eff_wvfrm_an_galvos, dev_list, dig_galvos_use, method_watch, update_time, mult_trig_fact, trig_perc_hyst, skip_behavior, off_fast_anlgGalvo, off_slow_anlgGalvo, fact_buffer, warnings, numpy, param_ini, write_task, daq_control_mp2, system)
                            # # # (nb_pmt_channel, unidirectional, num_dev_AO, device_to_use_AI, device_to_use_anlgTrig, device_to_use_watcherTrig, correct_unidirektionnal, export_smpclk, export_trigger, DO_parallel_trigger, write_scan_before, offset_x_um, offset_y_um, size_x_um, size_y_um, nb_px_X, nb_px_Y, obj_mag, scan_lens_mm, y_fast, time_by_point, galvos_reversing_time_script, eff_wvfrm_an_galvos, dev_list, use_dig_galvos, method_watch, update_time, mult_trig_fact, trig_perc_hyst, skip_behavior, off_fast_anlgGalvo, off_slow_anlgGalvo, fact_buffer, warnings, math, numpy, param_ini, write_task, daq_control_mp2, system)
                            # # skip_behavior is [nb_skip,  pause_trigger_diggalvo,  callback_notmeasline, unirek_skip_half_of_lines]

                            analog_input, ai_trig_control, _, _, _, _, time_by_point, update_time, sample_rate, AI_bounds_list, meth_read, params_galvos, nb_px_fast, [ishg_EOM_AC_insamps, mtr_trigout_cntr_task, ishg_EOM_AC2, tuple_EOMph] = daq_control_mp2.init_daq(nidaqmx, pmt_channel_list, self.min_val_volt_list, self.max_val_volt_list, self.digGalvo_timebase_src_end, self.trig_src, self.delay_trig, self.scan_mode, sample_rate, time_by_point, time_expected_sec, numpy, nb_px_fast, 0, 0, 0, 0, dev_list, update_time, pack_params_new_galvos, param_ini, external_clock, dig_galvos_use, time_base_ext, method_watch, analog_input, ai_trig_control, name_list_AI_tasks, name_list_trigctrl_tasks, ishg_EOM_AC, jobs_scripts,  mtr_trigout_cntr_task, nametask_mtr_trigout_list, mtr_trigout_retriggerable, lock_timing) 
                            # sample_rate, time_by_px, time_expected_sec, numpy, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, dev_list, update_time
                            
                            if (self.scan_mode == -2 and self.write_scan_before): # write all scan before on the AO memory of the DAQ
                                import nidaqmx.stream_writers

                                nb_ao_channel = 2 # X and Y
 
                                analog_output_daq_to_galvos, meth_write, buffer_write_size, shape_reverse_movement, correct_unidirektionnal, sample_rate_galvos, nb_line_prewrite, time_expected_sec, name_list_wr_dumb_tasks, ao_dumb = daq_control_mp2.define_AO_write_Task(nidaqmx, self.write_scan_before, unidirectional, param_ini.correct_unidirektionnal, param_ini.shape_reverse_movement, nb_ao_channel, duration_one_line_real, duration_one_line_imposed, sample_rate_AO_wanted, param_ini.small_angle_step, nb_px_slow, param_ini.use_velocity_trigger, param_ini.blink_after_scan, min_val_volt_galvos, max_val_volt_galvos, param_ini.duration_scan_prewrite_in_buffer, device_to_use_AO, time_expected_sec, param_ini.use_volt_not_raw_write, dev_list, numpy, analog_output_daq_to_galvos, name_list_AO_tasks, nb_pts_daq_one_pattern, name_list_wr_dumb_tasks, param_ini.ext_ref_AO_range, ao_dumb)
                                
                        [trig_src_end_master, trig_src_end_term_toExp_toWatcher, maxSmp_paquet, divider, dividand] = params_galvos # # trigger defined
                        # if (params_galvos is not None and params_galvos[0] is not None): 
                        # # else: trig_src_end_master = None;  trig_src_end_term_toExp_toWatcher = None # # cf l785 of daq_controlmp
                    # # print('sample_rate data_acq', sample_rate)
                        update_time_send = update_time if update_time00 != update_time else None
                        if (ishg_EOM_AC[0] and (ishg_EOM_AC[-2] != ishg_EOM_AC2[-2])): # not in samps, deadtimes
                            put1 = (sample_rate, update_time_send, ishg_EOM_AC2[-2][1], ishg_EOM_AC2[-2][2])
                        else: put1 = (sample_rate,update_time_send) # is a tuple, do not forget the comma !
                        self.new_img_flag_queue.put(put1)  # tuple_smp_rate_new
                        # # print('put1', put1)
                        # # if scan_xz:
                        # #     update_time = nb_px_x*time_by_point # on line
                                
                        nb_pmt_channel = sum(pmt_channel_list)
                        oversampling = sample_rate*time_by_point # = 80, 
                        
                        if abs(round(oversampling)-oversampling) < 1/sample_rate: # # avoid values like 79.9999999999999999999999999999
                            oversampling = round(oversampling)
                        
                        if self.scan_mode >= -1: # digital galvos or static
                            nb_AI_channels = nb_pmt_channel

                        if self.scan_mode == 1: # galvos digital
                            use_dig_galvos = 1
                            
                            if (len(list_galvo_scan) == 0 and dig_galvo is not None) :
                                list_galvo_scan, tot_time = galvos_util_scripts.list_galvos_func(galvos_util_scripts, time_by_point, param_ini.galvo_rotation, param_ini.img_pixel, obj_mag, param_ini.field_view, sample_rate, param_ini.SM_cycle, param_ini.SM_delay, param_ini.ohm_val, param_ini.induct_H, param_ini.max_voltage, param_ini.inertia, param_ini.torque, param_ini.bit_size_galvo, param_ini.bits_16_36, center_x, center_y, new_sz_x_um, new_sz_y_um, nb_px_x, nb_px_y, param_ini.scan_linse, numpy, optimize, param_ini.center_galvo_x00, param_ini.center_galvo_y00, unidirectional, param_ini.turn_time_unidirek, param_ini.dll_diggalvos_timing, dll_tuple)
                                # # for i in list_galvo_scan:
                                # #     print(i)
                            
                            else:
                                start = 'AI,'
                                end = ',4,0'
                                tot_time = int(list_galvo_scan[len(list_galvo_scan)-2][len(start):-len(end)])*param_ini.SM_cycle
                                # # if unidirectional:
                                # #     #tot_time = tot_time/(1+0.25*unidirectional)
                                # #     tot_time = time_by_point*nb_px_x*nb_px_y
                            # total_px = dividand; maxPx_paquet = divider
                            maxPx_paquet, total_px, nb_lines_inpacket = daq_control_mp2.mxsmp_func_totime(dig_galvos_use, param_ini, time_by_point, update_time , tot_time, nb_px_x, nb_px_slow)
                            if dividand is None: dividand = total_px
                            if divider is None: divider = maxPx_paquet
                            maxSmp_paquet = maxPx_paquet*round(oversampling)
                        elif self.scan_mode == -1: #  static acq
                        
                            list_galvo_scan = []
                            tot_time = time_by_point*nb_px_x*nb_px_y
                            unidirectional = 1 # static is considered unidirectional (convention, and faster)
                            total_px = dividand; maxPx_paquet = divider

                        elif self.scan_mode == -2:  # anlg galvo scan
                            dividand = nb_loop_line
                            nb_lines_inpacket = divider
                            if self.write_scan_before: # write all scan before on the AO memory of the DAQ
                                
                                bits_write = analog_output_daq_to_galvos.channels.ao_resolution
                                
                                [volt_pos_min_slow, volt_begin_fast] = init_pos_volt

                                write_task.galvo_goToPos_byWrite(nidaqmx, analog_output_daq_to_galvos, meth_write, 4, y_fast, volt_begin_fast, volt_pos_min_slow, sample_rate_galvos, param_ini.min_val_volt_galvos, param_ini.max_val_volt_galvos, bits_write, param_ini.use_volt_not_raw_write, time, numpy)
                                # # print('dfhd ',  unidirectional) #buf_size)

                                write_task.write_arrays_AO(analog_output_daq_to_galvos, meth_write, self.write_scan_before, param_ini.use_velocity_trigger, unidirectional, param_ini.angle_rot_degree_new_galvos, cos_angle, sin_angle, one_scan_pattern_vect, line_slow_daq_vect, line_slow_daq_vect_last, correct_unidirektionnal, shape_reverse_movement, sample_rate_galvos, y_fast, nb_pts_daq_one_pattern, nb_line_prewrite, param_ini.tolerance_nb_write_to_stop, nidaqmx, numpy, time, self.sideWrite_writeAcq_pipe, param_ini.use_volt_not_raw_write, bits_write, daq_pos_max_slow, daq_pos_min_slow, nb_px_slow)
                                
                            else: # write in LIVE
                                list_params_writelive = [self.write_scan_before, unidirectional, correct_unidirektionnal, shape_reverse_movement, nb_ao_channel, duration_one_line_real, duration_one_line_imposed, sample_rate_AO_wanted, sample_rate_AO_min_imposed, volt_pos_min_withDeadTime_fast, volt_pos_max_withDeadTime_fast, volt_pos_min_fast, volt_pos_max_fast, param_ini.small_angle_step, nb_px_slow, volt_pos_blink, volt_begin_fast, volt_end_fast, volt_pos_min_slow, volt_pos_max_slow, param_ini.use_velocity_trigger, param_ini.blink_after_scan, param_ini.min_val_volt_galvos, param_ini.max_val_volt_galvos, param_ini.duration_scan_prewrite_in_buffer, device_to_use_AO, param_ini.use_volt_not_raw_write, dev_list, param_ini.angle_rot_degree_new_galvos, cos_angle, sin_angle, volt_begin_slow, volt_end_slow, y_fast, param_ini.tolerance_nb_write_to_stop]
                                
                                self.sideAcq_writeAcq_pipe.send([1, list_params_writelive]) # tell the write Process to pre-write a part of the scan, without starting it
                            
                        if job[0] <= 1: # # not defined for nothing
                            self.queue_acq_fill.put([[pmt_channel_list, nb_px_x, nb_px_y, unidirectional, y_fast, oversampling, sample_rate, divider, dividand, delete_px_fast_begin, delete_px_fast_end, delete_px_slow_begin, delete_px_slow_end, nb_bins_hist, clrmap_nb, autoscalelive_plt, AI_bounds_list, param_ini.use_volt_not_raw, param_ini.use_median, skip_behavior, nb_accum, offset_scan_list, ishg_EOM_AC_insamps], True])
                        
                        # # print(list_galvo_scan) # !!
                        
                        if self.scan_mode == 1 : #galvo_Scan 

                            for i in list_galvo_scan:  # bug if None
                                b = dig_galvo.write(('%s\n' % i).encode('ascii')) # b to supress output
                                # print(dig_galvo.readline().decode()) # to check if the dig_galvo command has been received
                            del(b) # b is useless after
                
                        if nb_AI_channels == 0:  # 0 to avoid data acquisition, but keep the rest
                            nb_AI_channels = 1 

                        if (self.scan_mode in (1, -2)): # anlg or dig. galvos
                        
                            if (method_watch == 7 or not use_callbacks):
                                callback = None
                            else:
                                nb_lines_acumm_acq = param_ini.nb_lines_acumm_acq if param_ini.nb_lines_acumm_acq is not None else nb_lines_inpacket
                                
                                def callback(task_handle, signal_type, callback_data):
                                    
                                    new_galvos_funcs.read_fast_callback_meth(analog_input, meth_read, list_params, nb_AI_channels, skip_behavior, nb_loop_line, nb_acq_vect, None, nb_lines_acumm_acq, use_dig_galvos, data, arr_reshape, self.queue_acq_fill, scan_xz, min_pulse_width_digfltr_6259, use_dig_fltr_onAlgCmpEv, time_comp_fltr, numpy, nidaqmx) 
                                    return 0        
                        
                        # #if (self.scan_mode == -2 or (self.scan_mode == 1 and pause_trigger_diggalvo)): 
                        if self.scan_mode == -2: # anlg galvos
                            disp_info_flag = True # disp info shift array on 1st acq
                            device_to_use_anlgTrig = dev_list[param_ini.num_dev_anlgTrig] # device to use for get trig
                            device_to_use_watcherTrig = dev_list[param_ini.num_dev_watcherTrig]
                        else: # # elif (self.scan_mode == 1 and pause_trigger_diggalvo): # dig galvo or static
                            device_to_use_anlgTrig = self.trig_src[0] # not None
                            device_to_use_watcherTrig = self.trig_src[0]
                        nb_it_theo = dividand/divider # total_px/maxPx_paquet
                        anlgCompEvent_watcher_task, trig_AI_to_chck = daq_control_mp2.trig_watcher_ctrl_def_galvoscn(nidaqmx, use_callbacks, duration_one_line_imposed, param_ini.term_DI, trig_src_end_master, trig_src_end_term_toExp_toWatcher, method_watch, nb_loop_line, param_ini.use_velocity_trigger, device_to_use_AO, self.trig_src[0], device_to_use_anlgTrig, device_to_use_watcherTrig, dev_list, analog_input, ai_trig_control, param_ini.use_trigger_anlgcompEv_onFallingEdges, use_dig_fltr_onAlgCmpEv, master_trig_ctrl_scrpts, callback, pack_params_new_galvos, dig_galvos_use, anlgCompEvent_watcher_task, name_list_watcher_tasks, tuple_EOMph, param_ini) # # will print the summary
                    
                    else: # no new parameter
                        if job[0] == 1:
                            self.queue_acq_fill.put([None , False]) # order to begin treatment with same parameters as before
                            if (self.scan_mode == -2 and not self.write_scan_before): # new anlg galvos
                                self.sideAcq_writeAcq_pipe.send([1])
                    
                    if (self.scan_mode == -2): # new position for anlg new galvos
                        if job[0] == 7: # set pos
                            [pos_fast_deg, pos_slow_deg] = job[1]
                            write_task.galvo_goToPos_byWrite(nidaqmx, analog_output_daq_to_galvos, meth_write, 4, y_fast, pos_fast_deg + param_ini.offset_y_deg_00, pos_slow_deg + param_ini.offset_x_deg_00, sample_rate_galvos, param_ini.min_val_volt_galvos, param_ini.max_val_volt_galvos, bits_write, param_ini.use_volt_not_raw_write, time, numpy)
                            
                    else: # # digital or static
                        if not 'tot_time' in locals(): # wrong def
                            print('waiting for def of params in packet (acq)')
                            continue
                        time_expected_sec = tot_time
                    
                    # !! maybe wants to get the pos even if not an anlg galvo scan
                    if job[0] == 6: # get pos
                        if ('analog_input' in locals() and analog_input is not None):
                            analog_input.close()
                        from modules import new_galvos_funcs
                        self.queue_special_com_acqGalvo_stopline.put(new_galvos_funcs.get_anlg_galvo_pos(nidaqmx, self.trig_src[0].name, param_ini.ai_readposX_anlggalvo, param_ini.ai_readposY_anlggalvo)) # [fast_pos, slow_pos] = 
                        print('\n I sent the anlg galvo to GUI')
                            
                    if job[0] > 1: # just define the Tasks or pos
                        continue # return to the beginning, after the while True
                    
                    number_of_samples = int(round(maxSmp_paquet)) # 1320000 for 1st, 12298*80=983840 for last on
                    # # print('number_of_samples', number_of_samples)
                    if cond_read_counter_line_time: # # read time line with counter
                        nb_lines_inpacket_curr = nb_lines_inpacket
                        # # print('nb_lines_inpacket !!', nb_lines_inpacket)
                        time_wait_ct_lines = (nb_lines_inpacket+1)*time_expected_sec/nb_px_slow # # +1 to be sure it's long enough
                        timeoutAI = 0 # # read AI directly after having wait for the lines
                    else: # no count lines 
                        time_wait_ct_lines = update_time # # time_expected_sec/nb_it_max # # number_of_samples/sample_rate
                        timeoutAI = time_wait_ct_lines*1.1 
                    
                        # print( 'timeoutAI', timeoutAI)   
                    if self.scan_mode == -2:   # new anlg galvos
                        timeout00 = max(self.time_out/10, duration_one_line_real*(nb_lines_inpacket+1))
                    else: # other
                        timeout00 = max(self.time_out, duration_one_line_real)
                    print('acq # %d\n' % index_acq_current)
                    
                    ## Scan
                    
                    no_bug = 1
                
                    start_time = time.time()
                    
                    if ((self.scan_mode == -2 or dig_galvos_use == 1) and not method_watch == 7):  # new anlg galvos OR dig galvos without read line_time, but with callbacks line
                        
                        list_params = [0, 0, -1] # # [total_acq samples on Xth line, ind_slow on lines acquired TOTAL , flag for skip (1st) line]
                        # # print('l415', nb_AI_channels, nb_lines_acumm_acq, number_of_samples,fact_data)
                        data = numpy.zeros((nb_AI_channels, nb_lines_acumm_acq, number_of_samples*fact_data), dtype=param_ini.type_data_read_temp, order='c')
                        arr_reshape = numpy.zeros((number_of_samples*fact_data, nb_AI_channels), dtype=param_ini.type_data_read_temp, order='c') # # fastest option, normal if inverted !!
                        # # print('data3 !!!', number_of_samples,fact_data, data.shape)
                        list_params[2] = -1 
                        # # >= 0 : skip 1st line
                        # # >=1 : skip also last line, because - for anlg galvos - if you skip the 1st line you have to not wait for the N+1 line in the end
                        nb_acq_vect = numpy.zeros((nb_loop_line-max(list_params[2], 0)), dtype = numpy.int32) # [0]*nb_loop_line # None
                        doneflag, ignore_watcher_undone = new_galvos_funcs.scan_newGalvos(nidaqmx, self.write_scan_before, self.sideAcq_writeAcq_pipe, self.trig_src[0], device_to_use_anlgTrig, param_ini.DO_parallel_trigger, method_watch, ai_trig_control, use_callbacks, sender_read_to_trigger, trigWatcher_process, anlgCompEvent_watcher_task, analog_input, analog_output_daq_to_galvos, time_expected_sec, param_ini.DI_parallel_watcher, nb_loop_line, skip_behavior, None, arr_reshape, self.queue_acq_fill, nb_lines_acumm_acq, msg_warning_ifstop_taskundone, receiver_trigger_to_read, nb_px_slow, data, nb_AI_channels, time, numpy, warnings, dig_galvo, list_params, nb_acq_vect, meth_read, self.queue_special_com_acqGalvo_stopline, self.queue_com_to_acq_process, queueEmpty, mtr_trigout_cntr_task, acqGalvo_stopline_meth) # # nb_acq_vect is for diagnostics
                        # #(nidaqmx, write_scan_before, sideAcq_writeAcq_pipe, device_to_use_AI, device_to_use_anlgTrig, DO_parallel_trigger, method_watch, ai_trig_control, use_callbacks, sender_read_to_trigger, trigWatcher_process, anlgCompEvent_watcher_task, analog_input, analog_output_daq_to_galvos, time_expected_sec, DI_parallel_watcher, nb_loop_line, skip_behavior, data_read, queue_acq_fill, nb_lines_acumm_acq, msg_warning_ifstop_taskundone, receiver_trigger_to_read, nb_px_slow, data, nb_AI_channels, time, numpy, warnings, dig_galvo, list_params, nb_acq_vect, meth_read, queue_special_com_acqGalvo_stopline, queue_com_to_acq_process, queueEmpty, mtr_trigout_cntr_task, acqGalvo_stopline_meth)
                        if not doneflag:
                            break # outside 'while' loop
                        k = int(numpy.ceil(list_params[1]/nb_lines_acumm_acq)) 
                        if disp_info_flag:
                            if numpy.mean(nb_acq_vect) > 0:
                                print('diff nb_el ./ mean (%)', numpy.int16(numpy.round(abs(nb_acq_vect-numpy.mean(nb_acq_vect))/numpy.mean(nb_acq_vect)*100)), 'std_nbel', round(numpy.std(nb_acq_vect),1)) # can be useful to control
                            disp_info_flag = False
                        
                    else: # digital galvos or ctrl_lines anlg galvos or static (classic standard scan!)
                    
                        data = numpy.zeros((nb_AI_channels, number_of_samples), dtype=param_ini.type_data_read_temp, order='c')
                        meas_line_time_list = False
                        line_count = 0
                        
                        nb_it_full = int(numpy.floor(nb_it_theo)) # nb_it_theo is not an integer
                        
                        if nb_it_full == nb_it_theo: # last buffer is full size
                            nb_it_max = nb_it_full
                            samp_in_packet_last = number_of_samples
                        else: # full and a last one not full    
                            nb_it_max = nb_it_full + 1
                            if not cond_read_counter_line_time: # # NOT read time line 
                                last_nb_samp = total_px - maxPx_paquet*nb_it_full # can be non int !
                                samp_in_packet_last = int(numpy.floor(oversampling*last_nb_samp))
                        
                        ct_incr = 0
                        for k in range(1, nb_it_max+1): # # goes from 1 to nb_it_max
                        
                            # # if self.scan_mode != 1 : #galvo_Scan 
                            send_stop_inline, ignore_watcher_undone = acqGalvo_stopline_meth(self.queue_special_com_acqGalvo_stopline, self.queue_acq_fill, self.queue_com_to_acq_process, queueEmpty, analog_output_daq_to_galvos, self.scan_mode == -2)
                            if send_stop_inline:
                                break # outside the 'for' loop on slow
                        
                            # if verbose:
                            print('Buffer acq # %d/%d' % (k, nb_it_max))
                            
                            if (k >= nb_it_max and nb_it_max > 1): # last iteration
                            
                                # # print(number_of_samples, samp_in_packet_last,  number_of_samples/sample_rate*(1+0.35*unidirectional)) 
                                
                                if self.scan_mode != -1: # pause trigger, not static acq. 
                                    timeout00 = 0  

                                if not cond_read_counter_line_time:  # # NOT read time line 
                                    number_of_samples = samp_in_packet_last
                                    # # if nb_AI_channels > 1:
                                    # #     data = data[:nb_AI_channels,:number_of_samples].reshape(1, nb_AI_channels*(number_of_samples)).reshape(nb_AI_channels, number_of_samples)        
                                    # # else: # =1, one reshape needed
                                    # #     data = data[0, :number_of_samples].reshape(1, number_of_samples)   
                                else: # # read line with counter
                                    
                                    if self.scan_mode == -2:   # new anlg galvos
                                        
                                        try:
                                            analog_output_daq_to_galvos.wait_until_done(max(0, (nb_loop_line-line_count))*duration_one_line_real*1.5) 
                                            # print("--- %s sec galvo time ---" % (time.time() - start_time))
    
                                        except nidaqmx.DaqError as err:
                                            if err.error_type != nidaqmx.error_codes.DAQmxErrors.WAIT_UNTIL_DONE_DOES_NOT_INDICATE_DONE:
                                                print(err)
                                            else: # just timed out
                                                
                                                print('\n Wait until done timed out, the Task AO was not fullfilled !! \n')
                                            warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                                            analog_output_daq_to_galvos.stop()
                                            warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)
                                            
                                        else:
                                            analog_output_daq_to_galvos.stop()
                                        
                                        print('stopped AO') 
                                        # # continue # # !!   
                                        time_wait_ct_lines = 0  # # the AO Task already blocked the reading time enough 
                                        nb_lines_inpacket_curr = nidaqmx.constants.READ_ALL_AVAILABLE
                                        number_of_samples = analog_input.in_stream.avail_samp_per_chan                         
                                    else:   # # digital
                                        nb_lines_inpacket_prev = nb_lines_inpacket
                                        nb_lines_inpacket_curr = max(0, (nb_loop_line-line_count)) # not precise because some lines may have remained untreated
                                        number_of_samples = int(round(nb_lines_inpacket_curr/nb_lines_inpacket_prev*maxSmp_paquet)) #*oversampling
                                        time_wait_ct_lines = max(0, time_expected_sec - nb_it_full*update_time)

                                data = numpy.zeros((nb_AI_channels, number_of_samples), dtype=param_ini.type_data_read_temp, order='c') # #  recreate because can be bigger
                                    
                            elif k == 1: # the closest to the read
                                if (scan_xz):
                                    daq_control_mp2.scan_xz_reg_N_samps(analog_input, piezoZ_step_signal, step_Z_mm, k, sample_rate*nb_px_x*time_by_point)
                                if ((self.trig_src[0] != device_to_use_anlgTrig) and not param_ini.DO_parallel_trigger and not method_watch == 3): # master/slave config
                                    # # ai_trig_control.stop()
                                    ai_trig_control.start()
                                
                                if (dig_galvos_use and self.scan_mode != -1): # pause trigger, not static acq. # dig_galvos_use was 2
                                # # dig_galvos_use = 0 # static OR classic dig galvos with start trigger
                                # # dig_galvos_use = 2 # use pause trigger meas. with dig galvos
                                # #   dig_galvos_use = 1 # use pause trigger that callbacks with dig galvos
                                    anlgCompEvent_watcher_task.start()
                                if mtr_trigout_cntr_task is not None: # # for EOMph iSHG only, or calib one line
                                    mtr_trigout_cntr_task.stop(); mtr_trigout_cntr_task.start() # # is retrigerable so no need to stop it each time
                                analog_input.start() # YOU NEED to start task at each image
                                
                                # # !! 2019.5.16
                                if analog_input.in_stream.avail_samp_per_chan:
                                    remn = analog_input.read(timeout = 0)
                                    if type (remn) != float: print('cleaned from buffer', remn) # # empty the buffer
                                # # !!
                                
                                # # if self.scan_mode != -2: # #  not anlg galvos
                                if self.scan_mode == 1: #galvo_Scan    
                                    dig_galvo.write('X\n'.encode('ascii')) # execute scan, b to supress output
                                    # print(dig_galvo.readline().decode()) # to check if the dig_galvo command has been received
                                elif self.scan_mode == -2: # new anlg galvos
                                    analog_output_daq_to_galvos.start()
                                     
                            if cond_read_counter_line_time:  # # read time line with counter
                                try:
                                    meas_line_time_list = anlgCompEvent_watcher_task.read(number_of_samples_per_channel= nb_lines_inpacket_curr, timeout = time_wait_ct_lines + timeout00) # in sec # nidaqmx.constants.READ_ALL_AVAILABLE
                                except nidaqmx.DaqError as err:
                                    print('in err read counter lines')
                                    break_here = True # default
                                    meas_linetime_saved = meas_line_time_list[0] if (type(meas_line_time_list) in (list, tuple) and len(meas_line_time_list) > 0) else None
                                    meas_line_time_list = []
                                    if (err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_NOT_YET_AVAILABLE or err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_WILL_NEVER_BE_AVAILABLE): # # -200284 OR -200278
                                        if k > 1: 
                                            break_here = False # normal error
                                    elif err.error_type == nidaqmx.error_codes.DAQmxErrors.COUNTER_OVERFLOW: print('\n The galvo trigger seems to be too noisy now, maybe try to pass it to the external buffer cleaner ? \n') # # here the counter measured too many little linetime, that are fluctuations
                                    else: print(err)
                                if len(meas_line_time_list) == 0:
                                    print('this read ended before the end of at least one line, read is frequent/lines are long or check the counter connection to %s !' % anlgCompEvent_watcher_task.channels.ci_pulse_width_term)
                                    
                                line_count += len(meas_line_time_list)
                            
                            if not break_here: # # read counter worked
                                read = 0
                                try:
                                    read = meth_read(data, number_of_samples_per_channel=number_of_samples, timeout = timeoutAI + timeout00) # read is here !!
                                    
                                    # # print('\nmean = %.3f\n' % numpy.mean(data), clear_arr)
                                except nidaqmx.DaqError as err:
                                    print('in err read AI')
                                    break_here = True # default
                                    if err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_NOT_YET_AVAILABLE: #  -200284 
                                    #nidaqmx.error_codes.DAQmxErrors.TIMEOUT:
                                        nonzeros_length = len(data[numpy.nonzero(data)]); msg1 = ''
                                        if k > 1:  #  # if k ==1, break
                                            break_here = False # normal error  
                                        max_incr = 10
                                        if k < nb_it_max: # # not supposed to happen before last buffer ...
                                            if (ct_incr < max_incr and timeout00 < 10*timeout00/fct_incr**ct_incr):
                                                timeout00 = timeout00*fct_incr # # increase by 5% the timeout for this to not happen
                                                ct_incr += 1
                                            elif (ct_incr == max_incr): 
                                                timeout00 = timeout00/fct_incr**(ct_incr-1) # # finally useless to increase this time
                                                ct_incr += 1
                                            if timeout00==0: timeout00 = self.time_out_sync 
                                            if numpy.size(data) == nonzeros_length: # # the good nb was acquired !
                                                msg1 = 'finally good'
                                                if analog_input.in_stream.avail_samp_per_chan == 0: # nothing to try to read by wait anymore, so it's not a pb of timeout
                                                    ct_incr = max_incr + 1
                                                    timeout00 = 0
                                                else: msg1 += ' but timeout increased from %.2f to %.2f sec' % (timeoutAI +timeout00/fct_incr, timeoutAI +timeout00)
                                                break_here = False
                                            else: clear_arr = True; msg1 = 'not last buffer, break here (%.1f to %.1f sec)' % (timeoutAI +timeout00/fct_incr, timeoutAI +timeout00)
                                        else: msg1 = 'last buffer, will complete with all samps possible'; break_here = False
                                        
                                        try: nb_meas_str = analog_input.in_stream.avail_samp_per_chan  
                                        except: nb_meas_str =  'N/A'   
                                        print('ERROR : Tried to acq. %d smp but acquired only %d after timeout (avlb %s)' % (number_of_samples*nb_AI_channels, nonzeros_length, nb_meas_str), msg1, timeoutAI +timeout00) # # (data[0]!=0).argmin()
                                    else: print(err)

                            if break_here: # can be called by bug read counter or read AI
                                break_here = False # re-init
                                if read > 0:
                                    acq_nb = read
                                else:
                                    acq_nb = analog_input.in_stream.total_samp_per_chan_acquired
                                str1 = '' if self.scan_mode == -1 else 'you have not connected the GALVO trigger wire to %s port (or galvos are turned off), or' % trig_AI_to_chck
                                print('\nOnly %d/%d smps acq. \n Maybe %s DAQ card bugs !' % (acq_nb, number_of_samples, str1))
                                print('\n Anyway, you`ll have a chance to start the scan again \n')
                                
                                if self.scan_mode == -2: # new anlg galvos
                                    analog_output_daq_to_galvos.stop()
                                
                                stop = [-2] if k > 1 else [0]
                                self.queue_acq_fill.put(stop) # communicate the stop to fill_array process
                                if (self.scan_mode == -2 and not self.write_scan_before): # new anlg galvos
                                    self.sideAcq_writeAcq_pipe.send([0])
        
                                no_bug = 0
                                break # outside the 'for' loop
                                
                            else: # # ok, no bug
                                if (cond_read_counter_line_time and len(meas_line_time_list) == 0 and meas_linetime_saved is not None): # # AI read smp, but linetime had a bug
                                    meas_line_time_list = [meas_linetime_saved]*int(1+len(data[numpy.nonzero(data)])/(meas_linetime_saved*sample_rate)) # 1+ for safety
                                self.queue_acq_fill.put([data, meas_line_time_list])  # # data acq., and meas line time if applicable
                                
                            if clear_arr:
                                clear_arr = False
                                data[:, :]=0 # !!
        
                    print("--- %s seconds (acq.) --- " % (time.time() - start_time))
                    print('Expected time = %g s' % (time_expected_sec))
                    print('Nb loop done/expected in acq = %d/%.3g' % (k, nb_it_theo))        
                    
                    empty_all = 1
                    ar = None
                    if (self.scan_mode != -2 and not empty_all):
                        rest_of_samples = int(max(0, round(tot_time*sample_rate - total_px*oversampling))) # # sometimes round gives a .0 !!
                    else: # # anlg galvos or empty all 
                        rest_of_samples = nidaqmx.constants.READ_ALL_AVAILABLE # analog_input.in_stream.avail_samp_per_chan
                        # # doing analog_input.in_stream.avail_samp_per_chan is too slow if read after

                    # # if rest_of_samples>0:
                    # #     data_garbage = numpy.zeros((nb_AI_channels, rest_of_samples), dtype=param_ini.type_data_read_temp)  # data_garbage[:, :rest_of_samples].reshape(1, nb_pmt_channel*rest_of_samples).reshape(nb_pmt_channel, rest_of_samples) 
                    if no_bug: 
                    
                        if (type(rest_of_samples)!=int or rest_of_samples>0): # # remains samples in buffer
                            # skip intersync data, i.e. data acquired between images
                            # # read = meth_read(data_garbage, number_of_samples_per_channel=rest_of_samples, timeout = self.time_out_sync)
                            try: ar = analog_input.read(number_of_samples_per_channel = rest_of_samples, timeout= self.time_out_sync)
                            except nidaqmx.DaqError as err:
                                print('ERR in rest_of_samples')
                                if err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_NOT_YET_AVAILABLE: #  -200284
                                # # usually it's not because the timeout is too short, but because the buffer gets corrupted (full ??) !
                                    print('rest_of_samples was %d but now %d' % ('', analog_input.in_stream.avail_samp_per_chan))
                                 
                        if cond_read_counter_line_time:   # # read time line with counter
                            rest_lines = anlgCompEvent_watcher_task.in_stream.avail_samp_per_chan
                            if rest_lines >0:
                                _ = anlgCompEvent_watcher_task.read(number_of_samples_per_channel= rest_lines, timeout = self.time_out_sync)
                                print('remained lines time', len(_))
                    if ar is not None: print('rest_of_samples', numpy.size(ar)) # no error
                    no_bug = 1
                    analog_input.stop()
                    analog_input.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
                    analog_input.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # re-arm the Task
                    if ((self.trig_src[0] != device_to_use_anlgTrig) and not param_ini.DO_parallel_trigger and not method_watch == 3): # master/slave config
                        ai_trig_control.stop()
                    if (dig_galvos_use and self.scan_mode != -1): # pause trigger, not static acq. # dig_galvos_use was 2
                    # # dig_galvos_use = 0 # static OR classic dig galvos with start trigger
                    # # dig_galvos_use = 2 # use pause trigger meas. with dig galvos
                    # #   dig_galvos_use = 1 # use pause trigger that callbacks with dig galvos
                        if ignore_watcher_undone:
                            ignore_watcher_undone = False
                            warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                        anlgCompEvent_watcher_task.stop()
                        if ignore_watcher_undone:
                            warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)
                    
                    index_acq_current+=1 # can be kept
                    if mtr_trigout_cntr_task is not None: # # for EOMph iSHG only
                        mtr_trigout_cntr_task.stop()
                        if send_stop_inline: # # stopped in-line
                            mtr_trigout_cntr_task.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
                            mtr_trigout_cntr_task.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # re-arm the Task
        except:
            import traceback
            traceback.print_exc()
            self.queue_acq_fill.put([-2]) # stop in-line to try to save the image (part of)
            self.queue_acq_fill.put([-1]) # communicate the poison-pill to fill_array process
            if (self.scan_mode == -2 and not self.write_scan_before): # new anlg galvos
                self.sideAcq_writeAcq_pipe.send([job[-1]])
            
        finally: # in all cases
            if ('analog_input' in locals() and analog_input is not None):
                analog_input.close()
            
            if ('anlgCompEvent_watcher_task' in locals() and anlgCompEvent_watcher_task is not None):
                anlgCompEvent_watcher_task.close()
                
            if (self.scan_mode == 1 and 'dig_galvo' in locals() and dig_galvo is not None): #galvo_Scan    
                dig_galvo.close()
                # # if dig_galvos_use: # dig_galvos_use was 2
                    # # dig_galvos_use = 0 # static OR classic dig galvos with start trigger
                    # # dig_galvos_use = 2 # use pause trigger meas. with dig galvos
                    # #   dig_galvos_use = 1 # use pause trigger that callbacks with dig galvos
                
            elif self.scan_mode == -2: # anlg galvos new
                if not ('trig_src_end_master_toExp' in locals()):
                    trig_src_end_master_toExp = None
                new_galvos_funcs.end_newGalvos(system, dev_list, method_watch, param_ini.DO_parallel_trigger, use_callbacks, param_ini.DI_parallel_watcher, self.trig_src[0], device_to_use_anlgTrig, device_to_use_watcherTrig, export_trigger, trig_src_end_master_toExp, param_ini.term_toExp_Ctr0Gate_forAnlgCompEvent_6110, param_ini.trig_src_end_term_toExp_toWatcher, param_ini.trig_src_end_toExp_toDIWatcher, ai_trig_control, anlgCompEvent_watcher_task, analog_output_daq_to_galvos, ao_dumb)
            
            if (mtr_trigout_cntr_task is not None): # # flag ishg EOM, mtr_trigout_cntr_task (Task)  and ishg_EOM_AC[0]
                mtr_trigout_cntr_task.stop(); mtr_trigout_cntr_task.close()
                nidaqmx.system.System.local().disconnect_terms(source_terminal = ('/%s/%s' % (self.trig_src[0].name, self.trig_src[1])), destination_terminal = '/%s/%s' % (self.trig_src[0].name, param_ini.ctr_src_trigger_trigout_EOMph))