# -*- coding: utf-8 -*-
"""
Created on Tue May 10 09:35:13 2016

@author: Maxime PINSARD

you have to write V 7,0 to reset the imic galvos trigger
"""
                
def go_galvos_scan_func_mp( min_val_volt_list, max_val_volt_list, time_out, time, numpy, math, delay_trig, timebase_src_end, trig_src_name, time_out_sync, queue_com_to_acq_process, queue_list_arrays, new_img_to_disp_signal, external_clock, max_value_pixel, real_time_disp, queue_special_com_acqGalvo_stopline, write_scan_before, piezoZ_step_signal, num_dev_anlgTrig, num_dev_watcherTrig, num_dev_AO, start_sec_proc_beg, setnewparams_scan_signal, path_computer ):
    
    """    
    """
    
    import multiprocessing
    from modules import data_acquisition_script2, fill_array_script2, disp_results_script2
   
    # receiver_conn, sender_conn = multiprocessing.Pipe(False) # false is for unidirectionnal pipe
    queue_acq_fill = multiprocessing.Queue() 
    
    if real_time_disp:
        # receiver_conn_disp, sender_conn_fill = multiprocessing.Pipe(False) # false is for unidirectionnal pipe
        queue_fill_disp = multiprocessing.Queue()
    else: queue_fill_disp = 0
        
    new_img_flag_queue  =  multiprocessing.Queue()
    
    ## Création des process
        
    '''
    if param_ini.DO_parallel_trigger:
    
        # import importlib
        import master_trig_ctrl_scrpts
        trigControl_write_process = master_trig_ctrl_scrpts.Anlg_Pausetrig_Substitute(dev_list, device_to_use_anlgTrig, ai_trig_src_name_master,  smp_rate_trig, term_do, export_smpclk, use_RSE ,samp_src_term_master_toExp, queue_read_to_trigger, queue_special_com_stopline, queue.Empty, trig_process_gen_write)
        
        # # trigControl_write_process.start()
        
    if param_ini.DI_parallel_watcher:
        trigWatcher_process = master_trig_ctrl_scrpts.Anlg_trig_sender_process(device_to_use_watcherTrig, queue.Empty, term_DI, receiver_read_to_trigger, sender_trigger_to_read, queue_special_com_stopline, time, use_change_detect_event, rate, nb_lines)
        trigWatcher_process.start()
        
        receiver_read_to_trigger, sender_read_to_trigger = multiprocessing.Pipe(False) # undirek pipe
    '''
    
    if (external_clock == -2 and not write_scan_before): # new anlg galvos
      
        from modules import write_task
        sideWrite_writeAcq_pipe, sideAcq_writeAcq_pipe = multiprocessing.Pipe(True) # True for bidirectionnal
    
        write_live_galvos_process = write_task.Write_live_AO_process( sideWrite_writeAcq_pipe)
    else:
        sideAcq_writeAcq_pipe = None; sideWrite_writeAcq_pipe = None
    
    sec_proc =  False
    queue_prim2sec_ishg = multiprocessing.Queue() # # to put in a Proc
    queue_sec2prim_fill = multiprocessing.Queue() # # Pipe too slow for big packet, even in send()
    
    acq_process = data_acquisition_script2.acq_data( time_out, queue_acq_fill, min_val_volt_list, max_val_volt_list, delay_trig, timebase_src_end, trig_src_name, time_out_sync, queue_com_to_acq_process, external_clock, queue_special_com_acqGalvo_stopline, sideAcq_writeAcq_pipe, sideWrite_writeAcq_pipe, write_scan_before, piezoZ_step_signal, num_dev_anlgTrig, num_dev_watcherTrig, num_dev_AO, new_img_flag_queue, path_computer)
    
    fill_process = fill_array_script2.fill_array( send_img_to_gui, queue_acq_fill, queue_fill_disp, queue_list_arrays, new_img_flag_queue, max_value_pixel, real_time_disp, external_clock, queue_sec2prim_fill, queue_prim2sec_ishg, start_sec_proc_beg , True) # True for primary_worker
    
    if start_sec_proc_beg: # start from scratch sec. process
        sec_fill_process_ishg = fill_array_script2.fill_array(send_img_to_gui, queue_sec2prim_fill, None, None, None, max_value_pixel, real_time_disp, external_clock, None, queue_prim2sec_ishg, start_sec_proc_beg , False) # False for sec_worker
        sec_fill_process_ishg.start()
        sec_proc = True
    
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process = disp_results_script2.disp_results(queue_fill_disp, new_img_flag_queue)
        
    ## Lancement des process
    
    acq_process.start()
    fill_process.start()
    
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process.start()
    
    if (external_clock == -2 and not write_scan_before): # new anlg galvos
        write_live_galvos_process.start()
        # relay of the information : tell the GUI that an image must be disp
        
    while True: # infinite loop
        
        # # try:
        msg = new_img_flag_queue.get() # blocks, infinitely
        
        if type(msg) is float:
            # # print('l96', time.time())
            piezoZ_step_signal.emit(msg)  # in mm
        elif type(msg) is tuple:
            # # print('sending smp rate !!')
            setnewparams_scan_signal.emit(msg) # tuple
            
        elif msg == 'img':
            print('img signal sent to GUI') 
            new_img_to_disp_signal.emit() # tell gui that a new img has been acquired
            
        # # elif msg == 'stopAcq':
        # #     # # print('send order to stop Acq. because of disp Process')
        # #     queue_special_com_acqGalvo_stopline.put('stop') # special stop in-line ONLY if errors in disp Process
        # #     queue_com_to_acq_process.put([-2]) # stop in-line.
  
        elif msg == 'killAcq': # in addition the acq. Process must be stopped (error occured)
            queue_special_com_acqGalvo_stopline.put('stop') # in case acq. Process is still in the 'for' loop
            queue_com_to_acq_process.put([-1]) # poison-pill to acq.
            
        elif msg == '2ndprocON':
            if not sec_proc: # not yet started
                sec_fill_process_ishg = fill_array_script2.fill_array( send_img_to_gui, queue_sec2prim_fill, None, None, None, max_value_pixel, real_time_disp, external_clock, None, queue_prim2sec_ishg , False) # False for sec_worker
                sec_fill_process_ishg.start()
                sec_proc = True
            
        else:
            if msg == 'terminate': # poison-pill
                print('last img signal, term. in go_galv.') 
            
            break # outside while loop
        # # except queue.Empty:
        # #     
        # #     pass # do nothing
                
            
    ## Attend que les process se terminent
    
    tout = 2 # sec
    acq_process.join(timeout = tout) # normally should not timeout # this enable the process to be killed after completion
    al = acq_process.is_alive()
    if al: # # alive
        print('acq_process.is_alive()', al)
        acq_process.terminate();  acq_process.join(timeout = tout)
        
    fill_process.join(timeout = tout) # normally should not timeout
    al = fill_process.is_alive()
    if al: # # alive
        print('fill_process.is_alive()', al)
        fill_process.terminate(); fill_process.join(timeout = tout)
    if sec_proc:
        sec_fill_process_ishg.join(timeout = tout) # normally should not timeout
        al = sec_fill_process_ishg.is_alive()
        if al: # # alive
            print('sec_fill_process_ishg.is_alive()', al)
            sec_fill_process_ishg.terminate(); sec_fill_process_ishg.join(timeout = tout)
    
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process.join(timeout = tout) # normally should not timeout
        al = disp_results_process.is_alive()
        if al: # # alive
            print('disp_results_process.is_alive()', al)
            disp_results_process.terminate();  disp_results_process.join(timeout = tout)
        
    if (external_clock == -2 and not write_scan_before): # new anlg galvos
        write_live_galvos_process.join()
    
    '''    
    if (param_ini.DO_parallel_trigger):
        queue_special_com.put('stop') # stop
        queue_read_to_trigger.put([-1]) # poison-pill
        trigControl_write_process.join()
    if (param_ini.use_callbacks and param_ini.DI_parallel_watcher):
        sender_read_to_trigger.send([-1]) # kill it
        trigWatcher_process.join()
    '''
    
    # print('All processes joined')
    
def send_img_to_gui(queue_list_arrays, new_img_flag_queue, paquet_tosend, str_msg, ishg_EOM_AC_flag, sat_value_list, data_list, arr, array_ishg_4d):
    
    if (paquet_tosend is not None and sat_value_list is not None): # # not for stage
        if ishg_EOM_AC_flag: # # ishg fast
            if (arr is None):  # # no sec. wrkr
                arr = data_list if ishg_EOM_AC_flag == 2 else array_ishg_4d # # ishg_EOM_AC_insamps[0] == 2: # special for saving only whole array
                paquet_tosend[0][-1] = arr # # last el. of the list in the 0th position in the big list
                # # arr is data_list or array_ishg_4d
                if ishg_EOM_AC_flag == 11: # # data_list + treated
                    paquet_tosend[0].append(data_list) 
        paquet_tosend[1] = sat_value_list # re-init ; it won't affect paquet_2disp
        # # ind_disp = self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_2disp, str_msg) # # send_img_to_gui is in  go_scan_galvos.py
    if type(paquet_tosend[1][0]) == list: # # paquet_tosend[1] is actually param_to_disp so 0th is pmt_channel_list
        paquet_tosend[1] = paquet_tosend[1][-1] # # last val is sat_list
    
    if (len(paquet_tosend[0]) > 2 and paquet_tosend[0][1] is not None and paquet_tosend[0][1].shape[0] > 1): # # filled array in ishg, numerous PMTs
        paquet_tosend[0][1] = None # # arr_ctr 
    
    # print('paquet_tosend', paquet_tosend[1], paquet_tosend[0][0].shape, paquet_tosend[0][1] is None, paquet_tosend[0][2].shape, len(paquet_tosend[0][3]))
    '''
    paquet_tosend[1] = [sat_value_list]
    paquet_tosend[0] = arr_3D if no ishgFAST
    paquet_tosend[0] = [arr_3D, arr_ctr, arr4D] if ishgFAST; [arr_3D, arr_ctr, arr4D, arrlist] if ishgFAST with save .npy
    '''
    if (len(paquet_tosend[0]) > 3):  # # filled array in ishg with send of the buffers in npy !!
        buffers = paquet_tosend[0][3]; paquet_tosend[0][3] = 1
    # # paquet_tosend[0] = paquet_tosend[0][0] # #  for test!!!
    queue_list_arrays.put(paquet_tosend) # send in queue to the main gui
    if (len(paquet_tosend[0]) > 3):  # # filled array in ishg with send of the buffers in npy !!
    # # sent in 2 steps
        queue_list_arrays.put(buffers)
    new_img_flag_queue.put('img') # tell the GUI, via go_galvo_func, that an image must be disp
    print('signal new img to disp sent to GUI', str_msg, new_img_flag_queue.qsize())
# # end of func
    return 0
    
                        