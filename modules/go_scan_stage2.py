# -*- coding: utf-8 -*-
"""
Created on Tue Sept 10 09:35:13 2016

@author: Maxime PINSARD
"""

import multiprocessing

from modules import acq_stage_script5, fill_stage_array_script3, read_buffers_stage_script5, go_scan_galvos, disp_results_script2

def go_stage_scan_func_mp(motor_stageXY, min_val_volt_list, max_val_volt_list, trig_src, scan_mode, queue_com_to_acq, queue_special_com_acqstage_stopline, queue_list_arrays, max_value_pixel, time, numpy, time_out, new_img_to_disp_signal, queue_moveX_inscan, queue_moveY_inscan, reload_scan_worker_signal, queueEmpty, trigout_maxvelreached, calc_param_scan_stg_signal, stop_motorsXY_queue, profile_mode_slow_dflt, jerk_slow_dflt, accn_max, motor_blocking_meth, block_slow_stgXY_before_return, piezoZ_step_signal, good_trig_key1, sec_proc_forishgfill, real_time_disp, dep_dflt_list, debug_mode):
    # , motor_trans, list_pos_wrt_origin, pos_trans0, offset_pos_ps, pos_trans_signal, motor_trans_finished_move_signal

    
    """
    Method called by scan stage worker
    """
    
    """
    Possible a priori to do a common function for stage scan and galvos scan, but unnecessary because few things in common (just readanalogF64)
    Fill process is very different, and can be combined with disp
    but can use sub-functions that are the same
    
    Not really possible to have a process only for fill+disp a priori, because processes launch at the same time
    
    need of a communication between acq process and the APT worker, via queue.Queue() that already exist
    
    but need to tell APT worker that a element of move indeed arrived
    can implement smthg like this in GUI : worker_stagescan.move_motorX_signal.connect(worker_apt.move_motorX)
    a Worker for stage scan, independent of APT worker
    """
    
    # Pipe for com from read_analog to fill_disp workers
    queue_conn_acq_fill = multiprocessing.Queue() # # Pipe too slow for big packet, even in send()
    
    # Pipe for com.from move to read_analog workers
    receiver_move2read_pipe, sender_move2read_pipe = multiprocessing.Pipe(False) # false is for unidirectionnal pipe
    
    # Pipe for com. from read_analog to move workers
    receiver_read2move_pipe, sender_read2move_pipe = multiprocessing.Pipe(False) # false is for unidirectionnal pipe
    
    # new_move_mtrX_queue  =  multiprocessing.Queue() # cannot use pipe because there is a relay here
    # new_move_mtrY_queue  =  multiprocessing.Queue()
    
    if real_time_disp: queue_fill_disp = multiprocessing.Queue() # # receiver_conn_disp, sender_conn_fill = multiprocessing.Pipe(False) # false is for unidirectionnal pipe
    else: queue_fill_disp = 0
    
    new_img_flag_queue = multiprocessing.Queue() # queue for a flag telling a new image has been acquired
    emergency_ToMove_queue  =  multiprocessing.Queue() # queue for emergency stopping
    queue_prim2sec_ishg = queue_sec2prim_fill = None # dflt
    # # sec_proc_forishgfill will be True only for ishg_EOM_AC_insamps[0] == 1, i.e. fill array4D and not save datalist
    
    ## Def. of processes
    
    print('sec_proc_forishgfill', sec_proc_forishgfill)
    if sec_proc_forishgfill: # # ishg, with sec. wrkr for fill
        queue_prim2sec_ishg = multiprocessing.Queue() # # to put in a Proc
        queue_sec2prim_fill = multiprocessing.Queue() # # Pipe too slow for big packet, even in send()
        sec_fill_process_ishg = fill_stage_array_script3.fill_disp_array(go_scan_galvos.send_img_to_gui, queue_sec2prim_fill, max_value_pixel, None, None, None, None, queue_prim2sec_ishg, None, 0, False ) # False for sec_worker
        sec_fill_process_ishg.start()
    
    read_buffers_process = read_buffers_stage_script5.read_buffers_stage(receiver_move2read_pipe, sender_read2move_pipe, queue_conn_acq_fill, min_val_volt_list, max_val_volt_list, trig_src, scan_mode, time_out, emergency_ToMove_queue)
    
    fill_process = fill_stage_array_script3.fill_disp_array(go_scan_galvos.send_img_to_gui, queue_conn_acq_fill, max_value_pixel, queue_list_arrays, new_img_flag_queue, emergency_ToMove_queue, queue_sec2prim_fill, queue_prim2sec_ishg , queue_fill_disp, real_time_disp, True )
    
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process = disp_results_script2.disp_results(queue_fill_disp, new_img_flag_queue)
    
    ## Launch of processes
    
    read_buffers_process.start()
    fill_process.start()
    
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process.start()
    
    time.sleep(0.8) # to allow the read process to launch nidaqmx
    
    ## scan itself
    
    # !! do not put fake_sizes here, because it's for moving so it needs the real sizes + the nb of pixel to delete
    try:
        acq_stage_script5.acq_data_stage( motor_stageXY, sender_move2read_pipe, receiver_read2move_pipe, queue_com_to_acq, queue_special_com_acqstage_stopline, time, numpy, new_img_to_disp_signal, new_img_flag_queue, queue_moveX_inscan, queue_moveY_inscan, reload_scan_worker_signal, queueEmpty, trigout_maxvelreached, calc_param_scan_stg_signal, stop_motorsXY_queue, profile_mode_slow_dflt, jerk_slow_dflt, accn_max, motor_blocking_meth, block_slow_stgXY_before_return, emergency_ToMove_queue, piezoZ_step_signal, time_out, good_trig_key1, dep_dflt_list, debug_mode)

    # , motor_trans, list_pos_wrt_origin, pos_trans0, offset_pos_ps, pos_trans_signal, motor_trans_finished_move_signal
    except:
        import traceback
        traceback.print_exc()
        bb = b'0' # binary empty
        while len(bb) >=1: # not bool(bb):
            bb= motor_stageXY.read()
        sender_move2read_pipe.send([-2]) # stop in-line, to try to save the already acquired image part
        sender_move2read_pipe.send([-1]) # communicate the poison-pill to read Worker, which will kill the fill Process after
        try:
            msg = new_img_flag_queue.get(block=True, timeout=3) # blocks, wait for display and fill to assure image is ready (only during 3 seconds)
        except queueEmpty:
            msg = ''
        if msg == 'img':
            print('img signal sent to GUI') 
            new_img_to_disp_signal.emit() # tell gui that a new img has been acquired
        
    ## Attend que les process se terminent
    
    # # this enable the process to be killed after completion 
    tout = 3 # sec
    read_buffers_process.join(timeout = tout) # normally should not timeout # this enable the process to be killed after completion
    al = read_buffers_process.is_alive()
    if al: # # alive
        print('read_buffers_process.is_alive()', al)
        read_buffers_process.terminate();  read_buffers_process.join(timeout = tout)
        
    fill_process.join(timeout = tout) # normally should not timeout
    al = fill_process.is_alive()
    if al: # # alive
        print('fill_process.is_alive()', al)
        fill_process.terminate(); fill_process.join(timeout = tout)
    if real_time_disp: # disp only if nb buffer > 1
        disp_results_process.join(timeout = tout) # normally should not timeout
        al = disp_results_process.is_alive()
        if al: # # alive
            print('disp_results_process.is_alive()', al)
            disp_results_process.terminate();  disp_results_process.join(timeout = tout)
    if sec_proc_forishgfill:
        sec_fill_process_ishg.join(timeout = tout) # normally should not timeout
        al = sec_fill_process_ishg.is_alive()
        if al: # # alive
            print('sec_fill_process_ishg.is_alive()', al)
            sec_fill_process_ishg.terminate(); sec_fill_process_ishg.join(timeout = tout)
        
