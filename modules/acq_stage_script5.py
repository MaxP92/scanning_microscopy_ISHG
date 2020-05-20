# -*- coding: utf-8 -*-
"""
Created on Mon Sept 19 16:35:13 2016

@author: Maxime PINSARD
"""

def acq_data_stage(motor_stageXY, sender_move2read_pipe, receiver_read2move_pipe, queue_com_to_acq, queue_special_com_acqstage_stopline, time, numpy, new_img_to_disp_signal, new_img_flag_queue, queue_moveX_inscan, queue_moveY_inscan, reload_scan_worker_signal, queueEmpty, trigout_maxvelreached, calc_param_scan_stg_signal, stop_motorsXY_queue, profile_mode_slow_dflt, jerk_slow_dflt, accn_max, motor_blocking_meth, block_before_return, emergency_ToMove_queue, piezoZ_step_signal, time_out_ReadProcess, good_trig_key1, dep_dflt_list, debug_mode): 
    '''
    acq_data without the analog_read inside
    wait for analog_read ready signal and go
    '''

    from modules import strt_pos_stage_script, thorlabs_lowlvl_list, calc_scan_param_stagescan_script
    
    def verif_complete_nonblocking(motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, fast_complete_verified, slow_complete_verified, force_wait_fast, force_wait_slow, time):
        
        stop_scanloop = 0 # init
        if (force_wait_fast and not fast_complete_verified):
            res = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, 2) # necessary anyway to move in the direct direction
            stop_scanloop = res[0]; good_ch = res[1]
            # 2 for verify channel read
            # # print('good_ch', good_ch)
            if not good_ch: # slow channel read !
                slow_complete_verified = True
                stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, True) # necessary anyway to move in the direct direction
            fast_complete_verified = True    
        
        wait_slow = False
        if delta_fast_sec <= delta_slow_sec: # the total time for end of move fast and the acceleration of new fast is smaller than the total time for slow move : slow move won't be finished when the acq. begins. Have to wait.
        # !! on windows the smallest sleep is 20ms !!
        
            if delta_slow_sec-delta_fast_sec > 20/1000: # Windows can wait at this resolution (<20ms)
                time.sleep(delta_slow_sec-delta_fast_sec)
            else: # unfortunately no other option than to wait for the slow to finish
                wait_slow = True
        
        if not slow_complete_verified:
            if (wait_slow or force_wait_slow):  
                stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck, time, True)  # # read move_complete of previous slow move
                slow_complete_verified = True
    
        return stop_scanloop, fast_complete_verified, slow_complete_verified
        
    def move_slow(pixel_size_slow_mm, scan_xz, piezoZ_step_signal, k, step_Z_mm, use_stepper_slow, motor_stageXY, thorlabs_lowlvl_list, str_motor_slow, target_slow, rotation_stg_scan_deg, str_motor_fast, target_slow_0):        
        ## Move slow
            
        # the motor must go to the asked distance + deleted pixels (they are assured by the number of steps)
        
        # print('target_slow = ', target_slow)
        if pixel_size_slow_mm > 0: # otherwise the scan is stationary in Slow

            if use_stepper_slow:
                # set slow rel move
                # # motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveRelshort_meth(str_motor_slow)) # step
                motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveRelXY_meth(str_motor_slow, pixel_size_slow_mm))
            else:
                motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_slow, target_slow))  # move
                
                if rotation_stg_scan_deg > 0:
                    motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_fast, target_slow_0))  # move
                    
        elif scan_xz: 
            piezoZ_step_signal.emit((k+1)*step_Z_mm)  # in mm
    
    
    def move_flyback(pos_fast_start, rotation_stg_scan_deg, size_fast_mm_1, k, size_slow_mm_1, vel_fast_opt, vel_fast, accn_fast_opt, accn_fast, str_motor_fast, motor_stageXY, thorlabs_lowlvl_list, fast_complete_verified, motor_blocking_meth, stop_motorsXY_queue, queueEmpty,add_time_theory, nbPX_fast, pixel_size_fast_mm, time_out_min, nb_bytes_read_blck, time, pos_fast_end_2, str_motor_slow, block_before_return, queue_com_to_acq, verbose, stop_scanloop, slow_complete_verified, force_wait_fast, flag_reset_trig_out_each, good_trig_key1, tol_speed_flbck):
        
    ## Unidirek only : return to pos_ini for next move
        
        target_fast = pos_fast_start 
        if rotation_stg_scan_deg > 0:
            target_fast = size_fast_mm_1 + (k+1)*size_slow_mm_1
        # print('Going bacward to return')
        
        if flag_reset_trig_out_each:
            thorlabs_lowlvl_list.set_trig_meth(str_motor_fast, motor_stageXY, thorlabs_lowlvl_list.key_trigout_off)
        cond_reset_vel_acc_return = (abs(vel_fast_opt/vel_fast - 1) > tol_speed_flbck or abs(accn_fast_opt/accn_fast - 1) > tol_speed_flbck)
        if cond_reset_vel_acc_return: # 10% difference tolerated only
            # # print('change_vel_flback !')
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_fast, vel_fast_opt, accn_fast_opt))
        if (force_wait_fast and not fast_complete_verified): # the read move_complete was not performed before for fast direct
            res = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, 2) # 2 for verify channel
            stop_scanloop = res[0]; good_ch = res[1]
            if not good_ch: 
                slow_complete_verified = True
                stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, True)
            fast_complete_verified = True
        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_fast, target_fast))  # move back to origin
        
        if cond_reset_vel_acc_return: # reset previous values for next move
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_fast, vel_fast, accn_fast))
        if flag_reset_trig_out_each:
            thorlabs_lowlvl_list.set_trig_meth(str_motor_fast, motor_stageXY, good_trig_key1)
        
        if rotation_stg_scan_deg > 0:
            target_fast_2 = pos_fast_end_2 
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_slow, target_fast_2))  # move
            
        # read of motor fast if unidirek and no late blocking
        # don't skip a read !!
        if block_before_return: # direct rev fast blocking
            start_time01 = time.time()
            
            blocking = True
            # # print('in reading buffer fast rev.')
            stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, blocking)
            # # print('outside buffer fast rev.')
            
            if verbose:
                print('fast rev blck',  (time.time() - start_time01)*1000)
                
        else:
            fast_complete_verified = False
                    
        return fast_complete_verified, slow_complete_verified, stop_scanloop
        
    move_flbck_str = 'fast_complete_verified, slow_complete_verified, stop_scanloop = move_flyback(pos_fast_start, rotation_stg_scan_deg, size_fast_mm_1, k, size_slow_mm_1, vel_fast_opt, vel_fast, accn_fast_opt, accn_fast, str_motor_fast, motor_stageXY, thorlabs_lowlvl_list, fast_complete_verified, motor_blocking_meth, stop_motorsXY_queue, queueEmpty,add_time_theory, nbPX_fast, pixel_size_fast_mm, time_out_min, nb_bytes_read_blck, time, pos_fast_end_2, str_motor_slow, block_before_return, queue_com_to_acq, verbose, stop_scanloop, slow_complete_verified, force_wait_fast, flag_reset_trig_out_each, good_trig_key1, tol_speed_flbck)'
    
    def slow_wait_func(pixel_size_slow_mm, time, motor_blocking_meth, motor_stageXY, str_motor_fast, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck , verbose, queue_com_to_acq, rotation_stg_scan_deg, stop_scanloop):
    ## wait of Slow (except if Slow static)
    
        # # print('pixel_size_slow_mm', pixel_size_slow_mm, verbose)
        if pixel_size_slow_mm > 0: # otherwise the scan is stationary in Slow
        
            start_time01 = time.time()
        
            stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck, time, True) # 2nd str_motor_slow is for stop, which can't be listened if blocking False anwway
            
            if verbose:
                print('slow dir ',  (time.time() - start_time01)*1000)
                
            if rotation_stg_scan_deg > 0:
                # wait of (slow_1) not performed before
                stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck, time, True) # 2nd str_motor_slow is for stop, which can't be listened if blocking False anwway

        return stop_scanloop
    
    def flyback_wait_func(time, motor_blocking_meth, motor_stageXY, str_motor_fast, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast,  time_out_min, nb_bytes_read_blck, queue_com_to_acq, rotation_stg_scan_deg, verbose, stop_scanloop):
    ## For reading buffer : the read of previous Fast that was not performed (unidirek only)

        start_time01 = time.time()
        
        # read of motor fast because unidirek
        # don't skip a read !!
        blocking = True
        # # print('in reading buffer fast rev.')
        stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, blocking)
        # # print('outside buffer fast rev.')
        
    # print(bb)
        if rotation_stg_scan_deg > 0:
            blocking = True
            # # print('in reading buffer fast rev.')
            stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, blocking)
            # # print('outside buffer fast rev.')
            
        if verbose:
            print('fast rev ',  (time.time() - start_time01)*1000)
            
        return stop_scanloop
    
    wait_flbck_str = 'stop_scanloop = flyback_wait_func(time, motor_blocking_meth, motor_stageXY, str_motor_fast, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast,  time_out_min, nb_bytes_read_blck, queue_com_to_acq, rotation_stg_scan_deg, verbose, stop_scanloop)'
    
    def empty_read_motor_func(force_wait_fast, fast_complete_verified, slow_complete_verified, motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, time, unidirectional, finished, k):
        stop_scanloop = False
        flagtimed_out = True 
        if force_wait_fast:
            if (not fast_complete_verified or not slow_complete_verified): # (k > 0 and not block_each_step): # read move_complete of flyback
                stop_scanloop, fast_complete_verified, slow_complete_verified = verif_complete_nonblocking(motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, fast_complete_verified, slow_complete_verified, force_wait_fast, True, time) # True to force looking at slow verified
        else:  # fast not waited
            rg = k + unidirectional*k
            if finished:
                rg += 10*(not unidirectional) # # +2 if bidirek
                # # print('timed_out', unidirectional, rg)
                if not unidirectional: flagtimed_out = False
            # # time.sleep(add_time_theory) # let deccelerate
            for i in range(rg): 
                t_out = 2*add_time_theory #add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min
                stop_scanloop, good_b, timed_out = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, t_out, nb_bytes_read_blck, time, 2) # 2 for rich response
                if timed_out:
                    # # while True:
                    # #     # last read        
                    # #     stop_scanloop, good_b, timed_out = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_min, nb_bytes_read_blck, time, 2) # 2 for rich response
                    # #     if timed_out:
                    # #         break
                    if flagtimed_out:
                        print('normal timeout to be sure')
                        break
                    else: flagtimed_out = True # next

        return stop_scanloop, fast_complete_verified, slow_complete_verified
        
    def stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, line, motor_stageXY):
        stop_scanloop = 0 # reset
        sender_move2read_pipe.send([-2]) # communicate the stop to fill_array process in -line
        try: # empty the order queue, in case there is an order of launch image remaining
            while True:
                queue_com_to_acq.get_nowait() # raise queueEmpty error if empty, otherwise continue
        except queueEmpty:
            pass # do nothing
        # # print(line)# !!! 
        motor_stageXY.reset_input_buffer() # empty the buffer    
        return stop_scanloop 
        
    def go_init_pos(motor_stageXY, unidirectional, posFast00, posSlow00, offsetFast, offsetSlow, str_motor_fast, str_motor_slow, y_fast, size_fast_mm_1, size_slow_mm_1, pixel_size_fast_mm, pixel_size_slow_mm, acceleration_offset_direct, x_concerned, y_concerned, thorlabs_lowlvl_list, delete_px_fast_begin, delete_px_slow_begin, motor_blocking_meth, stop_motorsXY_queue, vel_x, vel_y, time_out_slow_motion, add_time_theory, dirSlow, good_trig_key1, limitwait_move_tuple, time, queueEmpty, force_wait_fast, quiet_trig_initpos):
        
        if not force_wait_fast:
            motor_stageXY.reset_input_buffer() # # empty buffer
        # # print('\n Warning : x_concerned, y_concerned = %d, %d \n' % (x_concerned, y_concerned))
        return strt_pos_stage_script.strt_pos_stage_func(motor_stageXY, unidirectional, posFast00, posSlow00, offsetFast, offsetSlow, str_motor_fast, str_motor_slow, y_fast, size_fast_mm_1, size_slow_mm_1, pixel_size_fast_mm, pixel_size_slow_mm, acceleration_offset_direct, x_concerned, y_concerned, thorlabs_lowlvl_list, delete_px_fast_begin, delete_px_slow_begin, motor_blocking_meth, stop_motorsXY_queue, vel_x, vel_y, time_out_slow_motion, add_time_theory, dirSlow, good_trig_key1, limitwait_move_tuple, quiet_trig_initpos, time, queueEmpty) 
         
        
    ## init scan
    
    print('Reading current motor positions...')
    # if motor_stageXY: # !! defined ?
    if not debug_mode:
        # # DON'T MOVE THIS OTHERWISE IT WILL SHIFT THE SCAN !!
        posX00 = thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, motor_stageXY) # in mm
        posY00 = thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, motor_stageXY) # in mm
    else: posX00 = posY00 = 50
    
    time_out_min00 = 0.05 # s # !! do not put 0.1, it's too short for S-curve !
    time_out_end = time_out_min = time_out_min00
    # 10secs should be largely enough

    ## receive order
    
    index_acq_current = 1 
    send_stop_inline = 0 # init
    read_is_ready = 1 # default
    
    flag_reset_trig_out_each = False # for flyback
    # # don't put to True as it will cause the code to bug if no blocking  (method fast) !!
    quiet_trig_initpos = False 
    # # if you put True, the moving init will bug !
    move_slow_before_flyback = False # does not really matter (for unidirek)
    verbose =  False #True #
    latency_fast = 25/1000 # in sec
    nb_bytes_read_blck = 20
     
    pos_fast_start=0; pos_slow_start=0; 
    moveX_after = 0 ; moveY_after = 0
    stop_scanloop = 0  # init
    
    while True: # loop on N full images
        
        # # if not read_is_ready:  # analog_read timed out and tell this worker to terminate
        # #     
        # #     break # outside the 'while' loop of img
        # #     # terminate this worker
        # #     # else --> continue to move
        try:
            msg = emergency_ToMove_queue.get_nowait() # listen to emergency call from other Processes
            if msg == 1: # error in other functions
                print('Move worker received that other workers have problems')
                sender_move2read_pipe.send([-1]) # communicate the poison-pill to read Worker (sometimes not necessary)
                motor_stageXY.reset_input_buffer() # empty the buffer    
                break # outside 'while' loop,  will end smoothly
        except queueEmpty:  # nothing in queue
            pass # do nothing 
        

        print('\n acq stage Reading a job in queue if any... \n')
        job = queue_com_to_acq.get() # blocking
        # # job = [1] # !!
        # job is a list of instruction
        # print('smthg detected from gui in data_acquistion') 
        
        # empty the STOP motor queue
        try:
            stop_motorsXY_queue.get_nowait()
        except queueEmpty:  # nothing in queue
            pass # do nothing 
          
        if job[0] == -1:
            print('Poison-pill in acq stage') 
            sender_move2read_pipe.send([-1]) # communicate the poison-pill to read Worker
            motor_stageXY.reset_input_buffer() # empty the buffer    
            break # outside big while loop, end function
            
        elif job[0] == 0:
                
            print('Order to stop detected acq stage') # if = 0
            sender_move2read_pipe.send([0]) # communicate the stop to read Worker
            index_acq_current = 1
            continue # go to beginning of while loop
                
        elif job[0] == 1 : # 1 = continue scan normally
        
            print('Order to acquire detected in acq stage')
            
            # # eventual redefinition of posX00 and posY00
            try: # raises error if nothing to read
                paquetX = queue_moveX_inscan.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                # there is only one element in the queue since it is re-empty in the GUI if several orders
            except queueEmpty:
                pass # do nothing
            else:  # received message
                posX00 = paquetX[0]
                    
            try: # raises error if nothing to read
                paquetY = queue_moveY_inscan.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                # there is only one element in the queue since it is re-empty in the GUI if several orders
            except queueEmpty:
                pass # do nothing
            else:  # received message
                posY00 = paquetY[0]
                           
            x_concerned = 1; y_concerned = 1;
            
            if len(job) > 1: # same scan, but change in parameter(s)
                
            ##    change in parameter(s)
            
                # print('change PMT in acq process')
                # analog_input.ClearTask() # clear old task
                if index_acq_current <= 1: # to do it just once
                    if not debug_mode: 
                        min_vel, accn_x, vel_x = thorlabs_lowlvl_list.get_velparam_bycommand_meth(1, motor_stageXY)
                        min_vel, accn_y, vel_y = thorlabs_lowlvl_list.get_velparam_bycommand_meth(2, motor_stageXY)
                
                list_param_stage_scan = job[1]
                
                print('in list_param_stage_scan')
                
                new_szX_um = list_param_stage_scan[0]; new_szY_um= list_param_stage_scan[1]; px_sz_x= list_param_stage_scan[2]; px_sz_y= list_param_stage_scan[3]; y_fast= list_param_stage_scan[4]; unidirectional= list_param_stage_scan[5]; pmt_channel_list= list_param_stage_scan[6]; acceleration_offset_direct_imposed= list_param_stage_scan[7]; acceleration_offset_reverse_imposed= list_param_stage_scan[8]; offset_buffer_direct_imposed = list_param_stage_scan[9]; offset_buffer_reverse_imposed = list_param_stage_scan[10]; nb_bins_hist= list_param_stage_scan[11]; vel_x_new_imposed = list_param_stage_scan[12]; vel_y_new_imposed = list_param_stage_scan[13]; accn_x_new_imposed = list_param_stage_scan[14]; accn_y_new_imposed = list_param_stage_scan[15]; offsetX_mm = list_param_stage_scan[16]; offsetY_mm = list_param_stage_scan[17];  delete_px_fast_begin = list_param_stage_scan[18];  delete_px_fast_end = list_param_stage_scan[19]; delete_px_slow_begin = list_param_stage_scan[20];  delete_px_slow_end = list_param_stage_scan[21]; real_time_disp = list_param_stage_scan[22]; profile_mode_fast_imposed = list_param_stage_scan[23]; jerk_fast_imposed = list_param_stage_scan[24]; trigout = list_param_stage_scan[25]; sample_rate = list_param_stage_scan[26]; scan_xz = list_param_stage_scan[27]; external_clock =  list_param_stage_scan[28]; 
                dirSlow = 1-2*list_param_stage_scan[29][0]  # 1 for direct, -1 for reverse (initially 0 for not inverse)
                force_reinit_AI_eachimg = list_param_stage_scan[29][1] # # reinit task to avoid empty buffers
                lock_timing= list_param_stage_scan[29][-1]
                block_each_step = list_param_stage_scan[30];  force_wait_fast = list_param_stage_scan[31] # force to wait the fast complete
                clrmap_nb = list_param_stage_scan[32]
                autoscalelive_plt = list_param_stage_scan[33]
                ishg_EOM_AC = list_param_stage_scan[34][:] # being sure that's a new el.
                
                nb_pmt_channel = sum(pmt_channel_list) # nb of PMT channels

                timeoutfinalgetmsgfill = 5 # # flag standard
                timeoutfinalgetmsgfill = timeoutfinalgetmsgfill*nb_pmt_channel
                if ishg_EOM_AC[0]: # ISHG
                    twolines_time = new_szY_um/vel_y_new_imposed/1000*2 if y_fast else new_szX_um/vel_x_new_imposed/1000*2
                    timeoutfinalgetmsgfill = max(timeoutfinalgetmsgfill, twolines_time) # at least 5
                    str1 = 'timeoutfinalgetmsgfill %d' % timeoutfinalgetmsgfill
                    if unidirectional: str1 += 'and quiet trigger when flyback is %r' % flag_reset_trig_out_each
                    print(str1)
                #     method_fast = True #if not unidirectional else False
                # else: method_fast = True # False if unidirectional else False # # could use fast, but was tested with slow

                if (not block_each_step or not force_wait_fast):
                    if (flag_reset_trig_out_each or quiet_trig_initpos): # # fast is too demanding to having the time to reset any trigger
                        str = '\n\n !!WARNING'
                        if (flag_reset_trig_out_each and unidirectional): str += 'for flyback move, ' 
                        if quiet_trig_initpos: str += 'for init repos'
                        str += '!! \n\n'
                        print( str)
                
                if nb_pmt_channel == 0: # no PMT, just do the scan with no acq.
                    special_pmt_str = 'with NO reading (pmt = 0)'
                    if not block_each_step or not force_wait_fast:
                        print('\n no PMT but will still have the Read since I need it to have a trigger signal (non blocking mode) \n')
                else: # pmts
                    special_pmt_str = ''
                #     nb_pmt_channel = 1 # nb_pmt_channel was indicating # of PMT, but now the number of channels 
                cond_com_read = nb_pmt_channel > 0 or not block_each_step or not force_wait_fast  # # no pmt = noread, and no block requies the read          
                
                if not debug_mode:
                    if (accn_x != accn_x_new_imposed or vel_x_new_imposed != vel_x):
                        # motorX.set_velocity_parameters(0, max_accn_motorX, max_speed_motorX) # first arg is 0 and ignored
                        
                        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(1, vel_x_new_imposed, accn_x_new_imposed))
                        # time.sleep(0.2)
                        
                    if (accn_y != accn_y_new_imposed or vel_y_new_imposed != vel_y):
                        # motorY.set_velocity_parameters(0, max_accn_motorY, max_speed_motorY) # first arg is 0 and ignored
                        
                        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(2, vel_y_new_imposed, accn_y_new_imposed))
                        # time.sleep(0.2)
                    
                    motor_stageXY.reset_input_buffer() # empty the buffer
                    min_vel, accn_x_new, vel_x_new = thorlabs_lowlvl_list.get_velparam_bycommand_meth(1, motor_stageXY)
                    print('In SCAN For CH1 : min_vel = %.1f, max_acc = %.2f /%.f, max_vel = %.6f /%.1f ; fast prof%d' % (min_vel, accn_x_new, accn_x_new_imposed, vel_x_new, vel_x_new_imposed, profile_mode_fast_imposed))
                    min_vel, accn_y_new, vel_y_new = thorlabs_lowlvl_list.get_velparam_bycommand_meth(2, motor_stageXY)
                    print('In SCAN For CH2 : min_vel = %.1f, max_acc = %.2f /%.f, max_vel = %.6f /%.1f' % (min_vel, accn_y_new, accn_y_new_imposed, vel_y_new, vel_y_new_imposed))
                    
                else: accn_x_new = accn_x_new_imposed; accn_y_new = accn_y_new_imposed; vel_x_new = vel_x_new_imposed; vel_y_new = vel_y_new_imposed
                
                accn_x = accn_x_new # something proper to this Worker, no communication with the GUI
                accn_y = accn_y_new
                vel_x = vel_x_new # is sent after if fast
                vel_y = vel_y_new # is sent after if fast
                # as the round is precise to +-1, the precision on the speed is 1/MLS203_scfactor_vel = 7.45e-06 mm/s
                # as the round is precise to +-1, the precision on the speed is 1/MLS203_scfactor_acc = 7.28e-02 mm/s2
                
                if y_fast:
                    pixel_size_fast_mm = px_sz_y/1000 # has to be in mm, not um
                    pixel_size_slow_mm = px_sz_x/1000 # has to be in mm, not um
                    if pixel_size_slow_mm > 0:
                        nbPX_slow = int(round(new_szX_um/pixel_size_slow_mm/1000)) # nb pixels # # sometimes round gives a .0 !!
                    else:
                        nbPX_slow = int(round(new_szX_um)) # # allows you to do a scan in Y, with a stationnary scan in 
                    if pixel_size_fast_mm > 0:
                        nbPX_fast = int(round(new_szY_um/pixel_size_fast_mm/1000)) # nb pixels
                    else:
                        nbPX_fast = int(round(new_szY_um)) # # allows you to do a scan in X, with a stationnary scan in Y
                    
                    str_motor_fast = 2 # motorY
                    str_motor_slow = 1 # motorX
                    accn_fast = accn_y_new
                    vel_fast = vel_y_new
                    accn_fast_imposed = accn_y_new_imposed
                    vel_fast_imposed = vel_y_new_imposed
                    accn_slow = accn_x_new
                    vel_slow = vel_x_new
                    offsetFast = offsetY_mm
                    offsetSlow = offsetX_mm
                    
                else: # x-fast, classic
                    pixel_size_fast_mm = px_sz_x/1000 # has to be in mm, not um
                    pixel_size_slow_mm = px_sz_y/1000 # has to be in mm, not um
                    if pixel_size_slow_mm > 0:
                        nbPX_slow = int(round(new_szY_um/pixel_size_slow_mm/1000)) # nb pixels # # sometimes round gives a .0 !!
                    else:
                        nbPX_slow = int(round(new_szY_um)) # # allows you to do a scan in X, with a stationnary scan in Y
                    if pixel_size_fast_mm > 0:
                        nbPX_fast = int(round(new_szX_um/pixel_size_fast_mm/1000)) # nb pixels
                    else:
                        nbPX_fast = int(round(new_szX_um)) # # allows you to do a scan in Y, with a stationnary scan in X
                    str_motor_fast = 1 # motorX
                    str_motor_slow = 2 # motorY
                    accn_fast = accn_x_new
                    vel_fast = vel_x_new
                    accn_fast_imposed = accn_x_new_imposed # previous
                    vel_fast_imposed = vel_x_new_imposed # previous
                    accn_slow = accn_y_new
                    vel_slow = vel_y_new
                    offsetFast = offsetX_mm
                    offsetSlow = offsetY_mm

                    step_Z_mm = pixel_size_slow_mm
                    if scan_xz:
                        pixel_size_slow_mm = 0 # acts as static

                tol_speed_flbck = dep_dflt_list[-2]
                method_fast = dep_dflt_list[-1]
                limitwait_move_tuple = dep_dflt_list[:-2] + (vel_fast, accn_fast, vel_slow, accn_slow)
                
                if not debug_mode:
                    thorlabs_lowlvl_list.set_trig_meth(str_motor_fast, motor_stageXY, good_trig_key1) # # trigger OUT
                    thorlabs_lowlvl_list.set_trig_meth(str_motor_slow, motor_stageXY, thorlabs_lowlvl_list.key_trigout_off) # # trigger OUT
                    
                # set profile mode (and jerk) of motor fast
                profile_mode, jerk = calc_scan_param_stagescan_script.profilemode_jerk_set_stgscn_func(profile_mode_fast_imposed, jerk_fast_imposed, str_motor_fast, profile_mode_slow_dflt, jerk_slow_dflt, str_motor_slow, motor_stageXY) if not debug_mode else (2,10000) 
                
                # print('offset_buffer_reverse_imposed ', offset_buffer_reverse_imposed)
                # calculate acc_offset parameters
                calc_scan_param = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(pixel_size_fast_mm, vel_fast, accn_fast, trigout_maxvelreached, acceleration_offset_direct_imposed, acceleration_offset_reverse_imposed, vel_fast_imposed, accn_fast_imposed, offset_buffer_direct_imposed, offset_buffer_reverse_imposed, profile_mode, jerk)
                
                # print(calc_scan_param)
                dwll_time = calc_scan_param[0]
                acceleration_offset_direct_theo  = calc_scan_param[1] 
                acceleration_offset_reverse_theo = calc_scan_param[2] 
                # 3,4 are not used
                acceleration_offset_direct = calc_scan_param[5]
                acceleration_offset_reverse = calc_scan_param[6]
                offset_buffer_direct = calc_scan_param[7]
                if unidirectional: # in unidirektional, the reverse read buffer is not used
                    offset_buffer_reverse = offset_buffer_direct
                else:
                    offset_buffer_reverse = calc_scan_param[8]
                
                add_time_theory = calc_scan_param[9] # acc + dec, in sec
                                
                delta_fast_sec = (2*latency_fast + add_time_theory) # # add_time_theory takes into account the acceleration and deceleration
                # # 2*latency_fast for fast because there are slow_fast and fast_fast
                delta_slow_sec = (2*latency_fast + (vel_slow/accn_slow + pixel_size_slow_mm/vel_slow)) # # 2*latency_fast for slow because there are fast_fast and fast_slow
                if profile_mode < 2: # trapez
                    time_out_min = time_out_min00 # s # !! do not put 0.1, it's too short for S-curve !
                else: # s-curve !!
                    time_out_min = 1 # s # !! do not put 0.1, it's too short for S-curve !
                time_out_slow_motion = time_out_min + delta_slow_sec  #10 # sec ( slow motion is in general small, so difficult to calculate a time_out)
                time_out_end = time_out_slow_motion + add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast
                # # print('delta_fast_sec', delta_fast_sec*1000, delta_slow_sec*1000)
                
                # print('offset_buffer_reverse ', offset_buffer_reverse) 
                
                trigger_maxvel = 1 # to be moved !
                # # profile = 0 # for S-curve it's 2 and it's more complicated (?)
                # # if profile < 2: # for the trapez profile, the maths are easy
                
                diff_PXAccoffset = (acceleration_offset_direct - acceleration_offset_direct_theo)/pixel_size_fast_mm # positive or negative
                diff_PXDecoffset = (acceleration_offset_reverse - acceleration_offset_reverse_theo)/pixel_size_fast_mm # positive or negative
                if diff_PXAccoffset < 0: # some samples will be at a non-constant velocity
                
                    if trigger_maxvel:
                        
                        diff_PXAccoffset = 2*diff_PXAccoffset
                    else: # in motion
                        
                        diff_PXAccoffset = 2*acceleration_offset_direct_theo/pixel_size_fast_mm # non-constant velocity
                        
                else: # >=0
                    if not trigger_maxvel: # in motion
                    
                        diff_PXAccoffset = diff_PXAccoffset + 2*acceleration_offset_direct_theo/pixel_size_fast_mm
                        
                if diff_PXDecoffset < 0: # some samples will be at a non-constant velocity
                    if trigger_maxvel:
                        diff_PXDecoffset = 2*diff_PXDecoffset
                    else: # in motion
                    
                        diff_PXDecoffset = 2*acceleration_offset_reverse_theo/pixel_size_fast_mm # non-constant velocity
                    
                else: # >0 
                    if not trigger_maxvel: # in motion
                    
                        diff_PXDecoffset = diff_PXDecoffset + 2*acceleration_offset_reverse_theo/pixel_size_fast_mm
                # # print('in move : vel_x = ', vel_x)
                
                # calculate ideal vel and accn
                # it's for return of unidirek scan, so it's necessarily trapez mode
                
                accn_fast_opt = accn_max
                vel_fast_opt = calc_scan_param_stagescan_script.vel_acc_opt_stgscn_func(0, 0, nbPX_fast*pixel_size_fast_mm*1000, 0, accn_fast_opt, 0)[1] # size_fast must be in um
                # # print('vel_fast_opt ', vel_fast_opt)
                
                x_concerned = 1; y_concerned = 1
    
            # this has to be done in all cases !
            if y_fast: # y-fast
                posFast00 = posY00
                posSlow00 = posX00
            else: # x-fast, classic
                posFast00 = posX00
                posSlow00 = posY00
    
            print('acq # %d %s\n' % (index_acq_current, special_pmt_str))
            
            decceleration_offset_direct = acceleration_offset_reverse
            # # print('decceleration_offset_direct ', decceleration_offset_direct)
            
            # # !!!
            rotation_stg_scan_deg = 0
            '''
            Not implemented yet : need to verify the sizes (theoretically)
            The idea is to scan with a rotation angle
            a priori, very few parameters change because the functions defining acc_offsets can be called again for motor 2 (for instance)
            '''
            size_fast_mm_1 = nbPX_fast*pixel_size_fast_mm
            size_slow_mm_1 = nbPX_slow*pixel_size_slow_mm
                
            if rotation_stg_scan_deg > 0:
                print('\n Warning : rotation_stg_scan_deg is different from 0 (not implemented yet) \n')
                size_fast_mm_2 = -size_fast_mm_1*numpy.sin(rotation_stg_scan_deg/180*numpy.pi)  #+ size_slow_um*numpy.cos(rotation_stg_scan_deg/180*numpy.pi)
                size_slow_mm_2 = size_slow_mm_1*numpy.cos(rotation_stg_scan_deg/180*numpy.pi)
                size_slow_mm_1 = size_fast_mm_1*numpy.sin(rotation_stg_scan_deg/180*numpy.pi)
                size_fast_mm_1 = size_fast_mm_1*numpy.cos(rotation_stg_scan_deg/180*numpy.pi) # + size_slow_um*numpy.sin(rotation_stg_scan_deg/180*numpy.pi)
            
            pos_fast_start, pos_slow_start = go_init_pos(motor_stageXY, unidirectional, posFast00, posSlow00, offsetFast, offsetSlow, str_motor_fast, str_motor_slow, y_fast, size_fast_mm_1, size_slow_mm_1, pixel_size_fast_mm, pixel_size_slow_mm, acceleration_offset_direct, x_concerned, y_concerned, thorlabs_lowlvl_list, delete_px_fast_begin, delete_px_slow_begin, motor_blocking_meth, stop_motorsXY_queue, vel_x, vel_y, time_out_slow_motion, add_time_theory, dirSlow, good_trig_key1, limitwait_move_tuple, time, queueEmpty, force_wait_fast, quiet_trig_initpos) if not debug_mode else (0,0) 
            
            fake_size_fast = nbPX_fast + delete_px_fast_begin + delete_px_fast_end # to consider the deleted pixels at the begin and the end for the FAST dir
            fake_size_slow = nbPX_slow + delete_px_slow_begin + delete_px_slow_end # to consider the deleted pixels at the begin and the end for the SLOW dir
            
            x_concerned = 0; y_concerned = 0 # resetting
            
            if cond_com_read: # nb_pmt_channel > 0 or not block_each_step or not force_wait_fast
                
                if len(job) > 1: # same scan, but change in parameter(s)
                    # # print('in move : vel_fast = ', vel_fast)
                    sender_move2read_pipe.send([1, [pixel_size_fast_mm, vel_fast, fake_size_fast, fake_size_slow , offset_buffer_direct, offset_buffer_reverse, unidirectional, nb_bins_hist, pmt_channel_list, y_fast, delete_px_fast_begin, delete_px_fast_end, delete_px_slow_begin, delete_px_slow_end, real_time_disp, diff_PXAccoffset, diff_PXDecoffset, sample_rate, external_clock, block_each_step, force_wait_fast, [dirSlow, force_reinit_AI_eachimg, lock_timing], clrmap_nb, autoscalelive_plt, method_fast, ishg_EOM_AC]]) # send order to acquire_buffer to acquire via Pipe
                    print('Move sent new parameters + start to reader')
                    # job = [1] # for the following of the scan, parameters need'nt be re-defined
                    # job will be re-set at next image
                    if receiver_read2move_pipe.poll(2 + time_out_ReadProcess):  # # waiting for parameters of Read # sec
                        params = receiver_read2move_pipe.recv(); # # smp_rate_new = params[0]  #  # ; print('lalla', type(params), smp_rate_new)
                    else: params = (); print('timeout getting params from Read in acq !!')
                    if type(params) != tuple: params = () # tuple_smp_rate_new
                    calc_param_scan_stg_signal.emit(accn_x, accn_y, vel_x, vel_y, dwll_time, acceleration_offset_direct, acceleration_offset_reverse, offset_buffer_direct, offset_buffer_reverse, profile_mode, jerk, params) # displays in the GUI the real parameters in real-time
                # for read_buffer acq.
                else: # scan with no change in parameters
                    sender_move2read_pipe.send([1]) # send order to read_buffer that Move is ready
                    # print('Move sent start to reader')
                
                ##  scan
            
            print('scan starts...')
                
                # calc_scan_param = calc_scan_param_stagescan_script.adjust_stage_scan_param_func(
                
                # acceleration_offset_direct = calc_scan_param[5]
                # acceleration_offset_reverse = calc_scan_param[6]
            
            use_stepper_slow = 0 # move rel (1) or abs for slow
            # if (use_stepper_slow and pixel_size_slow_mm > 0):
            # set slow rel move
            # motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveRelparamXY_meth(str_motor_slow, pixel_size_slow_mm))
            # motor_stageXY.write(thorlabs_lowlvl_list.command_ReqRelparam2)
            # bbn=b''
            # while len(bbn) < 12:
            #     bb = motor_stageXY.read(12-len(bbn))
            #     bbn = bbn + bb
            # print('set slow ', bbn)

            k = 0
            fast_complete_verified = slow_complete_verified = True # init, False if not blocking move
            
            start_time = time.time()
            
            # # print('fake_size_slow ', fake_size_slow, 'new_szY_um ', new_szY_um)
            print('blocking? ', block_each_step,  force_wait_fast, 'unidirek', bool(unidirectional))
            
            for k in range(0, fake_size_slow):
                
                ## listen for any order
                                
                if pixel_size_fast_mm == 0:
                    print('Warning : px_size was set to 0 for fast, meaning no move and no trigger !\n')
                    send_stop_inline = 1
                                    
                try: # raises error if nothing to read
                    msg = queue_special_com_acqstage_stopline.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                except queueEmpty:
                    pass # do nothing
                    
                else: # received message

                    if msg == 'stop':
                        print('stop signal in-line from the GUI') 
                        send_stop_inline = 1
                        
                if send_stop_inline:
                    stop_scanloop, fast_complete_verified, slow_complete_verified = empty_read_motor_func(force_wait_fast, fast_complete_verified, slow_complete_verified, motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, time, unidirectional, 0, k+1)
                    send_stop_inline = stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, 'l579', motor_stageXY)
                    break # outside the 'for' loop on slow
                
                if (unidirectional or ((k+1) % 2)): # always if unidirek or k even (0th line...) if bidirek
                    
                    try: # raises error if nothing to read
                        paquetX = queue_moveX_inscan.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                        # there is only one element in the queue since it is re-empty in the GUI if several orders
                    except queueEmpty:
                        pass # do nothing
                    
                    else:  # received message
                        # # print('Move X during scan order received')
                        
                        posX00 = paquetX[0]
                        moveX_after = 1 - paquetX[1]
                        
                        if not moveX_after: # move now
                            x_concerned = 1

                    try: # raises error if nothing to read
                        paquetY = queue_moveY_inscan.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                        # there is only one element in the queue since it is re-empty in the GUI if several orders
                    except queueEmpty:
                        pass # do nothing
                        
                    else:  # received message
                        # # print('Move Y during scan order received')
                        
                        posY00 = paquetY[0]
                        moveY_after = 1 - paquetY[1]
                        
                        if not moveY_after: # move now
                            y_concerned = 1

                    if (x_concerned or y_concerned or (k == 0 and (moveX_after or moveY_after))):
                        if y_fast:
                            posFast00 = posY00
                            posSlow00 = posX00
    
                        else: # x fast
                            posFast00 = posX00
                            posSlow00 = posY00
                            
                        if (k == 0 and moveX_after): 
                            x_concerned = 1 # to tell to, now, move X
                            moveX_after = 0 # reset it
                            
                        if (k == 0 and moveY_after): 
                            y_concerned = 1 # to tell to, now, move X
                            moveY_after = 0 # reset it
                            
                        if (not fast_complete_verified or not slow_complete_verified): # (k > 0 and not block_each_step): # read move_complete of flyback
                            stop_scanloop, fast_complete_verified, slow_complete_verified = verif_complete_nonblocking(motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, fast_complete_verified, slow_complete_verified, force_wait_fast, True, time) # # to read the msgs move_complete before veryfing these new moves
                        if not force_wait_fast:
                            motor_stageXY.reset_input_buffer() # empty the buffer
        
                        pos_fast_start, pos_slow_start = strt_pos_stage_script.strt_pos_stage_func(motor_stageXY, unidirectional, posFast00, posSlow00, offsetFast, offsetSlow, str_motor_fast, str_motor_slow, y_fast, size_fast_mm_1, size_slow_mm_1, pixel_size_fast_mm, pixel_size_slow_mm, acceleration_offset_direct, x_concerned, y_concerned, thorlabs_lowlvl_list, delete_px_fast_begin, delete_px_slow_begin, motor_blocking_meth, stop_motorsXY_queue, vel_x, vel_y, time_out_slow_motion, add_time_theory, dirSlow, good_trig_key1, limitwait_move_tuple, quiet_trig_initpos, time, queueEmpty) 
                        # print('posfast is indeed after func', pos_fast)
                     
                    if (k == 0 or x_concerned or y_concerned): # first move or pos ini redefined   
                        if unidirectional == 2: # to the left
                        
                            pos_fast_end = pos_fast_start - size_fast_mm_1 - acceleration_offset_direct - decceleration_offset_direct - delete_px_fast_begin*pixel_size_fast_mm - delete_px_fast_end*pixel_size_fast_mm
                            
                        else: # to the right or bidirek
                        
                            pos_fast_end = pos_fast_start + size_fast_mm_1 + acceleration_offset_direct + decceleration_offset_direct + delete_px_fast_begin*pixel_size_fast_mm + delete_px_fast_end*pixel_size_fast_mm
                                    
                        if rotation_stg_scan_deg > 0:
                            pos_fast_end_2 = pos_fast_start + size_fast_mm_2 + acceleration_offset_direct_2 + decceleration_offset_direct_2 + delete_px_fast_begin*pixel_size_fast_mm + delete_px_fast_end*pixel_size_fast_mm
                        else:
                            pos_fast_end_2 = 0
                            
                        x_concerned = 0; y_concerned = 0 # resetting
                    
                    ## define the position to reached    
                
                    target_fast = pos_fast_end
                        # the motor must go through acceleration_offset_direct, do the asked distance, and go through decceleration_offset_direct and through the will-be deleted pixels
                        
                else: # k odd AND bidirectionnal (reverse dir)
            
                    # to the right
                    # print('Going backward in scan')
                    target_fast = pos_fast_start # return to pos ini
                    
                # # print('I`m going to ', target_fast, 'meaning ', target_fast-pos_fast_start)
                
                target_slow = pos_slow_start + dirSlow*(k+1)*pixel_size_slow_mm
                
                if rotation_stg_scan_deg > 0:
                    target_slow_0 = pos_fast_start + (k+1)*size_slow_mm_1
                    target_slow = pos_slow_start + dirSlow*(k+1)*size_slow_mm_2
                else:
                    target_slow_0 = 0  
                
                ## Communicate with read_buffer worker
                
                if (not ((k+1) % (fake_size_slow/20)) or k in (0,fake_size_slow-1) or verbose): # avoid too high numbers, or last row or verbose
                    print('Buffer # %d' % (k+1)) # one buffer is here one line
                    
                if (not fast_complete_verified or not slow_complete_verified): # (k > 0 and not block_each_step): # read move_complete of flyback
                    stop_scanloop, fast_complete_verified, slow_complete_verified = verif_complete_nonblocking(motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, fast_complete_verified, slow_complete_verified, force_wait_fast, False, time) # verify flyback fast if unidirek, slow if the timing is too short (otherwise after)
                
                if (k > 0 and cond_com_read): # for k = 0 the order is launch before the 'for' loop
                # nb_pmt_channel > 0 or not block_each_step or not force_wait_fast
                    sender_move2read_pipe.send([2]) # send order that Move is ready for next move in loop
                    # # print('Move sent to read_buffer that he is ready for another acq line') 
  
                if cond_com_read: # nb_pmt_channel > 0 or not block_each_step or not force_wait_fast
                    if verbose:
                        print('Move waiting for msg of reader ...')
                    if receiver_read2move_pipe.poll(time_out_end + time_out_ReadProcess + time_out_min):  # # time that Read maybe timeout and re-start # sec
                        read_is_ready = receiver_read2move_pipe.recv() # blocking, receive order from read_buffer to continue to move
                    else: # pb
                        print('PROBLEM: Acq did no receive msg to stop from Read')
                        read_is_ready = 0
                else:
                    read_is_ready = 1
                    if (not (k % (fake_size_slow/20)) or verbose): # avoid too high numbers
                        print('I don`t listen to read_buffers since there is no PMT')
                
                if not read_is_ready:  # analog_read timed out 
                    print('Move worker detected that reader timed out')
                    print('Move worker is forced to stand-by because of read worker')
                    motor_stageXY.reset_input_buffer() # empty the buffer    
                    break # outside the 'for' loop of lines
                
                else: # normal behavior : move motor !
                    if read_is_ready != 1: # signature
                        print('move did not catch the good msg from read (@ begin move): %d !' % read_is_ready, 'k', k)
                        if cond_com_read: # nb_pmt_channel > 0 or not block_each_step or not force_wait_fast
                            if receiver_read2move_pipe.poll(): # there's an object to read, instantenously # sec
                                read_is_ready = receiver_read2move_pipe.recv() # blocking,  !!!!
                                print('read_is_ready is read after (@ begin move): %d' % read_is_ready)
                    else:
                        if verbose:
                            print('read_is_ready', read_is_ready, target_fast)
                
                ## Move fast
                    # print('target_fast ', target_fast)
                    start_time01 = time.time()
                    
                    if rotation_stg_scan_deg > 0:
                        target_fast = pos_fast_end + (k+1)*size_slow_mm_1
                    
                    motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_fast, target_fast))  # move
                    
                    if rotation_stg_scan_deg > 0:
                        target_fast2 = pos_fast_end_2 + (k+1)*size_slow_mm_2
                        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_slow, target_fast2))  # (move)
                    
                    if block_each_step:
                        blocking = True
                        stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, blocking) # 2nd str_motor_fast is for stop, 20 for nb_bytes_read_blck
                    else: # the move complete will be read before the next move in the same axis
                        fast_complete_verified = False
                        if not slow_complete_verified: # (k > 0 and not waited_slow): # # read move_complete of previous slow move
                            stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck, time, True) # # just to read the msg, no real wait !!
                            slow_complete_verified = True
                        
                        if cond_com_read:
                            if receiver_read2move_pipe.poll(add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min): # timeout # sec
                                read_is_ready = receiver_read2move_pipe.recv() # blocking, receive order from read_buffer that ref. trigger is there
                                if not read_is_ready: # pb
                                    stop_scanloop = 1
                                elif read_is_ready != 2: # signature
                                    print('move did not catch the good msg from read (end move fast): %d !' % read_is_ready)
                                elif verbose:
                                        print('read_is_ready END', read_is_ready)
                   
                    if stop_scanloop:
                        stop_scanloop = stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, 'L747', motor_stageXY)
                        break # outside 'for' loop on slow
                        
                    if verbose:
                        print('fast dir ',  (time.time() - start_time01)*1000)
                    
                    if rotation_stg_scan_deg > 0:
                        blocking = True
                        stop_scanloop = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min, nb_bytes_read_blck, time, blocking) # 2nd str_motor_fast is for stop
                        
                        if stop_scanloop:
                            stop_scanloop = stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, 'L760', motor_stageXY)
                            break # outside 'for' loop on slow
                    
                    if k >= fake_size_slow-1: # don't do the last flyback and last slow move (useless, but useful for ensuring the last flyback will not be kept in buffer of Nicard!!)
                        break     
                    
                    # # move
                    if (unidirectional and not move_slow_before_flyback):
                        exec(move_flbck_str)
                    
                    move_slow(pixel_size_slow_mm, scan_xz, piezoZ_step_signal, k, step_Z_mm, use_stepper_slow, motor_stageXY, thorlabs_lowlvl_list, str_motor_slow, target_slow, rotation_stg_scan_deg, str_motor_fast, target_slow_0)
                    
                    if (unidirectional and move_slow_before_flyback):
                        exec(move_flbck_str)
                        
                    if stop_scanloop: # of Fast
                        stop_scanloop = stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, 'L785', motor_stageXY)
                        break # outside 'for' loop on slow
                # print(bb)
                    
                    # # wait or not
                    if block_each_step: 
                    
                        if (unidirectional and not block_before_return and not move_slow_before_flyback): 
                            exec(wait_flbck_str)
                            
                        stop_scanloop = slow_wait_func(pixel_size_slow_mm, time, motor_blocking_meth, motor_stageXY, str_motor_fast, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_slow_motion, nb_bytes_read_blck , verbose, queue_com_to_acq, rotation_stg_scan_deg, stop_scanloop)
                
                        if (unidirectional and not block_before_return and move_slow_before_flyback): 
                            exec(wait_flbck_str)
                            
                        if stop_scanloop: # of Fast
                            stop_scanloop = stop_func(sender_move2read_pipe, queue_com_to_acq, queueEmpty, 'L790', motor_stageXY)
                            break # outside 'for' loop on slow
                    # print(bb)
                    
                    if (unidirectional and not block_each_step and not force_wait_fast): # flyback, wait for trigger of motor since blocking is false
                        if receiver_read2move_pipe.poll(add_time_theory + nbPX_fast*pixel_size_fast_mm/vel_fast + time_out_min): # timeout # sec
                            read_is_ready = receiver_read2move_pipe.recv() # blocking, receive order from read_buffer that ref. trigger is there
                            if not read_is_ready: # pb
                                stop_scanloop = 1
                            elif read_is_ready != 3: # signature
                                print('move did not catch the good msg from read (flyback): %d !' % read_is_ready)
                                if receiver_read2move_pipe.poll(): # there's an object to read # sec
                                    read_is_ready = receiver_read2move_pipe.recv() # blocking,  !!!!
                                    print('read_is_ready is read after (flbck): %d' % read_is_ready)
                            
                    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive1)
                    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive2)
                
                    # # time.sleep(2) 
                    
            ## after scan of all the lines
            
            if verbose:
                print("--- %s seconds in before last wait ---" % (time.time() - start_time), k)        
            
            stop_scanloop, fast_complete_verified, slow_complete_verified = empty_read_motor_func(force_wait_fast, fast_complete_verified, slow_complete_verified, motor_blocking_meth, motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, add_time_theory, nbPX_fast, pixel_size_fast_mm, vel_fast , time_out_min, nb_bytes_read_blck, delta_fast_sec, delta_slow_sec, str_motor_slow, time_out_slow_motion, time, unidirectional, 1, k+1)
            if not block_each_step:
                motor_stageXY.reset_input_buffer() # empty the buffer
                motor_stageXY.reset_output_buffer() # empty the orders
                    
            tt = (time.time() - start_time) # # secs
            print("--- %s seconds in move ---" % tt)
                  
            if ishg_EOM_AC[0]: timeoutfinalgetmsgfill = timeoutfinalgetmsgfill*1.5+tt*0.1 if method_fast else timeoutfinalgetmsgfill*1.5+tt  # ISHG
            if nb_pmt_channel > 0: # there are acq. asked, not just simple move
                try:
                    # # print('timeoutfinalgetmsgfill', timeoutfinalgetmsgfill)
                    msg = new_img_flag_queue.get(True, timeout = timeoutfinalgetmsgfill) # blocks, wait for display and fill to assure image is ready
                except queueEmpty:
                    msg = 'timeout' # # problem occured
                    print('I`ve waited %s sec and no reply from fill' % timeoutfinalgetmsgfill, new_img_flag_queue.qsize())
            else:
                msg = 'stand-by' # this message will make the worker listen to order, after
            # msg = 'img'
            
            if msg == 'img':
                print('img signal sent to GUI') 
                new_img_to_disp_signal.emit() # tell gui that a new img has been acquired
                
            elif msg in ( 'kill', 'timeout'):
                str1 = 'last img signal' if msg == 'kill' else 'pb fill'
                print(msg, str1) 
                reload_scan_worker_signal.emit(0) # tell gui that when next scan is launched, it will be with a reset of the worker's function
                # 0 for normal mode, just scan_set to 1
                motor_stageXY.reset_input_buffer() # empty the buffer    
                break # outside 'while' loop
                # close the function !
                
            elif msg == 'stand-by':
                print('Move worker is told to stand-by') 
                # go to job read
                            
            index_acq_current += 1
            # print('index_acq_current = ', index_acq_current) 
        
    ## after scan of all the imgs, outside 'while' loop    
        
# if final scan
    motor_stageXY.reset_input_buffer() # empty the buffer
    
    motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(1, posX00))  # move
    blocking = True
    was_stopped = motor_blocking_meth(motor_stageXY, 1, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_end, nb_bytes_read_blck, time, blocking) # 2nd str_motor is for stop
    
    if was_stopped: # has been stopped during return to init positions
        posX_real = thorlabs_lowlvl_list.get_posXY_bycommand_meth(1, motor_stageXY) # real posX set
        posX00 = posX_real
    
    motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(2, posY00))  # move
    blocking = True
    was_stopped = motor_blocking_meth(motor_stageXY, 2, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, time_out_end, nb_bytes_read_blck, time, blocking) # 2nd str_motor_fast is for stop
    
    if was_stopped: # has been stopped during return to init positions
        posY_real = thorlabs_lowlvl_list.get_posXY_bycommand_meth(2, motor_stageXY) # real posX set
        posY00 = posY_real

    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive1)
    motor_stageXY.write(thorlabs_lowlvl_list.command_serv_alive2)
    motor_stageXY.reset_output_buffer() # empty the orders

        