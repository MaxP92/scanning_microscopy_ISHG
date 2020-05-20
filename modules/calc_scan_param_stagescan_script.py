# -*- coding: utf-8 -*-
"""
Created on Nov 24 16:35:13 2017

@author: Maxime PINSARD
"""
'''
calculate scan parameters (stage scan)

pixell means read_buffer_offset
'''

from modules import thorlabs_lowlvl_list

def adjust_stage_scan_param_func(step_fast, speed_fast, acc_fast, trigout_maxvelreached, acc_offset_spbox_value, dec_offset_spbox_value, speed_fast_old, acc_fast_old, pixell_direct_imposed, pixell_reverse_imposed, profile_mode, jerk):
    # step_fast is in mm !!
    
    ## parameters with old values (for comparison)
     # INSIDE acq., the measured vel. and acc. may differ a bit from the imposed values, and (acc_offset, pixell) is calculated with old parameters for after
     
    if profile_mode < 2: # trapez
        fact = 2 # I wwanted to be able to change it at first, but it's clearly 2 if you do the maths
        
        acceleration_offset_direct_theo_before = 1/fact*speed_fast_old**2/acc_fast_old # distance in mm to do for acceleration or decceleration

    else: #s-curve
        acceleration_offset_direct_theo_before = 1/2*speed_fast_old**2/acc_fast_old + acc_fast_old*speed_fast_old/(2*jerk) # distance in mm to do for acceleration or decceleration
        
    deceleration_offset_direct_theo_before = acceleration_offset_direct_theo_before
    
    if trigout_maxvelreached == 1:
        pixell_theory_before = 0
    elif trigout_maxvelreached == 2: # in motion
        if profile_mode < 2: # trapez
            pixell_theory_before = speed_fast_old*(speed_fast_old/acc_fast_old)*step_fast # in number of pixel
        else: #s-curve
            pixell_theory_before =  speed_fast_old*(speed_fast_old/acc_fast_old + acc_fast_old/jerk)/step_fast # in number of pixel
    
    ## calculate new parameters 
    # outside acq., the user changed some parameters that lead to new theo vel. and acc., and acc_offset and pixell have thus new theo values
       
    dwll_time = (step_fast)/(speed_fast)*1e6 # in us
    
    fact = 2 # I wwanted to be able to change it at first, but it's clearly 2 if you do the maths
    if profile_mode < 2: # trapez
        
        acceleration_offset_direct_theo = 1/fact*speed_fast**2/acc_fast # distance in mm to do for acceleration or decceleration

    else: #s-curve
        acceleration_offset_direct_theo = 1/fact*speed_fast**2/acc_fast + acc_fast*speed_fast/(2*jerk) # distance in mm to do for acceleration or decceleration
    # distance in mm to do for acceleration or decceleration
    
    deceleration_offset_direct_theo = acceleration_offset_direct_theo
    #scan_stage_px_offset_direct_theo = 0.023500 # in mm, in "variables" file
    # scan_stage_px_offset_direct_theo = 0.1*acceleration_offset_direct_theo/0.25
    
    if acc_offset_spbox_value is None: acc_offset_spbox_value = acceleration_offset_direct_theo
    if dec_offset_spbox_value is None: dec_offset_spbox_value = deceleration_offset_direct_theo
    
    if profile_mode < 2: # trapez
        pixell_theory_inmotion =  speed_fast*(speed_fast/acc_fast)/step_fast # in number of pixel
    else: #s-curve
        pixell_theory_inmotion =  speed_fast*(speed_fast/acc_fast + acc_fast/jerk)/(step_fast) # in number of pixel
    
    if trigout_maxvelreached == 1:
        pixell_theory = 0 # in number of pixel
    elif trigout_maxvelreached == 2: # in motion
        pixel_theory = pixell_theory_inmotion
    
    if trigout_maxvelreached == 1: 
        # if max vel. reached
        scan_stage_px_offset_direct_theo = 0
    elif trigout_maxvelreached == 2:
        # if in motion
        scan_stage_px_offset_direct_theo = pixell_theory

    ## re-adjust pixell in function of the value of acc_offset entered by user
    # outside acq., the user changed acc_offset by a custom value and pixell must be changed accordingly
    
    # pixell = Delta_t(acc)/timePX = v_fast**2/(acc_fast*step_fast) = 2*acc_offset/step_fast
    
    # if trigout_maxvelreached == 1:
    #     # pixell_to_set = max((acc_offset_spbox_value/step_fast - 0.5*pixell_theory), 0) 
    #     pixell_to_set = 0 + max(0, (acc_offset_spbox_value - acceleration_offset_direct_theo))/step_fast
    #     # the additional acc_offset in this mode is normally done at constant speed, so it's just acc_offset_supp/v*timePX so acc_offset/step_fast
    # elif trigout_maxvelreached == 2: # in motion
        # pixell_to_set = 2*acc_offset_spbox_value/step_fast # 2* because of the 0.5 in acc_offset
        
    pixell_to_set = pixell_theory + max(0, (acc_offset_spbox_value - acceleration_offset_direct_theo))/step_fast 

    ## only to re-adjust acc_offset entered by user with the newly measured acc and vel. 
    # INSIDE acq., the user has changed acc_offset by a custom value (or not), this value is adjusted correspondingly with new vel. and acc. values measured

    acc_offset_recalc = max(0, acc_offset_spbox_value - acceleration_offset_direct_theo_before + acceleration_offset_direct_theo) 
    dec_offset_recalc = max(0, dec_offset_spbox_value - deceleration_offset_direct_theo_before + deceleration_offset_direct_theo) 
        # the additional acc_offset in this mode is normally done at constant speed, so it's just acc_offset/v*timePX so acc_offset/step_fast
        
    # # print('\nhey')
    # # print(acc_offset_spbox_value,  acceleration_offset_direct_theo_before ,acceleration_offset_direct_theo)
        
    ## re-adjust pixell in function of the value of pixell entered by user
    # INSIDE acq., the user has changed pixell by a custom value, this value is adjusted correspondingly with new vel. and acc. values measured
    
    # if trigout_maxvelreached == 1:
    #     # pixell_to_set_before = max((acc_offset_spbox_value/step_fast - 0.5*pixell_theory_before), 0) 
    #     pixell_to_set_before = max((acc_offset_spbox_value/step_fast - 1/fact*pixell_theory_before), 0) 

   # #       # the additional acc_offset in this mode is normally done at constant speed, so it's just acc_offset/v*timePX so acc_offset/step_fast
    # elif trigout_maxvelreached == 2: # in motion
    #     # pixell_to_set_before = 2*acc_offset_spbox_value/step_fast # 2* because of the 0.5 in acc_offset
    #     pixell_to_set_before = fact*acc_offset_spbox_value/step_fast 

    pixell_to_set_before = pixell_theory_before + max(0, (acc_offset_spbox_value - acceleration_offset_direct_theo_before))/step_fast
    
    if pixell_direct_imposed == pixell_theory_before: # supposed to be pixell_theory_before if the user did not imposed acc_offset or it manually
        pixell_direct_adjusted = pixell_theory
        
    else: # > 0, the user did imposed acc_offset or it manually
    
        if pixell_direct_imposed != pixell_to_set_before: # the user changed pixell manually, his order must be respected and the new acc_offset is not taken into account
            pixell_direct_adjusted = max((pixell_direct_imposed - pixell_theory_before + pixell_theory), 0) 
        else: # the user changed acc_offset manually, but this one has changed now and pixell must be changed accordingly
        
            pixell_direct_adjusted = pixell_to_set
    
    # reverse   
    if pixell_reverse_imposed == pixell_theory_before: # supposed to be pixell_theory_before if the user did not imposed acc_offset or it manually
        pixell_reverse_adjusted = pixell_theory
        
    else: # > 0, the user did imposed acc_offset or it manually
    
        if pixell_reverse_imposed != pixell_to_set_before: # the user changed pixell manually, his order must be respected and the new acc_offset is not taken into account
            pixell_reverse_adjusted = max((pixell_reverse_imposed - pixell_theory_before + pixell_theory), 0) 
        else: # the user changed acc_offset manually, but this one has changed now and pixell must be changed accordingly
        
            pixell_reverse_adjusted = pixell_to_set    
        
            
    # print('pixell_reverse_adjusted ', pixell_reverse_adjusted , 'pixell_reverse_imposed ', pixell_reverse_imposed)
    
    add_time_theory = 2*(pixell_theory_inmotion/speed_fast*step_fast) + (max(0, (acc_offset_spbox_value - acceleration_offset_direct_theo)) +  max(0, dec_offset_spbox_value  - deceleration_offset_direct_theo))/speed_fast # 2 for direct and reverse
    # first term is for real the accleration offset (factor of 2 in time, 2nd term is the imposed additionnal acc_offset (not the factor of 2 because it's travelled at constant velocity)
    
    # # print('acc_offset_spbox_value ', acc_offset_spbox_value, 'dec_offset_spbox_value ', dec_offset_spbox_value)
    
    ## return
    
    return dwll_time, acceleration_offset_direct_theo, deceleration_offset_direct_theo, scan_stage_px_offset_direct_theo, pixell_to_set, acc_offset_recalc, dec_offset_recalc, pixell_direct_adjusted, pixell_reverse_adjusted, add_time_theory
    
    
def profilemode_jerk_set_stgscn_func(profile_mode_fast, jerk_fast_imposed, lbl_mtr_fast, profile_mode_slow, jerk_slow, lbl_mtr_slow, motor_stageXY):
    '''
    to set the profile mode and the jerk, in stage scan
    profile_mode : 0 (or 1) for trapez ; 2 for S-curve
    jerk (S-curve) : in mm/s3, from 0.0108 to 22000002 mm/s3 
    lbl_mtr_fast : 1 for X, 2 for Y
    motor_stageXY : motor Object
    '''
    for ii in range(2):
        
        if ii == 0:
            lbl_mtr = lbl_mtr_slow
            profile_mode = profile_mode_slow
            jerk_imposed = jerk_slow
        elif ii == 1: 
            lbl_mtr = lbl_mtr_fast
            profile_mode = profile_mode_fast
            jerk_imposed = jerk_fast_imposed
    
        prof, jerk = thorlabs_lowlvl_list.get_profile_bycommand_meth(lbl_mtr, motor_stageXY)
        # # print(prof1, good_prof_verif, jerk1, good_prof_key1)
        
        if (prof < 2 and profile_mode < 2): # indeed trapezoidal
    
            print('Profile CH%d fast was indeed trapezoidal : OK' % (lbl_mtr))
            
        elif (prof == profile_mode and abs(jerk - jerk_imposed) < 1e-3): # S-curve wanted and Jerk param is good
            print('Profile CH%d fast was indeed S-curve : OK and Jerk was indeed %.2f mm/s3!' % (lbl_mtr, jerk))
            
        else: # not good profile
    
            command_set_profile = thorlabs_lowlvl_list.commandGen_setProfile_withjerk_meth(lbl_mtr, profile_mode, jerk_imposed)
            motor_stageXY.write(command_set_profile)  # set profile to trapezoidal for both channels
            # control
            prof, jerk = thorlabs_lowlvl_list.get_profile_bycommand_meth(lbl_mtr, motor_stageXY)
    
            if (prof < 2 and profile_mode < 2): # indeed trapezoidal
            
                print('Profile CH%d fast is now trapezoidal : OK' % (lbl_mtr))
                
            elif (prof == profile_mode and abs(jerk - jerk_imposed) < 1e-3): # S-curve wanted and Jerk param is good
                print('Profile CH%d fast is now S-curve : OK and Jerk is now %.2f mm/s3!' % (lbl_mtr, jerk))
                
            else:
                print('Profile CH%d is now %s : WARNING and Jerk is %.2f mm/s3!' % (lbl_mtr, prof, jerk))
    
    # last (prof, jerk) will be for fast motor
    
    return prof, jerk
    
def vel_acc_opt_stgscn_func(speed_fast, jerk_fast, size_fast_um, stp_slow_um, acc_fast, acc_slow):
    '''
    to calc the opt values for vel and accn, in stage scan
    sizes are in um !!
    '''

    # warning use this value only for S-curve !!
    opt_acc_fast = (speed_fast*jerk_fast)**0.5 # # different from opt_acc_fast_theo_scurve because does not use opt vel
    
    # # print(opt_acc_fast, speed_fast,jerk_fast)
    
    # for trapez AND S-curve
    opt_vel_fast =(size_fast_um*1e-3*acc_fast/2)**0.5
    
    opt_vel_slow = round((acc_slow*stp_slow_um*1e-3)**0.5) # the step is used, because it is the distance traveled each time
    # also, not a factor of two because acc+dec. is counted in the distance traveled (see theo calc.)
    
    ## theo for S-curve
    
    opt_vel_fast_theo_scurve = ((size_fast_um/2*1e-3)**2*jerk_fast)**(1/3)
    opt_acc_fast_theo_scurve = (opt_vel_fast_theo_scurve*jerk_fast)**0.5

    ## return
    
    return opt_acc_fast, opt_vel_fast, opt_vel_slow, opt_vel_fast_theo_scurve, opt_acc_fast_theo_scurve 