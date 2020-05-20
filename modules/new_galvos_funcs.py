# -*- coding: utf-8 -*-
"""
Created on May 10 09:55:13 2018

@author: Maxime PINSARD

"""

'''
You can operate up to  modes

- 6110 only with PFI0 (4 chans)
- 6259 only with APFI0 (many chans, rate dependent)
- 6110 only with ai3 as trigger (3 chans PMT)
- 6259 only with ai0 as trigger (0 chans PMT) : only for test
- 6110 (4 chans) with trig from 6259 by sample clock : have to set pause trigger for anlg_contrl, export_sign the smp_clck to term Dev2/PFI7, and define AI (no pause trigger) samp clck to a term (Dev1/PFI7) also 
- 6110 (4 chans) with trig from 6259 by AnlgCompEvent : have to connect terminals AnlgCompEvent to Dev2/PFI9, and set the Pause trigger of Read to Dev1/PFI9
- 6259 (many chans, rate dependent) with trig from 6110  : inverse of before
- one card Read, the other Trig but with no use of Pause trigger (DO_parallel_trigger) : an independent Process is used to read in a loop, and send a DO signal when condition met
--> high control of condition, but dependent on the speed of the read ! for 2ms per line, was not very efficient

2018.05.08
don't know why but when you just imported nidaqmx, bug at first try
but works for 2ms line time, bidirek and unidirek
'''

def scan_newGalvos(nidaqmx, write_scan_before, sideAcq_writeAcq_pipe, device_to_use_AI, device_to_use_anlgTrig, DO_parallel_trigger, method_watch, ai_trig_control, use_callbacks, sender_read_to_trigger, trigWatcher_process, anlgCompEvent_watcher_task, analog_input, analog_output_daq_to_galvos, time_expected_sec, DI_parallel_watcher, nb_loop_line, skip_behavior, data_read, arr_reshape, queue_acq_fill, nb_lines_acumm_acq, msg_warning_ifstop_taskundone, receiver_trigger_to_read, nb_px_slow, data, nb_AI_channels,  time, numpy, warnings, dig_galvo, list_params, nb_acq_vect, meth_read, queue_special_com_acqGalvo_stopline, queue_com_to_acq_process, queueEmpty, mtr_trigout_cntr_task, acqGalvo_stopline_meth):
    
    # # print('data !!!', data.shape)
    
    if not (write_scan_before): 
        if not sideAcq_writeAcq_pipe.recv(): # blocking, False if bug
            return False, False
                    
    cond_master_slave = ((device_to_use_AI != device_to_use_anlgTrig) and not DO_parallel_trigger and not method_watch == 3)            
    if cond_master_slave: # master/slave config, for anlg galvos normally
        ai_trig_control.stop()
        ai_trig_control.start()
        
    if (use_callbacks): 
    
        if DI_parallel_watcher:
            trigWatcher_process.start()
            sender_read_to_trigger.send( [1, [nb_px_slow, 1000]])
        else:
            anlgCompEvent_watcher_task.stop()
            anlgCompEvent_watcher_task.start() # will register events when needed
    
    if mtr_trigout_cntr_task is not None: # # for EOMph iSHG only
        mtr_trigout_cntr_task.stop(); mtr_trigout_cntr_task.start() # # is retrigerable so no need to stop it each time
    analog_input.stop()
    analog_input.start() # YOU NEED to start task at each image

    if dig_galvo is None: # # anlg galvos
        use_dig_galvos = False
        if not write_scan_before:
            sideAcq_writeAcq_pipe.send(1) # tell the write LIVE that the Task has started
        else:
            # # analog_output_daq_to_galvos.stop()
            analog_output_daq_to_galvos.start()
    else: # dig galvo
        # # time.sleep(50/1000)
        use_dig_galvos = True
        dig_galvo.write('X\n'.encode('ascii')) #dig_galvo.write('X') # st scan
    
    ignore_watcher_undone = send_stop_inline = False # init
    t00 = time.time()

    if (use_callbacks and DI_parallel_watcher): # read with watcher that is in another Process and send msg by queue
        total_acq_prev = 0
        for ind_slow in range(nb_loop_line):
            
            # ct=0
            if skip_behavior[-1]: # unidirek with acq flyback and ((ind_slow+1) % 2) and ind_slow>0): # even
                ind_slow -= int(numpy.floor(ind_slow/2)) # data will be erased after
                
            if receiver_trigger_to_read.recv():
                
                total_acq = analog_input.in_stream.total_samp_per_chan_acquired
                
                diff = total_acq - total_acq_prev
                total_acq_prev = total_acq
                
                data_read[(ind_slow % nb_lines_acumm_acq)*nb_AI_channels:((ind_slow % nb_lines_acumm_acq)+1)*nb_AI_channels, :min(diff, len(data[0]))] = analog_input.read(number_of_samples_per_channel = nidaqmx.constants.READ_ALL_AVAILABLE, timeout = 0) 
                        
            if not (ind_slow % nb_lines_acumm_acq):
                # queue_acq_fill.put(data[ind_slow*nb_AI_channels:(ind_slow+1)*nb_AI_channels, :])
                queue_acq_fill.put([data_read, False]) # # a 2 el list because 1 element means direct order
    
    elif use_callbacks: # not parallel watcher
        nb_buff = int(numpy.ceil(nb_loop_line/nb_lines_acumm_acq))
        # # the scan is executing in parallel
        for ind_buf in range(nb_buff-1): # # don't wait or listen to orders for last buffer
            # # look if stop in-line
            send_stop_inline, ignore_watcher_undone = acqGalvo_stopline_meth(queue_special_com_acqGalvo_stopline, queue_acq_fill, queue_com_to_acq_process, queueEmpty, analog_output_daq_to_galvos, dig_galvo is None) # # last is scan_mode
            if send_stop_inline:
                break # outside the 'for' loop on slow
            time.sleep(time_expected_sec/nb_buff) # # wait time of one buffer

    # # ctrl_vect = [0]*400
    if (use_dig_galvos and not skip_behavior[-1]): # for the last line (bidirek only)
        read_fast_callback_meth(analog_input, meth_read, list_params, nb_AI_channels, skip_behavior, nb_loop_line, nb_acq_vect, None, nb_lines_acumm_acq, use_dig_galvos, data, arr_reshape, queue_acq_fill, 0, None, None, None, numpy, nidaqmx)
        # # read_fast_callback_meth(analog_input, meth_read, list_params, nb_AI_channels, skip_behavior, nb_loop_line, nb_acq_vect, ctrl_vect, nb_lines_acumm_acq, use_dig_galvos, data, queue_acq_fill, scan_xz, min_pulse_width_digfltr_6259, use_dig_fltr_onAlgCmpEv, time_comp_fltr, numpy, nidaqmx)
              
    # # *****************************************************
    # # ************** End of write Task ********************
    # # *****************************************************
    if dig_galvo is None: # # anlg galvos
    
        if not send_stop_inline: # # no stop inline
            print('waiting for AO Task to finish generate ...')
    
            try:
                analog_output_daq_to_galvos.wait_until_done(max(0, time_expected_sec*1.5 - (time.time()-t00))) # infinite ?
            except nidaqmx.DaqError as err:
                send_stop_inline = True # # abort the AO even if not finished
                if err.error_type != nidaqmx.error_codes.DAQmxErrors.WAIT_UNTIL_DONE_DOES_NOT_INDICATE_DONE:
                    print(err)
                else: # just timed out
                    print('\n Wait until done timed out, the Task AO was not fullfilled !! \n')
            else:
                analog_output_daq_to_galvos.stop()
            print('... AO is over')
        
        # # do NOT merge the "if", they are different ! send_stop_inline is defined inside 1st one !!
        if send_stop_inline: # # stop inline user OR AO was longer than expected 
            warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
            analog_output_daq_to_galvos.stop()
            warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)
        
    else: time.sleep(max(0, time_expected_sec*1.02 - (time.time()-t00))) # !!
            
    analog_input.stop()
    
    if (use_callbacks and not DI_parallel_watcher):
    
        warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
        anlgCompEvent_watcher_task.stop()
        warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone) #200010 STOPPED_BEFORE_DONE
        
    if cond_master_slave: # master/slave config, for anlg galvos normally
        ai_trig_control.stop()
        
    return True, ignore_watcher_undone
    
def read_fast_callback_meth(analog_input, meth_read, list_params, nb_AI_channels, skip_behavior, nb_loop_line, nb_acq_vect, ctrl_vect, nb_lines_acumm_acq, use_dig_galvos, data, arr_reshape, queue_acq_fill, scan_xz, min_pulse_width_digfltr_6259, use_dig_fltr_onAlgCmpEv, time_comp_fltr, numpy, nidaqmx):
        
        if (list_params[2] >= 0): # first line is not good. skip it
            # -2: # last line must also be removed
            list_params[2] = -1 if list_params[2] == 0 else -2 # will be positive
            return
        
        total_acq_prev = list_params[0]  # otherwise cannot be modified
        total_acq = analog_input.in_stream.total_samp_per_chan_acquired
        
        diff = total_acq - total_acq_prev
        list_params[0] = total_acq # # nb samps (fast dir)
                
        ind_slow = list_params[1]
            
        if scan_xz:
            piezoZ_step_signal.emit((ind_slow+1)*step_Z_mm) 
        
        if ind_slow < (nb_loop_line+list_params[2]+1): 
            #'''
            if nb_acq_vect is not None:
                nb_acq_vect[ind_slow] = diff # len(a)
            # print('skip_behavior', skip_behavior)    
            #'''
            if skip_behavior[-1]: # and ((ind_slow+1) % 2) and ind_slow>0): # even
            # # skip_behavior[-1] = ((unidirectional and not(lvl_trigger_not_win or usedigfltr)
            # # not((use_dig_fltr_onAlgCmpEv and time_comp_fltr < min_pulse_width_digfltr_6259) or param_ini.lvl_trigger_not_win))
                ind_slow -= int(numpy.floor(ind_slow/2)) # data will be erase after
            
            '''
            N = 50000000
                a=numpy.ones((2,N), dtype=numpy.int16, order='c')
                t0=time.time(); a=numpy.ones((2,N), dtype=numpy.int16, order='c'); print(time.time()-t0) --> 60-70ms
                t0=time.time(); a1=numpy.asarray(a[:, :40000000], order='c'); print(time.time()-t0); print(a1.flags, a1.shape) --> 60-70ms, 90ms if a is F-orient. same as ascontiguousarray
                N2 = 40000000;t0=time.time(); a1=a[:, :N2 ].reshape(N2,2).reshape(2, N2); print(time.time()-t0); print(a1.flags, a1.shape) --> 70-80ms, 90ms if F
                a=numpy.ones((N,2), dtype=numpy.int16, order='c')
                N2 = 40000000;t0=time.time(); a1=a[:N2,: ].reshape(2, N2); print(time.time()-t0); print(a1.flags, a1.shape) --> 13ms !! (130 if F ^^)
            '''
      
            # data_int16 = numpy.zeros((nb_AI_channels, diff), dtype=numpy.int16 )
            data_int16 = arr_reshape[:diff, :nb_AI_channels].reshape(nb_AI_channels, min(diff, len(arr_reshape)))
             # data[:nb_AI_channels, (ind_slow % nb_lines_acumm_acq), :diff].T; print(data_int16 .flags)
              
            # # read is here !   
            try: meth_read(data_int16,  number_of_samples_per_channel = diff, timeout = 0)
                # # print('\nmean = %.3f\n' % numpy.mean(data), clear_arr)
            except nidaqmx.DaqError as err:
                print('in err read AI cbk')
                # # break_here = True # default
                try: cd1 = err.message[:48]=='Read cannot be performed because the NumPy array'
                except AttributeError:  cd1 =True
                cond_arr = (err.error_type == nidaqmx.error_codes.DAQmxErrors.UNKNOWN and cd1)
                if (err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_NOT_YET_AVAILABLE or cond_arr): #MISMATCHED_INPUT_ARRAY_SIZES
                    try: nonzeros_length = len(data_int16[numpy.nonzero(data_int16)])
                    except IndexError: nonzeros_length = 0
                    except MemoryError: nonzeros_length = 0; print('data.shape mem. error', data_int16.shape)
                    if err.error_type == nidaqmx.error_codes.DAQmxErrors.SAMPLES_NOT_YET_AVAILABLE:
                        try: nb_meas_str = analog_input.in_stream.avail_samp_per_chan  
                        except: nb_meas_str =  'N/A'   
                        print('Tried to acq. %d smp but acquired only %d after timeout (avlb %s)' % (diff*nb_AI_channels, nonzeros_length, nb_meas_str))
                    elif cond_arr:
                        print('acquired only %d and not %d because array provided too small !! (meaning many lines in buffer and not a single one)' % ( nonzeros_length, diff*nb_AI_channels))
                else: print('ERR', err.error_type, err)
                    
            # # print((ind_slow % nb_lines_acumm_acq))  
            if ctrl_vect is not None:
                diff2 = analog_input.in_stream.total_samp_per_chan_acquired - total_acq_prev
                ctrl_vect[ind_slow] = diff2-diff
            
            # # data[(ind_slow % nb_lines_acumm_acq)*nb_AI_channels:((ind_slow % nb_lines_acumm_acq)+1)*nb_AI_channels, :min(diff, len(data[0]))] = data_int16
            if diff > data[0,0,:].size: 
                diff0 =diff; diff = data[0,0,:].size
                data_int16 = data_int16[:, :diff]
                print('I had to reject %d samples from %d to match max_expected %d !!' % (diff0 - diff, diff0, diff))
            data[:, (ind_slow % nb_lines_acumm_acq), :diff] = data_int16
        
            # # if (use_dig_galvos):
            # list_params[1] += 1
            # # if (list_params[2] == 1): # first line is not good
            # #     list_params[2] = 0 # # list_params[2] is here a flag for passing 1st line   
            # # else: 
            list_params[1] += 1  # # ind_slow on lines acquired TOTAL 
                # # list_params[2] = 1 
            # # print('data2', ind_slow+1, (nb_loop_line+list_params[2]+1), not((ind_slow+1) % nb_lines_acumm_acq))

            #'''
            if ((nb_loop_line+list_params[2]+1) ==0 or not((ind_slow+1) % nb_lines_acumm_acq) or (ind_slow+1) == (nb_loop_line+list_params[2]+1)): # # send every nb_lines_acumm_acq, without the 1st case 
                # queue_acq_fill.put(data[ind_slow*nb_AI_channels:(ind_slow+1)*nb_AI_channels, :])
                # print('data32', nb_acq_vect.max(), data[:, :, :(ind_slow % nb_lines_acumm_acq)+1].shape, ind_slow, nb_lines_acumm_acq, numpy.mean(data[0, :, (ind_slow % nb_lines_acumm_acq)]), numpy.mean(data[0, :, (ind_slow % nb_lines_acumm_acq)-1]), numpy.mean(data[0, :, 0]), numpy.mean(data[0, :, 1]))
                # # print('ww', nb_lines_acumm_acq, (nb_loop_line+list_params[2]+1)) #data[0, :(ind_slow % nb_lines_acumm_acq)+1, :nb_acq_vect.max()], data[0, :(ind_slow % nb_lines_acumm_acq)+1, :nb_acq_vect.max()].shape)
                print('sent buffer # %d (%d lines)' % (round((ind_slow+1)/ nb_lines_acumm_acq), (ind_slow % nb_lines_acumm_acq)+1)) 
                queue_acq_fill.put([data[:, :(ind_slow % nb_lines_acumm_acq)+1, :nb_acq_vect.max()], False])
                # # data is ab initio larger than real number of samples, here we send the smallest array possible by croping in the zeros to the max of el. 
            #'''
    
def end_newGalvos(system, dev_list, method_watch, DO_parallel_trigger, use_callbacks, DI_parallel_watcher, device_to_use_AI, device_to_use_anlgTrig, device_to_use_watcherTrig, export_trigger, trig_src_end_master_toExp, term_toExp_Ctr0Gate_forAnlgCompEvent_6110, trig_src_end_term_toExp_toWatcher, trig_src_end_toExp_toDIWatcher, ai_trig_control, anlgCompEvent_watcher_task, analog_output_daq_to_galvos, ao_dumb):

    # #
    if ((device_to_use_AI != device_to_use_anlgTrig) and not DO_parallel_trigger and device_to_use_anlgTrig is not None):
        if export_trigger:
            system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % device_to_use_anlgTrig.name), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)))
            if device_to_use_anlgTrig == dev_list[0]: # 6110
                system.disconnect_terms(source_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, term_toExp_Ctr0Gate_forAnlgCompEvent_6110)))
    
    if (use_callbacks and device_to_use_anlgTrig is not None):  
    
        if not DI_parallel_watcher:
            if anlgCompEvent_watcher_task is not None:
                anlgCompEvent_watcher_task.close()
    
        if method_watch == 1: # DI chg detect
            system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_toExp_toDIWatcher))
            
        elif method_watch >= 4: # counter
        
            if device_to_use_anlgTrig.name != device_to_use_watcherTrig.name:
                
                system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_watcherTrig.name, trig_src_end_term_toExp_toWatcher))
                
    if ((device_to_use_AI != device_to_use_anlgTrig) and not DO_parallel_trigger and not method_watch == 3): # master/slave condition, not parallel
        
        if ai_trig_control is not None:
            ai_trig_control.close()
    
    if analog_output_daq_to_galvos is not None: # write all scan before on the AO memory of the DAQ    
        analog_output_daq_to_galvos.close() # clear task
        
    if ao_dumb is not None:
        ao_dumb.close()
        
def calc_max_min_volt_anlg_galvos(obj_mag, size_x_um, size_y_um, offset_x_um, offset_y_um, scan_lens_mm, trig_perc_hyst, y_fast, off_fast_anlgGalvo, off_slow_anlgGalvo, nb_px_X, nb_px_Y, factor_trigger, mult_trig_fact, num_dev_trig, numpy, daq_control_mp2, safety_fact_chan_trig, max_val_volt_galvos):

    # # print('mag !!!!!!!', obj_mag)
    if scan_lens_mm == 50: fact = 89/29/2 # # measured, compared to theory
    elif scan_lens_mm == 45: fact = 89/29/2*10/6*45/50 #  measured
    def fov_um_2_volt_degV(obj_mag, size_um, scan_lens_mm, fact):
        return 0.5*numpy.arctan(obj_mag*fact*size_um/1000/(2*scan_lens_mm))*180/numpy.pi # 1° <-> 1 V
        
    volt_fov_x = fov_um_2_volt_degV(obj_mag, size_x_um, scan_lens_mm, fact)
    volt_fov_y = fov_um_2_volt_degV(obj_mag, size_y_um, scan_lens_mm, fact)
    offset_x_deg = fov_um_2_volt_degV(obj_mag, offset_x_um, scan_lens_mm, fact)
    offset_y_deg = fov_um_2_volt_degV(obj_mag, offset_y_um, scan_lens_mm, fact)
    
    if not y_fast: # x-fast, classic
        # # size_fast_um = size_x_um
        # # size_slow_um = size_y_um
        volt_fov_fast = volt_fov_x
        volt_fov_slow = volt_fov_y
        volt_offset_fast = offset_x_deg + off_fast_anlgGalvo # # offsetX (or y) is the classic offset valid for all scan types, off_fast_anlgGalvo is the one set in the anlg galvos sec. window
        volt_offset_slow = offset_y_deg + off_slow_anlgGalvo
        nb_px_slow = nb_px_Y
        nb_px_fast = nb_px_X
        
        
    volt_pos_max_fast_forTrig = min(max_val_volt_galvos, volt_fov_fast/2 + volt_offset_fast )
    volt_pos_min_fast_forTrig = max(-max_val_volt_galvos, -volt_fov_fast/2 + volt_offset_fast)  # # negative !
    volt_pos_max_slow = min(max_val_volt_galvos, volt_fov_slow/2 + volt_offset_slow) 
    volt_pos_min_slow = max(-max_val_volt_galvos,-volt_fov_slow/2 + volt_offset_slow )
    
    # # # # don't-know-why-factor-of-two
    # # volt_pos_max_slow = volt_pos_max_slow/2 # V
    # # volt_pos_min_slow = volt_pos_min_slow/2 # (2*volt_pos_min_y)**2/(nb_px_slow-1) + volt_pos_min_y # V
    
    # # volt_pos_max_fast = volt_pos_max_fast_forTrig + abs(volt_pos_max_fast_forTrig/factor_trigger)*(mult_trig_fact-1)
    # # volt_pos_min_fast = volt_pos_min_fast_forTrig - abs(volt_pos_min_fast_forTrig/factor_trigger)*(mult_trig_fact-1)
    to_add = (volt_pos_max_fast_forTrig - volt_pos_min_fast_forTrig)*(mult_trig_fact-1)/2
    volt_pos_max_fast = min(max_val_volt_galvos, volt_pos_max_fast_forTrig + to_add)
    volt_pos_min_fast = max(-max_val_volt_galvos, volt_pos_min_fast_forTrig - to_add)
    
        ##  trigger thresh   
    lvl_trig_top = volt_pos_max_fast_forTrig/factor_trigger #- abs(volt_pos_max_fast/factor_trigger)*(mult_trig_fact-1)
    lvl_trig_bottom = volt_pos_min_fast_forTrig/factor_trigger # + abs(volt_pos_min_fast/factor_trigger)*(mult_trig_fact-1)
    # # print(lvl_trig_top, lvl_trig_bottom)
    # if (unidirectional and lvl_trigger_not_win == 2):
    #     lvl_trig_bottom = volt_begin_fast/factor_trigger # only one trigger # + abs(volt_pos_min_fast/factor_trigger)*(mult_trig_fact-1) 
    
    # print(volt_pos_min_fast_forTrig, volt_pos_min_fast)
         
    hyst_trig = (volt_pos_min_fast_forTrig - volt_pos_min_fast)/factor_trigger*trig_perc_hyst/100 # # V
    
    # print('factor_trigger', hyst_trig)
    
    min_val_read_trig = lvl_trig_bottom*safety_fact_chan_trig
    max_val_read_trig = lvl_trig_top*safety_fact_chan_trig
    val = max(abs(min_val_read_trig), abs(max_val_read_trig))
    
    if num_dev_trig == 0: # 6110
        max_val = 42
    else: # 6259
        max_val = 10

    bound_read_trig = daq_control_mp2.bounds_AI_daq(val, num_dev_trig+1, max_val)  # # for add_ai_voltage_chan if channel trigger
    
    if num_dev_trig == 0: # # 6110
        bits_trig = 8
    elif num_dev_trig == 1: # # 6259
        bits_trig = 10

    step_trig = (2*bound_read_trig)/2**bits_trig
    lvl_trig_top = step_trig*round(lvl_trig_top/step_trig)
    lvl_trig_bottom = step_trig*round(lvl_trig_bottom/step_trig)
    
    hyst_trig = min(bound_read_trig +  lvl_trig_bottom, hyst_trig)
    
    hyst_trig = step_trig*round(hyst_trig/step_trig) # V
    
    # print('factor_trigger2', hyst_trig)
    
    return nb_px_fast, nb_px_slow, volt_offset_fast, volt_offset_slow, volt_pos_max_fast_forTrig, volt_pos_min_fast_forTrig, volt_pos_max_fast, volt_pos_min_fast, volt_pos_max_slow, volt_pos_min_slow, lvl_trig_top, lvl_trig_bottom, hyst_trig, bound_read_trig
                
        
def params_newGalvos(nb_pmt_channel, unidirectional, num_dev_AO, device_to_use_AI, device_to_use_anlgTrig, device_to_use_watcherTrig, correct_unidirektionnal, export_smpclk, export_trigger, DO_parallel_trigger, write_scan_before, offset_x_um, offset_y_um, size_x_um, size_y_um, nb_px_X, nb_px_Y, obj_mag, scan_lens_mm, y_fast, time_by_point, galvos_reversing_time_script, eff_wvfrm_an_galvos, dev_list, use_dig_galvos, method_watch, update_time, mult_trig_fact, trig_perc_hyst, skip_behavior, off_fast_anlgGalvo, off_slow_anlgGalvo, fact_buffer, warnings, numpy, param_ini, write_task, daq_control_mp2, system):
    
    from scipy import optimize
    
    if len(dev_list) > 1: num_dev_trig = int(device_to_use_anlgTrig==dev_list[1])
    else: num_dev_trig = 0
    
    if device_to_use_AI == dev_list[0]:  # 6110
        sample_rate_min = param_ini.sample_rate_min_6110
        sample_rate_min_other = param_ini.sample_rate_min_6259
        term_trig_name = param_ini.term_trig_name_6110
        term_trig_other = param_ini.term_trig_name_6259
        samp_src_end_master_toExp = param_ini.term_6259_clckExt
        trig_src_end_master_toExp = param_ini.term_6259_trigExt
        samp_src_end_slave_if2Dev = param_ini.term_6110_clckExt
        trig_src_end_slave_if2Dev = param_ini.term_6110_trigExt
        
    else: # 6259
        sample_rate_min = param_ini.sample_rate_min_6259
        sample_rate_min_other = param_ini.sample_rate_min_6110
        samp_src_end_master_toExp = param_ini.term_6110_clckExt 
        trig_src_end_master_toExp = param_ini.term_6110_trigExt 
        samp_src_end_slave_if2Dev = param_ini.term_6259_clckExt
        trig_src_end_slave_if2Dev = param_ini.term_6259_trigExt
        term_trig_name = param_ini.term_trig_name_6259
        term_trig_other = param_ini.term_trig_name_6110
    
    if use_dig_galvos:
        term_trig_name = param_ini.term_trig_name_digital
        export_smpclk = 0 
        export_trigger = 0
        use_chan_trigger = False
        device_to_use_AO = device_to_use_anlgTrig = ai_trig_src_name_master= None
        time_trig_paused = 0
    else:
        device_to_use_AO = dev_list[num_dev_AO] # device to use for Write to galvos
        use_chan_trigger = param_ini.use_chan_trigger
    
    lvl_trigger_not_win = param_ini.lvl_trigger_not_win
        
    factor_trigger = param_ini.factor_trigger
        
    # # print('use_dig_galvos l381', use_dig_galvos, export_trigger, export_smpclk)
    # # ********************************************
    # # -------- AI read params --------------------
    # # ********************************************
                
    if param_ini.use_velocity_trigger:
        factor_trigger = 3/0.19 + 0
        
    if DO_parallel_trigger:
        nb_hysteresis_trig_subs = [2, 2]
    else:
        nb_hysteresis_trig_subs = None
    
    # # *****************************************************
    # # -------- sync parameters ----------------------------
    # # *****************************************************

    if method_watch == 1: # for 6259 only, DI analyse trigger with chg detection Event
        cond1 = device_to_use_AI != dev_list[1] if len(dev_list) > 1 else True
        if cond1:
            raise('cannot use this mode on 6110')
        else:
            print('connect %s term of %s to %s term of %s' % (param_ini.trig_src_end_term_toExp_toWatcher, device_to_use_anlgTrig, param_ini.term_DI,  device_to_use_watcherTrig))
        
    elif method_watch == 2:  # sample clock detect, has the drawback to have to set the rate,  FOR 6110 only, !! was not good when tested !!
    
        if device_to_use_watcherTrig != dev_list[0]: # 
            warnings.warn('using this mode with 6259 is not necessary, use DI chg detect evnt instead')
        else:
            if device_to_use_watcherTrig != device_to_use_anlgTrig:
                
                print('connect %s term of %s to %s term of %s' % (param_ini.trig_src_end_term_toExp_toWatcher, device_to_use_anlgTrig, param_ini.trig_src_end_term_toExp_toWatcher,  device_to_use_watcherTrig))
                
    elif method_watch == 3:  # anlg trig watch itself (2 cards)
        
        if device_to_use_anlgTrig == device_to_use_AI:   
            raise('You have to set 2 different devices for AI and trig control for this mode')
        else:
            device_to_use_watcherTrig = device_to_use_anlgTrig
            print('be sure to export trigger or sample clk')
            
    elif method_watch >= 4: # counter output, 6110 or 6259, both or 1 card
        if device_to_use_anlgTrig is not None: dev_temp = device_to_use_anlgTrig
        else: dev_temp = device_to_use_AI
        if (device_to_use_watcherTrig != device_to_use_anlgTrig or (method_watch == 6 and param_ini.use_dig_fltr_onAlgCmpEv)):
            print('be sure that AnlgCompEvent of the %s that trigs is connected to the %s that watch trig' % (dev_temp , device_to_use_watcherTrig))
        
    if (device_to_use_anlgTrig is not None and device_to_use_AI != device_to_use_anlgTrig):
        print('be sure that AnlgCompEvent of the %s that trigs is connected to the %s that reads AI, and that its trigger is lvl digital' % (device_to_use_anlgTrig, device_to_use_AI))
        
    if ((device_to_use_AI == device_to_use_anlgTrig) and (export_smpclk or export_trigger or DO_parallel_trigger)): # NOT master/slave condition
        warnings.warn('(newglavfunc) you wanted to NOT export signals but the config is master/slave !')
        export_smpclk = 0; export_trigger = 0; DO_parallel_trigger = 0
    # elif ((device_to_use_AI != device_to_use_anlgTrig) and (not export_smpclk and not export_trigger and not DO_parallel_trigger)): # master/slave condition
    #     warnings.warn(' you wanted master/slave but there`s no export signals : using DO_parallel !')
    #     DO_parallel_trigger = 1; export_smpclk = 0; export_trigger = 0
    
    if (export_smpclk and export_trigger): # not possible to have both
        export_smpclk = 1
        export_trigger = 0
        
    if (export_smpclk and DO_parallel_trigger): # not possible to have both
        DO_parallel_trigger = 1
        export_trigger = 0
        
    if (device_to_use_anlgTrig is not None and device_to_use_AI != device_to_use_anlgTrig):
        if not (export_trigger or export_smpclk):
            export_trigger  = 1
            export_smpclk = 0
            print('To use a master/slave config, you have to export trigger or samp clk (so I will export trigger right now)!')
        
    
    if (use_chan_trigger and device_to_use_AI == device_to_use_anlgTrig and device_to_use_AI == dev_list[0]): # on 6259, ai0 has to be the only channel ! (so cannot read, just control trigger)
        # nb_pmt_channel is without the (possible) trigger
        nb_AI_channels = nb_pmt_channel + 1
    else:
        nb_AI_channels = nb_pmt_channel
    
    samp_src_term_slave = '' # sampleclocktimebase (onboard)
    
    # # list_PMT_chan = []
    # # for ii in range(nb_pmt_channel):
    # #     list_PMT_chan.append(chan_PMT_names[ii])
        
    
    if (len(dev_list) <= 1 or device_to_use_anlgTrig == dev_list[0]):
        trig_src_end_chan  = param_ini.trig_src_end_chan_6110 
    elif device_to_use_anlgTrig == dev_list[1]:
        trig_src_end_chan = param_ini.trig_src_end_chan_6259  # you can use only one channel for pause trigger on 6259
    
    if device_to_use_anlgTrig is not None: # # use an anlg trigger detect
        if use_chan_trigger: # will be modified after if necessary
            trig_src_name_slave = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_chan)) # from chan
            
        else: # use a terminal port PFI0 directly
            if (len(dev_list) > 1 and device_to_use_anlgTrig == dev_list[1]): # 6259
                trig_src_name_slave = term_trig_name
            else: # 6110
                trig_src_name_slave = ('/%s/%s' % (device_to_use_anlgTrig.name, term_trig_name))  # from 6110
    else: trig_src_name_slave = param_ini.trig_src_name_dig_galvos # dig trigger
        
    trig_src_name_master = trig_src_name_slave  # in any cases, slave redefined after if necessary
                
    samp_src_term_master_toExp = 0
    
    if export_smpclk: # sync samps clocks, which limits the rate to [0.1, 1.25MHz] # receive sample clock from 6259, so no trigger on 6110
        if not use_chan_trigger: # will be modified after if necessary
            trig_src_name_slave = ('/%s/%s' % (device_to_use_anlgTrig.name, term_trig_other))  # it will be the other 
        
        samp_src_term_slave = ('/%s/%s' % (device_to_use_AI.name, samp_src_end_slave_if2Dev))
        samp_src_term_master_toExp = ('/%s/%s' % (device_to_use_anlgTrig.name, samp_src_end_master_toExp))
        trig_src_name_master = trig_src_name_slave  # in any cases, slave redefined after if necessary
    
    elif (export_trigger or DO_parallel_trigger):
        
        trig_src_name_slave = ('/%s/%s' % (device_to_use_AI.name, trig_src_end_slave_if2Dev ))
        if (trig_src_end_master_toExp == param_ini.term_toExp_Ctr0Gate_forAnlgCompEvent_6110 and device_to_use_anlgTrig == dev_list[0]):
            trig_src_end_master_toExp = param_ini.term_toExp_forAnlgCompEvent_6110
        # #trig_src_term_master_toExp = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp))
        if not use_chan_trigger: # will be modified after if necessary
            if (len(dev_list) > 1 and device_to_use_anlgTrig == dev_list[1]): # 6259
                trig_src_name_master = term_trig_other
            else: # 6110
                trig_src_name_master = ('/%s/%s' % (device_to_use_anlgTrig.name, term_trig_other))
        else:
            trig_src_name_master = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_chan))
    
    if device_to_use_anlgTrig is not None:        
        # if (device_to_use_AI != device_to_use_anlgTrig): # master/slave condition
        ai_trig_src_name_master = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_chan)) # from chan
        
    if (use_chan_trigger):
        ai_trig_src_name_master = ai_trig_src_name_master[1:]
        if len(trig_src_name_master) > 8: # is of type /Dev0/PFI or ai
            trig_src_name_master = trig_src_name_master[1:]
            
    # # if device_to_use_AI == dev_list[1]:   
    # #     if len(trig_src_name_slave) > 8: # is of type /Dev0/PFI or ai
    # #         trig_src_name_slave = trig_src_name_slave[1:]
            
    if DO_parallel_trigger:
        if device_to_use_AI == dev_list[0]: # 6110, cannot output DO signal on PFI
            trig_src_name_slave = ('/%s/%s' % (device_to_use_AI.name, 'PFI1' ))
        else:
            trig_src_name_slave = ('/%s/%s' % (device_to_use_AI.name, param_ini.term_trig_name_digital ))
                
    if use_dig_galvos:
        duration_one_line_imposed = time_by_point*nb_px_X
        duration_one_line_real = duration_one_line_imposed/param_ini.eff_unid_diggalvos if unidirectional else duration_one_line_imposed # # dig galvos effciency for unidirek is estimated at 84%
        time_expected_sec = nb_px_Y*duration_one_line_imposed
        nb_loop_line = nb_px_slow = nb_px_Y
        time_comp_fltr = param_ini.SM_cycle # sec
        nb_px_fast=nb_px_X
        volt_pos_max_fast= volt_pos_min_fast=volt_offset_fast= volt_offset_slow =sample_rate_AO_wanted =  sin_angle = cos_angle=nb_pts_daq_one_pattern=min_val_volt_galvos=max_val_volt_galvos=one_scan_pattern_vect= line_slow_daq_vect= line_slow_daq_vect_last= daq_pos_max_slow= daq_pos_min_slow= volt_pos_min_slow=volt_begin_fast=bound_read_trig=trig_src_end_chan=None
        list_trig_volt = [0]*3
    else: # # anlg new galvos
        
        # # ********************************************
        # # ------- scan params ------------------------
        # # ********************************************
            
        cos_angle = numpy.cos(param_ini.angle_rot_degree_new_galvos/180*numpy.pi)
        sin_angle = numpy.sin(param_ini.angle_rot_degree_new_galvos/180*numpy.pi)
        
        nb_px_fast, nb_px_slow, volt_offset_fast, volt_offset_slow, volt_pos_max_fast_forTrig, volt_pos_min_fast_forTrig, volt_pos_max_fast, volt_pos_min_fast, volt_pos_max_slow, volt_pos_min_slow, lvl_trig_top, lvl_trig_bottom, hyst_trig, bound_read_trig = calc_max_min_volt_anlg_galvos(obj_mag, size_x_um, size_y_um, offset_x_um, offset_y_um, scan_lens_mm, trig_perc_hyst, y_fast, off_fast_anlgGalvo, off_slow_anlgGalvo, nb_px_X, nb_px_Y, factor_trigger, mult_trig_fact, num_dev_trig, numpy, daq_control_mp2, param_ini.safety_fact_chan_trig, param_ini.max_val_volt_galvos)
        
        # print(volt_pos_max_fast, volt_pos_min_fast)
        # err
        
        duration_one_line_imposed = time_by_point*nb_px_fast*mult_trig_fact
    
        min_val_volt_galvos = param_ini.min_val_volt_galvos
        max_val_volt_galvos = param_ini.max_val_volt_galvos
        if (len(dev_list) > 1 and device_to_use_AO == dev_list[1]): # 6259
            min_val = min( volt_pos_min_fast - 0.5*param_ini.settling_time_galvo_us*1e-6/duration_one_line_imposed*(volt_pos_max_fast-volt_pos_min_fast), volt_pos_min_slow)*param_ini.safety_ao_gen_fact
            max_val = max( volt_pos_max_fast + 0.5*param_ini.settling_time_galvo_us*1e-6/duration_one_line_imposed*(volt_pos_max_fast-volt_pos_min_fast), volt_pos_max_slow)*param_ini.safety_ao_gen_fact
            
            ref = max(max_val, abs(min_val))
            if not param_ini.ext_ref_AO_range: # for 6259, use an internal src dflt
                if ref < 5:
                    min_val_volt_galvos = -5
                    max_val_volt_galvos = 5
            else: # for 6259, use an external src on APFI0 for determining the range of AO generation: need another AO (from 6110 ?) to supply a voltage
                max_val_volt_galvos = numpy.ceil(ref*10)/10
                min_val_volt_galvos = - max_val_volt_galvos
        
        DAQ_pos_max_fast = write_task.conv_volt2int16(volt_pos_max_fast, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        DAQ_pos_min_fast = write_task.conv_volt2int16(volt_pos_min_fast, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        
        # # nb_DAQ_fast_theo = round(duration_one_line_real*sample_rate_galvos) + 1
        nb_DAQ_fast_theo = DAQ_pos_max_fast - DAQ_pos_min_fast + 1
        if (nb_DAQ_fast_theo% 2): # odd
            DAQ_pos_max_fast +=1 # now even
            nb_DAQ_fast_theo += 1
            
        # volt_pos_max_fast = write_task.conv_int16tovolt(DAQ_pos_max_fast, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        
        maxSize_npVect_measured_forWriting = 64/param_ini.bits_write*round(param_ini.max_size_np_array/2) # (measured by random numpy array generation float64, so four times better for int16)
        # could up to 2e9 in python 64 bits !
        # 2 because X and Y !
        
        max_buf_size_AO_chanR_2chansW = param_ini.calc_max_buf_size(nb_pmt_channel)[1]
        
        Npts_max_forGen_oneline = min(max_buf_size_AO_chanR_2chansW/nb_px_slow, maxSize_npVect_measured_forWriting) # for one line
        
        noise_positionControl = 5/1000/factor_trigger # ° or V
        
        if (volt_pos_max_fast - volt_pos_min_fast) <= noise_positionControl*param_ini.security_noise_factor:
            print('error, scan too small to be performed')
            # raise error
        
        ratio_full_scale = (volt_pos_max_fast - volt_pos_min_fast)/(param_ini.max_val_volt_galvos - param_ini.min_val_volt_galvos)
        time_line_min_considering_BW_us = max(param_ini.small_angle_step_response_us*param_ini.smAngStpResp_safeFac, ratio_full_scale/param_ini.BW_full_scale_galvos*1e6, param_ini.small_angle_step/param_ini.BW_small_steps_galvos*1e6) # us
        
        time_line_min_galvos = max(time_line_min_considering_BW_us, (volt_pos_max_fast -volt_pos_min_fast)/param_ini.limit_small_step_angle_measured*param_ini.small_angle_step_response_us)*1e-6 # s
        
            ## sample rate AO
        # # sample_rate_AO_wanted = max(sample_rate_AO_min_imposed, (volt_pos_max_fast -volt_pos_min_fast)/param_ini.small_angle_step/duration_one_line_real)
        
        T_inc_apriori_us = param_ini.settling_time_galvo_us/param_ini.divider_settling_time_avoid_step_dflt
        if T_inc_apriori_us < 2*duration_one_line_imposed/nb_DAQ_fast_theo*1e6: T_inc_apriori_us = 2*duration_one_line_imposed/nb_DAQ_fast_theo*1e6 # # long scan
        # # print('num_step_in_one_ramp',  T_inc_apriori_us,0.5*duration_one_line_imposed/nb_DAQ_fast_theo*1e6)

        num_step_in_one_ramp = duration_one_line_imposed/(T_inc_apriori_us*1e-6) # Nr(temp)
        # # print('num_step_in_one_ramp',  T_inc_apriori_us, num_step_in_one_ramp, nb_DAQ_fast_theo)#step_size_daq,

        step_size_daq = nb_DAQ_fast_theo/num_step_in_one_ramp # Sz or W1D, not an even integer
        step_size_daq = max(1, int(numpy.floor(step_size_daq / 2.)) * 2) # previous even integer
        # # print('step_size_daq2',  step_size_daq)#step_size_daq,

        num_step_in_one_ramp = int(nb_DAQ_fast_theo/step_size_daq) # Nr, good number of steps
        sample_rate_AO_wanted = num_step_in_one_ramp/duration_one_line_imposed
        
        time_line_max_galvos = (Npts_max_forGen_oneline-1)/sample_rate_AO_wanted  # s
        
        # if  # more time spent on dead time than on acquisition
        #    print('Line time is too short for the galvo to reverse position fast enough : the acceleration part will be partially included in acquisition, unless you increase the line time')
            
        # duration_one_line_real = duration_one_line_imposed*triggerAddSafeFactor + reversing_time # sec    
        duration_one_line_real = duration_one_line_imposed*100/eff_wvfrm_an_galvos # efficiency of the ramp, taking into account non-linear parts of the ramp
        
        if duration_one_line_real < time_line_min_galvos:
            print('\n Duration of one line too small to ensure correct galvo move : either increase your exposure time or your number of pixel ! \n')
            raise(MemoryError)
            # if line_time too small, galvos will not be able to follow
        elif duration_one_line_real > time_line_max_galvos:
            print('\n Duration of one line too large for the RAM and galvo parameters : either decrease your exposure time or your number of pixel ! \n')
            # the galvo has chances to make steps (instead of continuous moves) if not enough points inside the command array
            # Problem is the buffer to write to galvo is limited
            raise(MemoryError)
        
        time_expected_sec = nb_px_slow*duration_one_line_real # taking into account the reversing time

        num_step_speedup = int(round(sample_rate_AO_wanted*param_ini.settling_time_galvo_us*1e-6)) # # Ns,  number of points for speedup, before the ramp
        
        volt_begin_fast = volt_pos_min_fast - write_task.conv_int16tovolt(0.5*num_step_speedup*step_size_daq, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        daq_begin_fast = write_task.conv_volt2int16(volt_pos_min_fast, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write) - 0.5*num_step_speedup*step_size_daq
        volt_end_fast = volt_pos_max_fast + write_task.conv_int16tovolt(0.5*num_step_speedup*step_size_daq, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        
        if volt_begin_fast < param_ini.min_val_volt_galvos or volt_end_fast > param_ini.max_val_volt_galvos:
            print('Parameters are such that the flyback makes the voltage values to saturate: the scan limits will be reduced to allow to stay in the bounds')
            
            if volt_begin_fast < param_ini.min_val_volt_galvos:
                volt_pos_min_fast = param_ini.min_val_volt_galvos + write_task.conv_int16tovolt(0.5*num_step_speedup*step_size_daq, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
            if volt_end_fast > param_ini.max_val_volt_galvos:
                volt_pos_max_fast = param_ini.max_val_volt_galvos - write_task.conv_int16tovolt(0.5*num_step_speedup*step_size_daq, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
            
        if time_expected_sec <= param_ini.duration_scan_prewrite_in_buffer: # scan is very short and would even be contained in pre-writing
            write_scan_before = 1
    
        if correct_unidirektionnal == 2: # act as it is bidirek
            unidirectional = 0
        if unidirectional:
            shape_reverse_movement = 0
        else:
            correct_unidirektionnal = 0
    
            ##  scan vect
            
        line_fast_linear = numpy.int16(step_size_daq*numpy.arange(0,  num_step_in_one_ramp+num_step_speedup, 1,  dtype=numpy.int16) + daq_begin_fast)
        
        # # ********************************************
        # # ------- galvos hardware --------------------
        # # **********************************************
        
        angle_range = volt_pos_max_fast - volt_pos_min_fast
        
        if param_ini.revers_time_meth == 0: # like the digital galvos, but was shown to be not similar to reality
            x0_dflt = 15e-5 # s
    
            reversing_time = galvos_reversing_time_script.calc_reversing_time_galvos(optimize, numpy, param_ini.induct_coil_H, param_ini.ohm_coil_val, param_ini.max_ddp, param_ini.torque_constant, param_ini.total_inertia, angle_range, duration_one_line_imposed, x0_dflt)
        
        elif param_ini.revers_time_meth == 1:
            reversing_time = 2*1/(param_ini.small_angle_step_response_us*1e-6)/(180/numpy.pi*(param_ini.max_rms_current_one_axis*param_ini.torque_constant/param_ini.total_inertia))
            
        elif param_ini.revers_time_meth == 2: # imposed
            fact_adj_scan_time = 1.01 # this factor just to ensure the scan time is equal to the theo scan time
            reversing_time = duration_one_line_real/fact_adj_scan_time - duration_one_line_imposed - param_ini.settling_time_galvo_us*1e-6 # # Tf
            
            # # !!
            # # settling_time_galvo_us is also Ts
            
        # flyback_vel = 2*numpy.pi/reversing_time # W2 (rad/sec), Circular Velocity of Flyback
        num_pts_flyback = int(round(reversing_time*sample_rate_AO_wanted)) # Nf
        flyback_vel = 2*numpy.pi/num_pts_flyback # W2 (rad/sec), Circular Velocity of Flyback
    
        # ampl_flyback = -angle_range*(1 + 1/duration_one_line_imposed*(reversing_time+param_ini.settling_time_galvo_us*1e-6))# # A2, Amplitude of the flyback waveform (deg)
        ampl_flyback = -((DAQ_pos_max_fast-DAQ_pos_min_fast) + step_size_daq*(num_pts_flyback + num_step_speedup)) # # A2, Amplitude of the flyback waveform (deg)
        
        # # st_pt_flyback = volt_pos_max_fast + 0.5*param_ini.settling_time_galvo_us*1e-6*angle_range/duration_one_line_imposed # # Astart
        st_pt_flyback = DAQ_pos_max_fast + 0.5*step_size_daq*num_step_speedup # # Astart
        
        vect_n = numpy.arange(0,  num_pts_flyback, 1)
        def fun_flyback(x, A2, W2, W1, As):
            return A2/(2*numpy.pi)*(W2*x - numpy.sin(W2*x)) + W1*x + As
            
        # # flyback_vect = ampl_flyback/(2*numpy.pi)*(flyback_vel*vect_n - numpy.sin(flyback_vel*vect_n)) + step_size_daq*vect_n + st_pt_flyback
        flyback_vect = numpy.int16(fun_flyback(vect_n, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback))
        
        # # print(line_fast_linear.dtype, flyback_vect.dtype)
        
        one_scan_pattern_vect = numpy.concatenate((line_fast_linear, flyback_vect))
        
        # upper_bound_ini=(st_pt_flyback+abs(ampl_flyback)/(2*3.14))/(abs(ampl_flyback)/(2*3.14)*flyback_vel-step_size_daq) # # it's sure it's under 0
    
        top_DAQ_trig = write_task.conv_volt2int16(lvl_trig_top*factor_trigger, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        btm_DAQ_trig = write_task.conv_volt2int16(lvl_trig_bottom*factor_trigger, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
    
        if lvl_trigger_not_win == 2: # # pause only on the dec/acc of the bottom
            btm_DAQ_trig_withhyst = write_task.conv_volt2int16(lvl_trig_bottom*factor_trigger + hyst_trig, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
            
            upper_bound_end = (st_pt_flyback+abs(ampl_flyback)/(2*3.14) + max(0, -btm_DAQ_trig))/(abs(ampl_flyback)/(2*3.14)*flyback_vel-step_size_daq) # # it's sure it's under 0
            # # print('wala !!!', daq_begin_fast, btm_DAQ_trig, upper_bound_end, fun_flyback(upper_bound_end, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback)-btm_DAQ_trig, fun_flyback(0, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback)-btm_DAQ_trig, ampl_flyback, st_pt_flyback)
            
            sol_ini = galvos_reversing_time_script.calc_reversing_time_anlg_galvos(optimize, fun_flyback, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback, btm_DAQ_trig, upper_bound_end) # pos at the end of the flyback at lower trig
            # # the total time that the flyback last inside the pause trigger window, in terms of AO samples
            
            sol_end = max(0, (btm_DAQ_trig_withhyst - daq_begin_fast)/step_size_daq)
            
            time_trig_paused = ((num_pts_flyback-sol_ini) + sol_end)/sample_rate_AO_wanted # # in sec
            
            time_comp_fltr = duration_one_line_real - time_trig_paused
    
        else: # window trigger, pause on the two acc/dec (top & bottom)
        
            nb_beg_linear = max(0, (btm_DAQ_trig - daq_begin_fast)/step_size_daq) # nb el. at the beg. of the ramp before lower trig
            nb_end_linear = (num_step_in_one_ramp+num_step_speedup) - max(0, (top_DAQ_trig - daq_begin_fast)/step_size_daq) # nb el. at the end of the ramp after upper trig
    
            upper_bound_ini=(st_pt_flyback+abs(ampl_flyback)/(2*3.14) + max(0, -top_DAQ_trig))/(abs(ampl_flyback)/(2*3.14)*flyback_vel-step_size_daq) # # it's sure it's under 0
            upper_bound_end = (st_pt_flyback+abs(ampl_flyback)/(2*3.14) + max(0, -btm_DAQ_trig))/(abs(ampl_flyback)/(2*3.14)*flyback_vel-step_size_daq) # # it's sure it's under 0
            
            sol_ini = galvos_reversing_time_script.calc_reversing_time_anlg_galvos(optimize, fun_flyback, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback, top_DAQ_trig, upper_bound_ini)  # pos at the beg. of the flyback at upper trig
            sol_end = galvos_reversing_time_script.calc_reversing_time_anlg_galvos(optimize, fun_flyback, ampl_flyback, flyback_vel, step_size_daq, st_pt_flyback, btm_DAQ_trig, upper_bound_end) # pos at the end of the flyback at lower trig
            
            time_trig_paused = (nb_beg_linear + nb_end_linear + num_pts_flyback - (sol_end-sol_ini))/sample_rate_AO_wanted # # in sec
            
            time_comp_fltr = (sol_end-sol_ini)/sample_rate_AO_wanted # sec  # # time_flyback_unpaused_trig
        
            ## slow
        daq_pos_min_slow = write_task.conv_volt2int16(volt_pos_min_slow, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        daq_pos_max_slow = write_task.conv_volt2int16(volt_pos_max_slow, min_val_volt_galvos, max_val_volt_galvos, param_ini.bits_write)
        
        nb_pts_daq_one_pattern = len(one_scan_pattern_vect)
        
        # step_slow = 1/(nb_pts_daq_one_pattern - 1)*(daq_pos_max_slow - daq_pos_min_slow)
        step_slow = 1/(nb_px_slow - 1)*(daq_pos_max_slow - daq_pos_min_slow)
    
        ampl_flyback_slow = step_slow # + step_size_daq*(num_pts_flyback + num_step_speedup) # # A2, Amplitude of the flyback waveform (deg)
        # nb_DAQ_slow_theo = (daq_pos_max_slow - daq_pos_min_slow) + 1
        # if (nb_DAQ_slow_theo % 2): # odd
        #     DAQ_pos_max_slow +=1 # now even
        #     nb_DAQ_slow_theo += 1
        #     
        # step_size_daq = nb_DAQ_slow_theo/num_step_in_one_ramp # Sz or W1D, not an even integer
        # step_size_daq =  int(numpy.floor(step_size_daq / 2.)) * 2 # previous even integer
        
        flyback_vect_slow = numpy.int16(ampl_flyback_slow/(2*numpy.pi)*(flyback_vel*vect_n - numpy.sin(flyback_vel*vect_n)) + daq_pos_min_slow) # # is equal to daq_pos_min_slow at first then daq_pos_min_slow+ampl_flyback_slow
    
        base = numpy.int16(numpy.ones(num_step_in_one_ramp+num_step_speedup)*daq_pos_min_slow)
        line_slow_daq_vect = numpy.concatenate((base, flyback_vect_slow))
        
        line_slow_daq_vect_last = numpy.concatenate((base*(daq_pos_max_slow/daq_pos_min_slow), numpy.int16((daq_pos_min_slow - daq_pos_max_slow)/(2*numpy.pi)*(flyback_vel*vect_n - numpy.sin(flyback_vel*vect_n)) + daq_pos_max_slow)))
        
        if nb_pts_daq_one_pattern > Npts_max_forGen_oneline: # too many points in one line to properly define the write vector
        # typically means that line_time > 50sec with 10kHz rate
            print("too many points in one line to properly define the write vector: you'll have to write a part in live")
        
        list_trig_volt = [lvl_trig_top, lvl_trig_bottom, hyst_trig ]
        
        ##  continued 
    
    if device_to_use_watcherTrig == dev_list[0]:
        use_dig_fltr_onAlgCmpEv = False
    else:
        use_dig_fltr_onAlgCmpEv = param_ini.use_dig_fltr_onAlgCmpEv
        
    if time_comp_fltr > param_ini.min_pulse_width_digfltr_6259_2: #longest (2.56ms)
        min_pulse_width_digfltr_6259 = param_ini.min_pulse_width_digfltr_6259_2
    elif time_comp_fltr > param_ini.min_pulse_width_digfltr_6259: # shortest (6us)
        min_pulse_width_digfltr_6259 = param_ini.min_pulse_width_digfltr_6259
    else:
        min_pulse_width_digfltr_6259 = 0
    
    # # print('skip_behavior', lvl_trigger_not_win, not(lvl_trigger_not_win or (use_dig_fltr_onAlgCmpEv and time_comp_fltr < min_pulse_width_digfltr_6259)))
    
    skip_behavior.append((unidirectional and not(lvl_trigger_not_win or (use_dig_fltr_onAlgCmpEv and time_comp_fltr < min_pulse_width_digfltr_6259)) ))
    # # for unidirek, skip half of the lines of not		    # # for unidirek, skip half of the lines of not
    # # True if has to skip the flyback		    # # True if has to skip the flyback
            # # skip_behavior is [nb_skip,  pause_trigger_diggalvo,  callback_notmeasline, unirek_skip_half_of_lines]

    if (unidirectional and skip_behavior[-1]): nb_loop_line = nb_px_slow*2
    else: nb_loop_line = nb_px_slow
        
    # # if (not unidirectional and lvl_trigger_not_win == 2): # pause only on top and not for flyback and bottom
    # #     nb_loop_line = math.ceil(nb_loop_line/2)
    # # # elif use_dig_galvos:
    # # #     nb_loop_line += 1
    
    pack_params_new_galvos =  [device_to_use_anlgTrig, device_to_use_watcherTrig, param_ini.num_ctrdflt, volt_pos_max_fast, volt_pos_min_fast, trig_src_name_slave, ai_trig_src_name_master, samp_src_term_slave, sample_rate_min_other, samp_src_term_master_toExp, trig_src_name_master, trig_src_end_master_toExp, param_ini.trig_src_end_toExp_toDIWatcher, term_trig_other, term_trig_name, trig_src_end_chan, unidirectional, factor_trigger, use_chan_trigger, lvl_trigger_not_win, volt_offset_fast, volt_offset_slow, min_pulse_width_digfltr_6259, bound_read_trig, system, nb_px_slow, nb_px_fast, time_by_point, [time_trig_paused, duration_one_line_real], list_trig_volt, skip_behavior[-1], export_smpclk, export_trigger, sample_rate_AO_wanted, param_ini.force_buffer_small, fact_buffer]
    
        
    return device_to_use_AO, factor_trigger, trig_src_name_slave, samp_src_term_slave, trig_src_name_master, samp_src_term_master_toExp, ai_trig_src_name_master, sin_angle , cos_angle, duration_one_line_real, write_scan_before, nb_hysteresis_trig_subs, sample_rate_min, sample_rate_min_other, trig_src_end_master_toExp, time_expected_sec, duration_one_line_imposed, sample_rate_AO_wanted, nb_px_fast, nb_px_slow, nb_loop_line, nb_pts_daq_one_pattern, term_trig_other, term_trig_name, trig_src_end_chan, nb_AI_channels, export_smpclk, export_trigger, pack_params_new_galvos, min_val_volt_galvos, max_val_volt_galvos, one_scan_pattern_vect, line_slow_daq_vect, line_slow_daq_vect_last, daq_pos_max_slow, daq_pos_min_slow, [volt_pos_min_slow, volt_begin_fast], time_comp_fltr, min_pulse_width_digfltr_6259, use_dig_fltr_onAlgCmpEv, skip_behavior
    
def get_anlg_galvo_pos(nidaqmx, dev, ai_readposX_anlggalvo, ai_readposY_anlggalvo):

    ai2 =  nidaqmx.Task()
        
    max_volt = 10
    ai2.ai_channels.add_ai_voltage_chan(('%s/%s, %s/%s' % (dev, ai_readposX_anlggalvo, dev, ai_readposY_anlggalvo)), min_val=0, max_val = max_volt) # ON DEMAND
    
    aa = ai2.read() # fast, slow (ai0, ai1)

    ai2.close()
    
    return aa # fast, slow (ai0, ai1)

    
## function to control via plot (used only in test, not in GUI !)


def plot_result_scan_galvo(plt, numpy, param_ini, array_fill_loops2, nb_acq_vect, nb_pmt_channel, nb_px_slow, nb_px_fast, oversampling, unidirectional, y_fast, data, number_of_samples, max_read_val_volt, min_read_val_volt, device_to_use_AI, device_to_use_anlgTrig):
    '''
    used only in test, not in GUI !
    '''
    
    plt.close('all')
    plt.plot(nb_acq_vect);plt.show(False)
    
    fact = 10
    print('std', numpy.std(nb_acq_vect[fact:len(nb_acq_vect)-fact]))
    max_value_pixel = 2**16-1
    
    array_3d = numpy.ones(shape=(nb_pmt_channel, nb_px_slow, nb_px_fast), dtype=param_ini.precision_float_numpy)
    
    # err
    read_buffer_offset_reverse = 0 # warning !!
    read_buffer_offset_dir = 0
    verbose = 0
    method_fast = 0
    for ind_slow in range(nb_px_slow):
        oversampling_real = oversampling #int(nb_acq_vect[ind_slow]/nb_px_fast) # the last px is incomplete # oversampling #
    
        if (not unidirectional and ((ind_slow) % 2)): # odd
            data_1 = data[ind_slow*nb_pmt_channel:(ind_slow+1)*nb_pmt_channel, max(0, min(nb_acq_vect[ind_slow], len(data[0]))-number_of_samples):min(nb_acq_vect[ind_slow], len(data[0]))]
        else:     # even (or bidirek)
            data_1 = data[ind_slow*nb_pmt_channel:(ind_slow+1)*nb_pmt_channel, :min(nb_acq_vect[ind_slow], number_of_samples)] # min(nb_acq_vect[ind_slow], len(data[0]))] #
            
        max_j = int(round(nb_acq_vect[ind_slow]/oversampling_real)) # #round(len(data_1[0])/oversampling)
    
        # print(numpy.amax(data_1))
        array_fill_loops2.fill_array_scan_good2(nb_px_slow, oversampling_real, data_1, array_3d, numpy, [max_read_val_volt]*4, ind_slow, min(nb_px_slow, ind_slow+1), min(max_j, nb_px_fast), verbose, nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_dir, read_buffer_offset_reverse, [min_read_val_volt]*4, 1, 0, [0]) 
    
    # go in control_galvo_scan.py for plot ^^
    # array_3d2 = array_3d
    
    # array_3d2[num_pmt,1::2,:nb_px_X-read_buffer_offset_reverse] = array_3d2[num_pmt,1::2,read_buffer_offset_reverse:]
    
    num_pmt = 1
    
    if device_to_use_AI != device_to_use_anlgTrig:
        num_pmt = 0
        
    if numpy.amin(array_3d[num_pmt,:,:]) < 0:
        array_3d[num_pmt,:,:] = array_3d[num_pmt,:,:] - numpy.amin(array_3d[num_pmt,:,:])
    
    fig1=plt.figure()
    ax1 = plt.subplot(111)
    img_grey = plt.imshow(array_3d[num_pmt,:,:]) # , cmap=cmap_str
    img_grey.autoscale() # autoscale
    cb1 = plt.colorbar() #cax=ax1, mappable=img_grey)
    #cb2 = 0
    plt.show(False)
    
    
    if (not unidirectional):
        # plt.close()
        fig1=plt.figure()
        ax1 = plt.subplot(121)
        img_grey = plt.imshow(array_3d[num_pmt,::2,::2]) # , cmap=cmap_str
        img_grey.autoscale() # autoscale
        cb1 = plt.colorbar() #cax=ax1, mappable=img_grey)
        #cb2 = 0
        ax1 = plt.subplot(122)
        img_grey = plt.imshow(array_3d[num_pmt,1::2,::2]) # , cmap=cmap_str
        img_grey.autoscale() # autoscale
        cb1 = plt.colorbar() #cax=ax1, mappable=img_grey)
        
        fig1=plt.figure()
        ax1 = plt.subplot(111)
        img_grey = plt.imshow(array_3d[num_pmt,::2,::2]) # , cmap=cmap_str
        img_grey.autoscale() # autoscale
        cb1 = plt.colorbar() #cax=ax1, mappable=img_grey)
        
        fig1, ax1, cb1
    
    plt.show(False)
    