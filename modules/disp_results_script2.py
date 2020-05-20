# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

import multiprocessing


class disp_results(multiprocessing.Process):

    """Process disp results"""

    def __init__(self, queue_fill_disp, new_img_flag_queue):
        
        multiprocessing.Process.__init__(self)
        
        self.queue_fill_disp = queue_fill_disp
        self.new_img_flag_queue = new_img_flag_queue

    def run(self):
        
        try:
            import matplotlib
            matplotlib.use('Qt5Agg') # optionnal
            import matplotlib.pyplot as plt
            # # print('plt backend', plt.get_backend())
            import numpy

            from modules import plot_fast_script2_mp, param_ini
            
            fig1 = 0; fig2 = 0; ax_list = ax_h_list = img_grey_list = cb_list = None; array_ishg_3d_diff = None
            
            ind_disp_full = 1
            
    #        order_to_stand_by = 0
            
            while True: # loop on buffers

                paquet_received = self.queue_fill_disp.get() # blocks until receive something
                # receive the buffers to disp
                
                if len(paquet_received) == 1: # order to stop or poison-pill
                
                    try:
                        plt.close(fig1) # if you don't close, the process works but the window of fig is freezed anyway
                        plt.close(fig2)
                    except:
                        pass # do nothing
                    # do nothing
                        
                    if paquet_received[0] == -1:
                        print('Poison-pill detected in disp_process')
                        break # outside big while loop, end of process
                        
                    else: # = 0
                        
                        print('Order to stop detected in disp_process')
                        ind_disp_full = 1
                        
                
                else: # data has been received
                    
                    array_3d = paquet_received[0]
                    if type(array_3d) == list: # # two arrays, meaning one is iSHG
                        array_ishg_3d_diff = array_3d[1]
                        array_3d = array_3d[0]
                        # # print('in disp:sz_y , sz_x', array_ishg_3d_diff.shape[1] , array_ishg_3d_diff.shape[2])
                    else:
                        array_ishg_3d_diff = None
                        
                    if paquet_received[1] is not None: # new parameters
                        param_to_disp = paquet_received[1]
                        if len(param_to_disp) == 8:
                            [pmt_channel_list, ind_max, nb_bins_hist, clrmap_nb, autoscalelive_plt, size_fast_px, size_slow_px, sat_value_list] = param_to_disp
                        
                            if clrmap_nb == 0: cmap_str = 'Greys_r'
                            elif clrmap_nb == 1: cmap_str = 'CMRmap'
                            elif clrmap_nb == 2: cmap_str = 'cubehelix'
                            elif clrmap_nb == 3: cmap_str = 'ocean'
                            elif clrmap_nb == 4: cmap_str = matplotlib.colors.ListedColormap(param_ini.lut_kryptonite/255.0)
                        else: print('len(param_to_disp) not 8 !!', len(param_to_disp), len(paquet_received), len(paquet_received[0]), len(paquet_received[1]) ) # # hopefully, parameters defined before ...
                    
                    # # print('sat_value_list', sat_value_list)
                    if ((not(ind_disp_full % min(ind_max, 5)) or not(ind_disp_full % ind_max)) and cb_list is None): continue # # cb_list was not updated, whereas it should have
                    
                    fig1, fig2, ax_list, ax_h_list, img_grey_list, cb_list = plot_fast_script2_mp.plot_fast_func(plt, array_3d, array_ishg_3d_diff, pmt_channel_list, ind_disp_full, ind_max, nb_bins_hist, fig1, ax_list, img_grey_list, cb_list, cmap_str, fig2, ax_h_list, numpy, param_ini.min_disp_perc, param_ini.max_disp_perc, size_fast_px, size_slow_px, sat_value_list, autoscalelive_plt)
                    
                    ind_disp_full +=1 # important to keep for display
                    
        except:
            import traceback
            traceback.print_exc()
            self.new_img_flag_queue.put('killAcq') # tell the Thread to close the Process Acq.
            self.queue_fill_disp.get(block=True, timeout=3) # receive the last paquet from fill
