# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 16:35:13 2017

@author: Maxime PINSARD
"""

import multiprocessing


class read_buffers_stage(multiprocessing.Process):

    """Process read buffer"""

    def __init__(self, receiver_move2read_pipe, sender_read2move_pipe, queue_conn_acq_fill, min_val_volt_list, max_val_volt_list, trig_src, scan_mode, time_out, emergency_ToMove_queue):

        multiprocessing.Process.__init__(self)

        self.receiver_move2read_pipe = receiver_move2read_pipe
        self.sender_read2move_pipe = sender_read2move_pipe
        self.queue_conn_acq_fill = queue_conn_acq_fill
        self.min_val_volt_list = min_val_volt_list; self.max_val_volt_list = max_val_volt_list
        self.trig_src = trig_src; self.scan_mode = scan_mode
        self.time_out = time_out
        self.emergency_ToMove_queue = emergency_ToMove_queue; #self.queueEmpty = queueEmpty
        
    def run(self):
        
        def ai_wait_done_func(nidaqmx, param_ini, analog_input, errors_raised, time_out, y_fast, trig_src, str_dir_or_rev):
            try:
                analog_input.wait_until_done(timeout = time_out) # #  seconds
                
            except nidaqmx.DaqError as err:
                
                if err.error_type == nidaqmx.error_codes.DAQmxErrors.WAIT_UNTIL_DONE_DOES_NOT_INDICATE_DONE: # just trigger was not received
                    print('\n Error : waited time is over time_out %g sec %s!' % (time_out, str_dir_or_rev))
                    axis = 'y' if y_fast else 'x'
                    print('Only %d smps acq. \n You may not have connected the STAGE %s axis trigger wire to %s/%s port (or DAQ card bugs) ! \n Anyway, you`ll have a chance to start the scan again\n' % (analog_input.in_stream.total_samp_per_chan_acquired, axis, trig_src[0].name, param_ini.trig_src_name_stgscan))
                else:
                    print(err)
                    
                errors_raised = 1 # see after
                
            return errors_raised
        
        try:
            import ctypes
            import numpy
            from queue import Empty as queueEmpty
            import warnings # can't be pickled in processes !!
            from modules import daq_control_mp2, param_ini
            print('Importing NIDAQmx in read_buffers ..')
            import nidaqmx
            import nidaqmx.stream_readers, nidaqmx.system # mandatory if read_stream
            print('in worker_stageXY : NIDAQmx ok')
            
            system = nidaqmx.system.System.local()
            # # print(system.driver_version)
            i = 0; dev_list=[]
            for device in system.devices:
                dev_list.append(nidaqmx.system.Device(device.name))
                
            device_toUse_AI = dev_list[self.trig_src[0]-1]
            self.trig_src[0] = device_toUse_AI # the whole device
            # # trig_src is  [device_used_AIread, self.trig_src_name_stgscan] (see stageXY wrkr)
            # # trig_src_name_stgscan in param_ini
            
            ct_lines = 0
            need2send_params = 0
            send_to_disp_flag = True
            verbose =  False #True
            errors_raised = 0
            timebase_src_name = 0; delay_trig = 0 # used only for digital galvos
            analog_input = None # init
            name_list_AI_tasks = param_ini.name_list_AI_tasks
            mtr_trigout_cntr_task = None 
            nametask_mtr_trigout_list = param_ini.nametask_mtr_trigout_list
            reinit_AI_task = False
            mtr_trigout_retriggerable = param_ini.mtr_trigout_retriggerable_stage
            nb_remaining = 0
            
            # flag_perso = 0
            
            ## loop on buffers
            
            while True : # loop on buffers
            # because changing X, Y init pos during scan might take some time, so need the approval of the move to listen for the trigger
                try:
                    msg = self.emergency_ToMove_queue.get_nowait() # listen to emergency call from fill Process
                    print('Read worker received that Fill has problems')
                    if msg == 1: # error in other functions
                        
                        self.emergency_ToMove_queue.put(1) # 1 means error, Move worker will end when listen to ermergency Queue
                        self.sender_read2move_pipe.send(0) # 0 to tell the Move worker that read is NOT ready for next acqs, which will make him to look for img in queue
                        # normally fill Process has sent the image and order to Move
                        break # outside 'while' loop,  will end smoothly
                except queueEmpty:  # nothing in queue
                    pass # do nothing 
                
                # print(nb_pmt_channel*number_of_samples)
                # # print('Reader listening ...')
                paquet_order = self.receiver_move2read_pipe.recv() # blocking, receive order to start acquire buffer by Pipe
                # # print( paquet_order )
                if verbose:
                    print('Reader received order by paquet from Move')
                # # if self.receiver_move2read_pipe.poll(): # a msg avail.
                # #     print('second msg to Read!!', self.receiver_move2read_pipe.recv()) # blocking, receive order to start acquire buffer by Pipe
                
                ## ------------------- control if stop  ----------------------------------------------
                
                if (len(paquet_order) == 1 and paquet_order[0] < 1): #  # stop command, 0 or -1 or -2
                    ct_lines = 0
                    if paquet_order[0] == -1: # poison-pill
                        print('Poison-pill in read_buffers') 
                        # is done in the end
                        # # if 'analog_input' in locals(): # hasattr(self, 'analog_input'):
                        # #     analog_input.close() # clear old task
                        
                        self.queue_conn_acq_fill.put([-1]) # communicate the poison-pill to fill_array process
                        
                        break # outside big while loop, end function
                    
                    else:     # just stop (=0) or stop_in_line (=2)
                        if paquet_order[0] == 0: # just stop, means stand-by
                            
                            print('Order to stop detected in read_buffer stage') # if = 0
                            self.queue_conn_acq_fill.put([0]) # communicate the stop to fill_array process 
                            
                        elif paquet_order[0] == -2: # stop_in_line (=2), will stand-by
                        
                            print('Order to stop in-line detected in read_buffer stage') # if = 0
                            self.queue_conn_acq_fill.put([-2]) # communicate the stop to fill_array process      
                        # return to recv()
                        nb_remaining = 0
                        continue # to the beginning of the while loop
                        
                else: # 1 or [1, params] : no stop command, acquire buffers !
                
                ## ------------------- perhaps new parameters sent ----------------------------------------------
    
                    if len(paquet_order) > 1: # scan with new parameters
                    
                        list_param_stage_scan = paquet_order[1]
                        ct_lines = 0
                        need2send_params = 1 # have to communicate the new params to the disp Worker
                        
                        # !!  fake_sizes are sent by sender_conn_acq (because for timing), whereas real_sizes are com. by move2read_pipe (because move_func) !!
                        pixel_size_fast_mm = list_param_stage_scan[0]; max_vel_fast = list_param_stage_scan[1]; fake_size_fast = list_param_stage_scan[2]; fake_size_slow = list_param_stage_scan[3]; read_buffer_offset_direct = list_param_stage_scan[4]; read_buffer_offset_reverse = list_param_stage_scan[5]; unidirectional = list_param_stage_scan[6]; nb_bins_hist  = list_param_stage_scan[7]; pmt_channel_list = list_param_stage_scan[8]; y_fast = list_param_stage_scan[9];  delete_px_fast_begin = list_param_stage_scan[10];  delete_px_fast_end = list_param_stage_scan[11]; delete_px_slow_begin = list_param_stage_scan[12];  delete_px_slow_end = list_param_stage_scan[13]; real_time_disp = list_param_stage_scan[14]; diff_PXAccoffset = list_param_stage_scan[15]; diff_PXDecoffset = list_param_stage_scan[16]; sample_rate = list_param_stage_scan[17]; external_clock = list_param_stage_scan[18]; block_each_step=list_param_stage_scan[19]; force_wait_fast = list_param_stage_scan[20]; [dirSlow, force_reinit_AI_eachimg, lock_timing] = list_param_stage_scan[21];  clrmap_nb =  list_param_stage_scan[22]; autoscalelive_plt = list_param_stage_scan[23]; method_fast= list_param_stage_scan[24]; ishg_EOM_AC = list_param_stage_scan[25]
                        print('\n ----- new params in Read-------')
                        if ishg_EOM_AC[0]: # # flag
                            from modules import jobs_scripts
                            print('ishg_EOM_AC', ishg_EOM_AC) 
                        else:
                            jobs_scripts = None
                        
                        time_by_px = pixel_size_fast_mm/max_vel_fast # in s/pixel
                        # # # # print('max_vel_fast = ', max_vel_fast)
                        time_expected_sec = fake_size_fast*pixel_size_fast_mm/max_vel_fast
 
                        # print(number_of_samples + nbPostTriggerSamps + safety_size)
                        if sum(pmt_channel_list) == 0: # if the code made it here, force to read something for communication, so we'll fake it
                            pmt_channel_list = [1,0,0,0]
                            send_to_disp_flag = False
                            print('No disp flag detected !!')
                        
                        update_time = time_expected_sec
                        reinit_AI_task = True # # 1st ini or chg params
                        remn = True # # will try to empty the buffer
                    
                    ct_lines += 1
    
                    if (reinit_AI_task or (force_reinit_AI_eachimg and (paquet_order[0] == 1 or nb_remaining == 0))):
                         # # either first line or not reinit at each img is True, so performed only if asked
                        reinit_AI_task = False # # reinit
                        # # print('force_reinit_AI_eachimg', force_reinit_AI_eachimg, nb_remaining, paquet_order[0])
                        analog_input, _, msg_warning_ifstop_taskundone, nb_pmt_channel, arr_reshape, nbPostTriggerSamps, time_by_px, _, sample_rate_new, AIPMT_bounds_list, meth_read, _, fake_size_fast, [ishg_EOM_AC_insamps, mtr_trigout_cntr_task, ishg_EOM_AC2, _] = daq_control_mp2.init_daq(nidaqmx, pmt_channel_list, self.min_val_volt_list, self.max_val_volt_list, timebase_src_name, self.trig_src, delay_trig, self.scan_mode, sample_rate, time_by_px, time_expected_sec, numpy, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, dev_list, update_time, (None, fake_size_slow), param_ini, external_clock, None, None, None, analog_input, None, name_list_AI_tasks, None, ishg_EOM_AC, jobs_scripts, mtr_trigout_cntr_task, nametask_mtr_trigout_list, mtr_trigout_retriggerable, lock_timing) 
                        print('I sent new sample rate (Read) !!')
                        if (ishg_EOM_AC[0] and (ishg_EOM_AC[-2] != ishg_EOM_AC2[-2])): # not in samps, deadtimes
                            put1 = (sample_rate_new, ishg_EOM_AC2[-2][1], ishg_EOM_AC2[-2][2]) # tuple_smp_rate_new
                        else: put1 = (sample_rate_new,) # if lock_timing, smp rate will be ignored after anyway
                        self.sender_read2move_pipe.send(put1) # # for Acq., can add new params in the future
                    
                    oversampling = sample_rate_new*time_by_px
                    
                    # # print('in read_acqstage_set', oversampling, sample_rate_new, time_by_px)
                        
                ## ------------------- acquire  ----------------------------------------------
                    
                    if verbose:
                        print('Reader`s ready : sent msg to move, waiting for trigger during %d seconds only !' % self.time_out) # print before to avoid latence
                    # # all cases
                    # # print('walladispdtage', mtr_trigout_retriggerable, ct_lines)
                    if (mtr_trigout_cntr_task is not None and (not mtr_trigout_retriggerable) or (mtr_trigout_retriggerable and ct_lines == 1)): # # for EOMph iSHG only
                        warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                        mtr_trigout_cntr_task.stop() # # avoid warning not done
                        warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)
                        mtr_trigout_cntr_task.start() # # is retriggerable so no need to stop it each time
                        # # print('done00', mtr_trigout_cntr_task.channels.co_pulse_done)
                    analog_input.start() # the Task will effectively starts after the StTrigger
                    
                    # # !! 2019.5.16
                    if (remn and analog_input.in_stream.avail_samp_per_chan):
                        remn = analog_input.read(timeout = 0)
                        if type (remn) != float: print(remn) # # empty the buffer
                        remn = False
                    # # !!
                    
                    # you have to start the task BEFORE the loop each time, because being outside the read loop stops the Task
                    self.sender_read2move_pipe.send(1) # 1 to tell the move to begin/go on moving by Pipe
                    
                    # # method = 2
                    # # if method == 2:
                    
                    ai_wait_done_func(nidaqmx, param_ini, analog_input, errors_raised, self.time_out + time_expected_sec, y_fast, self.trig_src, 'for direct')
                    
                    # # if (mtr_trigout_cntr_task is not None and not mtr_trigout_retriggerable): # # for EOMph iSHG only
                    # #     if mtr_trigout_cntr_task.channels.co_pulse_done: 
                    # #         print('done', mtr_trigout_cntr_task.channels.co_pulse_done, mtr_trigout_cntr_task.timing.samp_quant_samp_per_chan); 
                    # #         warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                    # #         mtr_trigout_cntr_task.stop() # # avoid warning not done
                    # #         warnings.filterwarnings('default', message=msg_warning_ifstop_taskundone)

                    
                    if not errors_raised: # no error until now
                        nb_remaining = analog_input.in_stream.avail_samp_per_chan    # also possible : real all buffer and remove the nbPreTriggerSamps_min samples
                        if verbose:
                            print('nb_remaining', nb_remaining)
                        
                        if nb_remaining == 0:
                            
                            print('Error: no samps remained in buffer !')
                            print('You could use the `force_reinit_AI_eachimg_chck` in read tab on main GUI to avoid this !!\n')
                            reinit_AI_task = True # # the buffer is fucked, have to reinit the Task
                            # # will raise an error safely after  
                            errors_raised = 1 
                        
                        else: # samples remained in buffer : ok  !
                        
                            if not block_each_step:
                                self.sender_read2move_pipe.send(2) # 1 to tell the move that reference trig has come (only if no blocking)!
                            data_temp = arr_reshape[:nb_remaining, :nb_pmt_channel].reshape(nb_pmt_channel, min(nb_remaining, len(arr_reshape)))
                            # # data_temp = numpy.zeros((nb_pmt_channel, nb_remaining), dtype=param_ini.type_data_read_temp) # number_of_samples pre-triggered + posttriggered
                            #  !! actually the fact to reshape the array instead of creating it showed no improving
                            # with no stream it's very long
                            
                            try:
                                nb_read = meth_read(data_temp, number_of_samples_per_channel=nb_remaining, timeout = 0)
                                
                            except nidaqmx.DaqError as err:
                                
                                if err.error_type != nidaqmx.error_codes.DAQmxErrors.SAMPLES_NO_LONGER_AVAILABLE:
                                    print(err)
                                    print("Increase the buffer size")
                                else: # just trigger was not received
                                    print('\n No available samps in buffer ! : try to decrease your acceleration_offset or increase reading_offset \n')
        
                                errors_raised = 1 # see after
                                
                            else: # read succesful
                            
                                if (unidirectional and not block_each_step and not force_wait_fast and ct_lines < fake_size_slow): # FLYBACK (even if last line)
                                    # print('ct_lines', ct_lines)
                                    warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                                    analog_input.stop() 
                                    analog_input.start() # flyback trigger will be raised when finished
                                    ai_wait_done_func(nidaqmx, param_ini, analog_input, errors_raised, self.time_out + time_expected_sec, y_fast, self.trig_src, 'for flyback')
 # normally each start will empty the buffer ...
                                    self.sender_read2move_pipe.send(3) # tell the acq that it returned to zero well
                                    analog_input.stop() #
                                    warnings.filterwarnings('always', message=msg_warning_ifstop_taskundone)
                                # elif ct_lines == fake_size_slow: print(len(analog_input.read(number_of_samples_per_channel = nidaqmx.constants.READ_ALL_AVAILABLE))) 

                                if verbose: print('nb_read', nb_read)
                                    
                                ## ------------------- send data to disp  ----------------------------------------------
                            
                                # !!  fake_sizes are sent by sender_conn_acq (because for timing), whereas real_sizes are sent by move2read_pipe (because move_func) !!
                                # # print(ct_lines, data_temp[:5])
                                if send_to_disp_flag:
                                    if need2send_params:
                                        self.queue_conn_acq_fill.put([data_temp[:,0:len(data_temp[0])- nbPostTriggerSamps], [fake_size_fast, fake_size_slow, read_buffer_offset_direct, read_buffer_offset_reverse, unidirectional, nb_bins_hist, pmt_channel_list, y_fast, delete_px_fast_begin, delete_px_fast_end, delete_px_slow_begin, delete_px_slow_end, real_time_disp, oversampling, AIPMT_bounds_list, param_ini.use_volt_not_raw, param_ini.use_median, dirSlow, clrmap_nb, autoscalelive_plt, method_fast, ishg_EOM_AC_insamps]]) # send data to fill+disp process by queue, Pipe too slow
                                        need2send_params = 0
                                    else:
                                        self.queue_conn_acq_fill.put([data_temp[:,0:len(data_temp[0])- nbPostTriggerSamps], [1]])
                                
                                # print('In read offset_buffer_direct ', read_buffer_offset_direct) 
                                
                                # # nb_remaining = analog_input.in_stream.avail_samp_per_chan # garbage
                                # # print('remaining', nb_remaining)
                                analog_input.stop() 
                                if ct_lines >= fake_size_slow: # a whole image has been acquired
                                    ct_lines = 0
                                    remn = True # # will try to empty the buffer at next img 
                                    if (mtr_trigout_cntr_task is not None and mtr_trigout_retriggerable): # # for EOMph iSHG only, last stop
                                        mtr_trigout_cntr_task.stop()
                                    # # DON'T DO THAT > THE TASK WILL BUG AT NEXT START
                                    # analog_input.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
                                    # analog_input.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # re-arm the Task
                    
                    # # keep it there because errors_raised can be True inside the not    
                    if errors_raised: # check for errors
                        # # print('in errors raised ')
                        errors_raised = 0 # reset
                        warnings.filterwarnings('ignore', message=msg_warning_ifstop_taskundone)
                        analog_input.stop() # normally, raises a warning
                        warnings.filterwarnings('always', message=msg_warning_ifstop_taskundone)
                        # # analog_input.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
                        # # analog_input.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # re-arm the Task
                        nb_remaining = 0
                        self.queue_conn_acq_fill.put([-2]) # communicate the stop to fill_array process (stop in-line)
                        self.sender_read2move_pipe.send(0) # 0 to tell the Move worker that read is NOT ready for next acqs
                        if self.receiver_move2read_pipe.poll(self.time_out + time_expected_sec): # sonething to read after timeout
                            paquet_order = self.receiver_move2read_pipe.recv() # blocking, to empty the next order of move to acquire, because Move doesn't know the read failed
                    # # all cases
                
        except:
            import traceback
            traceback.print_exc()
            self.queue_conn_acq_fill.put([-2]) # stop in-line, to try to save the part of image acquired
            # Move worker will send the order new img to GUI
            self.queue_conn_acq_fill.put([-1]) # communicate the poison-pill to fill_array process
            self.emergency_ToMove_queue.put(1) # 1 means error, Move worker will end when listen to ermergency Queue
            self.sender_read2move_pipe.send(0) # 0 to tell the Move worker that read is NOT ready for next acqs, which will make him to look for img in queue
            
            
        finally: # in all cases
            ## end of process, outside 'while' loop of get()
            
            if ('analog_input' in locals() and analog_input is not None):
                analog_input.close() # clear task
            if (not 'ishg_EOM_AC' in locals()):
                ishg_EOM_AC= [1]
            if (mtr_trigout_cntr_task is not None and ishg_EOM_AC[0]): # # flag ishg EOM, mtr_trigout_cntr_task (Task)
                mtr_trigout_cntr_task.stop(); mtr_trigout_cntr_task.close()
                nidaqmx.system.System.local().disconnect_terms(source_terminal = ('/%s/%s' % (self.trig_src[0].name, self.trig_src[1])), destination_terminal = '/%s/%s' % (self.trig_src[0].name, param_ini.ctr_src_trigger_trigout_EOMph))