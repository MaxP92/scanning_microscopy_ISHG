# -*- coding: utf-8 -*-
"""
Created on Mon Sept 26 16:35:13 2016

@author: Maxime PINSARD
"""    

def plot_fast_func(plt, array_3d, array_ishg_3d_diff, pmt_channel_list, ind_disp_full, ind_max, nb_bins_hist, fig1, ax_list, img_grey_list, cb_list, cmap_str, fig2, ax_h_list, numpy, min_disp_perc, max_disp_perc, size_X_px, size_Y_px, sat_value_list, autoscalelive_plt):
    """
    Uses matplotlib
    
    ok for real-time plotting, but pyqtgraph is faster
    """
    t_h_str = "Value Histogram"; x_h_str = "Counts"; y_h_str = "Number of pixels"
    nb_pmt_channel = sum(pmt_channel_list)
    
    def set_geom_mp(geom1, mngr1, scrX, scrY, fact, windows_task_bar_width, win2):
        
        try:
            x1,y1,dx1,dy1 = geom1.getRect()
            if win2:
                sx= scrX
                sy = scrY
            else:
                sx=max(20, round((scrX - dx1)/fact))
                sy = max(30, round((scrY - dy1)/fact)-windows_task_bar_width)
            mngr1.window.setGeometry(sx, sy, dx1, dy1) # posX, posY, sx, sy
        except AttributeError: # if Tkagg
            dx1,dy1 = mngr1.window.wm_maxsize()
            if win2:
                sx= scrX
                sy = scrY
            else:
                sx=max(20, round((scrX - dx1)/fact))
                sy = max(30, round((scrY - dy1)/fact)-windows_task_bar_width)
            mngr1.window.wm_geometry("%dx%d+%d+%d" % (sx, sy, dx1, dy1))
        
    if (not(ind_disp_full % min(ind_max, 5)) or not(ind_disp_full % ind_max)): # will update in the end of the image, and also every 10 buffers
    # if index of buffer is the first or the last one
        
        ind_temp = ind_disp_full % ind_max # to allow avg jobs to correctly work (ind_disp_full > ind_max)
        if (ind_temp==0 and ind_disp_full>0):
            ind_temp = ind_disp_full
        
        # # print('nb_pmt_channel!!', nb_pmt_channel)
        # # if nb_pmt_channel > 1: # 2 PMT
        for k in range(nb_pmt_channel):
            cb_list[k].update_normal(img_grey_list[k])

            # ax_h_list[k].remove()
            ax_h_list[k].cla()
            ax_h_list[k].hist(array_3d[k, :int(ind_temp/ind_max*numpy.size(array_3d[k, :,:], 0)-1), :].ravel(order='C'), bins = nb_bins_hist, histtype='step')
            ax_h_list[k].relim() 
            ax_h_list[k].set_title(t_h_str)
            ax_h_list[k].set_xlabel(x_h_str)
            ax_h_list[k].set_ylabel(y_h_str)
            # ax_h_list[k].draw_artist()
        
        fig2.canvas.draw_idle()
    
    if type(autoscalelive_plt) == tuple: autoscalelive_plt_local = autoscalelive_plt #[0]
    elif (autoscalelive_plt == 0 and ind_disp_full > 0.1*ind_max): autoscalelive_plt_local = False  
    else: autoscalelive_plt_local = True
        
    if (ind_disp_full == 1): #or not ((ind_disp_full) % (ind_max))): # if you want to close each time your figure
        ax_list = []; ax_h_list = []; img_grey_list = []; cb_list = [] # # do not group !!
        # print('In 1st img')
        # try:
        plt.close(fig1) # comment if noclose fig between images
        # except:
        #     pass
        dpi_dflt = 80
        fact = 1.3
        scrX = 1680; scrY = 1050
        fact_screen = 4/3 # for display on screen
        windows_task_bar_width = 53 # PX
        size_min_x = fact*350/dpi_dflt
        size_min_y = fact*300/dpi_dflt

        figX = max(size_min_x, min(fact*size_X_px/dpi_dflt, scrX/dpi_dflt)); figY = max(size_min_y, min(fact*size_Y_px/dpi_dflt, scrY/dpi_dflt))
        sz_sm = max(min(nb_pmt_channel*(1+int(array_ishg_3d_diff is not None))-1,2),1); sz_bg = min(nb_pmt_channel*(1+int(array_ishg_3d_diff is not None)), 2)
        sz_sm00 =  max(min(nb_pmt_channel-1,2),1); sz_bg00 = min(nb_pmt_channel, 2)
        # # if (array_ishg_3d_diff is not None and nb_pmt_channel <= 2): # # EOM iSHG
        # #     sz_sm += 1
        if numpy.size(array_3d[0,:,:],0) >= numpy.size(array_3d[0,:,:],1)/fact_screen: # more rows than columns (or less but screen aspect counts), aspect rather vertical
            sz_y = sz_sm; sz_x = sz_bg;
            if (nb_pmt_channel > 1 or array_ishg_3d_diff is not None):
                figX = min(figX*sz_bg, scrX/dpi_dflt/fact)
        else:
            sz_y = sz_bg; sz_x = sz_sm;
            if (nb_pmt_channel > 1 or array_ishg_3d_diff is not None):
                figY = min(figY*sz_bg, scrY/dpi_dflt/fact)

        fig1=plt.figure(num=1, figsize=(figX, figY), dpi = dpi_dflt) # plot imshow
        # # print('sz_y , sz_x', array_ishg_3d_diff.shape[1] , array_ishg_3d_diff.shape[2])
        mngr1 = plt.get_current_fig_manager()
        # to put it into the upper left corner for example:
        geom1 = mngr1.window.geometry()
        set_geom_mp(geom1, mngr1, scrX, scrY, fact, windows_task_bar_width, False)
        
        lim_ratio = 15; ratio = array_3d.shape[1]/array_3d.shape[2]
        frac_disp_cb = 0.096*ratio
        asp_r = 10
        # if frac_disp_cb*max(array_3d.shape[1], array_3d.shape[2]) < :
        if (ratio > lim_ratio or ratio < 1/lim_ratio):
            frac_disp_cb = 0.10 #*ratio
            asp_r = 20

        # # if nb_pmt_channel > 1: # 2 PMT
        k0 = 0
        for k in range(len(pmt_channel_list)):
            if pmt_channel_list[k] == 1: # PMT must be activated
                ax_list.append(plt.subplot(sz_y, sz_x, k0+1))
                img_grey_list.append(ax_list[k0].imshow(array_3d[k0,:,:], cmap=cmap_str)) # plt.imshow
                if type(autoscalelive_plt_local) == tuple: 
                    img_grey_list[k0].set_clim(numpy.quantile(array_3d[k0,:,:], autoscalelive_plt_local[0]/100), numpy.quantile(array_3d[k0,:,:], autoscalelive_plt_local[1]/100))
                elif autoscalelive_plt_local: img_grey_list[k0].autoscale( ) # autoscale enable =
                # # print('cb_list!!', cb_list, nb_pmt_channel)
                cb_list.append(plt.colorbar(img_grey_list[k0], ax=ax_list[k0],fraction=frac_disp_cb, pad=0.04, aspect = asp_r)) #cax=ax1, mappable=img_grey)
                ax_list[k0].set_title('Sat: '+ '{:,}'.format(round(sat_value_list[k], 1)))
                k0+=1
        
        L_ax = len(ax_list)    
        if (array_ishg_3d_diff is not None and nb_pmt_channel <= 2): # # EOM iSHG
            for k in range(nb_pmt_channel):  # # cannot merge both because of indexes   
                # up to 2 PMT
                ax_list.append(plt.subplot(sz_y, sz_x, L_ax+ k+1))
                img_grey_list.append(ax_list[-1].imshow(array_ishg_3d_diff[k,:,:], cmap='PiYG')) # plt.imshow
                img_grey_list[-1].autoscale() # autoscale enable = 
                # # print('cb_list!!', cb_list, nb_pmt_channel) 
                cb_list.append(plt.colorbar(img_grey_list[-1], ax=ax_list[-1],fraction=frac_disp_cb, pad=0.04, aspect = asp_r)) #cax=ax1, mappable=img_grey)
            
        plt.show(False)
        # print('In 1st img 2')
        # plt.show(block = False)
        # cache bckgrnd
        # background1 = fig1.canvas.copy_from_bbox(ax1.bbox)
        try:
            fig1.canvas.draw()
        except RuntimeError: # # just a colorbar problem
            for k in range(nb_pmt_channel): 
                cb_list[k].remove()
                cb_list[k] = plt.colorbar(img_grey_list[k], ax=ax_list[k])
            if (array_ishg_3d_diff is not None):
                cb_list[-1].remove()
                cb_list[-1] = plt.colorbar(img_grey_list[-1], ax=ax_list[-1])
            fig1.canvas.draw()
            # print('err')
        # # background1 = fig1.canvas.copy_from_bbox(ax1.bbox)
        # # 
        # # if nb_pmt_channel > 1: # 2 PMT
        # #     background2 = fig1.canvas.copy_from_bbox(ax2.bbox)
        
        if array_ishg_3d_diff is not None and nb_pmt_channel > 2: 
            fig3=plt.figure(num=3, figsize=(figX, figY), dpi = dpi_dflt) # plot imshow
            # ...

        # print('In hist')
        # try:
        plt.close(fig2)
        # except:
        #     pass # do nothing
            
        # fig1=plt.figure(1) # comment if no close fig between images
        fig2=plt.figure(2) # plot hist
        
        mngr = plt.get_current_fig_manager()
        # to put it into the upper left corner for example:
        geom = mngr.window.geometry()
        set_geom_mp(geom,mngr, 20, 30, fact, windows_task_bar_width, True)
        
        # # if nb_pmt_channel > 1: # 2 PMT
        for k in range(nb_pmt_channel):
            ax_h_list.append(plt.subplot(sz_bg00, sz_sm00, k+1))
            ax_h_list[k].set_title(t_h_str)
            ax_h_list[k].set_xlabel(x_h_str)
            ax_h_list[k].set_ylabel(y_h_str)
            # ax_h_list[k].draw_artist()
        
        plt.show(False)
        # # fig2.canvas.draw()
    
    else:  ## ind_disp_full > 1        
        # if ((ind_disp_full-1) % (self.ind_max+1)):
        #     fig1.canvas.draw()
        # print('In update img')
        # # if nb_pmt_channel > 1: # 2 PMT
         # up to 10%, after no autoscale+  
        
        for k in range(len(img_grey_list)):
            # update data
            if k >= nb_pmt_channel: # # coming to iSHG
                if (array_ishg_3d_diff is not None and nb_pmt_channel <= 2): # expected for ISHG fast
                    arr = array_ishg_3d_diff[k-nb_pmt_channel,:,:]
                else: # unexpected, will throw an error
                    break
            else: # normal
                arr = array_3d[k,:,:]
            img_grey_list[k].set_data(arr)
            if type(autoscalelive_plt_local) == tuple: img_grey_list[k].set_clim(numpy.quantile(array_3d[k,:,:], autoscalelive_plt_local[0]/100), numpy.quantile(array_3d[k,:,:], autoscalelive_plt_local[1]/100))
            elif autoscalelive_plt_local: 
                img_grey_list[k].autoscale( ) # autoscale enable =
                img_grey_list[k].set_clim(numpy.min(numpy.ma.masked_equal(arr, 0, copy=False))*min_disp_perc, numpy.max(arr)*max_disp_perc) # remove 0 without creating a copy
    
            # restore
            ax_list[k].draw_artist(ax_list[k].patch)
            # fig1.canvas.restore_region(background2)
            ax_list[k].draw_artist(img_grey_list[k])
            
            # cb2.remove()
            # cb2 = plt.colorbar() #cax=ax2, mappable=img_grey2)
            
        # hist.set_data(array_3d[k,:,:].ravel(order='C'))
        
        # IT'S DIFFICULT TO UPDATE THE COLORBAR : update does not work, nor remove(), nor colorbar to mappable and axis
        
        #if not ((ind_disp_full) % (ind_max)):
            # plt.sca(ax1)
            #cb1.mappable
            # cb1 = plt.colorbar(img_grey, ax1)
            # cb1.update_normal(img_grey)
            # cb1 = plt.colorbar()
        
            
        # ax1.draw_artist(hist)
    
        # fill in the axes rectangle
        # fig1.canvas.blit(ax1.bbox)
        try:
            fig1.canvas.update() #blit(ax2.bbox)
        except AttributeError:
            fig1.canvas.draw_idle()
        fig1.canvas.flush_events() # do not remove it, otherwise no display !
    
    return fig1, fig2, ax_list, ax_h_list, img_grey_list, cb_list
    
    