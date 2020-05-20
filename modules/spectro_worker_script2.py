# -*- coding: utf-8 -*-
"""
Created on Mon July 24 16:35:13 2017

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal
                
class Worker_spectro(QObject):

    # # pyqtSignals
    spectro_values_display_signal = pyqtSignal(int, str, str)
    
    spectro_msg_handler_signal = pyqtSignal(int)
    acqsave_fast_spect_scan_signal = pyqtSignal(int)

    def __init__(self, spectro_acq_flag_queue, queue_disconnections, queueEmpty, spectro_pack, numpy, time, datetime, newdirpath, min_exptime_msec, jobs_scripts, max_fwhm_util): 
    
        super(Worker_spectro, self).__init__()
        
        self.spectro_model = "USB4000"
        
        self.spectro_acq_flag_queue = spectro_acq_flag_queue
        self.queue_disconnections = queue_disconnections
        self.queueEmpty = queueEmpty
        self.numpy = numpy
        [self.central_wvlgth, self.lower_bound_window , self.upper_bound_window, self.lwr_bound_expected, self.upper_bound_expected, self.integration_time_spectro_us, self.wait_time_seconds] = spectro_pack
        self.time = time; self.datetime = datetime; self.newdirpath = newdirpath
        self.min_exptime_msec = min_exptime_msec
        self.jobs_scripts = jobs_scripts
        self.max_fwhm_util = max_fwhm_util
        
        self.msg_Err_spectro = 'Spectro already controlled by e.g. Spectrasuite (or no connected)'
        
        # self.spectro_connected = 0
        
    def __del__(self):
        if hasattr(self, 'spectro'):
            self.spectro.close()
        self.spectro_msg_handler_signal.emit(-1) # # will put thread to None in GUI

    @pyqtSlot()
    def open_lib(self):
        
        import seabreeze.spectrometers as seabreeze_spectro
        
        print('seabreeze imported')
        
        self.seabreeze_spectro = seabreeze_spectro
        
    @pyqtSlot(int)
    def connect_disconnect_spectro_meth(self, bb):
                
        print('in connect_disconnect_spectro', bb)

        try:
            self.spectro.integration_time_micros(max(self.min_exptime_msec*1000, self.integration_time_spectro_us))
            spectro_connected = 1 # if it succeed previous line
            
        except (self.seabreeze_spectro.SeaBreezeError, AttributeError): # spectro does not respond
            
            # # print(self.msg_Err_spectro)
            spectro_connected = 0
        
        if not spectro_connected: # spectro not yet connected
            try:
                devices = self.seabreeze_spectro.list_devices()
            
                list_spectro = [d for d in devices if d.model == self.spectro_model]
            except self.seabreeze_spectro.SeaBreezeError: # find how to handle seabreeze errors
                list_spectro = False
                print(self.msg_Err_spectro)
            
            if list_spectro: # spectro is here 
 
                # spectro = sb.Spectrometer.from_serial_number()
                self.spectro = self.seabreeze_spectro.Spectrometer(list_spectro[0])
                
                self.spectro.integration_time_micros(self.integration_time_spectro_us)
                
                print('wrkr connected spectro')
            
        else: # spectro is connected : order to disconnect it
            
            self.spectro.close()
            print('spectro disconnected')
            list_spectro = None
        
        # # print('s', spectro_connected ,  list_spectro, (spectro_connected or not list_spectro), ((not spectro_connected and list_spectro) or spectro_connected))
        
        if (spectro_connected or not list_spectro): # spectro not here, not connected or not available, OR order to disconnect it
            self.spectro_values_display_signal.emit(0, 'N/A', 'N/A')
        
        # # not exclusive to the one before !!
        if (spectro_connected or (not spectro_connected and list_spectro)):  # spectro in list but not yet connected OR spectro to disconnect  
            self.spectro_msg_handler_signal.emit(bb) # # 0 = classic

    def end_acq_util(self, ordr, mode, save_excel, newdirpath, wlth1, ct_tot, ct_spect, wait_time_seconds, res_theo_mm_mtr, vel_mtr, indexes_wl, slow):
        print('Order to exit the loop in acquire spectrum, slow =', slow)
        if (mode == 1 and self.data_big is not None and ordr != -2): # # scan save
            nb_avg_real = round(ct_tot/ct_spect)
            dtnw = self.datetime.datetime.strftime(self.datetime.datetime.now(), '%m-%d_%Hh%M.%S.%f')[:-5]
            if not slow:
                # # print(self.data_big[0, :])
                data_big = self.data_big
                data_big[1:, 1:] = self.data_big[1:, 1:] - self.base_line
                # # print(self.data_big[0, :])
                avg_data_big = True
                if avg_data_big:
                    st = self.time.time()
                    rest = (len(data_big)-1)%nb_avg_real
                    end1 = -rest if rest> 0 else len(data_big)
                    data_big_treat = data_big[1:end1 , :] # # 1st line is wavelengths
                    nbcol = len(data_big_treat[0]) ; nblines = len(data_big_treat) # one spectrum per line
                    data_big_treat = data_big_treat.reshape((nb_avg_real, int(nbcol*nblines/nb_avg_real)), order='F') # # not taking one row every nb_avg ('C'), but packets of nb_avg
                    data_big_treat = self.numpy.sum(data_big_treat, axis = 0)/nb_avg_real
                    data_big_treat = data_big_treat.reshape((int(nblines/nb_avg_real), nbcol), order='F') # # not taking one row every nb_avg ('C'), but packets of nb_avg
                    data_big = data_big[:1+len(data_big_treat), :]
                    data_big[1: ,:] = data_big_treat
                    print('time avg array', (self.time.time() - st), 'nb_avg', nb_avg_real)
                    nb_acq = ct_spect
                else:
                    nb_acq = ct_tot
            plot_FROG = False
            transpose_data = True
            
            print('saving spectrums to file ...')
            nm = r'%s\%s_res%gmm_exp%.1fmsec_avg%d_vel%gmmsec_nb%d' % (newdirpath, dtnw, res_theo_mm_mtr, wait_time_seconds*1000, nb_avg_real, vel_mtr, nb_acq)
            if save_excel == 1:
                writer = self.pandas.ExcelWriter(nm + '.xlsx', engine='xlsxwriter')
                df = self.pandas.DataFrame(data_big); df.to_excel(writer, sheet_name='data', index=False); writer.save()
            elif save_excel == -1: # # npy
                self.numpy.save(nm + '.npy', data_big)
            elif save_excel == 0: # # mat
                import scipy.io
                scipy.io.savemat(nm + '.mat', {'data': data_big})
                
            print('spectrums saved. \n')
            if plot_FROG:
                if len(data_big) > 1e6:
                    data_big = data_big[::int(len(data_big)/ 1e6) ,:]
                if transpose_data:
                    data_big = self.numpy.transpose(data_big)
                data_big = self.numpy.ascontiguousarray(data_big)
                # print(data_big.flags)  
                dvdr = max(1, int(len(data_big)/ 1e4)  )
                # # self.jobs_scripts.plot_autoco_frog_meth(self.plt, self.numpy, self.data_big, 'res_mtr%.fum, exp.%.fmsec, vel=%gmm/sec' % (res_theo_mm_mtr, wait_time_seconds*1e3, vel_mtr), indexes_wl, 100 , True) # # False for autoco
                self.jobs_scripts.plot_autoco_frog_meth(self.plt, self.numpy, data_big, 'res_mtr%.fum, exp.%.fmsec, vel=%gmm/sec' % (res_theo_mm_mtr, wait_time_seconds*1e3, vel_mtr), indexes_wl, dvdr , True) # # False for autoco
           
        self.data_big = data_big =0 # # free memory
        
        # # print(ordr)
        if (mode == 0 or ordr != -4):  # # -4 = relaunch
            # # if outside while loop  
            # # if mode == 0: ordr = 0
            self.connect_disconnect_spectro_meth(ordr)
        if ordr == -1:
            print('Order to kill the spectro worker')
            self.queue_disconnections.put(4) # tell the GUI the spectro is closed : spectro's signature is 4
    
    def init_scan_save_util(self, msg, min_exptime_msec, slow):
    # # not a Slot
    
        [lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, var, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, vel_mtr, save_excel, nb_acq, keep_wlth] = msg[1]
        if slow:
            integration_time_spectro_us = var
            nb_avg = wait_time_seconds/integration_time_spectro_us*1e6
            delay_fs = 0
        else: # # fast acq save
            nb_avg = var # # var is self.jobs_window.nblinesimg_fastcalib_spbx.value()
            integration_time_spectro_us = 1e6*wait_time_seconds/nb_avg
            
        if integration_time_spectro_us < 4000: # 4msec
            integration_time_spectro_us = 1e6*wait_time_seconds
            nb_avg = 1 # # var is self.jobs_window.nblinesimg_fastcalib_spbx.value()
        if integration_time_spectro_us < min_exptime_msec*1000: # physical minimum
            integration_time_spectro_us = min_exptime_msec*1000
            nb_avg = 1; wait_time_seconds = min_exptime_msec/1000
            print('\n WARNING : int.time spetcro was below min value of %d, now set to it !! \n' % integration_time_spectro_us)
        
        stp_fs = vel_mtr*wait_time_seconds*eq_inps_1mm_mtr*1000 # # res_theo_mm_mtr/eq_inps_1mm_mtr*1000 # # *1000 for ps to fs 
            # # eq_inps_1mm_mtr in ps/mm
            # # eq_inps_1mm_mtr = eq_inps_1mm_calci if single path, otherwise its eq_inps_1mm_calci*nb_pass
        if not slow:
            delay_fs = self.numpy.arange(0, nb_acq*stp_fs, stp_fs)
        
        print('spect. wrkr', 'int. time = ', round(integration_time_spectro_us), msg[1] )
        self.spectro.integration_time_micros(int(integration_time_spectro_us))
        if (type(pathsave) == str and (pathsave[1:3] == ':\\' or pathsave[1:2] ==':/')):
            newdirpath = pathsave
        else:
            newdirpath = self.newdirpath
        
        if save_excel:
            import pandas
            self.pandas = pandas
            
        return delay_fs, stp_fs, newdirpath, lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, integration_time_spectro_us, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, save_excel, nb_acq, nb_avg, keep_wlth, vel_mtr
        
    @pyqtSlot(int)
    def acquire_spectrum_continuous_meth(self, mode):            
        
        # # ii = 0
        # # max_ii_median = 10
        # # fwhm = self.numpy.zeros((max_ii_median+1))
        print('entering in acq spect.')
        self.data_big = newdirpath = save_excel = None; wlth1 = 0
        
        while True: # # infinite, loop on several acq.
            
            try:
                msg = self.spectro_acq_flag_queue.get_nowait() # wait without block, error if nothing, that's why there is a try/except
                ordr = msg[0]
                ct_spect = 0
                
                if (len(msg) == 1 or mode == 0): # # normal acq.
                    [lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, integration_time_spectro_us, wait_time_seconds] = [self.lower_bound_window , self.upper_bound_window, self.lwr_bound_expected, self.upper_bound_expected, self.integration_time_spectro_us, self.wait_time_seconds]
                    self.spectro.integration_time_micros(self.integration_time_spectro_us)
                    res_theo_mm_mtr= vel_mtr = 0
                elif mode == 1: # # scan save
                    delay_fs, stp_fs, newdirpath, lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, integration_time_spectro_us, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, save_excel, nb_acq, nb_avg, keep_wlth = self.init_scan_save_util( msg, self.min_exptime_msec, True)
                    
            except self.queueEmpty: # if there is an error on get, which means no order to stop
                if not 'ordr' in locals():
                    ordr = mode = 0
            finally:
                if ordr >= 1:
                    # # print('In spectro acq loop')
                    # for ii in range(max_ii_median):
                    st_time = self.time.time()
                    ct = 0
                    while (self.time.time() - st_time) < wait_time_seconds: # sec, one acq. 
                        
                        if ct_spect == 0: # # wvlth is always the same
                            wlth = self.spectro.wavelengths()
                        intens_temp = self.spectro.intensities()
                        if ct > 0:
                            intens=self.numpy.vstack((intens, intens_temp))
                        else:
                            intens=intens_temp
                        ct += 1
                    
                    if ct > 1:
                        intens = self.numpy.mean(intens, 0)
                    # # print('intens1', intens)
                    if ct_spect == 0: # # wvlth is always the same
                        indexes_wl = self.numpy.where((wlth > self.central_wvlgth-lower_bound_window) & (wlth < self.central_wvlgth+upper_bound_window))
                        # # print(ct_spect, 'indexes_wl', indexes_wl)
                        wlth1 = wlth[indexes_wl]
                    # # print(ct_spect, 'indexes_wl', indexes_wl, intens.shape)
                    intens1 = intens[indexes_wl]
                    
                    if (ct_spect == 0 or not hasattr(self, 'base_line')): # # wvlth is always the same
                        indexes_wl_dual = self.numpy.where((wlth < self.central_wvlgth-lower_bound_window) | (wlth > self.central_wvlgth+upper_bound_window))
                        intens1_dual = intens[indexes_wl_dual]
                        self.base_line = self.numpy.mean(intens1_dual)
                    
                    if mode == 0: # # normal acq.
                        pas_content = 1 # # see after, for max
                    elif mode == 1:  # # scan save
                        pas_content = len(intens)+1 # don't search the max for too long
                        if ct_spect == 0:
                            print('spectro is acquiring in scan save mode...')
                        elif (not(ct_spect%100) or ct_spect == nb_acq-1):
                            print('spectrum # %d' % ct_spect)
                    
                    intens1 = intens1 - self.base_line # # needs base-line
    
                    max_intens, max_intens_wlth, fwhm_disp = self.max_fwhm_util(self.numpy, pas_content, wlth1, intens1, intens, self.central_wvlgth, lwr_bound_expected, upper_bound_expected, mode)
                    
                    # # print(fwhm_disp,pas_content, wlth1.shape, intens1.shape, intens.shape, lwr_bound_expected, upper_bound_expected, mode )
                    if mode == 1: # # scan save
                        fwhm_disp = max_intens # # it will display the nb of counts instead
                        delay_fs += stp_fs
                        intens1 = self.numpy.insert(intens1, 0, delay_fs, axis=0);
                        # # print('s', intens1.shape)
                        if save_live:
                            st_time1 = self.time.time()
                            # # if save_excel:
                            self.numpy.save('%s/%s_%d.npy' % (newdirpath, self.datetime.datetime.strftime(self.datetime.datetime.now(), '%m-%d_%Hh%M.%S.%f')[:-5], ct_spect), [wlth1, intens1]) 
                            # # else:
                            # #     pass
                            # # excel pandas is far too slow if very big arrays! (0.2sec for 20000 elements)
                            # # but only 3msec for 150 elements
                            print('save time %.f msec', ((self.time.time() - st_time1)*1000))
                        if save_big:
                            if ct_spect == 0:
                                self.data_big = self.numpy.concatenate(([0], wlth1))
                                # # print('ss', data_big.shape)
                                
                            self.data_big=self.numpy.vstack((self.data_big, intens1))
                                # # wlth_big=self.numpy.vstack((wlth_big, wlth1)) # # useless
                           
                                # # wlth_big=wlth1 # # useless
                            
                        # # one wlth = 100 pts, one intens = 100 pts. ; 10sec at 100msec int.time is 100 acq.
                        # # (100+100)*100 = 2e4 pts --> 1msec save
                        
                    self.spectro_values_display_signal.emit(1, '%.1f' % max_intens_wlth, '%.1f' % fwhm_disp)
                    ct_spect += 1
                    if (mode == 1 and ct_spect >= nb_acq): # # every acq are done
                        ordr = 0 # # will exit
                        self.spectro_msg_handler_signal.emit(-2) # # 0 = classic; 1 = end of scan save job
                    
                if ordr <= 0:
                    self.end_acq_util(ordr, mode, save_excel, newdirpath, wlth1, None, None, wait_time_seconds, res_theo_mm_mtr, vel_mtr, indexes_wl, True)
                    break # # outside while loops
            
    @pyqtSlot(int)
    def acqsave_fast_spect_scan_meth(self, mode):
        
        if not hasattr(self, 'plt'):
            import matplotlib
            matplotlib.rcParams['toolbar'] = 'None' # no toolbar
            import matplotlib.pyplot
            self.plt = matplotlib.pyplot
        self.data_big = newdirpath = save_excel = None; wlth1 = 0
        full_verbose = True
        probe_stop_inline = True
        try:
            msg = self.spectro_acq_flag_queue.get_nowait()  # # no wait
            # # print(msg)
        except self.queueEmpty: # if there is an error on get, which means no order to stop
            if not 'ordr' in locals():
                mode = 0; ordr = -2
        else:
            if (len(msg) <=1 or msg[0] <=0): # # not msg with params !
                try:
                    msg = self.spectro_acq_flag_queue.get(True, timeout = 2)  # # no wait
                except self.queueEmpty:
                    mode = 0; ordr = -2
                    print('timeout while reading order scan fast save in spectro !!')
            # # print('@', msg)
            ordr = msg[0]
            err_str = 'ordr is not a start in scan fast save in spectro'
            if ordr == -2: # # ?
                print(err_str)
            else: # # go on
                ct_spect = ct_tot = 0
                delay_fs, stp_fs, newdirpath, lower_bound_window , upper_bound_window, lwr_bound_expected, upper_bound_expected, integration_time_spectro_us, wait_time_seconds, save_live, save_big, pathsave, res_theo_mm_mtr, eq_inps_1mm_mtr, save_excel, nb_acq, nb_avg, keep_wlth, vel_mtr = self.init_scan_save_util( msg, self.min_exptime_msec, False)
                wlth = self.spectro.wavelengths()
                intens = self.spectro.intensities()
                indexes_wl = self.numpy.where((wlth > self.central_wvlgth-lower_bound_window) & (wlth < self.central_wvlgth+upper_bound_window))
                # # print(ct_spect, 'indexes_wl', indexes_wl)
                wlth1 = wlth[indexes_wl] if not keep_wlth else wlth
                indexes_wl_tight = self.numpy.where((wlth1 > self.central_wvlgth-lwr_bound_expected) & (wlth1 < self.central_wvlgth+upper_bound_expected))
                self.data_big = self.numpy.zeros((nb_avg*nb_acq+1, 1+len(wlth1))) # # 1st line is wvlth, 1st col. is delay[fs]
                self.data_big[0, 1:] = wlth1 # # first line
                indexes_wl_dual = self.numpy.where((wlth < lower_bound_window) | (wlth > upper_bound_window))  # # wlth > (upper_bound_expected*2) (wlth > self.central_wvlgth+upper_bound_window & wlth < self.central_wvlgth-lwr_bound_expected*2) |
                intens1_dual = intens[indexes_wl_dual]
                intens1 = intens[indexes_wl] if not keep_wlth else intens
                try:
                    self.base_line = self.numpy.mean(intens1_dual); intens1 = intens1 - self.base_line
                    max_intens, max_intens_wlth, fwhm_disp = self.max_fwhm_util(self.numpy, 1, wlth1, intens1, intens, self.central_wvlgth, lwr_bound_expected, upper_bound_expected, 0)
                    self.spectro_values_display_signal.emit(2, '%.1f' % max_intens_wlth, '%.1f' % fwhm_disp)
                except Exception as e: # # not essential
                    print(e)
                    
                disp_every = 10**(self.numpy.floor(self.numpy.log(3/wait_time_seconds)/self.numpy.log(10)))*2  # # 200 # frames # ~ 3sec
                print('acq. ready : baseline, window, wlth, array defined. \n This scan should take %d sec' % (nb_acq*wait_time_seconds)) 
                            
                msg = self.spectro_acq_flag_queue.get() # blocking, wait for scan start
                
                st_time_tot = self.time.time()
                ## acq. 
                if (len(msg) > 1 or msg[0] < 1): # # not a start
                    mode = 0; ct_spect = -2; 
                    if ordr !=-1: ordr = -2  # # -1 is poison-pill
                    print(err_str, 2)
                else: # # acq
                    
                    while ct_spect < nb_acq: # # on spectrums
                        if full_verbose:
                            st_time00 = self.time.time()
                        if (probe_stop_inline and not self.spectro_acq_flag_queue.empty()): # # some msg
                            try:
                                msg = self.spectro_acq_flag_queue.get_nowait()  # # no wait
                                ordr = msg[0]
                            except self.queueEmpty: # if there is an error on get, which means no order to stop
                                if not 'ordr' in locals():
                                    ordr = mode = 0
                            if ordr < 1: # # stop
                                break
                        if ct_spect == 0:
                            print('spectro is acquiring in scan save FAST mode...')
                        st_time = self.time.time()
                        ct = 0
                        while (ct < nb_avg): # # on avg 
                            ct_tot +=1 # # 1st is wavelength
                            self.data_big[ct_tot, 0] = delay_fs[ct_spect] # # first column
                            if not keep_wlth:
                                self.data_big[ct_tot, 1:] = self.spectro.intensities()[indexes_wl]
                            else:
                                self.data_big[ct_tot, 1:] = self.spectro.intensities()
                            ct += 1
                            if (self.time.time() - st_time) >= wait_time_seconds:
                                break
                            
                        if (not(ct_spect%disp_every) or ct_spect == nb_acq-1):
                            a = (self.time.time() - st_time00) if full_verbose else ''
                            print('spectrum #', ct_spect+1, '/', nb_acq, 'avg', nb_avg, ct, round(a, 4))
                        ct_spect += 1
        ## saving
        if ct_spect>=0: # # no err
            self.data_big = self.data_big[:min(len(self.data_big), max(0, ct_tot+1)), :] # # +1 because of wvlth 
            print('time_tot spect acq.', (self.time.time() - st_time_tot), ct_tot )
            if ct_spect == nb_acq: ordr = -22 # # the scan was done until the end
        self.end_acq_util(ordr, mode, save_excel, newdirpath, wlth1, ct_tot, ct_spect, wait_time_seconds, res_theo_mm_mtr, vel_mtr, indexes_wl_tight, False) # # last False for fast
                
        
def max_fwhm_util(numpy, pas_content, wlth1, intens1, intens, central_wvlgth, lwr_bound_expected, upper_bound_expected, mode):
    
    while pas_content:
        max_intens_wlth = wlth1[numpy.argmax(intens1)]
        max_intens = numpy.max(intens1)
        if pas_content >= len(intens):
            if pas_content == len(intens):
                max_intens_wlth = 0
            break
        # # print(max_intens_wlth)
        if (max_intens_wlth < central_wvlgth-lwr_bound_expected or max_intens_wlth > central_wvlgth+upper_bound_expected):
            intens1 = intens1[intens1!=max_intens_wlth]
            pas_content+=1 # # keep searching !
        else:
            pas_content = 0
        # # print(pas_content)

    if mode == 0: # # normal acq.
        d = intens1 - (max(intens1) / 2) 
        indexes = numpy.where(d > 0)[0] 
        # print('wlth1', d, indexes)
        if len(indexes) > 2: indexes = numpy.where((indexes[1:]-indexes[:-1]) < 5)[0] # # avoid a spike in the window to false the measure
            # # basically, it rejects any dip larger than X=5 samples
            # # fwhm[ii] =abs(wlth1[indexes[-1]] - wlth1[indexes[0]])
        if len(indexes) > 2: # useful that they are separated
            fwhm_disp = abs(wlth1[indexes[-1]] - wlth1[indexes[0]])
        else:
            fwhm_disp = 0
        # if ii == max_ii_median-1:
            # fwhm_disp = numpy.median(fwhm)
            # ii=0
            # print('fwhm=', fwhm_disp)
                # print('spectro values current emitted')
                # # time.sleep(wait_time_seconds)
    else:
        fwhm_disp = None
        
    return max_intens, max_intens_wlth, fwhm_disp

        
        
        