# -*- coding: utf-8 -*-
"""
Created on March 17 09:35:13 2018

@author: Maxime PINSARD
""" 

import multiprocessing

class Anlg_trig_sender_process(multiprocessing.Process):

    """
    class used to send order to read via a callback
    after, discovered that the callback can be called easily and pass parameters, and is quite fast so no need of this function
    """

    def __init__(self, device_to_use_watcherTrig, queueEmpty,  term_DI, receiver_read_to_trigger, sender_trigger_to_read, queue_special_com_stopline, time, use_change_detect_event, rate, nb_lines):
    
        multiprocessing.Process.__init__(self)

        self.receiver_read_to_trigger = receiver_read_to_trigger
        self.sender_trigger_to_read = sender_trigger_to_read
        self.queue_special_com_stopline = queue_special_com_stopline 
        self.term_DI = term_DI
        
        self.device_to_use_watcherTrig = device_to_use_watcherTrig
    
        self.queueEmpty = queueEmpty
        
        self.time = time
        
        self.use_change_detect_event = use_change_detect_event
        self.rate  = rate # if chg detection, pass 0
        self.nb_lines = nb_lines

    def run(self):
        
        def anlg_trig_sender(device_to_use_watcherTrig, queueEmpty,  term_DI, receiver_read_to_trigger, sender_trigger_to_read, queue_special_com_stopline, time, smallest_OS_sleep):
        
            def callback(task_handle, signal_type, callback_data):
                # # print('in call')
                sender_trigger_to_read.send(True)
                                
                return 0 # an integer must be return
                
            print('Starting nidaqmx in anlg_trig_watcher ...')
            import nidaqmx
            
            ## DIGITAL input Task
            
            if 'anlgComp_watcher_task' in locals():
                anlgComp_watcher_task.close() # clear task 
            
            method_watch = 1
            anlgComp_watcher_task = anlgCompEvent_watcher(nidaqmx, device_to_use_watcherTrig, device_to_use_anlgTrig, term_DI,  trig_src_end_master, method_watch, rate, nb_lines, volt_pos_max_fast, volt_pos_min_fast, volt_pos_max_fast, volt_pos_min_fast, factor_trigger, use_velocity_trigger, callback, pack_params_new_galvos, anlgComp_watcher_task, name_list_watcher_tasks, port_trigout_EOMph) 
            
            while True: # 'while' loop of msg
                print('Trig watcher Process is waiting for orders ...') 
                msg = receiver_read_to_trigger.recv() # receiving orders, blocking
                
                
                if msg[0] == -1:# poison-pill
                    print('poison-pill (in Trig watcher Process) !')
                
                    anlgComp_watcher_task.close()
                    
                    break # outside 'while' loop of msg, exiting Process
                    
                elif msg[0] == 0: # stand-by
                    continue # for now
                
                elif msg[0] == 1: # acq.
                
                    if len(msg) > 1:
                        params = msg[1]
                
                        nb_lines = params[0]
                        control_stop_each_N_line = params[1]
                        # queue_special_com_stopline.put('params') # !!
                    # the other parameters must not change : the terminal cannot be changed, the Device neither
                
                    anlgComp_watcher_task.stop()
                    anlgComp_watcher_task.start() # will register events when needed

                    ii = 0
                    for ii in range(nb_lines): # loop of 1 acq. # while True:
                    
                        # # anlgComp_watcher_task.wait_until_done(nb_lines/rate*1.5) # error if Task not finished
                        
                        time.sleep(smallest_OS_sleep)
                        
                        if not (ii % control_stop_each_N_line): # a multiple
                            try: # control if a stop in-line was sent
                                msg = queue_special_com_stopline.get_nowait()
                                if msg == 'stop':
                                    print('stop signal in-line inside DI trig watcher (img line = %d)' % ii) 
                                    break
                            except queueEmpty:
                                pass
                                
                    anlgComp_watcher_task.stop()
                    # queue_special_com_stopline.put('stop') # !!

                                
            print('Trig watcher Process is finishing (img line = %d)' % ii)
            
        anlg_trig_sender(self.device_to_use_watcherTrig, self.queueEmpty,  self.term_DI, self.receiver_read_to_trigger, self.sender_trigger_to_read, self.queue_special_com_stopline, self.time, self.use_change_detect_event, self.rate, self.nb_lines)

class Anlg_Pausetrig_Substitute(multiprocessing.Process):

    """
    Process to substitute to Pause trigger by generating a custom trigger with a DO Task, analysing the trigger channel
    """

    def __init__(self, dev_list, device_to_use_anlgTrig, ai_trig_src_name_master,  smp_rate_trig, term_do, export_smpclk, use_RSE ,samp_src_term_master_toExp, queue_read_to_trigger, queue_special_com_stopline, queueEmpty, gen_write):
    
        multiprocessing.Process.__init__(self)

        self.dev_list = dev_list
        self.device_to_use_anlgTrig = device_to_use_anlgTrig
        self.ai_trig_src_name_master = ai_trig_src_name_master
        self.smp_rate_trig = smp_rate_trig
        self.term_do = term_do
        self.export_smpclk = export_smpclk
        self.use_RSE = use_RSE
        self.samp_src_term_master_toExp = samp_src_term_master_toExp
        self.queue_read_to_trigger = queue_read_to_trigger
        # buf_size_2set
        self.queue_special_com_stopline = queue_special_com_stopline 
        self.queueEmpty = queueEmpty
        self.gen_write = gen_write

    def run(self):
        
        print('In run') 
        
        def anlg_trig_substitute(dev_list, device_to_use_anlgTrig, ai_trig_src_name_master,  smp_rate_trig, term_do, export_smpclk, use_RSE ,samp_src_term_master_toExp, queue_read_to_trigger, queue_special_com_stopline, queueEmpty, gen_write):
            
            print('Starting nidaqmx in anlg_trig_substitute ...')
            import nidaqmx
            import nidaqmx.stream_readers # mandatory if read_stream
            import nidaqmx.stream_writers
            # import nidaqmx.system
            
            ## AI trig read Task
            
            # if 'ai_trig_control' in locals():
            #    ai_trig_control.close() # clear task 
            ai_trig_control = nidaqmx.Task() # Task for the AI channel on 6259, just used for trig
            ai_trig_control.ai_channels.add_ai_voltage_chan(ai_trig_src_name_master)
            if (len(dev_list) > 1 and device_to_use_anlgTrig.name == dev_list[1].name): # 6259
                if use_RSE:
                    ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.RSE # nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL #
                else:
                    ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.DIFFERENTIAL #
                    
            else: # 6110
                ai_trig_control.channels.ai_term_cfg = nidaqmx.constants.TerminalConfiguration.PSEUDODIFFERENTIAL # only one available
                
            ai_trig_control.timing.cfg_samp_clk_timing(rate= smp_rate_trig, source= '', sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = 1 ) # source = internal Onboard src of 6259
            
            # allow to read last sample
            ai_trig_control.in_stream.over_write = nidaqmx.constants.OverwriteMode.OVERWRITE_UNREAD_SAMPLES 
            ai_trig_control.in_stream.relative_to = nidaqmx.constants.ReadRelativeTo.MOST_RECENT_SAMPLE 
            ai_trig_control.in_stream.offset = -1
            ai_trig_control.in_stream.wait_mode = nidaqmx.constants.WaitMode.POLL  # CPU intensive
            # could try YIELD as well
            ai_trig_control.in_stream.wait_mode = nidaqmx.constants.WaitMode.SLEEP
            ai_trig_control.in_stream.sleep_time = 0.1e-3
            
            ai_trig_control.triggers.start_trigger.trig_type = nidaqmx.constants.TriggerType.NONE
            ai_trig_control.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.NONE
            
            stream_reader_trig_control = nidaqmx.stream_readers.AnalogSingleChannelReader(ai_trig_control.in_stream)
            
            if export_smpclk:
                ai_trig_control.export_signals.export_signal(nidaqmx.constants.Signal.SAMPLE_CLOCK, output_terminal = samp_src_term_master_toExp) 
            
            ai_trig_control.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
            
            ## DIGITAL output Task
            
            #if 'DO_sender' in locals():
            #    DO_sender.close() # clear task 
            DO_sender = nidaqmx.Task() # Task for the AI channel on 6259, just used for trig
            DO_sender.do_channels.add_do_chan('%s/%s' % (device_to_use_anlgTrig.name, term_do), line_grouping= nidaqmx.constants.LineGrouping.CHAN_FOR_ALL_LINES)
            
            DO_sender.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.ON_DEMAND #cfg_samp_clk_timing(rate = 1e6, sample_mode=  nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = buffer_write_size)
            
            DO_sender.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.ALLOW_REGENERATION
            
            stream_writer_DO = nidaqmx.stream_writers.DigitalSingleChannelWriter(DO_sender.out_stream, auto_start=True) # fastest

            DO_sender.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
            
            ## loop
            
            analog_output_daq_to_galvos = 0
            
            while True:
                
                print('Trig control Process is waiting for orders ...') 
                msg = queue_read_to_trigger.get() # blocking
                
                if msg[0] == -1:# poison-pill
                    print('poison-pill (in Trig control Process) !')
                    if gen_write:        
                        analog_output_daq_to_galvos.close()     
                    ai_trig_control.close()
                    DO_sender.close()
                    
                    break # outside 'while' loop of msg, exiting Process
                    
                elif msg[0] == 0: # stand-by
                    continue # for now
                
                elif msg[0] == 1: # acq.
                
                    print('order of Acq (Trig control Process) !')
                    
                    # # DO_sender.write(False, auto_start = True, timeout=0) # in pause
                    stream_writer_DO.write_one_sample_one_line(False, timeout=0)
                    
                    state_pause_trig = 1
                    
                    ai_trig_control.stop()

                    if len(msg) > 1:  # params
                        volt_pos_max_fast = msg[1][0]
                        volt_pos_min_fast = msg[1][1]
                        factor_trigger = msg[1][2]
                        volt_pos_min_fast = msg[1][3]
                        volt_pos_max_fast = msg[1][4]
                        nb_lines = msg[1][5]
                        nb_hysteresis_acc = msg[1][6]
                        nb_hysteresis_dec = msg[1][7]
                        limit_listening_special_sec = msg[1][8] 
                        
                        ai_trig_control.channels.ai_min = volt_pos_min_fast/factor_trigger
                        ai_trig_control.channels.ai_max = volt_pos_max_fast/factor_trigger
                        
                    
                    k = 0; ct_hysteresis_acc = 0; ct_hysteresis_dec = nb_hysteresis_dec; ct_it = 0
                    
                    ai_trig_control.start()
                    
                    if gen_write:
                        analog_output_daq_to_galvos.start()
                            
                    while k < nb_lines:
                        
                        ct_it +=1
                        
                        if ct_it > limit_listening_special_sec*smp_rate_trig/2:
                            try: # raises error if nothing to read
                                msg = queue_special_com_stopline.get_nowait() # wait without block, raises error if nothing, that's why there is a try/except
                                if msg == 'stop':
                                    print('stop signal in-line from the GUI (at line = %d)' % k) 
                                    break
                                    
                            except queueEmpty:
                                pass # do nothing
                        
                        samp = stream_reader_trig_control.read_one_sample(timeout = 0)
                        
                        if (volt_pos_min_fast/factor_trigger <= samp <= volt_pos_max_fast/factor_trigger): # acquisition of one line
                            ct_hysteresis_dec = 0 # one point inside the window and the count restart
                            ct_hysteresis_acc += 1
                            if (ct_hysteresis_acc == nb_hysteresis_acc): # a transition must be done
                                if state_pause_trig:
                                    # # DO_sender.write(True, timeout=0) # no pause trigger+
                                    stream_writer_DO.write_one_sample_one_line(True, timeout=0)
                                    state_pause_trig = 0
                                
                            else:
                                continue # re-iteration
                                
                        else: # out of window pos
                            # default
                            ct_hysteresis_acc = 0 # one point outside the window and the count restart
                            ct_hysteresis_dec += 1
                            
                            if (ct_hysteresis_dec == nb_hysteresis_dec): # a transition must be done
                                if not state_pause_trig:
                                    # # DO_sender.write(False, timeout=0) # pause trigger
                                    stream_writer_DO.write_one_sample_one_line(False, timeout=0)
                                    state_pause_trig = 1
                                    k += 1 # one more line
                                
                            else:
                                continue # re-iteration
            
                    if gen_write:        
                        analog_output_daq_to_galvos.wait_until_done()      
                    ai_trig_control.stop()
                    DO_sender.stop()
                    if gen_write:
                        analog_output_daq_to_galvos.stop()
                    
                    print('Trig control Process is finishing (img line = %d)' % k)
                
        anlg_trig_substitute(self.dev_list, self.device_to_use_anlgTrig, self.ai_trig_src_name_master,  self.smp_rate_trig, self.term_do, self.export_smpclk, self.use_RSE , self.samp_src_term_master_toExp, self.queue_read_to_trigger, self.queue_special_com_stopline, self.queueEmpty, self.gen_write)
            
        
def anlgCompEvent_watcher(nidaqmx, dev_list, term_DI, trig_src_end_master, term_anlg_comp_routed, method_watch, dur_lines, nb_lines, use_velocity_trigger, use_trigger_anlgcompEv_onFallingEdges, use_dig_fltr_onAlgCmpEv, callback, pack_params_new_galvos, anlgComp_watcher_task, name_list_watcher_tasks, tuple_EOMph):
    
    port_trigout_EOMph, use_same_CO_for_EOMphtrig, pulsewidth_ctroutEOM_sec = tuple_EOMph
    
    '''
    Various methods to watch the Anlg Comp Event signal
    # 7: # counter input to MEASURE the line time
    # 6: # counter input for callback, that counts the falling triggers edges
    # 4 counter OUTPUT retriggerable that makes a pulse (for callback) each time the st trigger = pause trigger of read task is asserted
    # 5 -
    # 3  anlg trig watches itself (2 cards): callback on sample clock of an AI task (on other card), whose clock is the analogComparisonEvent of the main read
    # 2 : DI with sample clock detect (callback on sample clock), has the drawback to have to set the rate,  FOR 6110 only
    # 1 : DI with a callback on CHANGE_DETECTION_EVENT  # for 6259 only 
    '''
    
    # # print('trig_src_end_master', trig_src_end_master, ctr_port)
    trig_src_end_master = trig_src_end_master.split('/')[-1] # # in case of /Dev1/PFI0 instead of PFI0
    
    if len(pack_params_new_galvos) > 3: # special galvos (anlg or dig callback)
        [device_to_use_anlgTrig, device_to_use_watcherTrig, num_ctr, volt_pos_max_fast, volt_pos_min_fast, _, _, _, _, _, _, _, _, _, _, _, _, factor_trigger, _, lvl_trigger_not_win, _, _, min_pulse_width_digfltr_6259, _, _, _, _, _, _, _, _, _, _, _, _, _] = pack_params_new_galvos
          
    else:
        [device_to_use_anlgTrig, device_to_use_watcherTrig, num_ctr] = pack_params_new_galvos 
    
    if ('anlgComp_watcher_task' in locals() and anlgComp_watcher_task is not None):
        anlgComp_watcher_task.close()
    name_watcher = name_list_watcher_tasks[0] # last
    anlgComp_watcher_task = nidaqmx.Task(name_watcher)
    name_list_watcher_tasks = ['%s_0%d' % (name_watcher[:len(name_watcher)-3], int(name_watcher[len(name_watcher)-1])+1)]

    if method_watch <= 2:
        anlgComp_watcher_task.di_channels.add_di_chan('%s/%s' % (device_to_use_watcherTrig.name, term_DI), line_grouping= nidaqmx.constants.LineGrouping.CHAN_FOR_ALL_LINES)
        
        # anlgComp_watcher_task.timing.cfg_implicit_timing(sample_mode = nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan=nb_lines)
        # implicit timing is not available, only nidaqmx.constants.SampleTimingType.ON_DEMAND
    
    ctr_port = '%s/ctr%d' % (device_to_use_watcherTrig.name, num_ctr) # # for 4, 6, 7
    # # if method_watch == 4: # # ctr OUTput retriggerable
    # # elif method_watch == 6: # # ctr Input callback at falling edges of anlgcmpevent
    # # if method_watch == 7: # counter input to MEASURE the line time, no callback
    # #     if (len(dev_list) > 1 and device_to_use_watcherTrig == dev_list[1]): # 6259
    # #         ctr_port = '%s/ctr0' % device_to_use_watcherTrig.name
            # # ctr_timebase_rate = 80e6
    if (port_trigout_EOMph is not None and ctr_port == port_trigout_EOMph and not(method_watch == 4 and use_same_CO_for_EOMphtrig)): # # ishg fast EOM, same counter cannot be used twice
    # # the only case that would save the port is that the counter OUT of meth4 is also used by iSHG fast
        ctr_port = '%s/ctr%d' % (device_to_use_watcherTrig.name, int(not num_ctr))  #len(pack_params_new_galvos) > 2: num_ctr = 0  # # anlg galvos
    #else: num_ctr = 1 # # dig galvos, because one card used only, and the counter is used by the output for iSHG fast. If no ishg fast, could use the same params as anlg galvos
    if (method_watch == 7 and device_to_use_watcherTrig == dev_list[0] and ctr_port == '%s/ctr0' % device_to_use_watcherTrig.name): # counter input to MEASURE the line time, no callback
    # # 6110  --> Ctr0 cannot be used
        if port_trigout_EOMph is not None: print('meth readlines uses same ctr as ctrout ishgfast: trig on other card !!\n'); raise(ValueError)# # ishg fast, ctr was already corrected on line before, so there is a conflict here !
        else: 
            ctr_port = '%s/ctr1' % device_to_use_watcherTrig.name # Ctr0 cannot be used
            # # ctr_timebase_rate = 20e6
            
    if method_watch == 1:
    #use_change_detect_event: # for 6259 only
    
        anlgComp_watcher_task.timing.cfg_change_detection_timing(rising_edge_chan='', falling_edge_chan='%s/%s' % (device_to_use_watcherTrig.name, term_DI), sample_mode=  nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan = nb_lines) #, sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan=1000)
        
        anlgComp_watcher_task.timing.change_detect_di_rising_edge_physical_chans # verify it's good
        anlgComp_watcher_task.timing.change_detect_di_falling_edge_physical_chans # verify it's nothing
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.CHANGE_DETECTION_EVENT, None)
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.CHANGE_DETECTION_EVENT, callback)
        
    elif method_watch == 2: # DI sample clock detect, has the drawback to have to set the rate,  FOR 6110 only
    
        # it WORKS, but has to set the rate
        # trig_source_event = '/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name) # or can be a terminal
        if use_trigger_anlgcompEv_onFallingEdges:

            trig_source_event = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master)
        else:
            
            trig_source_event = '/%s/%s' % (device_to_use_watcherTrig.name, term_anlg_comp_routed)  # the terminal were anlg comp was INVERTED

        # # !! the event has to be inverted,  otherwise acq. when inside window !!
        anlgComp_watcher_task.timing.cfg_samp_clk_timing( 1/dur_lines,  source = trig_source_event, sample_mode=  nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan = nb_lines) # nidaqmx.constants.AcquisitionType.CONTINUOUS
        anlgComp_watcher_task.timing.samp_clk_rate
        
        if use_trigger_anlgcompEv_onFallingEdges:

            anlgComp_watcher_task.timing.samp_clk_active_edge = nidaqmx.constants.Edge.FALLING
        else:
            anlgComp_watcher_task.timing.samp_clk_active_edge = nidaqmx.constants.Edge.RISING
        
        if (len(dev_list) > 1 and device_to_use_watcherTrig == dev_list[1]): # 6259
            anlgComp_watcher_task.export_signals.samp_clk_output_behavior = nidaqmx.constants.ExportAction.LEVEL
        
        # # CANNOT be used
        # # if use_dig_fltr_onAlgCmpEv: 
        # #     anlgComp_watcher_task.channels.di_dig_fltr_enable
            # # impossible to use the filter on the sample clk
            # # anlgComp_watcher_task.timing.samp_clk_dig_fltr_enable = True
            # # anlgComp_watcher_task.timing.samp_clk_dig_fltr_min_pulse_width = 6.425000e-6
            # # anlgComp_watcher_task.timing.samp_clk_dig_fltr_timebase_src = '80MHzTimebase'
        # optionnal ??
        # to sync correctly the clk, despite the rate might be fluctuating

        # might not work because ticks are not LVL but pulses !! ok of anlgCompEvent is long
        
        # start trigger with terminal CANNOT be defined if Smp clk is on ine terminal
        # anlgComp_watcher_task.triggers.start_trigger.cfg_dig_edge_start_trig('/%s/%s' % (device_to_use_watcherTrig.name, trig_src_end_master), trigger_edge = nidaqmx.constants.Edge.RISING)
        

        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, None) # WORKS (at least in commit)
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, callback)

    elif method_watch == 3:  # anlg trig watches itself (2 cards)
    
    # use_anlg_trig_watch_itself:
    # see http://www.ni.com/example/31130/en/
    # and ai_ext_sample_clk_trig_event.vi

        anlgComp_watcher_task.ai_channels.add_ai_voltage_chan('%s/%s' % (device_to_use_anlgTrig.name, term_anlg_comp_routed), min_val=volt_pos_min_fast/factor_trigger, max_val = volt_pos_max_fast/factor_trigger)
        trig_source_event = '/%s/AnalogComparisonEvent' % (device_to_use_anlgTrig.name) # or can be a terminal
        anlgComp_watcher_task.timing.cfg_samp_clk_timing( 1/dur_lines,  source = trig_source_event, sample_mode=  nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan = nb_lines) # nidaqmx.constants.AcquisitionType.CONTINUOUS
        
        if device_to_use_anlgTrig == dev_list[0]: # 6110
            trig_src = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master)
        else: # 6259
            trig_src = '%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master)
            
        anlg_win_bottom = volt_pos_min_fast/factor_trigger
        anlg_win_top = volt_pos_max_fast/factor_trigger # V
        # # anlg_win_bottom = -0.15
        # anlg_win_bottom = anlg_win_bottom/2
        # anlg_win_top = anlg_win_top/2 # !!
        # # anlg_win_top = 0.15
        use_st_trigger = 0
        if use_st_trigger == 1: 
            anlgComp_watcher_task.triggers.start_trigger.trig_type = nidaqmx.constants.TriggerType.ANALOG_WINDOW
            anlgComp_watcher_task.triggers.start_trigger.anlg_win_btm = anlg_win_bottom # V
            anlgComp_watcher_task.triggers.start_trigger.anlg_win_top = anlg_win_top
            anlgComp_watcher_task.triggers.start_trigger.anlg_win_src = trig_src # rising default
            
            if use_velocity_trigger:
                anlgComp_watcher_task.triggers.start_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition1.ENTERING_WINDOW 
                
            else:
                anlgComp_watcher_task.triggers.start_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition1.LEAVING_WINDOW
                
        elif use_st_trigger == 2: # pause trigger
            anlgComp_watcher_task.triggers.pause_trigger.trig_type = nidaqmx.constants.TriggerType.ANALOG_WINDOW
            anlgComp_watcher_task.triggers.pause_trigger.anlg_win_src = trig_src # rising default
            
            if use_velocity_trigger:
                anlgComp_watcher_task.triggers.pause_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition2.OUTSIDE_WINDOW # pause when outside
            else:
                anlgComp_watcher_task.triggers.pause_trigger.anlg_win_when = nidaqmx.constants.WindowTriggerCondition2.INSIDE_WINDOW # anlgCompEvent low when inside window
                
            anlgComp_watcher_task.triggers.pause_trigger.anlg_win_btm = anlg_win_bottom # V
            anlgComp_watcher_task.triggers.pause_trigger.anlg_win_top = anlg_win_top
        
        anlgComp_watcher_task.export_signals.samp_clk_output_behavior = nidaqmx.constants.ExportAction.LEVEL
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, None) # WORKS (at least in commit)
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, callback)
        
    elif method_watch == 4: # counter output
        # # from https://forums.ni.com/t5/Example-Programs/Single-Counter-Pulse-on-Analog-Edge-Trigger-with-Continuous/ta-p/3524580
        if use_trigger_anlgcompEv_onFallingEdges: trig_src_end = trig_src_end_master; edge = nidaqmx.constants.Edge.FALLING
        else: trig_src_end = term_anlg_comp_routed; edge = nidaqmx.constants.Edge.RISING
        # from Single Counter Pulse on Analog Edge Trigger.vi 
        if use_same_CO_for_EOMphtrig: 
            pulse_width = pulsewidth_ctroutEOM_sec # # from param_ini
        else: pulse_width = 1/1e6 # # sec
        # min is 1/20e6
        
        anlgComp_watcher_task.co_channels.add_co_pulse_chan_time(counter = ctr_port, units=nidaqmx.constants.TimeUnits.SECONDS, idle_state = nidaqmx.constants.Level.LOW, initial_delay=0.0, low_time=pulse_width, high_time=pulse_width) # we don't care about the output of ctr0
        
         # counter output retriggerable
        # # # TODO: 
        # # use_trigger_anlgcompEv_onFallingEdges = not use_trigger_anlgcompEv_onFallingEdges # #  !!!!
        # # print('params_galvos !! master l 452', trig_src_end_master, use_trigger_anlgcompEv_onFallingEdges, num_ctr)
        anlgComp_watcher_task.timing.cfg_implicit_timing( sample_mode= nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan= 1) # is retriggerable
            
        anlgComp_watcher_task.triggers.start_trigger.cfg_dig_edge_start_trig('/%s/%s' % (device_to_use_watcherTrig.name, trig_src_end) , trigger_edge =  edge) # the term routed is inverted
    
        anlgComp_watcher_task.triggers.start_trigger.retriggerable = True
    
        # anlgComp_watcher_task.export_signals.ctr_out_event_output_behavior = nidaqmx.constants.ExportAction.TOGGLE # to increase the detection by callback
    
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.COUNTER_OUTPUT_EVENT, None) #
        anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.COUNTER_OUTPUT_EVENT, callback) #
            
    elif (method_watch == 6 or method_watch == 7): # counter input
    
        if (use_trigger_anlgcompEv_onFallingEdges and not use_dig_fltr_onAlgCmpEv and device_to_use_anlgTrig == device_to_use_watcherTrig): # to watch at anlgCompevent directly with a dig filter does NOT work, you have to pass by a terminal
        # is rising edges, you passed by a terminal because the anlgCompEv is inverted
        # if devices are different, you passed by a terminal
        # not that inversion of AnlgCompEv is NOT possible for 6259, so you passed by a terminal but the signal was NOT inverted
            trig_source_event = '/%s/%s' % (device_to_use_anlgTrig.name, trig_src_end_master)
        else: # pass by a terminal
            
            trig_source_event = '/%s/%s' % (device_to_use_watcherTrig.name, term_anlg_comp_routed) 
            # '/Dev2/PFI8'
            
        if method_watch == 6: # counter input for callback, that counts the falling triggers edges
    
            if (use_trigger_anlgcompEv_onFallingEdges): # and not lvl_trigger_not_win):
                edge_cnt = nidaqmx.constants.Edge.FALLING
            else:
                edge_cnt = nidaqmx.constants.Edge.RISING
        
            anlgComp_watcher_task.ci_channels.add_ci_count_edges_chan(counter = ctr_port, edge= edge_cnt, initial_count=0, count_direction= nidaqmx.constants.CountDirection.COUNT_UP) # dummy counter
                
            # # anlgComp_watcher_task.timing.samp_timing_type
            anlgComp_watcher_task.timing.cfg_samp_clk_timing(rate= 1/dur_lines, source= trig_source_event, sample_mode= nidaqmx.constants.AcquisitionType.HW_TIMED_SINGLE_POINT, samps_per_chan = nb_lines) # rate and nb_pts is not important here 
            # finite or continuous not possible
            
            anlgComp_watcher_task.channels.ci_count_edges_term = trig_source_event
            
            if (len(dev_list) > 1 and device_to_use_watcherTrig == dev_list[1] and use_dig_fltr_onAlgCmpEv):
                min_pulse_width = min_pulse_width_digfltr_6259  # s
                anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_min_pulse_width = min_pulse_width # s
                # # You Can Select:  0.000000,  2.560000e-3,  6.425000e-6,  125.0e-9
                # anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_timebase_rate = 80e6
                # anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_timebase_src = '80MHzTimebase'
                # anlgComp_watcher_task.channels.ci_count_edges_dig_sync_enable = False
                anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_enable = True
                anlgComp_watcher_task.timing.samp_clk_dig_fltr_min_pulse_width = min_pulse_width # have to set the smp clk AND the counter filter, together
                anlgComp_watcher_task.timing.samp_clk_dig_fltr_enable = True
            
            anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, None)  
            anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.SAMPLE_CLOCK, callback) #
            # NOT possible
            # anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.COUNTER_OUTPUT_EVENT, None)  
            # anlgComp_watcher_task.register_signal_event(nidaqmx.constants.Signal.COUNTER_OUTPUT_EVENT, callback) #
        
        elif method_watch == 7: # counter input to MEASURE the line time, no callback
            
            minval_ticks = min(1e-6, dur_lines*0.5) # *ctr_timebase_rate
            maxval_ticks = dur_lines*1.1 #ci.channels.ci_ctr_timebase_rate *ctr_timebase_rate
    
            anlgComp_watcher_task.ci_channels.add_ci_pulse_width_chan(counter = ctr_port, min_val=minval_ticks, max_val=maxval_ticks, units=nidaqmx.constants.TimeUnits.SECONDS, starting_edge=nidaqmx.constants.Edge.RISING)
            
            # # print('trig_source_event', trig_source_event, term_anlg_comp_routed)
            anlgComp_watcher_task.channels.ci_pulse_width_term = trig_source_event
            
            # anlgComp_watcher_task.timing.cfg_implicit_timing(sample_mode= nidaqmx.constants.AcquisitionType.CONTINUOUS, samps_per_chan = nb_lines)
            anlgComp_watcher_task.timing.cfg_implicit_timing(sample_mode= nidaqmx.constants.AcquisitionType.FINITE, samps_per_chan = nb_lines)
            
            anlgComp_watcher_task.in_stream.read_all_avail_samp = True # if FINITE, do not wait for all samples to be acquired
            
            if (len(dev_list) > 1 and device_to_use_watcherTrig == dev_list[1] and use_dig_fltr_onAlgCmpEv and len(pack_params_new_galvos) > 3): # anlg galvos
                anlgComp_watcher_task.channels.ci_pulse_width_dig_fltr_min_pulse_width = min_pulse_width_digfltr_6259 # s
                # anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_timebase_rate = 80e6
                # anlgComp_watcher_task.channels.ci_count_edges_dig_fltr_timebase_src = '80MHzTimebase'
                # anlgComp_watcher_task.channels.ci_count_edges_dig_sync_enable = False
                anlgComp_watcher_task.channels.ci_pulse_width_dig_fltr_enable = True
                
            # anlgComp_watcher_task.export_signals.export_signal(nidaqmx.constants.Signal.SAMPLE_CLOCK, output_terminal = '/%s/PFI8'%device_to_use_watcherTrig) # impossible
            # anlgComp_watcher_task.export_signals.export_signal(nidaqmx.constants.Signal.START_TRIGGER, output_terminal = '/%s/PFI8'%device_to_use_watcherTrig)  # impossible
 

    anlgComp_watcher_task.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
    
    return anlgComp_watcher_task
