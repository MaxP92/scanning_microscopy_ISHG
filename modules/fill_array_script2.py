# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

import multiprocessing

class fill_array(multiprocessing.Process):

    """Process fill"""

    def __init__(self, send_img_to_gui, queue_acq_fill, queue_fill_disp, queue_list_arrays, new_img_flag_queue, new_max_disp, real_time_disp, scan_mode, queue_sec2prim_fill, queue_prim2sec_ishg, sec_proc_forishgfill, primary_worker):
        
        multiprocessing.Process.__init__(self)

        self.queue_fill_disp = queue_fill_disp
        self.queue_acq_fill = queue_acq_fill
        self.queue_list_arrays = queue_list_arrays; self.new_img_flag_queue = new_img_flag_queue
        self.new_max_disp = new_max_disp
        self.real_time_disp = real_time_disp
        self.scan_mode = scan_mode
        self.primary_worker = primary_worker
        self.queue_sec2prim_fill = queue_sec2prim_fill
        self.queue_prim2sec_ishg  = queue_prim2sec_ishg 
        self.sec_proc_forishgfill = sec_proc_forishgfill
        self.send_img_to_gui = send_img_to_gui # # send_img_to_gui is in  go_scan_galvos.py

    def run(self):

        try:
            from modules import array_fill_loops3, param_ini
            import numpy, time
            from queue import Empty as queueEmpty
    
            expand_data_to_fit_line = False # if less data acquired than number of px, change the oversampling to stretch the data to the array
            verbose = 0 # print or not
            test_if_poison_pill = 0 # init
            ind_data_packet = ind_disp_sec = 0 # init
            nb_skip = 0 # ini
            array_ishg_4d = arr_in_packet = max_j_ishg = arr =data_list=None
            sat_value_list = []; ishg_EOM_AC_insamps=[0]
            sec_proc_fill_started = False # init
            prim_process_str = 'pr.' if self.primary_worker else 'secondary ishg'
            real_time_disp = self.real_time_disp
            str_msg = 'via go_galvo'
            
            print('\n fill Proc galvos started %s wrkr ID%d' % (prim_process_str, self.pid))
            
            while True: # index_img_current <= self.nb_img_max: 
                            
                if test_if_poison_pill: # # stop or kill
                    test_if_poison_pill = 0 # re-init
                    if paquetFromAcq[0] == -1: # # poison-pill
                        print('Poison-pill detected in fill_process %s (prim %r)' % (prim_process_str, self.primary_worker))
                        # # the poison-pill will come from primary Worker to sec.
                        if self.primary_worker: # standard
                            # # print('paquet_2disp', 'paquet_2disp' in locals() ,len(paquet_2disp) > 0 , 'ind_disp' in locals() , ind_disp>1)
                            if ('paquet_2disp' in locals() and len(paquet_2disp) > 0 and 'ind_disp' in locals() and ind_disp>1):
                                ind_disp = self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_2disp, str_msg+'last for now', ishg_EOM_AC_insamps[0], sat_value_list, data_list, arr, array_ishg_4d) # # send_img_to_gui is in  go_scan_galvos.py
                            self.new_img_flag_queue.put('terminate') # close the qthread
                            if sec_proc_fill_started: # # second process ishg is there, filling its 4D array !
                                self.queue_prim2sec_ishg.put([-1]) # communicate the poison-pill to sec. Worker if it is there
                        if (self.queue_fill_disp is not None and type(self.queue_fill_disp) != int): # #real_time_disp:    # disp only if nb buffer > 1
                            self.queue_fill_disp.put([-1]) # communicate the poison-pill to disp process
                        break # outside big while loop, end process
            
                    else: # just stop
                        print('Order to stop detected in fill_process %s' % prim_process_str)
                        if paquetFromAcq[0] == -2: # stop in-line
                            if self.primary_worker: # standard
                                if 'paquet_2disp' in locals():
                                    ind_disp = self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_2disp, str_msg+'last for now', ishg_EOM_AC_insamps[0], sat_value_list, data_list, arr, array_ishg_4d) # # send_img_to_gui is in  go_scan_galvos.py
                                else: print('pb (in fill) for retrieving paquet_2disp !!')
                                # # print('l77 pack', prim_process_str, len(paquet_2disp), len(paquet_2disp[0])) # ,  paquet_2disp, len(paquet_2disp[0][3]
                            else: # sec. worker
                                self.queue_acq_fill.put([ind_max+1, array_ishg_4d]) # # try to save it, send to primary worker
                        # # the Stop will come from primary Worker to sec. wrkr
                        if (self.primary_worker and real_time_disp):    # disp only if nb buffer > 1
                            self.queue_fill_disp.put([0]) # communicate the stop command to disp process
                        if (self.primary_worker and sec_proc_fill_started): # # second process ishg is there, filling its 4D array !
                            self.queue_prim2sec_ishg.put([0]) # communicate the stop to sec. Worker if it is there
                        # will block after
                
                real_time_disp = self.real_time_disp
                arr_in_packet = None

                if self.primary_worker:
                    paquetFromAcq = self.queue_acq_fill.get() # blocks until receive something from acq.
                else:  # # sec. wrkr
                    paquetFromAcq = self.queue_prim2sec_ishg.get()
                
                if len(paquetFromAcq) == 1: # order 
                    test_if_poison_pill = 1
                    continue #rejects all the remaining statements in the current iteration of the loop and moves the control back to the top of the loop
                if (self.primary_worker and sec_proc_fill_started):   # # second process ishg is there, filling its 4D array !
                    self.queue_prim2sec_ishg.put(paquetFromAcq) # # communicate the packet to sec. worker
                     # # pipe_prim2sec is here sender_prim2sec_pipe
                    # # the sec. Process will start after if not yet, and will receive the packet directly
                 
                # # print('paquetFromAcq', paquetFromAcq)
                if (isinstance(paquetFromAcq[1], bool) and paquetFromAcq[1]): # new parameters (or first scan)
                    listParamScan = paquetFromAcq[0] # 
                    
                    pmt_channel_list = listParamScan[0]
                    nb_px_x =  listParamScan[1]
                    nb_px_y =  listParamScan[2]
                    unidirectional = listParamScan[3]
                    y_fast = listParamScan[4]
                    oversampling = listParamScan[5]
                    sample_rate = listParamScan[6] 
                   # see after
                    delete_px_fast_begin = listParamScan[9] 
                    delete_px_fast_end = listParamScan[10] 
                    delete_px_slow_begin = listParamScan[11] 
                    delete_px_slow_end = listParamScan[12] 
                    nb_bins_hist = listParamScan[13] 
                    clrmap_nb  = listParamScan[14] 
                    autoscalelive_plt = listParamScan[15]
                    [min_val_volt_list_corr, max_val_volt_list_corr, AI_bounds_list] = listParamScan[16] 
                    use_volt_not_raw = listParamScan[17] 
                    use_median = listParamScan[18] 
                    skip_behavior = listParamScan[19]
                    # # skip_behavior is [nb_skip,  pause_trigger_diggalvo,  callback_notmeasline, unirek_skip_half_of_lines]
                    nb_accum = listParamScan[20] 
                    [read_buffer_offset_direct, read_buffer_offset_reverse] = listParamScan[21] 
                    ishg_EOM_AC_insamps = listParamScan[22]
                    # # ishg_EOM_AC_insamps is [flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime] with the times in nb smps !!
                    
                    # # print('wlh', skip_behavior)
                    nb_pmt_channel = sum(pmt_channel_list)
                    unirek_skip_half_of_lines = False # default
                    pause_trigger_diggalvo = False
                    if skip_behavior[1] is not None:
                        pause_trigger_diggalvo = skip_behavior[1]
                        if not pause_trigger_diggalvo: skip_behavior[2] = None # # no paus trigger dig. galvos
                        
                    get_dur_lines = (skip_behavior[2]==0 and ((self.scan_mode == 1 and pause_trigger_diggalvo) or (self.scan_mode == -2)))
                    
                    missing_samps_atendnotright_bidirek = False if get_dur_lines else True # 3 for dig galvos, missing samples seem to be at end for dir, and beginining for reverse
                    # True: keep missing samples at the end of the line, even in reverse. Contrary is to keep them always on the right side.

                    if self.scan_mode == -2: # anlg new galvos
                        unirek_skip_half_of_lines = skip_behavior[-1] # last el
                        nb_it_theo = listParamScan[8]/listParamScan[7]  # # nblooplines/nb_lines_inpacket
                        nb_skip = skip_behavior[0]
                    else:
                        nb_skip = skip_behavior[0]
                        maxPx_paquet = listParamScan[7] 
                        total_px = listParamScan[8]
                        nb_it_theo = total_px/maxPx_paquet
                    
                    if oversampling >= 2**31/self.new_max_disp: # too much for int32 image (if dwell time is > 100ms at max rate
                        avg_px = 1
                    else: avg_px = param_ini.avg_px
                        
                    # (min(AI_bounds_list[k][1], max_val_volt_list_corr[k]) - max(AI_bounds_list[k][0], min_val_volt_list_corr[k]))/(AI_bounds_list[k][1] - AI_bounds_list[k][0])*self.new_max_disp
                    if avg_px==0: # 1 for averaging (range expanded in uint16) 
# 2 for averaging (range in phys. limit int16) 
# 0 for sum (int32)
                        max_value_pixel = self.new_max_disp # useless
                    elif avg_px==1:
                        max_value_pixel = 2**16-1
                    elif avg_px==2:
                        max_value_pixel = min(2**16-1, self.new_max_disp)
                        
                    if self.primary_worker:
                        # # TODO: sd
                        # max_val_volt_list_corr = [max_val_volt_list_corr[0], max_val_volt_list_corr[0], 0,0]  # !!!!
                        # min_val_volt_list_corr = [min_val_volt_list_corr[0], min_val_volt_list_corr[0], 0,0] # !!!
                        sat_value_list = []; k=k0=0
                        while k < len(pmt_channel_list):
                            if pmt_channel_list[k]>0:
                                sat_value_list.append(oversampling*(max_val_volt_list_corr[k0] - min_val_volt_list_corr[k0]) if avg_px==0 else max_value_pixel)
                                k0+=1
                            else: sat_value_list.append(0)
                            k+=1
                        # sat_value_list = [oversampling*(max_val_volt_list_corr[k] - min_val_volt_list_corr[k]) if avg_px==0 else max_value_pixel for k in range(len(pmt_channel_list)) if pmt_channel_list[k]>0 ]
                        # # print('sat_value_list11 !!!', sat_value_list, pmt_channel_list, max_val_volt_list_corr, min_val_volt_list_corr)
                    
                    if (self.scan_mode != -1 and not unidirectional and nb_skip>0 and read_buffer_offset_direct==0 and read_buffer_offset_reverse==0 and not pause_trigger_diggalvo):
                        read_buffer_offset_direct = nb_skip
                            
                    # # print('nb_skip', nb_skip)
                    nb_it_full = int(nb_it_theo) # floor
                    
                    ind_max = nb_it_full # last buffer is full size                        
                    if (nb_it_full != nb_it_theo and not(self.scan_mode == -2 and listParamScan[8]-int(listParamScan[8]/listParamScan[7])*listParamScan[7] == 1)): # full and a last one not full    
                    # # for anlg galvo, last buffer must not contain only one line
                        ind_max += 1
            
                    if ind_max <= 1: real_time_disp = False # no disp if one buffer

                    verbose = 0 # print or not
                    
                    if y_fast:
                        nbPX_fast = nb_px_y
                        nbPX_slow = nb_px_x
                    else:
                        nbPX_fast = nb_px_x
                        nbPX_slow = nb_px_y 
                    
                    fake_size_fast = nbPX_fast + delete_px_fast_begin + delete_px_fast_end # to consider the deleted pixels at the begin and the end for the FAST dir
                    fake_size_slow = nbPX_slow + delete_px_slow_begin + delete_px_slow_end # to consider the deleted pixels at the begin and the end for the SLOW dir
                    if unirek_skip_half_of_lines: # # read and garbage the flyback, so the number of lines to read is x2
                        nb_lines_treat = fake_size_slow*2
                    else:
                        nb_lines_treat = fake_size_slow
                    
                    # because 2^E <= abs(X) < 2^(E+1) with E = 15 (worst case, meaning X is between 32000 and sat)
                    # if you use float16, precision is 2**(15-10) = 2**(5)=32 --> not good
                    # if you use float32, precision is 2**(15-23) = 2**(-8) = 4e-3 --> fair
                    # precision in practical at (1e-2)e4 = 1e2 --> limit !!!
                    # if you use float (float64), precision is 2**(15-52) = 7e-12 (highest value can be 2**16-1) --> too precis
                    # a float64 put into a float32 array is just rounded
                    # size imposed by readAnalogF64 !!
                    
                    if self.primary_worker: # standard
                        param_to_disp = [pmt_channel_list , ind_max, nb_bins_hist , clrmap_nb, autoscalelive_plt, fake_size_fast, fake_size_slow, sat_value_list ]
                    
                    else: # # ishg sec. proc
                        param_to_disp = None
                    # # a second. worker shoul have self.real_time_disp = False
                    
                    range_forloop_pmt = numpy.arange(nb_pmt_channel)
                    if (nb_pmt_channel == 0 or (all(x==min_val_volt_list_corr[0] for x in min_val_volt_list_corr))): # all is the same, else # some min are different
                        min_val_volt_list_corr = [min_val_volt_list_corr[0]]
                        if use_volt_not_raw:
                            if (nb_pmt_channel == 0 or (all(x==max_val_volt_list_corr[0] for x in max_val_volt_list_corr))): # all is the same, else # some min are different 
                                max_val_volt_list_corr = [max_val_volt_list_corr[0]] 
                                range_forloop_pmt = [range_forloop_pmt]
                        else: # min is sufficient
                        
                            range_forloop_pmt = [range_forloop_pmt]  # everything will be treated at the same time
                    
                    # if (ishg_EOM_AC_insamps[0]  in (1, 11) and len(range_forloop_pmt) == 1 and nb_pmt_channel > 1): range_forloop_pmt = range_forloop_pmt[0]
                    
                    treat_ishg_here = (ishg_EOM_AC_insamps[0]  in (1, 11)  and ((not self.primary_worker) or (self.primary_worker and not self.sec_proc_forishgfill))) # # if fill array ishg here, AND {second. Worker or {prim wrkr and not start sec. wrkr}}     
                    
                    if ishg_EOM_AC_insamps[0] in (1, 11): # flag ishg acq. treat
                        from modules import jobs_scripts
                        # # ovrsmp_ph = ishg_EOM_AC_insamps[-1][1]
                        # # oversampling == ovrsmp_ph: # # scan was well-defined or imposed to suit ramp time

                        max_j_ishg = jobs_scripts.ishgEOM_defnbcol_func(fake_size_fast, oversampling, ishg_EOM_AC_insamps[-1][1])  # # it a func !! see EOMph_nb_samps_phpixel_meth
                        # # oversampling != ovrsmp_ph :  scan does not suit ramp time ! array3d will stay same, but max_j_ishg will be different (smaller array in fast)
                        if (self.primary_worker and self.sec_proc_forishgfill and not sec_proc_fill_started): # # start a second Process for filling or ishg array
                        # # no need to start it if just fill a list of raw data
                            self.new_img_flag_queue.put('2ndprocON') # # tell go_scan_galvo to start the 2nd process
                            sec_proc_fill_started = True
                            print('Primary ordered start of secondary wrkr')
                            self.queue_prim2sec_ishg.put(paquetFromAcq) # # starter pack
                             # # pipe_prim2sec is here sender_prim2sec_pipe
                                                        
                        # # if ishg_EOM_AC_insamps[0] in (1, 11):
                            
                        sz_arr_ishg_x = max_j_ishg if not y_fast else nb_px_x # # oversampling/oversmp_ph where oversmp_ph = ramptime_samps + deadtime_beg_samps + deadtime_end_samps
                        sz_arr_ishg_y = max_j_ishg if y_fast else nb_px_y  # # oversampling/oversmp_ph where oversmp_ph = ramptime_samps + deadtime_beg_samps + deadtime_end_samps
                        # # print('size_x' , max_j_ishg) 
                        str1 = '\n flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime' 
                            
                    else: # # no ISHG
                        jobs_scripts = None
                        array_ishg_4d = array_ishg_3d_diff = None # 3 redef !! important !!
                        # sec_proc_fill_started = False # re-init
                        str1 = ' flag, ramp time sec00, step theo(deg), Vpi, VMax, nb_samps_perphsft, task_mtrtrigger_out, offset_samps, flag_impose_ramptime_as_exptime'
                        # raise Exception('min values of different PMTs must be the same, otherwise correct the filling of array with `for` loops to take into account different values !')
                    if (self.primary_worker and ishg_EOM_AC_insamps[0]):
                        print('ishg_EOM_AC_insamps', ishg_EOM_AC_insamps, str1, 'sec+prim_proc', self.sec_proc_forishgfill)
                                                
                if not 'nb_pmt_channel' in locals(): # wrong def
                    print('waiting for def of params in packet')
                    continue
                
                if self.scan_mode == 1: # digital galvo scan
                    lower_lim = 0
                    pos_px = 0
                    ind_data_total = 0
                    method_fast = 1 # 12 # length may vary
                elif self.scan_mode == -1: # static acq
                    method_fast = 1 # full lines that we know the length
                    skip_behavior[2] = None
                elif self.scan_mode == -2: # anlg galvo scan
                    method_fast = 1 # length may vary
                    nb_rows = 1
                # # speed of filling : 1 = fast fast (line by line, index shifting)
                # # 12 = fast slow (line by line, array shaping), for time_line_reading (galvos)
                # # 21 = slow fast (px by px, index shifting), for time_line_reading (galvos)
                # # 22 or 0 = slow slow (px by px, array shaping), for galvos or stage
                
                array_3d = numpy.zeros(shape=(nb_pmt_channel, nb_px_y, nb_px_x), dtype=param_ini.precision_float_numpy) if self.primary_worker else None # sec. wrkr
                # px to delete will be deleted in the end        
                # redifine it to have black pixel where no acquisition
                
                # # if ishg_EOM_AC_insamps[0]: method_fast = 1 # temporary !!!
                max_j_list = [fake_size_fast]
                
                if treat_ishg_here:  # flag for EOM iSHG, fill array in here
                # # even if there is a sec. wrkr for ishg, define the array to display it empty
                    array_ishg_4d = numpy.zeros(shape=(nb_pmt_channel, sz_arr_ishg_y, sz_arr_ishg_x, ishg_EOM_AC_insamps[2]), dtype= param_ini.precision_float_ishg)  # # if don't fill here, it will display a black array until the receive from sec. worker
                    
                    max_j_list.append(max_j_ishg)
                                        
                if self.primary_worker: # # not sec. wrkr

                    data_list = [] if ishg_EOM_AC_insamps[0] in (2, 11) else None # special for saving whole array
                    if (ishg_EOM_AC_insamps[0] in (1, 11) and self.sec_proc_forishgfill):  # # there is a sec. process that will eventually replace it, and array must be plotted here
                        array_ishg_3d_diff = numpy.empty(shape=(nb_pmt_channel, sz_arr_ishg_y, sz_arr_ishg_x), dtype= param_ini.precision_float_ishg) # # random numbers
                        # # print('size_xx' , sz_arr_ishg_x) 
                
                end_i = 0
                
                # # print('rrr', (self.scan_mode == -1 or (self.scan_mode == -2 and skip_behavior[2] == 0)), pause_trigger_diggalvo, 1, self.scan_mode, expand_data_to_fit_line, missing_samps_atendnotright_bidirek, unirek_skip_half_of_lines, nb_skip,)
                # # print('rrr', (avg_px, fake_size_fast, nb_lines_treat, oversampling, 'data', 'array_3d', 'array_ishg_4d', 'numpy', max_val_volt_list_corr, 'st_i', 'end_i', max_j_list, verbose, nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse , min_val_volt_list_corr, use_volt_not_raw, use_median, range_forloop_pmt, pause_trigger_diggalvo, 'nb_el_line_list', self.scan_mode, expand_data_to_fit_line, missing_samps_atendnotright_bidirek, 'math', unirek_skip_half_of_lines, nb_skip, ishg_EOM_AC_insamps))

                ## filling of the array(s)
                
                start_time = time.time()
                    
                for ind_disp in range(1, ind_max+1): # goes from 1 to ind_max
                    # # print('max_j_list00', max_j_list)

                    if self.primary_worker:
                        if (pause_trigger_diggalvo and not get_dur_lines): print('Fill waiting for packet from acq...', ind_disp, ind_max)
                        paquetFromAcq = self.queue_acq_fill.get() # blocks until receive something from acq Wrkr
                    else:  # # sec. wrkr
                        paquetFromAcq = self.queue_prim2sec_ishg.get()
                    
                    # print('walla fillarr', len(paquetFromAcq), ind_max)
                    if len(paquetFromAcq) == 1: # data = 0 or -1, not an array
                        if type(paquetFromAcq[0]) == int:
                            test_if_poison_pill = 1
                            break # outside this loop for
                        else: print('paquetFromAcq??', paquetFromAcq)
                    else:
                        # # paquetFromAcq --> [data, meas_line_time_list] ; meas_line_time_list can be empty
                        if (self.primary_worker and sec_proc_fill_started): # # second process ishg is there, filling its 4D array !
                            self.queue_prim2sec_ishg.put(paquetFromAcq) # # communicate the packet to sec. wrkr
                            # # pipe_prim2sec is here sender_prim2sec_pipe
                        data_temp = paquetFromAcq[0]
                        
                        if data_temp.size == 0: print('array with size 0 !!'); continue
                        
                        if (self.primary_worker and sec_proc_fill_started and real_time_disp): # # second process ishg is there, filling its 4D array !
                            ind_queue = 0
                            
                            if not self.queue_sec2prim_fill.empty():
                                qsz = self.queue_sec2prim_fill.qsize()
                                while ind_queue < qsz: # # maybe it has some msg late, so it will erase the oldest ones
                                    try:
                                        packet_sec = self.queue_sec2prim_fill.get_nowait() # there is one el. for sure
                                        ind_queue += 1
                                    except queueEmpty: # can happen
                                        pass
                                if ind_queue>0:  # one el. read
                                    ind_disp_sec = packet_sec[0] # # index
                                        # # array_ishg_4d = packet_sec[1] # do NOT assign it here, because it won't no longer be None for primary
                                    arr_in_packet = packet_sec[1] # # arr_ishg_3d_diff
                                # # # print('l272', packet_sec)
                                                
                        if get_dur_lines:
                            nb_el_line_list_temp =  numpy.array(paquetFromAcq[1])*sample_rate # number of samples per line
                            # # print(len(nb_el_line_list_temp))
                            # # if ind_disp > ind_max-2:
                            # #     print(paquetFromAcq[1])

                            if ind_disp == 1: # # frst row
                                data = data_temp   
                                nb_el_line_list = nb_el_line_list_temp
                                
                            else: # ind_disp > 1
                                data = numpy.concatenate((data[:, ind_data_packet:], data_temp), axis=1) # warning is normal
                                if ct_i < len(nb_el_line_list): # previous line time array was not completely emptied
                                # # ct_i is defined when ind_disp == 1
                                    # # print(nb_el_line_list[ct_i:], nb_el_line_list_temp)
                                    nb_el_line_list = numpy.concatenate((nb_el_line_list[ct_i:], nb_el_line_list_temp))
                                else:
                                    nb_el_line_list = nb_el_line_list_temp
                            
                        else:
                            data = data_temp
                        if (ind_disp == 1 and self.primary_worker and ishg_EOM_AC_insamps[0] in (1, 11)): # # frst row
                            ttot_theo_ishg = (8.5/154/400/(80*400*31)*nbPX_slow*ishg_EOM_AC_insamps[2]*data.size) # # empirical
                            print('estimated fill ishg %.1f sec' % ttot_theo_ishg)
                      
                    if verbose:
                        print('Buffer fill # %d'%  ind_disp)
                    
                    if (self.scan_mode == -1 or (skip_behavior[2] is not None and skip_behavior[2]==1)):  # # static scan, OR anlg galvos callback OR dig. galvos callback
                        if self.scan_mode == -1: # # static acq, no callback
                            nb_rows = int(len(data[0])/oversampling/nbPX_fast) # int is equivalent to floor
                        elif data.ndim == 3: # # galvos with callback line-by-line, the lines being stored in the 3rd dimension
                            nb_rows = numpy.size(data,1) # # will treat that many rows at the same time !

                        if ind_disp > nb_it_full: # last it.
                            st_i = end_i
                            end_i = st_i + nb_rows
                            if end_i > nbPX_slow:
                                end_i = end_i-1
                                
                        else: # full it.
                            st_i = (ind_disp-1)*nb_rows
                            end_i = (ind_disp)*nb_rows
                        
                        # # print(st_i, end_i, len(data[0]), nb_rows*oversampling*max_j_list[0])
                        # # print('arr',  array_ishg_4d, prim_process_str)
                        array_fill_loops3.fill_array_scan_good2(avg_px, fake_size_fast, nb_lines_treat, oversampling, data, array_3d, array_ishg_4d, numpy, max_val_volt_list_corr, st_i, end_i, max_j_list, verbose, nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse, min_val_volt_list_corr, use_volt_not_raw, use_median, range_forloop_pmt, None, self.scan_mode, expand_data_to_fit_line, missing_samps_atendnotright_bidirek, skip_behavior, ishg_EOM_AC_insamps) # last is read_buffer_offset_direct, read_buffer_offset_reverse (used for stage scan)
                        
                    elif (self.scan_mode == 1 and not pause_trigger_diggalvo): # CLASSIC OLD digital galvo scan
                    
                        # # print('classic digital scan ...')
                    
                        pos_px = pos_px + lower_lim
                        upper_limit = total_px - pos_px # varies during the scan
                        lower_lim = min(maxPx_paquet, upper_limit) # = 16500 or less (e.g. 12298)
                        # # number_of_samples = round(oversampling*lower_lim) # 1320000 for 1st, 12298*80=983840 for last one
                        
                        ind_data_total = array_fill_loops3.fill_array_scan_digital2(avg_px, fake_size_fast, fake_size_slow, unidirectional, round(oversampling), data, array_3d, numpy, max_val_volt_list_corr, ind_data_total, verbose, max_value_pixel, nb_pmt_channel, y_fast, min_val_volt_list_corr, use_volt_not_raw, use_median, range_forloop_pmt, lower_lim, nb_skip)
                                                
                    else: # galvo scan with time line reading (can be DIGITAL)
                    
                        if len(nb_el_line_list) > 0:
                           
                            iter = len(nb_el_line_list)
                            st_i = end_i 
                            end_i = min(st_i + iter, numpy.size(array_3d, 1)) # # nb lines
                            # print(iter)
                            # if ind_disp > 1:
                            #     ind_data_packet = 0
                            # else:
                            # # ind_data_packet = int(0 + nb_skip)
                        
                            ind_data_packet, ct_i = array_fill_loops3.fill_array_scan_good2(avg_px, fake_size_fast, nb_lines_treat, oversampling, data, array_3d, array_ishg_4d, numpy, max_val_volt_list_corr, st_i, end_i, max_j_list, verbose, nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse , min_val_volt_list_corr, use_volt_not_raw, use_median, range_forloop_pmt, nb_el_line_list, self.scan_mode, expand_data_to_fit_line, missing_samps_atendnotright_bidirek, skip_behavior, ishg_EOM_AC_insamps) # last is read_buffer_offset_direct, read_buffer_offset_reverse (used for stage scan)
                            # a numpy array is passed by reference
                            if ct_i < len(nb_el_line_list): # not full
                                end_i-= len(nb_el_line_list) - ct_i
                        else:
                            print('line not finished for this packet')
                    
                    if (self.primary_worker and ishg_EOM_AC_insamps[0] in (2, 11)): # special for saving whole array
                        if not get_dur_lines: # normal
                            data_list.append(paquetFromAcq[0]) # if ishg_EOM_AC_insamps[0] != 1
                        else: # # read durations
                            data_list.append(paquetFromAcq) # # + duration lines
                    
                    if (ind_disp == ind_max or (real_time_disp and not(ind_disp%nb_accum))): # disp only if nb buffer > 1 
                    # # last display or all if real-time disp.  
                        
                        if ishg_EOM_AC_insamps[0] in (1, 11):  # flag for EOM iSHG fill array in here     
                            if array_ishg_4d is not None:  # # defined here, prim that does all or sec.
                            # # packet_sec[1] is array_ishg_4d, but if received from desc. it has to be kept in packet not to be treated in primary
                                array_ishg_3d_diff = jobs_scripts.EOMph_3d_diff_meth(ishg_EOM_AC_insamps, array_ishg_4d)
                            else: # # result of sec. wrkr
                                if arr_in_packet is not None: # # otherwise array_ishg_3d_diff will stays zeros
                                    array_ishg_3d_diff = arr_in_packet 
                        if self.primary_worker:  # # standard
                            if ishg_EOM_AC_insamps[0] in (1, 11):  # flag for EOM iSHG fill array in here  
                                paquet_2disp = [[array_3d, array_ishg_3d_diff, None], param_to_disp]              
                                # # ishg_EOM_AC_insamps : [flag, time, nb_p-s, Vpi, Vmax] 
                                # # so you don't send a useless big array to Disp   
                                # # print('in fill pr sz_y , sz_x', array_ishg_3d_diff.shape[1] , array_ishg_3d_diff.shape[2], arr_in_packet is not None)
                            elif ishg_EOM_AC_insamps[0] == 2: # special for saving whole array
                                paquet_2disp = [[array_3d, None], param_to_disp] 
                            else: # normal mode
                                paquet_2disp = [array_3d, param_to_disp] # DON`T use dstack, it transposes !
                        else: # # sec. worker
                            paquet_2disp = [ind_disp, array_ishg_3d_diff] # # frst arg is to specify the ind
                            # # print('in fill sec sz_y , sz_x', array_ishg_3d_diff.shape[1] , array_ishg_3d_diff.shape[2], arr_in_packet is not None)
                        if (real_time_disp and (self.primary_worker or ishg_EOM_AC_insamps[0] in (1, 11))): # # otherwise only at the end
                            queue_send = self.queue_fill_disp if self.primary_worker else self.queue_acq_fill
                            if not queue_send.empty(): # # previous not consumed
                                try:
                                    queue_send.get_nowait() # # empty the queue (overwrite)
                                except queueEmpty: # can happen
                                    pass
                            # # print('l498 pack',  len(paquet_2disp), prim_process_str, ind_disp, ind_max)
                            
                            queue_send.put(paquet_2disp) # send the full array to disp OR primary fill
                            # # queue_fill_disp.put
                ttot = (time.time() - start_time)            
                print('--- Fill time = %.1f sec %s ---' % (ttot, prim_process_str)) 
                    
                if not test_if_poison_pill: # no stop received, normal, end
                        
                    if self.primary_worker:
                        if (sec_proc_fill_started and ishg_EOM_AC_insamps[0]  in (1, 11)):  # # keep BOTH, because sec_proc might be kept for after but not needed now
                        # # second process ishg is there, filling its 4D array !                           
                            tout = min(120, max(3, ttot_theo_ishg - ttot + 3)) # # min 3 sec and max 120sec of waiting
                            print('getting final result of ishg sec. wrkr during %.1f sec...' % tout)
                            # # print(data.shape, ishg_EOM_AC_insamps[2])
                            while ind_disp_sec < ind_max+1: # # sec. worker did not reach the final line yet
                                try:
                                    packet_sec = self.queue_sec2prim_fill.get(timeout = tout) # blocking during 3sec + time  theo (empirical)
                                    
                                except queueEmpty: # timed out, sec. wrkr in trouble
                                    packet_sec = [None, None]
                                    break # out of loop
                                ind_disp_sec = packet_sec[0]
                                if ind_disp_sec < ind_max+1:
                                    arr_in_packet = packet_sec[1]
                                    if real_time_disp:
                                        self.queue_fill_disp.put([[array_3d, arr_in_packet, None], param_to_disp]) # # queue_fill_disp.put
                            arr = packet_sec[1] # # array_ishg_4d
                            
                            # never defined diff 3D, if no realtimedisp and sec. wrkr ishg
                            
                            paquet_2disp[0][1] = jobs_scripts.EOMph_3d_diff_meth(ishg_EOM_AC_insamps, arr) if (arr_in_packet is None and arr is not None) else arr_in_packet # # diff3Dishg
                        #else: # # no sec. wrkr
                        # # arr = array_ishg_4d
                        # # print('arrfill2!!', numpy.amin(arr), numpy.amin(array_3d))
                        # # !! data_list is a list of list [[data, dur]1, [data, dur]2, ...]
                        # # ishg_EOM_AC_insamps[0] == 1: # flag for EOM iSHG 
                        # complete_send_paquet
                        if not 'paquet_2disp' in locals(): paquet_2disp = None
                        ind_disp = self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_2disp, str_msg, ishg_EOM_AC_insamps[0], sat_value_list, data_list, arr, array_ishg_4d)
                            # # print('l400 pack',  paquet_2disp, prim_process_str)
                    # # print('l210', time.time())
                    else: # sec. worker, and array not sent by real-time disp.
                        paquet_2disp = [ind_max+1, array_ishg_4d] # in pratice here arr is never paquet_2disp, because no need of sec. worker for this
                        self.queue_acq_fill.put(paquet_2disp) # # queue_acq_fill is actually queue_acq_fill_second
                        # # print('l403 pack',  paquet_2disp, prim_process_str)
        
        except:
            import traceback
            print('-- Errors in ', prim_process_str)
            traceback.print_exc()
            if self.primary_worker: # standard
                self.new_img_flag_queue.put('killAcq') # tell the Thread to close the Process Acq.
            queue_com = self.queue_fill_disp if self.primary_worker else self.queue_acq_fill  # # second. worker # # or sec. wrkr, is actually queue_sec2prim_fill
            if (queue_com is not None and type(queue_com) != int):    # disp only if nb buffer > 1 
                # # self.primary_worker: # standard
                queue_com.put([-1]) # communicate the poison-pill to disp process, or to primary worker if secondary
                if (self.primary_worker and sec_proc_fill_started): # # second process ishg is there, filling its 4D array !
                    self.queue_prim2sec_ishg.put([-1]) # communicate the poison-pill to sec. Worker if it is there. Pipe is here sender_prim2sec_pipe
            # try to display the uncomplete image on the GUI
            if 'paquet_2disp' in locals():
                if self.primary_worker: # standard
                    ind_disp = self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_2disp, str_msg+', incomplete!', ishg_EOM_AC_insamps[0], sat_value_list, data_list, arr, array_ishg_4d) # # send_img_to_gui is in  go_scan_galvos.py
                else: # # second. worker
                    self.queue_acq_fill.put(paquet_2disp) # # send the packet to primary Worker, to try to save it
                    # # is actually queue_sec2prim_fill
                # # print('l423 pack',  paquet_2disp, prim_process_str)
            if self.primary_worker: # standard
                self.new_img_flag_queue.put('terminate') # close the qthread by sending to go_scan
                try:
                    self.queue_acq_fill.get(block=True, timeout=3) # allow the Acq. (or the main Fill for sec.) to send its last paquet
                except queueEmpty:
                    pass
            else: # # sec. wrkr
                try:
                    self.queue_prim2sec_ishg.get(block=True, timeout=3)
                except queueEmpty:
                    pass