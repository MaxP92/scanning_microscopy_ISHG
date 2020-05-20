# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

def init_daq(nidaqmx, pmt_channel_list, min_val_volt_list, max_val_volt_list, timebase_src_end, trig_src, delay_trig, scan_mode, sample_rate, time_by_px, time_expected_sec, numpy, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, dev_list, update_time, pack_params_new_galvos, param_ini, external_clock, dig_galvos_use, time_base_ext, method_watch, analog_input, ai_trig_control, name_list_AI_tasks, name_list_trigctrl_tasks, ishg_EOM_AC, jobs_scripts, mtr_trigout_cntr_task, nametask_mtr_trigout_list, mtr_trigout_retriggerable, lock_timing):
    
    
    '''
    init DAQ
    list of NI constant can be found here : http://pamguard.sourceforge.net/API_1_15_09/doc/constant-values.html#nidaqdev.NIConstants
    '''
    
    if len(pack_params_new_galvos) > 2: [_, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, _, lvl_trigger_not_win, _, _, _, _, _, nb_px_slow, _, _, time_list, _, _, _, _, _, _, fact_buffer] = pack_params_new_galvos
    else: lvl_trigger_not_win, nb_px_slow = pack_params_new_galvos; fact_buffer = 1
    
    min_val_volt_list_corr = list(min_val_volt_list) # WARNING A LIST IS PASSED BY REFERENCE
    max_val_volt_list_corr = list(max_val_volt_list)
    
    device_to_use_AI = trig_src[0]
    
    if device_to_use_AI == dev_list[0]: # 6110
        bits_read = 12
        sample_rate_min = param_ini.sample_rate_min_6110
        calibration_volt = param_ini.calibration_volt_6110
        master_tb_name = 'MasterTimebase'
        min_rate = 0.1e6  # Hz
        
    elif (len(dev_list) > 1 and device_to_use_AI == dev_list[1]): # 6259
        bits_read = 16
        sample_rate_min = param_ini.sample_rate_min_6259
        calibration_volt = param_ini.calibration_volt_6259 
        master_tb_name = '20MHzTimebase'
        min_rate = 0.1 # Hz

    device_to_use_AI.reset_device() # abort all the Task and clear buffers/properties
    # # trig_src_name = ('/%s/%s' % (device_to_use_AI.name, trig_src[1])) 
    
    # # '''BUG IN SCAN STAGE MODE !!'''
    # # if (ishg_EOM_AC[0] and ishg_EOM_AC[-1][0]): # flag for fast iSHG
    # # # flag_impose_ramptime_as_exptime
    # #     time_by_px = jobs_scripts.ishgEOM_defexptime_func(ishg_EOM_AC)  # # ishg_EOM_AC[-1][1] it's a function !! # # see EOMph_nb_samps_phpixel_meth
    # #     # new exp. time, sec = ramp_time00 + dead_time_begin + dead_time_end
    # #     fake_size_fast = int(time_expected_sec/nb_px_slow/time_by_px)
    # #     # time_expected_sec is  line time
    # #     # # continued after
        
    ## task creation
    
    if ('analog_input' in locals() and analog_input is not None):
        analog_input.close()
    name_AI = name_list_AI_tasks[-1] # last
    analog_input = nidaqmx.Task(name_AI)
    name_list_AI_tasks = ['%s_0%d' % (name_AI[:-3], int(name_AI[-1])+1)]

    nb_pmt_channel = sum(pmt_channel_list)
    
    ct = 0
    for k in range(len(pmt_channel_list)):
        if pmt_channel_list[k] == 1: # PMT must be activated
            
            if ct == 0: # first PMT
                name_pmt = ('%s/ai%d' % (device_to_use_AI.name, k))
                # # if nb_pmt_channel == 1: # one PMT 
                # #     break # outside 'for' loop
                # else: # more than one PMT
                ct += 1
            else: # next PMTs
                name_pmt = ('%s,%s/ai%d' % (name_pmt, device_to_use_AI.name, k))
                
    analog_input.ai_channels.add_ai_voltage_chan(name_pmt) 
    # when you put up above 10, it returns 20, also the min is -max
    # default is nidaqmx.constants.TerminalConfiguration.DEFAULT
    # the AI channel (read) uses Pseudodifférential config for input, and reference assymetrical (RSE) for output on a 6110 card so choosing the default indeed choose Pseudodifferential
    
    AI_bounds_list =[]; AI_bounds_list = [AI_bounds_list+[0,0] for _ in range(nb_pmt_channel)]
    # for min max voltage
    k0 = 0; ct_supp = 0
    for num_pmt in range(len(pmt_channel_list)):
        if pmt_channel_list[num_pmt] == 1: # PMT must be activated
            # # print(num_pmt, min_val_volt_list_corr, k0)
            AI_bounds_list[k0][0] = analog_input.ai_channels[k0].ai_min = min_val_volt_list_corr[k0] # will be coerced
            AI_bounds_list[k0][1] = analog_input.ai_channels[k0].ai_max = max_val_volt_list_corr[k0] # will be coerced
            
            max_val_volt_list_corr[k0] = min(max_val_volt_list_corr[k0], analog_input.ai_channels[k0].ai_max)
            if not param_ini.use_volt_not_raw:
                min_val_volt_list_corr[k0] = round((min_val_volt_list_corr[k0]-analog_input.ai_channels[k0].ai_min)*(2**(bits_read)-1)/(analog_input.ai_channels[k0].ai_max-analog_input.ai_channels[k0].ai_min) - 2**(bits_read-1)) # from now it will be in int16 !
                
                max_val_volt_list_corr[k0] = round((max_val_volt_list_corr[k0]-analog_input.ai_channels[k0].ai_min)*(2**(bits_read)-1)/(analog_input.ai_channels[k0].ai_max-analog_input.ai_channels[k0].ai_min) - 2**(bits_read-1)) # from now it will be in int16 !
            # !!!  (2**(bits_read)-1) NOT 2**(bits_read-1)
                
            else: # the device use a calibration
                max_val_volt_list_corr[k0] = max_val_volt_list_corr[k0]*calibration_volt
                min_val_volt_list_corr[k0] =  min_val_volt_list_corr[k0]*calibration_volt
        # else: # no PMT # num_pmt
        #     max_val_volt_list_corr[num_pmt] = min_val_volt_list_corr[num_pmt] = 0
            k0+=1
        else: # no PMT
            if num_pmt < len(min_val_volt_list_corr)+ct_supp:
                del min_val_volt_list_corr[num_pmt - ct_supp]
                del max_val_volt_list_corr[num_pmt - ct_supp]
                ct_supp+=1
    # analog_input.channels.ai_min = min_val_volt
    # analog_input.channels.ai_max = max_val_volt
    # # only valid ranges are +-42, +-20, +-10, +-5, +-2, +-1, +-0.5, +-0.2
    # # every other value is ceiled to the nearest value
    # # so might be good to have the PMT in -10, 10V physically rather than 0, 13V
    # # print(min_val_volt_list_corr, max_val_volt_list_corr)
    
    # # max_val_volt_list_corr and min are now the values that would be min and max if no action were applied to the img values
    # # print('!!!!!', max_val_volt_list_corr)
    
    if (len(dev_list) > 1 and device_to_use_AI.name == dev_list[1].name): # 6259
        if param_ini.use_RSE:
            analog_input.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.RSE # 
        else:
            analog_input.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL #
            
    else: # 6110
        analog_input.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.PSEUDODIFFERENTIAL # only one available
        
    data = 0 ;  nbPostTriggerSamps = 0;  params_galvos = None
    
    if external_clock: # use timebase from galvos
    
        sample_rate = meas_smp_rate_ext_clck(nidaqmx, device_to_use_AI.name, param_ini.ext_smpclk_end, param_ini.ext_smpclk_minRate, param_ini.ext_smpclk_maxRate)
        time_by_px = max(1, round(time_by_px*sample_rate))/sample_rate  # a discrete range of exp time can be used
        
        print('exp time is ', time_by_px, 'meaning averaging on ', round(time_by_px*sample_rate))
    
    if scan_mode != 0: #elif (scan_mode == 1 or scan_mode == -1): # galvos or static acq
        if nb_px_slow<=1: lock_timing= (lock_timing[0], True) # lock_uptime
        sample_rate_new, buffer_continuous, update_time = daq_acq_params_def(sample_rate, numpy, time_by_px, time_expected_sec, analog_input, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, 1, update_time, None, None, None, sample_rate_min, None, None, lock_timing, 1)  # buffer mode
    else: # stage scan only , or one line buffer
        max_buffer_AI = round((2**32/(2*nb_pmt_channel)-2))/param_ini.meas_fact_forMaxBufferDAQ_add
        
        sample_rate_new, data, number_of_samples, buf_size, nbPostTriggerSamps, nbPreTriggerSamps_min = daq_acq_params_def(sample_rate, numpy, time_by_px, time_expected_sec, analog_input, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, 1, None, max_buffer_AI, sample_rate_min, None, (None,None,nb_px_slow,None,None,None,None), lock_timing, 0) # no buffer many lines in stg scn
        
    ## triggers

    # # print('scan_mode', scan_mode, dig_galvos_use)
    
    # # dig_galvos_use = 0 # static OR classic dig galvos with start trigger
    # # dig_galvos_use = 2 # use pause trigger meas. with dig galvos
    # #   dig_galvos_use = 1 # use pause trigger that callbacks with dig galvos
    
    if (scan_mode == -2 or (scan_mode == 1 and dig_galvos_use)): # anlg galvos or dig galvo with pause trigger
    
        use_trigger_anlgcompEv_onFallingEdges = param_ini.use_trigger_anlgcompEv_onFallingEdges if scan_mode == -2 else False # # the counter is used by the output for iSHG fast. If no ishg fast, could use the same params as anlg galvos
        # # print('\n use_trigger_anlgcompEv_onFallingEdges', use_trigger_anlgcompEv_onFallingEdges, '\n')
                
        ai_trig_control, sample_rate_new, params_galvos = ai_read_def_galvoscn(nidaqmx, analog_input, dev_list, device_to_use_AI, param_ini.DO_parallel_trigger, method_watch, param_ini.use_RSE, sample_rate_new, numpy, time_by_px, time_expected_sec, sample_rate_min, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, dig_galvos_use, pack_params_new_galvos, ai_trig_control, name_list_trigctrl_tasks, use_trigger_anlgcompEv_onFallingEdges, lock_timing )
        
        # # print('params_galvos !!', params_galvos)
        
    elif scan_mode == 0:  # # stage scan    
        
        trig_src_name = ('/%s/%s' % (device_to_use_AI.name, trig_src[1]))
        analog_input.triggers.start_trigger.cfg_dig_edge_start_trig(trig_src_name) # default rising
        # (trigger_source, trigger_edge=<Edge.RISING: 10280>)
        # analog_input.CfgDigEdgeStartTrig(trig_src_name, 10280)  # DAQmx_Val_Rising = rising = 10280
        # print(analog_input.triggers.start_trigger.delay)
        # print(analog_input.triggers.start_trigger.delay_units)
        analog_input.triggers.reference_trigger.cfg_dig_edge_ref_trig(trig_src_name, nbPreTriggerSamps_min, trigger_edge=nidaqmx.constants.Edge.FALLING)
        # (trigger_source, pretrigger_samples, trigger_edge=<Edge.RISING: 10280>)
        num_samps_per_chans = nbPostTriggerSamps + nbPreTriggerSamps_min # per channel
    else: # # no stage, no galvos callback and no anlg galvos
        if scan_mode == -2:# anlg galv
            [time_trig_paused, duration_one_line_real] = time_list
        else: lvl_trigger_not_win = duration_one_line_real= time_trig_paused=None 
        params_anlg_galv = (lvl_trigger_not_win, method_watch, nb_px_slow, duration_one_line_real, time_trig_paused, dig_galvos_use, time_expected_sec)
        sample_rate_new, buffer_continuous, maxSmp_paquet, divider, dividand = daq_acq_params_def(sample_rate_new, numpy, time_by_px, time_expected_sec, analog_input, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, scan_mode, fact_buffer, param_ini.calc_max_buf_size(nb_pmt_channel)[0], sample_rate_min, None, params_anlg_galv, lock_timing, 0)   #no buffer mode
        params_galvos=[None, None, maxSmp_paquet, divider, dividand]

        if (scan_mode == 1 and dig_galvos_use == 0): #  dig galvos with no pause trigger (so st trigger)
        
            # sample_rate_new is round(param_ini.clock_galvo/param_ini.min_timebase_div)
            analog_input.triggers.start_trigger.cfg_dig_edge_start_trig(('/%s/%s' % (device_to_use_AI.name, trig_src[1])), trigger_edge=nidaqmx.constants.Edge.RISING) # default rising
            
            # print('trigger', ('/%s/%s' % (device_to_use_AI.name, trig_src[1])))
            
            #'''
            max_master_rate = 8e6 #analog_input.timing.samp_clk_timebase_rate # to use after
            if (delay_trig > 2/max_master_rate and not external_clock): # delay trig impossible if external sample clock
                
                analog_input.triggers.start_trigger.delay_units = nidaqmx.constants.TimeUnits.SECONDS
                # # analog_input.SetStartTrigDelayUnits(10364) # or 10364 for DAQmx_Val_Seconds is a int32
                analog_input.triggers.start_trigger.delay = delay_trig
                # # analog_input.SetStartTrigDelay(delay_trig) # is a float 64, 5e-6 sec
        #'''
     
    if ishg_EOM_AC[0]: # flag for fast iSHG
        # just for avoiding bug
        if scan_mode == 0: analog_input.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK; analog_input.timing.samp_quant_samp_mode = nidaqmx.constants.AcquisitionType.FINITE; analog_input.timing.samp_quant_samp_per_chan = num_samps_per_chans
        max_rate = analog_input.timing.samp_clk_max_rate if sample_rate_new == sample_rate else sample_rate_new
        sample_rate_new, ishg_EOM_AC, _ = jobs_scripts.ishgEOM_adjdtvsrate_func(sample_rate_new, max_rate, min_rate, param_ini.master_rate_daq_normal, ishg_EOM_AC, time_by_px, lock_timing[0], False, False, True) # # adjust if necessary rate or dead times to match
        # # last args : fixed, fixed, fixed, expfixed
    ## timing

    # # if scan_mode != 0:  # not stage scan
    
    # # print('\n scan_mode \n', scan_mode, external_clock)
    
    if (scan_mode != 0 and not (scan_mode == 1 and time_base_ext and not external_clock)): # static acquisition or galvos (dig, anlg) scan. Internal clock
        analog_input.timing.samp_clk_timebase_src = '/%s/%s' % (device_to_use_AI.name, master_tb_name) # internal
        # 2nd sample_rate_new is buffer size, max rate = 5MHz due to analog2digital converter of the DAQ card
        analog_input.timing.cfg_samp_clk_timing(rate = sample_rate_new, sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS ) # buffer size specified after
        
    elif (scan_mode == 1 and time_base_ext and not external_clock): # use of external master_timebase (digital galvos mode classic) 
    
        analog_input.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK # 10388) # = DAQmx_Val_SampClk # SetSampTimingType
        
        # important not to set it if an external clock is imposed after
        analog_input.timing.samp_clk_timebase_src = ('/%s/%s' % (device_to_use_AI.name, timebase_src_end))  #.SetSampClkTimebaseSrc(timebase_src_name) # PFI1 is galvo clock at 8MHz
        analog_input.timing.samp_clk_timebase_rate = param_ini.clock_galvo_digital # SetSampClkTimebaseRate(sample_rate_new)
        # max expected rate
        analog_input.timing.samp_clk_timebase_div = int(round(param_ini.clock_galvo_digital/sample_rate_new)) # SetSampClkTimebaseDiv(2) # timebase divisor is 2 minimum, which gives a rate 8/2 = 4MHz # # sometimes round gives a .0 !!
        analog_input.timing.samp_clk_timebase_active_edge = nidaqmx.constants.Edge.RISING #SetSampClkTimebaseActiveEdge 

        analog_input.timing.samp_quant_samp_mode = nidaqmx.constants.AcquisitionType.CONTINUOUS #SetSampQuantSampMode(10123) # 10123 for DAQmx_Val_ContSamps
            
    elif scan_mode == 0: # internal clock , indeed stage scan, and not static acquisition

        analog_input.timing.cfg_samp_clk_timing(sample_rate_new, sample_mode= nidaqmx.constants.AcquisitionType.FINITE , samps_per_chan = num_samps_per_chans)
        
        analog_input.in_stream.over_write = nidaqmx.constants.OverwriteMode.OVERWRITE_UNREAD_SAMPLES # if some samples were not read and still in buffer, the new line is more important so the Task will overwrite them rather than bugs
        
        ## new imposed buffer size
        
        analog_input.in_stream.input_buf_size = buf_size
        # max buffer_size is max_buffer_size_daq_theo = round((2**32/(2*nb_pmt_channel)-2))
        # numpy arrays are limited to 1e8 if float precision
            
        buf_size = analog_input.in_stream.input_buf_size
        print('buf_size ', buf_size)
        
        ## read properties
        
        # if method_read > 0:
        #     analog_input.in_stream.read_all_avail_samp = True# 
        # else:
        analog_input.in_stream.read_all_avail_samp = False
        
        # print(analog_input.in_stream.read_all_avail_samp)
        
        analog_input.in_stream.relative_to = nidaqmx.constants.ReadRelativeTo.CURRENT_READ_POSITION # is DAQmx_Val_FirstPretrigSamp by default if you use CfgDigEdgeRefTrig
        # # analog_input.in_stream.relative_to = nidaqmx.constants.ReadRelativeTo.FIRST_PRETRIGGER_SAMPLE
        # normally, allows to read samples just after the trigger was fired
        #DAQmxSetReadRelativeTo ; 10425 DAQmx_Val_CurrReadPos ; 10427 DAQmx_Val_FirstPretrigSamp
    
    device_to_use_trigout_EOMph = analog_input.devices[0].name 
    
    if (scan_mode != 0): # # no stage scn
        analog_input.timing.samp_quant_samp_per_chan = buffer_continuous # in CONTINUOUS, used to set the buffer size
        analog_input.in_stream.input_buf_size = buffer_continuous # 
        # # nametask_mtr_trigout_list = None # # so task won't be defined
        if (ishg_EOM_AC[0] and scan_mode != -1):  # ishg fast, but not the case of static acq. (no trigger possible)
            src_trigger_motor_EOMph = pack_params_new_galvos[11] if scan_mode == -2 else params_galvos[0] # trig_src_end_master_toExp # the term to be connected (PFI9)
        
    else: # internal clock , indeed stage scan, and not static acquisition
        src_trigger_motor_EOMph = trig_src[1]  # the term to be connected 
        # # 'AnalogComparisonEvent'# !!!! 2019.08.14 
        device_to_use_trigout_EOMph = device_to_use_AI.name
        
    CO_for_EOMphtrig_already_def = (param_ini.use_same_CO_for_EOMphtrig and method_watch == 4 and ((scan_mode == 1 and dig_galvos_use))) # scan_mode == -2 or 
    if CO_for_EOMphtrig_already_def: 
        device_to_use_trigout_EOMph = pack_params_new_galvos[1].name # # dev to use watch trig, if same CO is used for outputting EOM pulse and galvo callback
        ctr_src_trigger_trigout_EOMph = params_galvos[0] # # src end master
    else: ctr_src_trigger_trigout_EOMph = param_ini.ctr_src_trigger_trigout_EOMph
    
    if external_clock: # external SAMPLE clock, not master timebase
        analog_input.timing.samp_clk_src = ('/%s/%s' % (device_to_use_AI.name, param_ini.ext_smpclk_end)) # # ''
        
    if param_ini.use_volt_not_raw:
        stream_reader_ai = nidaqmx.stream_readers.AnalogMultiChannelReader(analog_input.in_stream)
        meth_read = stream_reader_ai.read_many_sample

    else: # read int16
        stream_reader_ai = nidaqmx.stream_readers.AnalogUnscaledReader(analog_input.in_stream)
        meth_read = stream_reader_ai.read_int16

    msg_warning_ifstop_taskundone = '\nWarning 200010 occurred.\n\nFinite acquisition or generation has been stopped before the requested number of samples were acquired or generated.'
    
    print('allocating buffer read ...')
    analog_input.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # commit the Task (programme), so that it can start faster 
    print(' ... buffer read allocated')
    buf_size = analog_input.in_stream.input_buf_size
    print('buf_size AI read', buf_size)
    actual_rate = analog_input.timing.samp_clk_rate
    print('actual_rate AI', actual_rate, 'src', analog_input.timing.samp_clk_src, '// timebase', analog_input.timing.samp_clk_timebase_src) # just verify
    print(analog_input.channels)
    # # print(analog_input.timing.samp_quant_samp_mode)
    # the Task is now programmed
    
    # # print('\n scan_mode \n', analog_input.timing.samp_clk_timebase_src, analog_input.triggers.start_trigger.dig_edge_src)

    # to commit the Task, i.e. program hardware to fit the task so it can start faster
    # analog_input.TaskControl (DAQmx_Val_Task_Commit)
    
    if mtr_trigout_cntr_task is not None: # 'mtr_trigout_cntr' in locals() 
        mtr_trigout_cntr_task.close()
        mtr_trigout_cntr_task = None # # reinit
    
    # # if not ishg_EOM_AC[0]:  # standard
    ishg_EOM_AC_insamps = ishg_EOM_AC # because sent to other Processes !!
    port_to_use_trigout_EOMph = None
    
    if ishg_EOM_AC[0] in (1, 11): # flag ishg acq. treat
        ishg_EOM_AC_insamps = jobs_scripts.EOMph_nb_samps_phpixel_meth(sample_rate_new, ishg_EOM_AC, param_ini.tolerance_change_nbphsft, param_ini.exploit_all_acqsamps, param_ini.ps_step_closest_possible_so_lstsamps_inddtime, param_ini.add_nb_ps)
            
    if ((ishg_EOM_AC[0] and scan_mode != -1) or mtr_trigout_retriggerable == -1): # # not static acq., or one line scan
        port_to_use_trigout_EOMph = '%s/%s' % (device_to_use_trigout_EOMph, param_ini.cntr_chan_name_trigout_EOMph) if not CO_for_EOMphtrig_already_def else '%s/ctr%s' % (device_to_use_trigout_EOMph, pack_params_new_galvos[2])  # # Dev1 ctr0
        if mtr_trigout_retriggerable == -1: # # no trigger because just one line of scan
            ctr_src_trigger_trigout_EOMph = src_trigger_motor_EOMph = None # # no trigger because just one line of scan
            nametask_mtr_trigout_list = param_ini.nametask_mtr_trigout_list
        mtr_trigout_cntr_task, nametask_mtr_trigout_list = mtr_trigout_redefine_EOMph(nidaqmx,  mtr_trigout_cntr_task, nametask_mtr_trigout_list, device_to_use_trigout_EOMph, port_to_use_trigout_EOMph, ctr_src_trigger_trigout_EOMph, src_trigger_motor_EOMph, CO_for_EOMphtrig_already_def, param_ini.pulsewidth_ctroutEOM_sec, mtr_trigout_retriggerable) # # a list is passed by reference
        # # mtr_trigout_redefine_EOMph(nidaqmx, mtr_trigout_cntr, nametask_mtr_trigout_list, device_to_use, cntr_chan_name, ctr_src_trigger, src_trigger_motor, CO_for_EOMphtrig_already_def, pulse_width)
        
    return analog_input, ai_trig_control, msg_warning_ifstop_taskundone, nb_pmt_channel, data, nbPostTriggerSamps, time_by_px, update_time, sample_rate_new, [min_val_volt_list_corr, max_val_volt_list_corr, AI_bounds_list], meth_read, params_galvos, fake_size_fast, [ishg_EOM_AC_insamps, mtr_trigout_cntr_task, list(ishg_EOM_AC), (port_to_use_trigout_EOMph, param_ini.use_same_CO_for_EOMphtrig, param_ini.pulsewidth_ctroutEOM_sec)]
    
def daq_acq_params_def(sample_rate, numpy, time_by_px, time_expected_sec, analog_input, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, force_buffer_small, fact_buffer, max_buffer_AI, sample_rate_min, sample_rate_max, params_anlg_galv, lock_timing, mode_buffer):
    '''
    galvos will enter twice in that func, one with scan_mode=1 for buf continuous, one with 
    '''
    lock_smprate, lock_uptime = lock_timing
    master_clock_rate = analog_input.timing.samp_clk_timebase_rate # Hz, # 20e6 # this rate is divided to obtain other rates
    # # analog_output_daq_to_galvos.timing.samp_clk_timebase_master_timebase_div
    # # the 20MHz of the master clock rate is either divided by one (then by another integer) to produce rates > 100kHz, or by 200 to produce rates < 100kHz
    # master clock rate can be also 100e3 Hz, but is always 20e6 when Start first initiated
    if sample_rate_max is None:
        
        sample_rate_max = analog_input.timing.samp_clk_max_rate # 5e6
        # our 6110 card is a S-serie, so uses simultaneous sampling
    
    if (master_clock_rate % sample_rate): # not a divider of the master clock rate of 20MHz
        sample_rate00 = sample_rate
        sample_rate = master_clock_rate/numpy.ceil(master_clock_rate/sample_rate)
        
        print('Warning / I had to change the sample rate from %.2f to %.2f' % (sample_rate00, sample_rate))
    if sample_rate >  sample_rate_max:
        sample_rate00 = sample_rate
        sample_rate =  sample_rate_max
        if sample_rate == 1.25e6:
            sample_rate = param_ini.sample_rate_max_6259 # it's not good to drive the card 6259 to its max rate
        print('Warning / I had to change the sample rate from %.2f to %.2f' % (sample_rate00, sample_rate))

    if sample_rate < sample_rate_min:
        sample_rate = sample_rate_min
        
    fact_safety_buffer = 4 # # for mcontinuous buffers many lines

    if mode_buffer: # digital galvo or static, mode that have a buffer (and not one line only like stage scan)
        buf_size_2set = int(round(sample_rate*update_time*fact_safety_buffer)) # size of the buffer # # sometimes round gives a .0 !!
        
        max_buf = round((2**32/(2*nb_pmt_channel)-2))/param_ini.meas_fact_forMaxBufferDAQ_add
        # # print('l343, in buf check AI', sample_rate, update_time, fact_safety_buffer, buf_size_2set, max_buf)

        if buf_size_2set > max_buf:
            if (not lock_uptime or not lock_smprate):
                if not lock_uptime: # normal
                    update_time = int(max_buf/sample_rate/fact_safety_buffer)
                    print('sample_rate_read*update_time leads to a too large buffer for the DAQ: I will put update time to a lower value: %.2f' % update_time)
                elif not lock_smprate: sample_rate = max(sample_rate_min,  master_clock_rate/numpy.ceil(master_clock_rate/(max_buf/update_time/fact_safety_buffer)))
                buf_size_2set = int(round(sample_rate*update_time*fact_safety_buffer)) # size of the buffer # # sometimes round gives a .0 !!
            else: # have to put at limit
                buf_size_2set = int(round(sample_rate*update_time)) # no fact_safety_buffer
                if buf_size_2set > max_buf: raise Exception('smp rate AND update_time locked, cannot adjust the too high buffer !')
                else: print('WARN: smp rate AND update_time locked, too high buffer so risk to errors !!\n')

    else: # for defining the array size max
        lvl_trigger_not_win, method_watch, nb_px_slow, duration_one_line_real, time_trig_paused, dig_galvos_use, tot_time  = params_anlg_galv

        if scan_mode == 1: # galvos digital
            maxPx_paquet, total_px, _ = mxsmp_func_totime(dig_galvos_use, param_ini, time_by_px, update_time , tot_time, fake_size_fast, nb_px_slow)
        elif scan_mode == -1: #  static acq
            total_px = fake_size_fast*nb_px_slow  # = 160798 = 3.21956/2e-5
            up_to_lntm = min(round(update_time/(fake_size_fast*time_by_px)), nb_px_slow) # # can be number of lines per packet 
            maxPx_paquet = int(up_to_lntm*fake_size_fast) if up_to_lntm > 0 else fake_size_fast #round(update_time/time_by_px) #16500 # # sometimes round gives a .0 !!
        elif scan_mode == -2:  # anlg galvo scan
            # # print('wallou dataacq !!',  divider , dividand)
            nb_lines_inpacket, maxSmp_paquet = nb_linespacket_meth(numpy, scan_mode == 1, param_ini.last_buff_smallest_poss, param_ini.lvl_trigger_not_win, param_ini.add_nb_lines_safe, method_watch != 7, sample_rate, nb_px_slow, update_time, time_expected_sec, duration_one_line_real, time_trig_paused)
            divider = nb_lines_inpacket ; dividand = None # defined later  # # nb_loop_line = nb_px_slow
            
        if scan_mode == 0: # stage scan
            nbPostTriggerSamps = 2  # per channel
            if nbPostTriggerSamps % 2: # odd, not a multiple of 2
                nbPostTriggerSamps += 1 # for the DAQ, the num_samps_per_channel has to be a multiple of 2
                
        else: # anlg galvos
            read_buffer_offset_direct = 0; read_buffer_offset_reverse = 0 # just here
            nbPostTriggerSamps = 0
        
        safety_fact_stgScn = param_ini.safety_fact_stgScn
        safety_mult_stgscn = param_ini.safety_mult_stgscn
        max_size_np_array = param_ini.max_size_np_array
        safety_nb_px_anlgScn = param_ini.safety_nb_px_anlgScn
        while True: # to see if the sample rate will not lead to too large arrays
            try:
                
                oversampling = time_by_px*sample_rate # in element acquired
                # take floor because otherwise array will be overfilled
                if scan_mode == -2: # anlg galvo scan
                    oversampling = int(round(oversampling)) # this round was tested to be super-important for things to work, but I don't know why ... # # sometimes round gives a .0 !!
                                
                number_of_samples = int(round(oversampling*(fake_size_fast +read_buffer_offset_direct + read_buffer_offset_reverse))) # # sometimes round gives a .0 !!
                
                safety_nb_px = max(0, (safety_mult_stgscn-1))*(fake_size_fast +read_buffer_offset_direct + read_buffer_offset_reverse) if scan_mode == 0 else safety_nb_px_anlgScn
                safety_size = round(safety_nb_px*oversampling )  # int after         
                
                size_np = int(safety_fact_stgScn*round((number_of_samples + nbPostTriggerSamps + safety_size))) # # sometimes round gives a .0 !!
                if (size_np > max_size_np_array and sample_rate > sample_rate_min):
                    if lock_smprate: lock_smprate+=1
                    raise(MemoryError)
                
                # # print('l363', number_of_samples, size_np, oversampling, fake_size_fast +read_buffer_offset_direct + read_buffer_offset_reverse)
                data_temp = numpy.zeros(((nb_pmt_channel, size_np)), dtype=param_ini.type_data_read_temp) # just to test
                # # if round(number_of_samples + safety_size)+ 1000 > max_buffer_size_daq_read_theo: # buffer size too high
                # #     raise(MemoryError)
                
                if (scan_mode in (0, -2) or (scan_mode==1 and dig_galvos_use and not method_watch == 7)):
                    if force_buffer_small:
                        if scan_mode == 0: # stage scan
                            buf_size_2set = int(round(number_of_samples + nbPostTriggerSamps + safety_size))
                        else: # anlg galvo scan
                            buf_size_2set = int(round(number_of_samples*fact_buffer)) # # sometimes round gives a .0 !!
                            # # buf_size_2set = number_of_samples*fact_buffer*16*4*10
                    else:
                        time_buffer_tobeCorrect = 0.5
                        if number_of_samples/sample_rate > time_buffer_tobeCorrect: # size buffer corresponding to 1 sec
                            buf_size_2set = int(round(number_of_samples*fact_buffer)) # # sometimes round gives a .0 !!
                        else:
                            buf_size_2set = int(round(time_buffer_tobeCorrect*sample_rate))  # size buffer corresponding to 1 sec
                    if lvl_trigger_not_win == 2:# lvl_trigger_not_win # pause only for small vibrations on top of acq
                        buf_size_2set = 2*buf_size_2set
                else: buf_size_2set = int(round(sample_rate*update_time*fact_safety_buffer)) # size of the buffer # # sometimes round gives a .0 !!

                if (buf_size_2set > max_buffer_AI and sample_rate > sample_rate_min): # buffer size too high
                        raise(MemoryError)
                
            except MemoryError:
                
                if lock_smprate-1 == 1: # # 1st try : the smp rate is locked by user 
                    max_size_np_array = 4*max_size_np_array # # 10e6
                    print('\nsmp rate locked and size array over limit: you risk MemoryError!')
                elif lock_smprate-1 == 2:# # 2nd try the smp rate is locked by user 
                    safety_fact_stgScn = safety_mult_stgscn = 1
                    safety_nb_px_anlgScn = 0 # no safety anymore
                    print('\nsmp rate locked and size array over limit 2: no safety px!')
                elif lock_smprate-1 == 3:# # 3rd try the smp rate is locked by user 
                    raise(Exception('\nsmp rate locked and size array over limit 3: scan too long, sample rate too high!!'))
                else: # ok change smp rate
                    div = int(round(master_clock_rate/sample_rate))+1
                    sample_rate = master_clock_rate/div
                    # # sample_rate = master_clock_rate/numpy.ceil(master_clock_rate/sample_rate_wanted)
                    if sample_rate < sample_rate_min: sample_rate = sample_rate_min #break
                    
                    print('I had to downsize the (too high) sample_rate to %d' % sample_rate) 
            except Exception as err:
                if type(err) == ValueError:
                    print('nb_pmt_channel, size_np', nb_pmt_channel, size_np)
                raise(err)
            else:
                del data_temp
                break # outside while loop 
        if sample_rate-int(sample_rate)>1e-6: # not round !
            div_min = int(round(master_clock_rate/sample_rate_max))
            div_max = int(round(master_clock_rate/sample_rate_min))
            div = int(round(master_clock_rate/sample_rate))
            sample_rate_prev = sample_rate; br = 0
            for k in (1,2,3,4,5):
                for i in (1,-1):
                    sample_rate = master_clock_rate/min(div_max, max(div_min, (div +i*k)))  
                    if (sample_rate-int(sample_rate)<=1e-6 and sample_rate<=2*sample_rate_prev): br = 1; break
                if br: break
            if (sample_rate-int(sample_rate)>1e-6 or sample_rate>2*sample_rate_prev): sample_rate = sample_rate_prev # # still high diff, or too high final difference between rates
            else: print('I had to set sample_rate (no match) to %d' % sample_rate) 
        # if sample_rate < sample_rate_min: sample_rate = sample_rate_min
    
        ## new imposed buffer size
        
        if (number_of_samples+safety_size) % 2: # odd, not a multiple of 2
            safety_size += 1 # for the DAQ, the num_samps_per_channel has to be a multiple of 2
        
    if scan_mode == 0: # stage scan
      
        if (number_of_samples+safety_size) < 10:
            nbPreTriggerSamps_min_dflt = 4
        else:
            nbPreTriggerSamps_min_dflt = param_ini.nbPreTriggerSamps_min_dflt # empirical value, 2 leads to some sporadic bugs in buffer
    
        fact = 2
        nbPreTriggerSamps_min = int(max(nbPreTriggerSamps_min_dflt, round(oversampling*((fake_size_fast + diff_PXAccoffset + diff_PXDecoffset)/fact))))  # per channel # # sometimes round gives a .0 !!
        # nbPreTriggerSamps_min =  10
        # when half of the samples have been acquired, begin to listen to Ref. trigger
        # is 2 minimum, but 2 leads to insatbilities so it's preferable to set it higher
        # lackAccOffset are negatives or 0
        # factor of 2 in lackAccOffset because theoretically, for trapez profiles, dist_cst_speed_v = 2*dist_cst_acceleration_2reach_v
        
        nbPreTriggerSamps_min = verify_even(nbPreTriggerSamps_min) # for the DAQ, the num_samps_per_channel has to be a multiple of 2
        
        buf_size = verify_even(int(round(number_of_samples + nbPostTriggerSamps + safety_size))) #time_out*sample_rate_new
        # # sometimes round gives a .0 !!
    
        # # data = numpy.zeros((nb_pmt_channel, buf_size), dtype= param_ini.type_data_read_temp) # number_of_samples pre-triggered + posttriggered
        arr_reshape = numpy.zeros((buf_size, nb_pmt_channel), dtype=param_ini.type_data_read_temp, order= 'c') # # fastest option, normal if inverted !!
    # forced by analogF64 read
    
        print('number_of_samples', number_of_samples, 'oversampling', oversampling)
        print('nbPreTriggerSamps_min ', nbPreTriggerSamps_min)
        
        return sample_rate, arr_reshape, number_of_samples, buf_size, nbPostTriggerSamps, nbPreTriggerSamps_min

    else: # static acq or digital galvos scan  # anlg galvo scan
        if mode_buffer: return sample_rate, verify_even(buf_size_2set), update_time
        else: # def max array
            if scan_mode != -2: 
                maxSmp_paquet = maxPx_paquet*round(oversampling)
                divider = maxPx_paquet ; dividand = total_px
            
            return sample_rate, verify_even(buf_size_2set), maxSmp_paquet, divider, dividand
        
def verify_even(nb):
    if nb % 2: # odd, not a multiple of 2
        nb += 1
    return nb
def mxsmp_func_totime(dig_galvos_use, param_ini, time_by_px, update_time , tot_time, fake_size_fast, nb_px_slow):
    nb_lines_inpacket =None
    if dig_galvos_use: # # read time line with counter
        total_px = fake_size_fast*nb_px_slow  # = 160798 = 3.21956/2e-5# # pauses when flyback
        # # if scan_mode >= -1: # # not anlg new galvos (nb_lines_inpacket defined earlier for them)
        nb_lines_inpacket = int(round(update_time/(tot_time/nb_px_slow))) # the update time is rounded # # sometimes round gives a .0 !!
        if param_ini.last_buff_smallest_poss: nb_lines_inpacket = int(nb_px_slow/max(1, int(nb_px_slow/nb_lines_inpacket))) # # retaking nb_lines_inpacket
        # # to have the smallest last buffer, because PMT2 last buffer is not good with galvos
        # # print('nb_lines_inpacket', nb_lines_inpacket)
        maxPx_paquet = nb_lines_inpacket*fake_size_fast
    else: # classic
        total_px = int(round((tot_time - param_ini.SM_cycle)/time_by_px)) # + corr_sync_inPx  # = 160798 = 3.21956/2e-5 # # sometimes round gives a .0 !!
         # # acq. samples even if flyback

        maxPx_paquet = int(round(update_time/tot_time*total_px)) # if read line after
    # so buffer_size is sample_rate*update_time
    return maxPx_paquet, total_px, nb_lines_inpacket

def ai_read_def_galvoscn( nidaqmx, analog_input, dev_list,  device_to_use_AI, DO_parallel_trigger, method_watch, use_RSE, sample_rate_wanted, numpy, time_by_px, time_expected_sec, sample_rate_min, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, use_dig_galvos, pack_params_new_galvos, ai_trig_control, name_list_trigctrl_tasks, use_trigger_anlgcompEv_onFallingEdges, lock_timing ):

    '''
    For galvos special only, def of the AI Task and others like trigger watcher
    '''
    number_of_samples = None
    sample_rate = sample_rate_wanted
        
    if (scan_mode == -2 or (scan_mode == 1 and method_watch != 7)): #  galvos callbacks only (or meas linetime for anlg)
    
        [device_to_use_anlgTrig, device_to_use_watcherTrig, _, volt_pos_max_fast, volt_pos_min_fast, trig_src_name_slave, ai_trig_src_name_master, samp_src_term_slave, sample_rate_min_other, samp_src_term_master_toExp, trig_src_name_master, trig_src_end_master_toExp, trig_src_end_toExp_toDIWatcher, term_trig_other, term_trig_name, trig_src_end_chan, unidirectional, factor_trigger, use_chan_trigger, lvl_trigger_not_win, volt_offset_fast, volt_offset_slow, min_pulse_width_digfltr_6259, bound_read_trig, system, nb_px_slow, nb_px_fast, time_by_point, time_list, trig_lvl, unirek_skip_half_of_lines, export_smpclk, export_trigger, sample_rate_AO_wanted, force_buffer_small, fact_buffer] = pack_params_new_galvos

        # # [min_val_read_trig, max_val_read_trig] = pack_volt
        [lvl_trig_top, lvl_trig_bottom, hyst_trig ] = trig_lvl
        [time_trig_paused, duration_one_line_real] = time_list
        
        cond1 = device_to_use_AI != dev_list[1] if len(dev_list) > 1 else True # # ternary
        if ((device_to_use_AI == device_to_use_anlgTrig) and use_chan_trigger and cond1):  # NOT master/slave condition
            
            # # it's adding the TRIGGER channel, only
            
            # # analog_input.ai_channels[trig_src_name_slave].ai_min = min_val_read
            # # analog_input.ai_channels[trig_src_name_slave].ai_max = max_val_read
            analog_input.ai_channels.add_ai_voltage_chan(trig_src_name_slave, min_val=-bound_read_trig, max_val = bound_read_trig)
        # # else:
        # #     nb_AI_channel = nb_pmt_channel
        master_slave_cond_diffdev = (device_to_use_anlgTrig is not None and (device_to_use_AI != device_to_use_anlgTrig) and not DO_parallel_trigger and not method_watch == 3)
        
        if master_slave_cond_diffdev: # master/slave condition, not parallel # for anlg galvos normally
        
            # # print('ai_trig_control !!!!!!!!', ai_trig_control)
            if ('ai_trig_control' in locals() and ai_trig_control is not None):
                ai_trig_control.close()
            
            # # print('name_list_trigctrl_tasks', name_list_trigctrl_tasks)
            name_trigctrl = name_list_trigctrl_tasks[-1] # last
            while True:
                name_list_trigctrl_tasks = ['%s_0%d' % (name_trigctrl[:-3], int(name_trigctrl[-1])+1)]
                try:
                    ai_trig_control = nidaqmx.Task(name_trigctrl) # Task for the AI channel on 6259, just used for trig
                except nidaqmx.DaqError as err:
                    if err.error_type == nidaqmx.error_codes.DAQmxErrors.DUPLICATE_TASK:
                        name_trigctrl = name_list_trigctrl_tasks[-1] # last
                        continue
                    else:
                        raise(err)
                else: # # success
                    break # outside 'while' loop
            # # print('name_list_trigctrl_tasks', name_list_trigctrl_tasks)
            
            ai_trig_control.ai_channels.add_ai_voltage_chan(ai_trig_src_name_master, min_val= -bound_read_trig, max_val = bound_read_trig)
            
            if (len(dev_list) > 1 and device_to_use_anlgTrig.name == dev_list[1].name): # 6259
                if use_RSE:
                    ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.RSE # nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL #
                else:
                    ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL #
                    
            else: # 6110
                ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.PSEUDODIFFERENTIAL # only one available
            
            master_task = ai_trig_control # Task that dictates the sample rate
            
            if export_smpclk:
                sample_rate_max = master_task.timing.samp_clk_max_rate
                if device_to_use_anlgTrig == dev_list[0]:  # 6110
                    sample_rate_min = param_ini.sample_rate_min_6110
                else:
                    sample_rate_min = param_ini.sample_rate_min_6259
                    
            else: # export trigger only
                sample_rate_max = analog_input.timing.samp_clk_max_rate 
            
        else: # only one Task AI  OR parallel
                
            master_task = analog_input # Task that dictates the sample rate
            
            if (DO_parallel_trigger and export_smpclk and device_to_use_AI == dev_list[0]): # 6110, other one is 6259 in a process
            
                sample_rate_max = param_ini.sample_rate_max_6259 # of 6259
            else:
                sample_rate_max = analog_input.timing.samp_clk_max_rate
        
        max_buffer_AI_2chansW_chanR = param_ini.calc_max_buf_size(nb_pmt_channel)[0]
            
        sample_rate, buf_size_2set, maxSmp_paquet, divider, dividand = daq_acq_params_def(sample_rate_wanted, numpy, time_by_px, time_expected_sec, analog_input, nb_pmt_channel, fake_size_fast, diff_PXAccoffset, diff_PXDecoffset, read_buffer_offset_direct, read_buffer_offset_reverse, param_ini, scan_mode, update_time, force_buffer_small, fact_buffer, max_buffer_AI_2chansW_chanR, sample_rate_min, sample_rate_max, (lvl_trigger_not_win, method_watch, nb_px_slow, duration_one_line_real, time_trig_paused, use_dig_galvos, time_expected_sec), lock_timing, 0)
        
        # # if method_watch == 7: # no callback
        # #     number_of_samples = None
        
    # #  oversampling = int(time_by_px*sample_rate) # take floor because otherwise array will be overfilled
        
        if (device_to_use_AI != device_to_use_anlgTrig): # master/slave condition # trig on 6259, external from the 6110 where read is performed (or inverse)
        
            smp_rate_trig = sample_rate_AO_wanted # param_ini.smp_rate_trig
            if export_trigger: # else exp samp clck
                # # smp_rate_trig = sample_rate
                if smp_rate_trig < sample_rate_min_other:
                    smp_rate_trig = sample_rate_min_other
                elif smp_rate_trig > master_task.timing.samp_clk_max_rate:
                    smp_rate_trig = master_task.timing.samp_clk_max_rate
                    
            # # else:
            # #     smp_rate_trig = sample_rate
                
            if (len(dev_list) > 1 and device_to_use_anlgTrig == dev_list[1]): # 6259
                smp_rate_trig = min(param_ini.sample_rate_max_6259, smp_rate_trig)
                
            if (device_to_use_anlgTrig is not None and not DO_parallel_trigger and not method_watch == 3):
                ai_trig_control.timing.cfg_samp_clk_timing(rate= smp_rate_trig, source= '', sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = 1000 ) # 1000 is sufficient # source = internal Onboard src of 6259
            
                if export_smpclk:
                    ai_trig_control.export_signals.export_signal(nidaqmx.constants.Signal.SAMPLE_CLOCK, output_terminal = samp_src_term_master_toExp) 
                    
        # # sample_rate_temp = sample_rate
        if (export_smpclk and len(samp_src_term_slave) > 0): # external exported smp clk
            sample_rate = smp_rate_trig
        # # else: # no export smp clk
        # #     sample_rate_temp = sample_rate
            
        analog_input.timing.cfg_samp_clk_timing(rate= sample_rate, source= samp_src_term_slave, sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS ) # buffer size set after for CONTINUOUS
            
        # print(analog_input.channels.ai_data_xfer_mech) # DMA
        # # print(analog_input.channels.ai_data_xfer_req_cond) # InputDataTransferCondition.ON_BOARD_MEMORY_NOT_EMPTY default
        analog_input.channels.ai_data_xfer_req_cond = nidaqmx.constants.InputDataTransferCondition.ON_BOARD_MEMORY_NOT_EMPTY # default
        # it means the read has to be faster than the whole next line to be acquired
    
        analog_input.timing.samp_quant_samp_per_chan = buf_size_2set # this value is used to set the buffer size in CONTINUOUS mode
        analog_input.in_stream.input_buf_size = buf_size_2set # just to be sure
        
        # analog_input.timing.cfg_samp_clk_timing(sample_rate, sample_mode= nidaqmx.constants.AcquisitionType.FINITE,samps_per_chan = buf_size_2set )
        # analog_input.in_stream.read_all_avail_samp = True
        
        analog_input.in_stream.relative_to = nidaqmx.constants.ReadRelativeTo.CURRENT_READ_POSITION # is DAQmx_Val_FirstPretrigSamp by default if you use 
        
        # # ******** pause trigger ************
        
        if (not DO_parallel_trigger and scan_mode == -2): # # or (scan_mode == 1 and use_dig_galvos != 1)): # # anlg or dig galvos use_dig_galvos = 2

            if (lvl_trigger_not_win or (param_ini.use_velocity_trigger and unidirectional)): # pause trigger for analog_input, or trig_control if trig on 6259 and read on 6110
                master_task.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.ANALOG_LEVEL
                master_task.triggers.pause_trigger.anlg_lvl_src = trig_src_name_master

                if lvl_trigger_not_win == 1: # # 1 to pause only on top of waveform, and during the flyback # LIMITED BY HYST !!
                    master_task.triggers.pause_trigger.anlg_lvl_when = nidaqmx.constants.ActiveLevel.BELOW
                    master_task.triggers.pause_trigger.anlg_lvl_lvl = lvl_trig_top #-(volt_pos_max_fast - volt_pos_min_fast)/30
                    master_task.triggers.pause_trigger.anlg_lvl_hyst =  lvl_trig_top - lvl_trig_bottom #1/1000 # (volt_end_fast - volt_pos_max_fast)/factor_trigger/param_ini.safety_lvl_trig_max_fact 
                    
                elif lvl_trigger_not_win == 2: # # pause on btm DFLT
                    if not unidirectional: # bidirek
                        master_task.triggers.pause_trigger.anlg_lvl_when = nidaqmx.constants.ActiveLevel.BELOW
                        master_task.triggers.pause_trigger.anlg_lvl_lvl = lvl_trig_top #-(volt_pos_max_fast - volt_pos_min_fast)/30
                        master_task.triggers.pause_trigger.anlg_lvl_hyst =  lvl_trig_top/100 #1/1000 # (volt_end_fast - volt_pos_max_fast)/factor_trigger/param_ini.safety_lvl_trig_max_fact 
                        # the trigger does not deassert until the source signal passes above Level plus the hysteresis
                        # the trigger asserts if signal passes below lvl
                    else: # unidirectional
                        master_task.triggers.pause_trigger.anlg_lvl_when = nidaqmx.constants.ActiveLevel.ABOVE # the trigger does not deassert until the source signal passes below Level minus the hysteresis
                        # the trigger asserts if signal passes above lvl
                        master_task.triggers.pause_trigger.anlg_lvl_lvl = lvl_trig_bottom # the lvl with hyst will be lvl_trig_bottom, and the lvl will be lvl_trig_bottom - hyst_trig
                        master_task.triggers.pause_trigger.anlg_lvl_hyst = hyst_trig # abs(lvl_trig_bottom/10) #1/1000 # (volt_end_fast - volt_pos_max_fast)/factor_trigger/param_ini.safety_lvl_trig_max_fact 
            
            else: # use pos
                master_task.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.ANALOG_WINDOW
                # #analog_input.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.NONE
                master_task.triggers.pause_trigger.anlg_win_src = trig_src_name_master
                
                if (param_ini.use_velocity_trigger or (device_to_use_AI != device_to_use_anlgTrig and not use_trigger_anlgcompEv_onFallingEdges)):
                    master_task.triggers.pause_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition2.INSIDE_WINDOW # pause when inside
                else:
                    master_task.triggers.pause_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition2.OUTSIDE_WINDOW # pause when outside
                    
                # # anlg_win_bottom = -0.15
                # anlg_win_bottom = anlg_win_bottom/2
                master_task.triggers.pause_trigger.anlg_win_btm = lvl_trig_bottom # V
                # anlg_win_top = anlg_win_top/2 # !!
                # # anlg_win_top = 0.15
                master_task.triggers.pause_trigger.anlg_win_top = lvl_trig_top
                
        if master_slave_cond_diffdev: # master/slave condition
            ai_trig_control.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
            
        # # total_px = nb_px_slow*(nb_px_fast + time_flyback_unpaused/time_by_point)
        # # print('l.676', time_expected_sec, time_trig_paused, duration_one_line_real)
    
        total_smp = (time_expected_sec - time_trig_paused*nb_px_slow)*sample_rate
        # print(time_expected_sec, nb_px_slow)
        
        divider, maxSmp_paquet = nb_linespacket_meth(numpy, scan_mode == 1, param_ini.last_buff_smallest_poss, param_ini.lvl_trigger_not_win, param_ini.add_nb_lines_safe, method_watch != 7, sample_rate, nb_px_slow, update_time, time_expected_sec, duration_one_line_real, time_trig_paused)
                        
    else: # not anlg galvos or not galvos callback
        trig_src_name_slave = param_ini.trig_src_name_dig_galvos
        total_smp = maxSmp_paquet = divider = dividand=None # both
    
    # # print('trig_src_end_master21', trig_src_name_slave) 
    # # print('btm', analog_input.triggers.pause_trigger.anlg_win_btm)
    if (ai_trig_control is None or (ai_trig_control.triggers.pause_trigger.anlg_win_when == nidaqmx.constants.WindowTriggerCondition2.OUTSIDE_WINDOW and use_trigger_anlgcompEv_onFallingEdges) or (ai_trig_control.triggers.pause_trigger.anlg_win_when == nidaqmx.constants.WindowTriggerCondition2.INSIDE_WINDOW and not use_trigger_anlgcompEv_onFallingEdges) or (ai_trig_control.triggers.pause_trigger.anlg_lvl_when == nidaqmx.constants.ActiveLevel.BELOW and use_trigger_anlgcompEv_onFallingEdges) or (ai_trig_control.triggers.pause_trigger.anlg_win_when == nidaqmx.constants.ActiveLevel.ABOVE and not use_trigger_anlgcompEv_onFallingEdges)): # signal is already correct
        sig_mod = nidaqmx.constants.SignalModifiers.DO_NOT_INVERT_POLARITY
    else:
        sig_mod = nidaqmx.constants.SignalModifiers.INVERT_POLARITY
        
    print(sig_mod)
                                
    ## ******** trigger digital ************
    analog_input.triggers.start_trigger.trig_type = nidaqmx.constants.TriggerType.NONE # default is software
    
    if (scan_mode == -2 and export_smpclk): # # anlg galvos, trigger is contained in the sample clock
        analog_input.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.NONE
            
    elif (scan_mode == 1 or (export_trigger and device_to_use_anlgTrig != device_to_use_AI) or param_ini.DO_parallel_trigger): # # dig galvos, or export trigger anlg galvos
        
        analog_input.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_LEVEL
        analog_input.triggers.pause_trigger.dig_lvl_src = trig_src_name_slave
        if (scan_mode == -2 and (device_to_use_AI != device_to_use_anlgTrig and not param_ini.use_trigger_anlgcompEv_onFallingEdges)):  # use anlg cmp event on 
            lvl = nidaqmx.constants.Level.HIGH 
        else: # # use anlg cmp event on falling edges (when paused, it's low)
            lvl = nidaqmx.constants.Level.LOW
        analog_input.triggers.pause_trigger.dig_lvl_when = lvl # trigger is LOW when condition matched (outside window)
        
        if (scan_mode == -2 and export_trigger): # # anlg galvos, exp trigger not smp rate
        
            system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)))
            system.connect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)), signal_modifiers=nidaqmx.constants.SignalModifiers.DO_NOT_INVERT_POLARITY)
            # never invert polarity here as 6259 cannot do it !!
            
            trig_src_end_master_toExp_real = trig_src_end_master_toExp

            if device_to_use_anlgTrig == dev_list[0]: # 6110
                trig_src_end_master_toExp_real = param_ini.term_toExp_Ctr0Gate_forAnlgCompEvent_6110
                system.disconnect_terms(source_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp_real)))
                system.connect_terms(source_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp)), destination_terminal = ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp_real)), signal_modifiers=nidaqmx.constants.SignalModifiers.DO_NOT_INVERT_POLARITY)
                
            print('I connected %s to %s' % ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name), ('/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master_toExp_real))))
            
    trig_src_end_term_toExp_toWatcher = '' # default
    
    # # print('l705daq', scan_mode, param_ini.use_callbacks, method_watch == 7)
    
    if (scan_mode == -2 and (param_ini.use_callbacks or method_watch == 7)): # # anlg galvos, watcher for trigger
    
        if method_watch == 1: # DI chg detect
            trig_src_end_master = 0
            cond = nidaqmx.constants.SignalModifiers.DO_NOT_INVERT_POLARITY
  
            system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_toExp_toDIWatcher))
            system.connect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_toExp_toDIWatcher), signal_modifiers=cond)
            
            # export is mandatory as trig_src_end_toExp_toDIWatcher is physically connected to P0.0

            trig_src_end_term_toExp_toWatcher = trig_src_end_toExp_toDIWatcher
        
        elif  method_watch == 3: # self watching !! not precise !!
        
            if not use_chan_trigger:
                if (len(dev_list) > 1 and device_to_use_anlgTrig == dev_list[1]):
                    trig_src_end_master = term_trig_other
                else:
                    trig_src_end_master = term_trig_name
            else:
                trig_src_end_master = trig_src_end_chan # from chan # chan
        
            trig_src_end_term_toExp_toWatcher = trig_src_end_chan # from chan # chan
        
        elif method_watch >= 4: # counter
        
            if ((method_watch >= 6 and param_ini.use_dig_fltr_onAlgCmpEv) or (scan_mode == -2 and (device_to_use_anlgTrig.name != device_to_use_watcherTrig.name or param_ini.use_diff_terms_expAI_expWatch))):
                # to allow the device that watch trig to be connected to trigger
                
                if (export_trigger and not param_ini.use_diff_terms_expAI_expWatch):# and device_to_use_watcherTrig == device_to_use_anlgTrig):  # already connected
                    trig_src_end_term_toExp_toWatcher = trig_src_end_master_toExp_real
                    print('trig src will actually be re-used: %s' % trig_src_end_master_toExp_real)
                    
                else: # use diff terms   
 
                    # # if device_to_use_anlgTrig == device_to_use_watcherTrig, same device so ok
                    # # otherwise connections on same device but terminal of both devices are physically linked
                    if (scan_mode == -2 and (device_to_use_anlgTrig.name == device_to_use_watcherTrig.name) and param_ini.use_diff_terms_expAI_expWatch and device_to_use_anlgTrig == dev_list[0]): # # 6110 only
                        trig_src_end_term_toExp_toWatcher = param_ini.term_toExp_forAnlgCompEvent_6110
                    else:
                        trig_src_end_term_toExp_toWatcher = param_ini.trig_src_end_term_toExp_toWatcher
                        
                    system.disconnect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_term_toExp_toWatcher))
                    system.connect_terms(source_terminal = ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name)), destination_terminal = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_term_toExp_toWatcher), signal_modifiers=sig_mod)
                    
                    print('I connected also %s to %s with %s' % ('/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name), (device_to_use_anlgTrig.name, trig_src_end_term_toExp_toWatcher), sig_mod))
            
                trig_src_end_master = trig_src_end_term_toExp_toWatcher

            else:
            
                trig_src_end_master = 'AnalogComparisonEvent'
                
        elif method_watch == 2: # DI smp clk
        
            raise Exception('DI smp clk method never worked on tests')
    
    elif scan_mode == 1: # digital galvos
        trig_src_end_master = trig_src_name_slave
        trig_src_end_term_toExp_toWatcher = trig_src_end_master
    else: # # anlg galvos, no callback and no line time measure
        trig_src_end_master = None
    # # analog_input.triggers.pause_trigger.anlg_win_coupling = nidaqmx.constants.Coupling.AC
    
    analog_input.in_stream.wait_mode = nidaqmx.constants.WaitMode.YIELD
    # POLL  # CPU intensive
    return ai_trig_control, sample_rate, [trig_src_end_master, trig_src_end_term_toExp_toWatcher, maxSmp_paquet, divider, dividand]
    
def trig_watcher_ctrl_def_galvoscn(nidaqmx, use_callbacks, duration_one_line_imposed, term_DI, trig_src_end_master, trig_src_end_term_toExp_toWatcher, method_watch, nb_loop_line, use_velocity_trigger, device_to_use_AO, device_to_use_AI, device_to_use_anlgTrig, device_to_use_watcherTrig, dev_list, analog_input, ai_trig_control, use_trigger_anlgcompEv_onFallingEdges, use_dig_fltr_onAlgCmpEv, master_trig_ctrl_scrpts, callback, pack_params_new_galvos, galvos_use, anlgCompEvent_watcher_task, name_list_watcher_tasks, tuple_EOMph, param_ini ):
    # # used by anlg galvos, and also by dig galvos if pause trigger used (meas line time or callbacks)    
    
    # # print('trig_watcher_ctrl_def_galvoscn', trig_src_end_master, trig_src_end_term_toExp_toWatcher)
    
    if (galvos_use or (len(pack_params_new_galvos) > 3 and (use_callbacks or method_watch == 7))): # anlg or dig. galvos, trig width measurement or callbacks lines # # NORMALLY EVERY CASES for galvos !
    
        anlgCompEvent_watcher_task = master_trig_ctrl_scrpts.anlgCompEvent_watcher(nidaqmx, dev_list, term_DI, trig_src_end_master, trig_src_end_term_toExp_toWatcher, method_watch, duration_one_line_imposed, nb_loop_line, use_velocity_trigger, use_trigger_anlgcompEv_onFallingEdges, use_dig_fltr_onAlgCmpEv, callback, pack_params_new_galvos, anlgCompEvent_watcher_task, name_list_watcher_tasks, tuple_EOMph)
    
    print(' --- Summary ---')
    
    if len(pack_params_new_galvos) > 3: # # galvo special
        device_AOname = device_to_use_AO.name if device_to_use_AO is not None else '-'
        device_AITrigname = device_to_use_anlgTrig.name if device_to_use_anlgTrig is not None else '-'
        device_wtchTrigname = device_to_use_watcherTrig.name if device_to_use_watcherTrig is not None else '-'
        export_smpclk, export_trigger = pack_params_new_galvos[-5:-3] # [-2:] for two last
        print('device to AO %s, device to read %s, dev to trig %s, dev to watchtrig % s \n export trigger %d, export smp clk %d \n use_callbacks %d, method_watch %d, ' % ( device_AOname, device_to_use_AI.name, device_AITrigname, device_wtchTrigname, export_trigger, export_smpclk, use_callbacks, method_watch ))
    else:
        export_smpclk = False ; export_trigger = False
        
    trig_AI_to_chck = '/%s/%s' % (device_to_use_AI.name, param_ini.trig_src_name_dig_galvos) # dflt
    
    if method_watch: # no static
        print('read input START trigger : %s' % (analog_input.triggers.start_trigger.trig_type) )
    
        if analog_input.triggers.pause_trigger.trig_type == nidaqmx.constants.TriggerType.DIGITAL_LEVEL:
            print('read input PAUSE trigger DIGITAL on src %s (slave) with pause when %s' % (analog_input.triggers.pause_trigger.dig_lvl_src,  analog_input.triggers.pause_trigger.dig_lvl_when) )
            trig_AI_to_chck = analog_input.triggers.pause_trigger.dig_lvl_src
    
        elif analog_input.triggers.pause_trigger.trig_type == nidaqmx.constants.TriggerType.ANALOG_WINDOW:
            print('read input PAUSE trigger Anlg window on src (alone)', analog_input.triggers.pause_trigger.anlg_win_src, 'with pause when', analog_input.triggers.pause_trigger.anlg_win_when )
            trig_AI_to_chck = analog_input.triggers.pause_trigger.anlg_win_src
            
        elif analog_input.triggers.pause_trigger.trig_type == nidaqmx.constants.TriggerType.ANALOG_LEVEL:
            print('read input PAUSE trigger pause Anlg lvl on src (alone)', analog_input.triggers.pause_trigger.anlg_lvl_src, 'with pause (lvl LOW) when', analog_input.triggers.pause_trigger.anlg_lvl_when, 'hysteresis', analog_input.triggers.pause_trigger.anlg_lvl_hyst )
            trig_AI_to_chck = analog_input.triggers.pause_trigger.anlg_lvl_src
        else:
            print('read input trigger : no PAUSE trigger !')
        
    if ai_trig_control is not None: #'ai_trig_control' in locals():
        if ai_trig_control.triggers.pause_trigger.trig_type == nidaqmx.constants.TriggerType.ANALOG_LEVEL: #lvl_trigger_not_win:
            print('Trig input trigger Anlg LEVEL on src (alone)', ai_trig_control.triggers.pause_trigger.anlg_lvl_src, 'with pause (lvl LOW) when', ai_trig_control.triggers.pause_trigger.anlg_lvl_when, 'hysteresis', ai_trig_control.triggers.pause_trigger.anlg_lvl_hyst)
        elif ai_trig_control.triggers.pause_trigger.trig_type == nidaqmx.constants.TriggerType.ANALOG_WINDOW:
            print('Trig input trigger Anlg window on src %s (alone, channel = %s)' % (ai_trig_control.triggers.pause_trigger.anlg_win_src, ai_trig_control.channels.name), 'with pause (lvl LOW) when', ai_trig_control.triggers.pause_trigger.anlg_win_when )
        
    if anlgCompEvent_watcher_task is not None: # #'anlgCompEvent_watcher_task' in locals():
        if  method_watch <= 6: print('uses CALLBACKs to separate lines') 
        else: print('scan algo standard (no callback)')
        if  method_watch == 4:  # # CO
            print('TrigWatcher input START trigger DIGITAL on src (slave)', anlgCompEvent_watcher_task.triggers.start_trigger.dig_edge_src, ' ; pulsewidth_low-high: (%.3g, %.3g) µs' % (anlgCompEvent_watcher_task.co_channels[0].co_pulse_low_time, anlgCompEvent_watcher_task.co_channels[0].co_pulse_high_time)) 
        elif  method_watch >= 6:
            
            if method_watch == 6:
                try:
                    dig_fltr_cond = anlgCompEvent_watcher_task.channels.ci_count_edges_dig_fltr_enable
                except: # otherwise error, if device does not handle it
                    dig_fltr_cond = 'False'
                print('TrigWatcher input clk on %s and count_edges term on %s and dig fltr is %s, on %s' % (anlgCompEvent_watcher_task.timing.samp_clk_src, anlgCompEvent_watcher_task.channels.ci_count_edges_term, dig_fltr_cond, anlgCompEvent_watcher_task.channels.ci_count_edges_active_edge) )
            elif method_watch == 7:
                try:
                    dig_fltr_cond = anlgCompEvent_watcher_task.channels.ci_pulse_width_dig_fltr_enable
                    fltr_time =  anlgCompEvent_watcher_task.channels.ci_pulse_width_dig_fltr_min_pulse_width
                except: # otherwise error, if device does not handle it
                    dig_fltr_cond = 'False'
                    fltr_time = 0
                print('TrigWatcher pulse width %s measure on %s and dig fltr is %s and time %.3f msec' % (anlgCompEvent_watcher_task.channels.channel_names[0], anlgCompEvent_watcher_task.channels.ci_pulse_width_term, dig_fltr_cond, fltr_time*1000) )
            
        elif  method_watch == 3:
            if anlgCompEvent_watcher_task.triggers.start_trigger.trig_type != nidaqmx.constants.TriggerType.NONE:
                print('TrigWatcher input st trigger Anlg window on src (master)', anlgCompEvent_watcher_task.triggers.start_trigger.anlg_win_src )
            else:
                print('TrigWatcher input pause trigger Anlg window on src (master)', anlgCompEvent_watcher_task.triggers.pause_trigger.anlg_win_src )
                
        elif method_watch == 2:
            print('cannot put trigger')

    return anlgCompEvent_watcher_task, trig_AI_to_chck
    
    
def define_AO_write_Task(nidaqmx, write_scan_before, unidirectional, correct_unidirektionnal, shape_reverse_movement, nb_ao_channel, duration_one_line_real, duration_one_line_imposed, sample_rate_AO_wanted , small_angle_step, nb_px_slow, use_velocity_trigger, blink_after_scan, min_val_volt_galvos, max_val_volt_galvos, duration_scan_prewrite_in_buffer, device_to_use, time_expected_sec, use_volt_not_raw_write, dev_list, numpy, analog_output_daq_to_galvos, name_list_AO_tasks, nb_pts_daq_one_pattern, name_list_wr_dumb_tasks, ext_ref_AO_range, ao_dumb):
    
    '''
    For the analog new galvos, def of write Task
    '''
    # # try:
    if ('analog_output_daq_to_galvos' in locals() and analog_output_daq_to_galvos is not None):
        analog_output_daq_to_galvos.close()
        
    name_AO = name_list_AO_tasks[0] # last
    analog_output_daq_to_galvos = nidaqmx.Task(name_AO)
    name_list_AO_tasks = ['%s_0%d' % (name_AO[:-3], int(name_AO[-1])+1)]

    # # except nidaqmx.DaqError as err:
    # #     # pass
    # #     if err.error_type == nidaqmx.error_codes.DAQmxErrors.DUPLICATE_TASK:
    # #         pass
    # #     else:
    # #         raise(err)
    
    # # return analog_output_daq_to_galvos ##
    
    if nb_ao_channel > 1:
        channel_AO_X_Y = ('%s/ao0:%d' % (device_to_use.name, (nb_ao_channel-1)))
        
    else:
        channel_AO_X_Y = ('%s/ao0' % device_to_use.name)
    str_chan_AO = 'AO_2galvos'
    
    analog_output_daq_to_galvos.ao_channels.add_ao_voltage_chan(channel_AO_X_Y, name_to_assign_to_channel=str_chan_AO, min_val=min_val_volt_galvos, max_val=max_val_volt_galvos)
    
    if (len(dev_list) > 1 and device_to_use == dev_list[1] and ext_ref_AO_range): # # 6259
        if analog_output_daq_to_galvos.channels.ao_dac_ref_val != 10:
            analog_output_daq_to_galvos.channels.ao_dac_ref_val = 10 # # because it's stupid, have to do this action before to set a value
        else: # is 10
            analog_output_daq_to_galvos.channels.ao_dac_ref_val = 5 # # because it's stupid, have to do this action before to set a value
            
        # # print(max_val_volt_galvos)
        analog_output_daq_to_galvos.channels.ao_dac_ref_src = nidaqmx.constants.SourceSelection.EXTERNAL
        analog_output_daq_to_galvos.channels.ao_dac_ref_val = max_val_volt_galvos
        analog_output_daq_to_galvos.channels.ao_dac_ref_ext_src # if Dev2 and INTERNAL, you can select only 5 or 10
        if ('ao_dumb' in locals() and ao_dumb is not None):
            ao_dumb.close()
        name_wr_dumb = name_list_wr_dumb_tasks[0] # last
        ao_dumb = nidaqmx.Task(name_wr_dumb)
        name_list_wr_dumb_tasks = ['%s_0%d' % (name_wr_dumb[:-3], int(name_wr_dumb[-1])+1)]
        val = min(max_val_volt_galvos, 10)
        ao_dumb.ao_channels.add_ao_voltage_chan('%s/ao0' % dev_list[0].name, name_to_assign_to_channel='dumb_write_ch', min_val=-val, max_val=val, units=nidaqmx.constants.VoltageUnits.VOLTS)
        # ao_dumb.channels.ao_dac_ref_val
        # ao_dumb.channels.ao_dac_ref_src
        ao_dumb.write(max_val_volt_galvos, auto_start=True) # write the reference to APFI0/AO ext ref
        print('Warning: Dumb Task on %s is giving AO range to %s (verif cable): %.1f!!' % (dev_list[0].name, channel_AO_X_Y ,max_val_volt_galvos))
    
    print(analog_output_daq_to_galvos.channels.ao_min, analog_output_daq_to_galvos.channels.ao_max)
    
    master_clock_rate = analog_output_daq_to_galvos.timing.samp_clk_timebase_rate # Hz
    # # analog_output_daq_to_galvos.timing.samp_clk_timebase_master_timebase_div
    # # the 20Mhz of the master clock rate is either divided by one (then by another integer) to produce rates > 100kHz, or by 200 to produce rates < 100kHz
    
    master_clock_rate_AO = analog_output_daq_to_galvos.timing.samp_clk_timebase_rate
    sample_rate_galvos_min = master_clock_rate_AO/3355443200 # measured smallest sample rate for galvos
    
    sample_rate_galvos_max = analog_output_daq_to_galvos.timing.samp_clk_max_rate
    # # print(master_clock_rate)
    # # print(analog_output_daq_to_galvos.timing.samp_clk_timebase_master_timebase_div)
    
    sample_rate_galvos = master_clock_rate/numpy.ceil(master_clock_rate/sample_rate_AO_wanted)
    if sample_rate_galvos >  sample_rate_galvos_max: # very unlikely
        sample_rate_galvos =  sample_rate_galvos_max
    elif sample_rate_galvos <  sample_rate_galvos_min: # very unlikely
        sample_rate_galvos =  sample_rate_galvos_min
    # nPts is defined after ^^
    
    ## specific to method of write
    
    print('write_scan_before', write_scan_before)
        
    # # ******** timing AO ************
    if write_scan_before:
        
        nb_line_prewrite = 0 # for nothing
        sampsPerChanToGenerate_to_galvos = nb_pts_daq_one_pattern*nb_px_slow
            
        buffer_write_size = sampsPerChanToGenerate_to_galvos
         
        analog_output_daq_to_galvos.timing.cfg_samp_clk_timing(sample_rate_galvos, sample_mode=  nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan = sampsPerChanToGenerate_to_galvos)
        
        analog_output_daq_to_galvos.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.ALLOW_REGENERATION # allow to start do the buffer write multiple times without having to write data again to it (e.g. several same scans)
        
    else: # write scan in LIVE
    
        nb_line_prewrite = max(1, int(round(duration_scan_prewrite_in_buffer*sample_rate_galvos/nb_pts_daq_one_pattern))) # # sometimes round gives a .0 !!
        
        buffer_write_size = nb_pts_daq_one_pattern + nb_line_prewrite*nb_pts_daq_one_pattern #200 # sampsPerChanToGenerate_to_galvos*3


        analog_output_daq_to_galvos.timing.cfg_samp_clk_timing(sample_rate_galvos, sample_mode=  nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = buffer_write_size)
        
        
        # # ******** generation behavior ************
        
        # # analog_output_daq_to_galvos.out_stream.relative_to = nidaqmx.constants.WriteRelativeTo.FIRST_SAMPLE
        # # analog_output_daq_to_galvos.out_stream.offset = 0
        #analog_output_daq_to_galvos.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.ALLOW_REGENERATION # maybe only for CONTINUOUS mode
        analog_output_daq_to_galvos.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.DONT_ALLOW_REGENERATION
        
        # #analog_output_daq_to_galvos.out_stream.nextWriteIsLast # custom
        # N/A
        analog_output_daq_to_galvos.out_stream.output_onbrd_buf_size # 1024 for 6160, board's onboard FIFO size
        # the buffer size needs to be at least as large as this size if ON_BOARD_MEMORY_LESS_THAN_FULL is used
        # otherwise the buffer size needs to be at least 500
        analog_output_daq_to_galvos.channels.ao_data_xfer_mech
        # # analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = nidaqmx.constants.OutputDataTransferCondition.ON_BOARD_MEMORY_LESS_THAN_FULL # default
        # Transfer data to the device only when there is no data in the FIFO 

     
    analog_output_daq_to_galvos.out_stream.output_buf_size = buffer_write_size
    
    # # WANING : set this property AFTER any change of buffer
    # analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = nidaqmx.constants.OutputDataTransferCondition.ON_BOARD_MEMORY_EMPTY
    
    if use_volt_not_raw_write:
        stream_writer_galvos = nidaqmx.stream_writers.AnalogMultiChannelWriter(analog_output_daq_to_galvos.out_stream, auto_start=False) # is used only for the scan, not for blinking
        meth_write = stream_writer_galvos.write_many_sample
        
    else:
        stream_writer_galvos = nidaqmx.stream_writers.AnalogUnscaledWriter(analog_output_daq_to_galvos.out_stream, auto_start=False) # is used only for the scan, not for blinking
        meth_write = stream_writer_galvos.write_int16
    
    # # ******** verification AO ************
    
    analog_output_daq_to_galvos.out_stream.wait_mode # nidaqmx.constants.WaitMode.SLEEP default, with analog_output_daq_to_galvos.out_stream.sleep_time = 0.001sec
    
    buf_size = analog_output_daq_to_galvos.out_stream.output_buf_size
    print('buf_size AO ', buf_size)
    actual_rate = analog_output_daq_to_galvos.timing.samp_clk_rate
    print('actual_rate AO', actual_rate)
    # print(analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond)
    
    analog_output_daq_to_galvos.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # start faster the Task
        # analog_output_daq_to_galvos.channels.ao_term_cfg # is indeed RSE
    
    return analog_output_daq_to_galvos, meth_write, buffer_write_size, shape_reverse_movement, correct_unidirektionnal , sample_rate_galvos, nb_line_prewrite, time_expected_sec, name_list_wr_dumb_tasks, ao_dumb

def scan_xz_reg_N_samps(analog_input, piezoZ_step_signal, step_Z_mm, k, number_of_samples):
    
    def callback_Nsamps(task_handle, every_n_samples_event_type, number_of_samples, callback_data):
        
        piezoZ_step_signal.emit((k)*step_Z_mm)  # in mm
            
        return 0 # The function should return an integer
    
    analog_input.register_every_n_samples_acquired_into_buffer_event(number_of_samples, None) 
    analog_input.register_every_n_samples_acquired_into_buffer_event(number_of_samples, callback_Nsamps)
    
def meas_smp_rate_ext_clck(nidaqmx, dev, term_ext_clck, min_val_extRate, max_val_extRate):
    # # is called in the init_dzq meth 
    try:
        if ('dummy_task' in locals() and dummy_task is not None):
            dummy_task.close() # clear task
        dummy_task =  nidaqmx.Task()
        
        dummy_task.ci_channels.add_ci_freq_chan(counter = '%s/ctr0' % dev, min_val=min_val_extRate, max_val=max_val_extRate, units=nidaqmx.constants.FrequencyUnits.HZ, edge=nidaqmx.constants.Edge.RISING, meas_method=nidaqmx.constants.CounterFrequencyMethod.LOW_FREQUENCY_1_COUNTER)
        # only Large Frequency Range with 2 Counters could also be used
        dummy_task.channels.ci_freq_term = ('/%s/%s' % (dev, term_ext_clck))
        
        stream_reader_CI = nidaqmx.stream_readers.CounterReader(dummy_task.in_stream)
        dummy_task.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # commit the Task
        
        rate_meas = stream_reader_CI.read_one_sample_double() #
    except:
        print(Exception)
        rate_meas = 0
    finally:
        dummy_task.close() # clear task 
    
    return rate_meas
    
def bounds_AI_daq(val, dev, max_val):

    if val>10:
        if dev == 2: # 6259
            bound = max_val
        else: # 6110
            if val>20:
                bound =  max_val # 42
            else:
                bound = 20
            bound = 20
    elif 5< val<=10:
        bound = 10
    elif 2< val<=5:
        bound = 5
    elif 1< val<=2:
        bound = 2
    elif 0.5< val<=1:
        bound = 1
    elif 0.2< val<=0.5:
        bound = 0.5
    elif val<=0.2:
        if dev == 2: # 6259
            if val<=0.1:
                bound = 0.1
            else:
                bound = 0.2
        else: # 6110
            bound = 0.2
            
    return bound
    
def nb_linespacket_meth(numpy, diggalvomode, last_buff_smallest_poss, lvl_trigger_not_win, add_nb_lines_safe, callbacks, sample_rate, nb_px_slow, update_time, time_expected_sec, duration_one_line_real, time_trig_paused):

    nb_lines_inpacket = int(round(update_time/(time_expected_sec/nb_px_slow))) if time_expected_sec > update_time else nb_px_slow # # sometimes round gives a .0 !!
    # the update time is rounded
    
    if nb_lines_inpacket <= 0: maxSmp_paquet = 0
    else: # ok
        lastpckt_nbln = nb_px_slow-nb_lines_inpacket*int(nb_px_slow/nb_lines_inpacket)
        szmax_lastpckt = 10
        if( nb_lines_inpacket != nb_px_slow and nb_lines_inpacket > 2*lastpckt_nbln and lastpckt_nbln < szmax_lastpckt): # # less than 10 lines in last buffer !
            # # print('\n nb_lines_inpacket\n', nb_lines_inpacket, nb_px_slow/int(nb_px_slow/nb_lines_inpacket) )
    
            nb_lines_inpacket = int(numpy.ceil(nb_px_slow/int(nb_px_slow/nb_lines_inpacket))) # !!!
    
        # # warnings.warn('correct the write galvos by int16 !') time_trig_paused
        if not callbacks: # no callback
            # maxPx_paquet = update_time/(time_by_point +  time_flyback_unpaused/time_by_point
            # maxSmp_paquet = (update_time - time_trig_paused*update_time/duration_one_line_real)*sample_rate # # if read line time after
            if lvl_trigger_not_win == 2: # # pause only on the dec/acc of the bottom
                nb_cons = nb_lines_inpacket + add_nb_lines_safe
            else:
                nb_cons = nb_lines_inpacket
                
        else:  nb_cons =  1 # line by line, callback
            # # this value will be multiplied by 2 after for szie of the array
        
        maxSmp_paquet = nb_cons*sample_rate*(duration_one_line_real - time_trig_paused)  
        #nb_px_fast*(sample_rate*time_by_point)
        # # print('walla', maxSmp_paquet, nb_px_fast, sample_rate, time_by_point)
            
        if not lvl_trigger_not_win: # window pos, also the return gives a line time
            nb_lines_inpacket = nb_lines_inpacket*2
    
        # # dig galvos
        if (diggalvomode and last_buff_smallest_poss): nb_lines_inpacket = int(nb_px_slow/max(1, int(nb_px_slow/nb_lines_inpacket))) # # retaking nb_lines_inpacket
    
    return nb_lines_inpacket, maxSmp_paquet

    
def mtr_trigout_redefine_EOMph(nidaqmx, mtr_trigout_cntr, nametask_mtr_trigout_list, device_to_use, ctr_str, ctr_src_trigger, src_trigger_motor, CO_for_EOMphtrig_already_def, pulse_width, mtr_trigout_retriggerable):
    # # Task just used for generate a proper pulse trigger to the EOM HV unit
    
    ctr_trg_str = '/%s/%s' % (device_to_use, ctr_src_trigger) if ctr_src_trigger is not None else ''
    # # print('nametask_mtr_trigout_list', nametask_mtr_trigout_list is None)
    if (CO_for_EOMphtrig_already_def or nametask_mtr_trigout_list is None): low_verif = high_verif = ''; just_str = 'the input trig'; mtr_trigout_cntr = None
    else: # # have to define a Task
        name_mtr_trigout = nametask_mtr_trigout_list[-1] # last
        while True:
            nametask_mtr_trigout_list = ['%s_0%d' % (name_mtr_trigout[:-3], int(name_mtr_trigout[-1])+1)] # next name to try
            try:
                mtr_trigout_cntr = nidaqmx.Task(name_mtr_trigout) 
            except nidaqmx.DaqError as err:
                if err.error_type == nidaqmx.error_codes.DAQmxErrors.DUPLICATE_TASK:
                    name_mtr_trigout = nametask_mtr_trigout_list[-1] # last
                    continue
                else:
                    raise(err)
            else: # # success
                break # outside 'while' loop
        # # ctr_str = '%s/%s' % (device_to_use, cntr_chan_name)
        mtr_trigout_cntr.co_channels.add_co_pulse_chan_time(counter = ctr_str, units=nidaqmx.constants.TimeUnits.SECONDS, idle_state = nidaqmx.constants.Level.LOW, initial_delay=0, low_time=pulse_width, high_time=pulse_width)
        
        mtr_trigout_cntr.timing.cfg_implicit_timing( sample_mode= nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan= 1)
        
        if ctr_src_trigger is not None:
            # # triggers
            mtr_trigout_cntr.triggers.start_trigger.cfg_dig_edge_start_trig(ctr_trg_str, trigger_edge = nidaqmx.constants.Edge.RISING) # default rising
            if mtr_trigout_retriggerable: mtr_trigout_cntr.triggers.start_trigger.retriggerable = True
            # # mtr_trigout_cntr.triggers.arm_start_trigger.trig_type = nidaqmx.constants.TriggerType.DIGITAL_EDGE
            # # mtr_trigout_cntr.triggers.arm_start_trigger.dig_edge_src = '/%s/PFI1' % device_to_use
            # mtr_trigout_cntr.triggers.arm_start_trigger.term
            # # print('walaaa', mtr_trigout_cntr, nametask_mtr_trigout_list, device_to_use, ctr_src_trigger, pulse_width)
            # # print('/%s/AnalogComparisonEvent' % (device_to_use), '/%s/%s' % (device_to_use, ctr_src_trigger))
            # # print('warning!!!, conn terminals OFF in eomph trig mtr')
            # # '''
            system = nidaqmx.system.System.local()
            system.disconnect_terms(source_terminal = ('/%s/%s' % (device_to_use, src_trigger_motor)), destination_terminal = ctr_trg_str)
            system.connect_terms(source_terminal = ('/%s/%s' % (device_to_use, src_trigger_motor)), destination_terminal = ctr_trg_str) # AnalogComparisonEvent
            # # # # because AnalogComparisonEvent cannot be directly used
            print('ishg : connected /%s/%s to %s' % (device_to_use, src_trigger_motor, ctr_trg_str), nametask_mtr_trigout_list)
            # # '''
        # # if nametask_mtr_trigout_list is not None: # # stage scn
        else: ctr_trg_str = mtr_trigout_cntr.triggers.start_trigger.trig_type.name
        low_verif = str(mtr_trigout_cntr.co_channels[0].co_pulse_low_time)
        high_verif = str( mtr_trigout_cntr.co_channels[0].co_pulse_high_time)
        just_str = 'an internal pass'
        
        mtr_trigout_cntr.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
        
    if (nametask_mtr_trigout_list is not None): # # normally not in this function if None !!
        retr_str = mtr_trigout_cntr.triggers.start_trigger.retriggerable if mtr_trigout_cntr is not None else 'same_watchTrig'
        print('counter OUT ishg %s with trig %s pulsewidth_meas:%.3g (%s, %s) us retrig%r' % (ctr_str, ctr_trg_str, pulse_width*1e6, low_verif, high_verif, retr_str))
        print(' %s is just %s, connect %s OUT to instrument (via buffer_cleaner) !' % (ctr_src_trigger, just_str, ctr_str))
    
    return mtr_trigout_cntr, nametask_mtr_trigout_list