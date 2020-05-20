# -*- coding: utf-8 -*-
"""
Created on Mon Sept 19 16:35:13 2016

@author: Maxime PINSARD
"""

import multiprocessing


class fill_disp_array(multiprocessing.Process):

    """Process acq"""

    def __init__(self, send_img_to_gui, queue_conn_acq_fill, new_max_disp, queue_list_arrays, new_img_flag_queue, emergency_ToMove_queue, queue_sec2prim_fill, queue_prim2sec_ishg, queue_fill_disp, real_time_disp, primary_worker):

        multiprocessing.Process.__init__(self)

        self.queue_conn_acq_fill = queue_conn_acq_fill
 
        self.new_max_disp = new_max_disp
        self.queue_list_arrays = queue_list_arrays; self.new_img_flag_queue = new_img_flag_queue
        self.emergency_ToMove_queue = emergency_ToMove_queue
        self.primary_worker = primary_worker
        self.queue_prim2sec_ishg = queue_prim2sec_ishg
        self.queue_sec2prim_fill = queue_sec2prim_fill
        self.send_img_to_gui = send_img_to_gui # # send_img_to_gui is in  go_scan_galvos.py
        # # self.queueEmpty = queueEmpty
        self.queue_fill_disp = queue_fill_disp
        self.real_time_disp = real_time_disp
        
    def run(self):
        prim_process_str = 'pr.' if self.primary_worker else 'secondary ishg'
        print('\n fill Proc stage started %s wrkr ID%d' % (prim_process_str, self.pid))
        
        def paquet_tosendfunc(array_3d,  array_ishg_3d_diff, array_ishg_4d, sat_value_list, delete_px_X_begin, delete_px_Y_begin, delete_px_X_end, delete_px_Y_end, ishg_EOM_AC_insamps, primary_worker, ind_disp_sec, ind_max, queue_sec2prim_fill, queue_conn_acq_fill, queue_list_arrays, packet_sec, queueEmpty, real_time_disp, pmt_channel_list, nb_bins_hist, numpy, min_disp_perc, max_disp_perc, fake_size_fast, fake_size_slow, arr_in_packet, data_list, ttot_theo_ishg, time, st, no_error, autoscalelive_plt, clrmap_nb, jobs_scripts):
            
            ttot = time.time()-st
            if primary_worker:
                paquet_tosend = [array_3d[:, delete_px_Y_begin:numpy.size(array_3d, 1)-delete_px_Y_end,delete_px_X_begin:numpy.size(array_3d, 2)-delete_px_X_end], sat_value_list] # last el for case of galvos scan
                if ishg_EOM_AC_insamps[0] in (1, 11): # flag for EOM iSHG
                    paquet_tosend = [[paquet_tosend[0], array_ishg_3d_diff, array_ishg_4d], sat_value_list] # last el for case of galvos scan
                elif ishg_EOM_AC_insamps[0] == 2: # special for saving whole array
                    paquet_tosend = [[paquet_tosend[0], data_list], sat_value_list]
                # # print(array_3d[0,:,size_x-1])
                # # if ishg_EOM_AC_insamps[0] == 1:  # flag for EOM iSHG 
                if queue_sec2prim_fill is not None: # # second process ishg is there, filling its 4D array !
                    tout = min(120, max(3, ttot_theo_ishg - ttot + 3)) # # min 3 sec and max 120sec of waiting
                    print('getting final result of ishg sec. wrkr during %.1f sec...' % tout)
                    # # print(data.shape, ishg_EOM_AC_insamps[2])
                    while ind_disp_sec < ind_max+1: # # sec. worker did not reach the final line yet
                        try:
                            packet_sec = queue_sec2prim_fill.get(timeout = tout) # blocking during 3sec + time  theo (empirical)
                            
                        except queueEmpty: # timed out, sec. wrkr in trouble
                            packet_sec = [None, None]
                            break # out of loop
                        ind_disp_sec = packet_sec[0]
                        if ind_disp_sec < ind_max+1:
                            arr_in_packet = packet_sec[1]
                            if real_time_disp:
                                # # fig1, fig2, ax_list, ax_h_list, img_grey_list, cb_list = plot_fast_script2_mp.plot_fast_func(plt, array_3d, array_ishg_3d_diff, pmt_channel_list, ind_disp_line, ind_max, nb_bins_hist, fig1, ax_list, img_grey_list, cb_list, cmap_str, fig2, ax_h_list, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, size_x, size_y, sat_value_list, autoscalelive_plt)
                                self.queue_fill_disp.put([[array_3d, arr_in_packet, None], [pmt_channel_list , fake_size_slow, nb_bins_hist , clrmap_nb, autoscalelive_plt, fake_size_fast, fake_size_slow, sat_value_list ]])
                    arr = packet_sec[1] # # array_ishg_4d
                    
                    if no_error:
                        # never defined diff 3D, if no realtimedisp and sec. wrkr ishg
                        paquet_tosend[0][1] = jobs_scripts.EOMph_3d_diff_meth(ishg_EOM_AC_insamps, arr) if (arr_in_packet is None and arr is not None) else arr_in_packet # # diff3Dishg
                else: # # no sec. wrkr
                    arr = data_list if ishg_EOM_AC_insamps[0] == 2 else array_ishg_4d # # ishg_EOM_AC_insamps[0] == 2: # special for saving whole array
                # # arr = array_ishg_4d
                # # ishg_EOM_AC_insamps[0] == 1: # flag for EOM iSHG 
                if ishg_EOM_AC_insamps[0]:
                    paquet_tosend[0][-1] = arr # # last el. of the list in the 0th position in the big list
                    if ishg_EOM_AC_insamps[0] == 11: # # data_list + treated
                        paquet_tosend[0].append(data_list)
                paquet_tosend[1] = sat_value_list # re-init ; it won't affect paquet_tosend
                queue_send = queue_list_arrays
                
            else: # sec. worker, and array not sent by real-time disp.
                paquet_tosend = [ind_max+1, array_ishg_4d] # in pratice here arr is never paquet_tosend, because no need of sec. worker for this
                queue_send = queue_conn_acq_fill # # is actually queue_sec2prim_fill
            
            return paquet_tosend, queue_send, ttot
        
        ## beg. of Proc
        try:
            from modules import param_ini, array_fill_loops3
            import numpy, time
            from queue import Empty as queueEmpty 
            
            paquet_tosend = ind_disp_sec = start_time = autoscalelive_plt = 0
            jobs_scripts = None
            verbose = 0
            # # method_fast = 0
            array_ishg_4d = array_3d = array_ishg_3d_diff = arr_in_packet = sat_value_list = packet_sec = data_list = ttot_theo_ishg = None
            expand_data_to_fit_line = False # if less data than px, change the oversampling to stretch the data to the array
            missing_samples_at_end_not_right = False # in stage scn, keep missing samples always on the right side.
            
            ## loop on buffers
            while True : 
                # # print('fill stage waiting packet ...', self.primary_worker)
                arr_in_packet = None # # reinit for display
                ## receive order + data
                if self.primary_worker:
                    paquet = self.queue_conn_acq_fill.get() # blocking, receive data from acq process by Pipe
                else:  # # sec. wrkr
                    paquet = self.queue_prim2sec_ishg.get()
                
                if len(paquet) == 2: # no stop command
                
                    if (self.primary_worker and self.queue_prim2sec_ishg is not None):   # # second process ishg is there, filling its 4D array !
                        self.queue_prim2sec_ishg.put(paquet) # # communicate the packet to sec. worker
                
                    if len(paquet[1]) > 1: # 2 arrays with one containing new parameters
                        
                        # data = paquet
                        
                        # goes to second data is None in big loop
                        
                        # print('Received a line data to fill disp ')
                    
                    ## order to treat data
                    
                        # data = paquet[0]
                    
                        fake_size_fast = paquet[1][2-2]; fake_size_slow= paquet[1][3-2]; read_buffer_offset_direct = paquet[1][4-2]; read_buffer_offset_reverse = paquet[1][5-2]; unidirectional = paquet[1][6-2]; nb_bins_hist  = paquet[1][7-2]; pmt_channel_list = paquet[1][8-2]; y_fast = paquet[1][9-2]; delete_px_fast_begin = paquet[1][10-2];  delete_px_fast_end = paquet[1][11-2]; delete_px_slow_begin = paquet[1][12-2];  delete_px_slow_end = paquet[1][13-2]; real_time_disp = paquet[1][14-2]; oversampling = paquet[1][15-2]; [min_val_volt_list_corr, max_val_volt_list_corr, AI_bounds_list] = paquet[1][16-2];  use_volt_not_raw = paquet[1][18-3] ; use_median = paquet[1][19-3]; dirSlow = paquet[1][20-3] ; clrmap_nb = paquet[1][21-3];  autoscalelive_plt = paquet[1][22-3]; method_fast = paquet[1][23-3]; ishg_EOM_AC_insamps = paquet[1][24-3]
                        
                        nb_pmt_channel = sum(pmt_channel_list)
                        if fake_size_slow <= 1: real_time_disp = False # no disp if one buffer
                        
                        if self.primary_worker:
                            if (real_time_disp and not self.real_time_disp): print('ERR: you should reset the Process, as the disp Task is not started\n'); raise(RuntimeError)
                        # # else: real_time_disp = 0 # # real_time_disp is indicator of primary in sec. process !!!
                        
                        if oversampling >= 2**31/self.new_max_disp: # too much for int32 image (if dwell time is > 100ms at max rate
                            avg_px = 1
                        else: avg_px = param_ini.avg_px
                        # # print('In disp, offset_buffer_direct !!!!!!', read_buffer_offset_direct, ishg_EOM_AC_insamps[0]) 
                        if avg_px==0: # 1 for averaging (range expanded in uint16) 
    # 2 for averaging (range in phys. limit int16) 
    # 0 for sum (int32)
                            max_value_pixel = self.new_max_disp # useless
                        elif avg_px==1:
                            max_value_pixel = 2**16-1
                        elif avg_px==2:
                            max_value_pixel = min(2**16-1, self.new_max_disp)
                        if self.primary_worker:
                            sat_value_list = []; k=k0=0
                            while k < len(pmt_channel_list):
                                if pmt_channel_list[k]>0:
                                    sat_value_list.append(oversampling*(max_val_volt_list_corr[k0] - min_val_volt_list_corr[k0]) if avg_px==0 else max_value_pixel)
                                    k0+=1
                                else: sat_value_list.append(0)
                                k+=1
                            # # sat_value_list = [oversampling*(max_val_volt_list_corr[k] - min_val_volt_list_corr[k]) if avg_px==0 else max_value_pixel for k in range(len(max_val_volt_list_corr)) if pmt_channel_list[k]>0 ]
                        # size_fast is nb of px !
                        
                        # # print('fake_size_fast', fake_size_fast, 'fake_size_slow', fake_size_slow)
                        '''
                        fake_size are the sizes that contains pixels to remove at the beginning and the end
                        size are the sizes that do not contains pixels to remove
                        
                        pixels_to_remove are deleted only in the final display on the GUI, but not during the real-time display (that way you can see what you delete)
                        2 things different : read_buffer_offset are elements to delete because of the acceleration of the stage, and pixel_to_remove are chosen by user to remove the edges of the image (for example remaining acceleration, or bad first line or whatever)
                        '''
                        # # print('max_vel_fast is indeed (in disp)', max_vel_fast)
                        # time_by_px = pixel_size_fast/max_vel_fast # in s/pixel
                        # # # # # print('max_vel_fast = ', max_vel_fast)
                        # oversampling = time_by_px*self.sample_rate # in element acquired
                        # number_of_samples = round(oversampling*(fake_size_fast + read_buffer_offset_direct))
                    
                        if y_fast:
                            size_y = fake_size_fast # nb of px ! # px to delete will be deleted in the end
                            size_x = fake_size_slow # nb of px ! # px to delete will be deleted in the end
                            
                            delete_px_Y_begin = delete_px_fast_begin
                            delete_px_Y_end = delete_px_fast_end
                            delete_px_X_begin = delete_px_slow_begin
                            delete_px_X_end = delete_px_slow_end
                            
                        else:
                            size_x = fake_size_fast # px to delete will be deleted in the end
                            size_y = fake_size_slow # px to delete will be deleted in the end
                            
                            delete_px_X_begin = delete_px_fast_begin
                            delete_px_X_end = delete_px_fast_end
                            delete_px_Y_begin = delete_px_slow_begin
                            delete_px_Y_end = delete_px_slow_end
                        
                        treat_ishg_here = (ishg_EOM_AC_insamps[0]  in (1, 11) and ((not self.primary_worker)  or (self.primary_worker and self.queue_prim2sec_ishg is None))) # # if fill array ishg here, AND {second. Worker or {prim wrkr and not start
                        if ishg_EOM_AC_insamps[0] in (1, 11): # flag_impose_ramptime_as_exptime
                            from modules import jobs_scripts
                            # # ovrsmp_ph = ishg_EOM_AC_insamps[-1][1] 
                            # # oversampling == ovrsmp_ph: # # scan was well-defined or imposed to suit ramp time
                            # # oversampling != ovrsmp_ph :  scan does not suit ramp time ! array3d will stay same, but max_j_ishg will be different (smaller array in fast)
                            # # if ishg_EOM_AC_insamps[0] in (1, 11): # # put res. in array 4d
                                
                            sz_ishg = jobs_scripts.ishgEOM_defnbcol_func(fake_size_fast, oversampling, ishg_EOM_AC_insamps[-1][1]) # int(size_x*oversampling/(ishg_EOM_AC_insamps[1] + ishg_EOM_AC_insamps[-2][1] + ishg_EOM_AC_insamps[-2][2]))
                            
                            sz_arr_ishg_x = sz_ishg if not y_fast else size_x # if xfast
                            # # ishg_EOM_AC_insamps[1] is nb_samps_ramp00
                            sz_arr_ishg_y = sz_ishg if y_fast else size_y  
                            str1 = '\n flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime' 
                                                        
                        else: # # no ISHG
                            array_ishg_4d = array_ishg_3d_diff = None # 3 redef !! important !!
                            str1 = ' flag, ramp time sec00, step theo(deg), Vpi, VMax, nb_samps_perphsft, task_mtrtrigger_out, offset_samps, flag_impose_ramptime_as_exptime'
                            
                        if (self.primary_worker and ishg_EOM_AC_insamps[0]):
                            print('ishg_EOM_AC_insamps', ishg_EOM_AC_insamps, str1, 'sec+prim_proc', self.queue_prim2sec_ishg is not None)
                                
                        data = paquet[0] # no we consider only the data, no longer the parameters
                        
                        range_forloop_pmt = numpy.arange(nb_pmt_channel)
                        if (nb_pmt_channel == 0 or (all(x==min_val_volt_list_corr[0] for x in min_val_volt_list_corr))): # all is the same, else # some min are different
                            min_val_volt_list_corr = [min_val_volt_list_corr[0]]
                            if use_volt_not_raw:
                                if (nb_pmt_channel == 0 or (all(x==max_val_volt_list_corr[0] for x in max_val_volt_list_corr))): # all is the same, else # some min are different 
                                    max_val_volt_list_corr = [max_val_volt_list_corr[0]] 
                                    range_forloop_pmt = [range_forloop_pmt]
                            else: # min is sufficient
                            
                                range_forloop_pmt = [range_forloop_pmt]
                    
                    if not 'nb_pmt_channel' in locals(): # wrong def
                        print('waiting for def of params in packet')
                        continue
                        
                    array_3d = numpy.zeros(shape=(nb_pmt_channel, size_y, size_x), dtype= param_ini.precision_float_numpy) if self.primary_worker else None # sec. wrkr
                    # # px to delete will be deleted in the end
                    # if you use float (float64), precision is 2**(15-52) = 7e-12 (highest value can be 2**16-1) --> too precise
                    # if you use float16, precision is 2**(15-10) = 2e5 --> not good
                    # if you use float32, precision is 2**(15-23) = 2e-8 = 4e-3 --> precision in practical at (1e-2)e4 = 1e2 --> limit !!!
                    # # print('la', treat_ishg_here, self.primary_worker, ishg_EOM_AC_insamps[0], self.queue_prim2sec_ishg)
                    if treat_ishg_here:  # flag for EOM iSHG, fill array in here
                        array_ishg_4d = numpy.zeros(shape=(nb_pmt_channel, sz_arr_ishg_y, sz_arr_ishg_x, ishg_EOM_AC_insamps[2]), dtype= param_ini.precision_float_ishg)
                        max_j_list = [fake_size_fast, None] # None for now
                    elif self.primary_worker: # not sec. wrkr
                        max_j_list = [fake_size_fast]
                        if (ishg_EOM_AC_insamps[0]  in (1, 11) and self.queue_prim2sec_ishg is not None):  # # there is a sec. process that will eventually replace it, and array must be plotted here
                            array_ishg_3d_diff = numpy.empty(shape=(nb_pmt_channel, sz_arr_ishg_y, sz_arr_ishg_x), dtype= param_ini.precision_float_ishg) # # random numbers
                    if (self.primary_worker and ishg_EOM_AC_insamps[0] in (2, 11)): # special for saving whole array
                        data_list = []
                            
                    ## filling of the array(s)
                    start_time = time.time()
                    for k in range(0, fake_size_slow):
                        
                        if k > 0:
                            # for k = 0, it's performed before  
                            queue_get = self.queue_conn_acq_fill if self.primary_worker else self.queue_prim2sec_ishg  # # sec. wrkr

                            if (param_ini.stock_data_to_avoid_buff_corrupt and len(acc_list) > 0): paquet = acc_list[0]; del acc_list[0]
                            else:
                                paquet = queue_get.get() # blocking, receive data from acq process by Pipe
                            # # sz = queue_get.qsize()

                            if param_ini.stock_data_to_avoid_buff_corrupt:
                                sz = queue_get.qsize()

                                if sz > 0: # accumulation in buffer
                                    for ii in range(sz):
                                        try: arr1 = queue_get.get(timeout = 1) # # secs, need some time to extract packet from buffer !
                                        except queueEmpty: print('empty!', ii, sz); break # outside for 
                                        acc_list.append(arr1)
                            # # print('self.queue_conn_acq_fill',sz, len(acc_list))                          
                            
                            # if len(paquet[0]) > 1: print('self.queue_conn_acq_fill',paquet[0][:5]) #queue_get.qsize())

                            # # for the stop in-line
                            if len(paquet) == 1: # received  0 or -1 or -2, not an array ( in fact it can be only -2)
                                paquet_tosend, queue_send, t_tot = paquet_tosendfunc(array_3d,  array_ishg_3d_diff, array_ishg_4d, sat_value_list, delete_px_X_begin, delete_px_Y_begin, delete_px_X_end, delete_px_Y_end, ishg_EOM_AC_insamps, self.primary_worker, ind_disp_sec, fake_size_slow, self.queue_sec2prim_fill, self.queue_conn_acq_fill, self.queue_list_arrays, packet_sec, queueEmpty, real_time_disp, pmt_channel_list, nb_bins_hist, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, fake_size_fast, fake_size_slow, arr_in_packet, data_list, ttot_theo_ishg, time, start_time, True, autoscalelive_plt, clrmap_nb,  jobs_scripts)
                                break # outside this 'for' loop
                            else:
                                if (self.primary_worker and self.queue_prim2sec_ishg is not None): # # second process ishg is there, filling its 4D array !
                                    self.queue_prim2sec_ishg.put(paquet) # # communicate the packet to sec. wrkr
                                    # # pipe_prim2sec is here sender_prim2sec_pipe
                                data = paquet[0]
                        else: # # k = 0
                            acc_list = []; sz=0 # init
                            ttot_str = ''
                            if (self.primary_worker and ishg_EOM_AC_insamps[0]  in (1, 11)): # # frst row
                                ttot_theo_ishg = (8.5/154/400/(80*400*31)*fake_size_slow*ishg_EOM_AC_insamps[2]*data.size) # # empirical
                                ttot_str = '%.1f sec' % ttot_theo_ishg
                            print('estimated fill ishg %s' % ttot_str, 'unidirectional', unidirectional, 'method_fast', method_fast)
                        # # print('method_fast', method_fast)    
                        if (self.primary_worker and self.queue_prim2sec_ishg is not None and real_time_disp): # # second process ishg is there, filling its 4D array !
                            ind_queue = 0
                            # # print('l292',self.queue_sec2prim_fill.empty()) 
                            if not self.queue_sec2prim_fill.empty():
                                qsz = self.queue_sec2prim_fill.qsize()
                                
                                while ind_queue < qsz: # # maybe it has some msg late, so it will erase the oldest ones
                                    try:
                                        packet_sec = self.queue_sec2prim_fill.get_nowait() # there is one el. for sure
                                        ind_queue += 1
                                    except queueEmpty: pass # can happen
                                        
                                if ind_queue>0:  # one el. read
                                    ind_disp_sec = packet_sec[0] # # index
                                        # # array_ishg_4d = packet_sec[1] # do NOT assign it here, because it won't no longer be None for primary
                                    arr_in_packet = packet_sec[1] # # arr_ishg_3d_diff
                        
                        # if (size_data != len(data) and size_data!=0 and==1): # length of data has changed since last image
                        #     #print('change PMT in fill process')
                        #     nb_pmt_channel = round(len(data)/number_of_samples) # reset the good number of PMT (1 or 2)
                        # 
                        # size_data = len(data) # store the current length of data
                    
                        # # max_j = fake_size_fast-1
                        max_j_list[0] = min(int(numpy.floor(len(data[0])/oversampling)), fake_size_fast) # max_j
                        if treat_ishg_here: # flag_impose_ramptime_as_exptime
                            # # oversampling == ovrsmp_ph: # # scan was well-defined or imposed to suit ramp time
                           # # max_j_list[1] = jobs_scripts.ishgEOM_defnbcol_func(fake_size_fast, oversampling, ishg_EOM_AC_insamps[-1][1])  # # it a func !! see EOMph_nb_samps_phpixel_meth
                           max_j_list[1] = jobs_scripts.ishgEOM_defnbcol_func(max_j_list[0], oversampling, ishg_EOM_AC_insamps[-1][1])  # # it a func !! see EOMph_nb_samps_phpixel_meth
                           #  max_j_ishg 
                        if dirSlow == 1:
                            st_i = k; end_i = k+1
                        else: # reverse
                            st_i = fake_size_slow - 1 - k; end_i = fake_size_slow - k
                        
                        # # print('nb_pmt_channel\n', nb_pmt_channel, array_3d.shape, data.shape)
                        array_fill_loops3.fill_array_scan_good2(avg_px, fake_size_fast, fake_size_slow, oversampling, data, array_3d, array_ishg_4d, numpy, max_val_volt_list_corr, st_i, end_i, max_j_list, verbose, nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse, min_val_volt_list_corr, use_volt_not_raw, use_median, range_forloop_pmt, None, 0, expand_data_to_fit_line, missing_samples_at_end_not_right, None, ishg_EOM_AC_insamps)
                        # , read_duration_lines, nb_el_line_list, scan_mode, expand_data_to_fit_line, missing_samples_at_end_not_right
                        
                        # # print('l326', self.primary_worker, arr_in_packet is not None, array_ishg_4d is not None, self.queue_prim2sec_ishg is not None, real_time_disp)
                        if ishg_EOM_AC_insamps[0] in (1, 11): # flag for EOM iSHG fill array
                            if (k == fake_size_slow or real_time_disp):
                                if array_ishg_4d is not None:  # # defined here, prim that does all or sec.
                                    array_ishg_3d_diff = jobs_scripts.EOMph_3d_diff_meth(ishg_EOM_AC_insamps, array_ishg_4d) # # flag, ramp time sec00, step theo(deg), Vpi, VMax, nb_samps_perphsft, task_mtrtrigger_out, offset_samps, flag_impose_ramptime_as_exptime 
                                    if not self.primary_worker: # # sec. worker
                                        # # queue_conn_acq_fill is for Sec. wrkr queue_sec2prim !!
                                        if not self.queue_conn_acq_fill.empty(): # # previous not consumed
                                            try:
                                                self.queue_conn_acq_fill.get_nowait() # # empty the queue (overwrite)
                                            except queueEmpty: # can happen
                                                pass
                                        self.queue_conn_acq_fill.put([k, array_ishg_3d_diff]) # send the full array to disp OR primary fill
                                else: # # result of sec. wrkr
                                    if arr_in_packet is not None: # # otherwise array_ishg_3d_diff will stay random
                                        array_ishg_3d_diff = arr_in_packet 
                        
                        if (self.primary_worker and ishg_EOM_AC_insamps[0] in (2, 11)): # special for saving whole array
                            data_list.append(data)
                        
                        ## disp of acquired buffers
                            
                        # print('fill ', num_pmt)  
                        # print(array_3d[num_pmt,k,20:30])
                                                
                        if (self.primary_worker and real_time_disp):
                            # # fig1, fig2, ax_list, ax_h_list, img_grey_list, cb_list = plot_fast_script2_mp.plot_fast_func(plt, array_3d, array_ishg_3d_diff, pmt_channel_list, fake_size_slow, nb_bins_hist, fig1, ax_list, img_grey_list, cb_list, cmap_str, fig2, ax_h_list, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, size_x, size_y, sat_value_list, autoscalelive_plt)
                            param_to_disp = [pmt_channel_list , fake_size_slow, nb_bins_hist , clrmap_nb, autoscalelive_plt, fake_size_fast, fake_size_slow, sat_value_list ]
                            if ishg_EOM_AC_insamps[0] in (1, 11):  # flag for EOM iSHG fill array in here  
                                paquet_2disp = [[array_3d, array_ishg_3d_diff, None], param_to_disp]              
                                # # ishg_EOM_AC_insamps : [flag, time, nb_p-s, Vpi, Vmax] 
                                # # so you don't send a useless big array to Disp   
                                # # print('in fill pr sz_y , sz_x', array_ishg_3d_diff.shape[1] , array_ishg_3d_diff.shape[2], arr_in_packet is not None)
                            elif ishg_EOM_AC_insamps[0] == 2: # special for saving whole array
                                paquet_2disp = [[array_3d, None], param_to_disp] 
                            else: # normal mode
                                paquet_2disp = [array_3d, param_to_disp] # DON`T use dstack, it transposes !
                            self.queue_fill_disp.put(paquet_2disp)
                                                            
                    ## after one total image filled & disp
                    
                    paquet_tosend, queue_send, t_tot = paquet_tosendfunc(array_3d,  array_ishg_3d_diff, array_ishg_4d, sat_value_list, delete_px_X_begin, delete_px_Y_begin, delete_px_X_end, delete_px_Y_end, ishg_EOM_AC_insamps, self.primary_worker, ind_disp_sec, fake_size_slow, self.queue_sec2prim_fill, self.queue_conn_acq_fill, self.queue_list_arrays, packet_sec, queueEmpty, real_time_disp, nb_pmt_channel, nb_bins_hist, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, fake_size_fast, fake_size_slow, arr_in_packet, data_list, ttot_theo_ishg, time, start_time, True, autoscalelive_plt, clrmap_nb, jobs_scripts)
                    print('--- Fill time = %.1f sec %s ---' % (t_tot, prim_process_str)) 
                
                # # if break received in loop, it goes here
                if len(paquet) > 1: # stop or poison-pill was not received
                    ## normal : send img to GUI
                
                    # print('Nb loop expected/done in fill = %.3g/%d' % (-1, self.size_slow))
                    if self.primary_worker:
                        self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_tosend, '', None, None, None, None, None)  # # send_img_to_gui is in go_scan_galvos.py
                    else: # # secondary
                        queue_send.put(paquet_tosend) # send in queue to the main gui if primary, sec2prim for sec. wrkr
                    # index_img_current+=1 # next image
                    
                else: # stop or poison-pill received
                
                    # print('paquet ', paquet)
                    ## stop or poison-pill was received
                    
                    if paquet[0] == -1:
                        print('Poison-pill detected in fill_process %s (prim %r)' % (prim_process_str, self.primary_worker))
                        if (self.queue_fill_disp is not None and type(self.queue_fill_disp) != int): # #real_time_disp:    # disp only if nb buffer > 1
                            self.queue_fill_disp.put([-1]) # communicate the poison-pill to disp process
                        if self.primary_worker:
                            self.new_img_flag_queue.put('kill') # close the qthread
                            if self.queue_prim2sec_ishg is not None: # # second process ishg is there, filling its 4D array !
                                self.queue_prim2sec_ishg.put([-1]) # communicate the poison-pill to sec. Worker if it is there
                        break # outside big while loop, end process
                    else: # just stop (=0 or -2)
                        print('Order to stop detected in fill_process %s' % prim_process_str)
                        
                        if (self.primary_worker and self.real_time_disp):    # disp only if nb buffer > 1
                            self.queue_fill_disp.put([0]) # communicate the stop command to disp process                  
                        if paquet[0] == -2: # stop, in-line
                            if self.primary_worker:
                                # to un-lock the scan worker waiting for this data to stop
                                if (type(paquet_tosend) !=  list):  # an error ocured in reading, scan never started
                                # paquet_tosend remains the init value
                                    self.new_img_flag_queue.put('stand-by') # just stand-by, something failed so no img to send
                                else: # cancel in-line
                                    self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_tosend, '(the last for now)', None, None, None, None, None)  # # send_img_to_gui is in go_scan_galvos.py
                                    # # tell the acq function that an image must be disp
                        if (self.primary_worker and self.queue_prim2sec_ishg is not None): # # second process ishg is there, filling its 4D array !
                            self.queue_prim2sec_ishg.put(paquet) # communicate the stop to sec. Worker if it is there
                    
        except: # # error
            import traceback
            print('-- Errors in ', prim_process_str)
            traceback.print_exc()
            paquet_tosend, queue_send, t_tot = paquet_tosendfunc(array_3d,  array_ishg_3d_diff, array_ishg_4d, sat_value_list, delete_px_X_begin, delete_px_Y_begin, delete_px_X_end, delete_px_Y_end, ishg_EOM_AC_insamps, self.primary_worker, ind_disp_sec, fake_size_slow, self.queue_sec2prim_fill, self.queue_conn_acq_fill, self.queue_list_arrays, packet_sec, queueEmpty, real_time_disp, nb_pmt_channel, nb_bins_hist, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, fake_size_fast, fake_size_slow, arr_in_packet, data_list, ttot_theo_ishg, time, start_time, False, autoscalelive_plt, clrmap_nb, jobs_scripts)  # #  False for error
            if queue_send is not None:
                if self.primary_worker:
                    self.send_img_to_gui(self.queue_list_arrays, self.new_img_flag_queue, paquet_tosend, '(incomplete !!!)', None, None, None, None, None)  # # send_img_to_gui is in go_scan_galvos.py
                else: # # secondary
                    queue_send.put(paquet_tosend) # send in queue to the main gui if primary, sec2prim for sec. wrkr
            if self.primary_worker:
                if (self.queue_fill_disp is not None and type(self.queue_fill_disp) != int): self.queue_fill_disp.put([-1])  #  # disp only if nb buffer > 1
                self.emergency_ToMove_queue.put(1) # 1 means error, Move worker will end (when listen to emergency queue)
                try:
                    self.queue_conn_acq_fill.get(block=True, timeout=3) # blocking, receive the last data from Read (cannot make a timeout)
                except queueEmpty:
                    pass
                # # the smallest Proc end the loop by telling the main to close the thread
                self.new_img_flag_queue.put('kill') # the acq.move function receive order to terminate
            else: #  # sec. wrkr
                try:
                    self.queue_prim2sec_ishg.get(block=True, timeout=3)
                except queueEmpty:
                    pass