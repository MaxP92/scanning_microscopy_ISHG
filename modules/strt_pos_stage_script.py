# -*- coding: utf-8 -*-
"""
Created on Mon Nov 02 16:35:13 2016

@author: Maxime PINSARD
"""

def strt_pos_stage_func(motor_stageXY, unidirectionnal, posFast00, posSlow00, offsetFast, offsetSlow, motor_fast, motor_slow, y_fast, size_fast_mm, size_slow_mm, pixel_size_fast, pixel_size_slow, acceleration_offset_direct, x_concerned, y_concerned, thorlabs_lowlvl_list, delete_px_fast_begin, delete_px_slow_begin, motor_blocking_meth, stop_motorsXY_queue, vel_X, vel_Y, time_out_slow_motion, add_time_theory, dirSlow, good_trig_key1, limitwait_move_tuple, quiet_the_trigger, time, queueEmpty):

    
    ## define pos
        
    pos_slow_start = posSlow00 - dirSlow*(size_slow_mm/2 + offsetSlow + delete_px_slow_begin*pixel_size_slow) # slow is always in increasing value, you have to define another flag before if you want to be able to choose for that
    
    # # print('pos_slow_start ', pos_slow_start)
    
    if unidirectionnal == 2: # to the left
    
        pos_fast_start = posFast00 + size_fast_mm/2 + offsetFast + acceleration_offset_direct + delete_px_fast_begin*pixel_size_fast
        
    else: # to the right or bidirek (standard)
    
        pos_fast_start = posFast00 - size_fast_mm/2 - offsetFast - acceleration_offset_direct - delete_px_fast_begin*pixel_size_fast
        # offset is just a value in mm imposed by user
        # acceleration_offset_direct is the offset that allows the motor to accelerate
    
    if y_fast:
        
        fast_concerned = y_concerned
        slow_concerned = x_concerned
        vel_fast = vel_Y
        vel_slow = vel_X
        str_motor_fast = 2
        str_motor_slow = 1
        
    else: # y is slow

        fast_concerned = x_concerned
        slow_concerned = y_concerned
        vel_fast = vel_X
        vel_slow = vel_Y
        str_motor_fast = 1
        str_motor_slow = 2
    
    posFast0 = thorlabs_lowlvl_list.get_posXY_bycommand_meth(str_motor_fast, motor_stageXY) # in mm
    posSlow0 = thorlabs_lowlvl_list.get_posXY_bycommand_meth(str_motor_slow, motor_stageXY) # in mm

    # # in sec
    dur_move_fast = add_time_theory + abs(pos_fast_start - posFast0)/vel_fast # # add_time_theory = acc+dec
    dur_move_slow = add_time_theory + abs(pos_slow_start - posSlow0)/vel_slow
    timeout_fast = time_out_slow_motion + dur_move_fast
    timeout_slow = time_out_slow_motion + dur_move_slow
    # # print('timeout_slow', timeout_slow, timeout_fast)
    
    # # motor_stageXY.write(thorlabs_lowlvl_list.key_trigout_off)
    
    if quiet_the_trigger: # # was tested and in the end, did the inverse effect !! (making scan to bug)
        thorlabs_lowlvl_list.set_trig_meth(str_motor_fast, motor_stageXY, thorlabs_lowlvl_list.key_trigout_off)
    
    ## go to pos
    
    print(' !! telling to go to Xstart, Ystart positions... !!', pos_fast_start, pos_slow_start)

    if slow_concerned: # or (not x_concerned and not y_concerned)):
        
        cond_vel = dur_move_slow > limitwait_move_tuple[0]
        if cond_vel: # # velocity too slow to wait for it
            # # print('reset vel slow', dur_move_slow, limitwait_move_tuple[0])
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_slow, limitwait_move_tuple[1], limitwait_move_tuple[2])) # dflt vel, accn
        
        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_slow, pos_slow_start))  # move

        blocking = True
        was_stopped = motor_blocking_meth(motor_stageXY, str_motor_slow, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, timeout_slow, 20, time, blocking) # 2nd str_motor is for stop
        
        if was_stopped: # has been stopped during return to init positions
            pos_slow_start = thorlabs_lowlvl_list.get_posXY_bycommand_meth(str_motor_slow, motor_stageXY) # real posX set
        
        if cond_vel: # # velocity too slow to wait for it
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_slow, limitwait_move_tuple[5], limitwait_move_tuple[6])) # normal vel, accn
    
    # setting fast position in last normally improve perf. because next move will also be with fast motor      
    if fast_concerned: # or (not x_concerned and not y_concerned)):
    
        cond_vel = dur_move_fast > limitwait_move_tuple[0]
        if cond_vel: # # velocity too slow to wait for it
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_fast, limitwait_move_tuple[1], limitwait_move_tuple[2])) # dflt vel, accn
    
        motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(str_motor_fast, pos_fast_start))  # move

        blocking = True
        was_stopped = motor_blocking_meth(motor_stageXY, str_motor_fast, stop_motorsXY_queue, queueEmpty, thorlabs_lowlvl_list, timeout_fast, 20, time, blocking) # 2nd str_motor_fast is for stop
    
        if was_stopped: # has been stopped during return to init positions
            pos_fast_start = thorlabs_lowlvl_list.get_posXY_bycommand_meth(str_motor_fast, motor_stageXY) # real posX set
        
        if cond_vel: # # velocity too slow to wait for it
            motor_stageXY.write(thorlabs_lowlvl_list.commandGen_setvelparamXY_meth(str_motor_fast, limitwait_move_tuple[3], limitwait_move_tuple[4])) # dflt vel, accn
            
    # if ((k % 2) and not unidirectionnal): # odd line and bidirec (going reverse)
    '''the change of pos during scan is more tricky in bidirek because the scan can be in process of going in reverse direction, so you have to shift the positions wisely
    
    You could redefined pos_fast_start, but it could imply some trigger/reading problem if the new distance to travel is too short
    So I chose to consider the order to change X or Y only if the motot is about to go to direct direction (that could lead a latence, though)
    '''
    
        # #motor_fast.move_to(pos_fast+ nbPX_fast*pixel_size_fast + acceleration_offset_reverse + acceleration_offset_direct, True) # first pos of fast
        # motor_stageXY.write(thorlabs_lowlvl_list.commandGen_moveAbsXY_meth(motor_fast, pos_fast + nbPX_fast*pixel_size_fast + acceleration_offset_reverse + acceleration_offset_direct))
        # blocking = True
        # if blocking: # wait for MGMSG_MOT_MOVE_COMPLETED
        #     bb = motor_stageXY.read(20) 
        # print(bb)
        
    # # print('posfast is in return ', pos_fast)
    if quiet_the_trigger:
        thorlabs_lowlvl_list.set_trig_meth(str_motor_fast, motor_stageXY, good_trig_key1)
    
    return pos_fast_start, pos_slow_start