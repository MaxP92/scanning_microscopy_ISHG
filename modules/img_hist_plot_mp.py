# -*- coding: utf-8 -*-
"""
Created on Sept 12 15:35:13 2016

@author: Maxime PINSARD
"""
def plot_img_hist(numpy, LUT, array_main, img_item_pg, hist, isoLine):

    useLut = LUT # you can update it, see VideoSpeedTest example
    downsample = 0
    
    # if len(paquet_received) == 2:
    #     array_main = paquet_received[0] # fwd, PMT 1
    #     array_second = paquet_received[1] # bwd, PMT 2
    #     
    #     do_array_main = 1
    #     do_array_second = 1
    #     # # print(do_array_main, do_array_second)
    #     
    # else: # 1 array to disp
    #     if not do_array_main: # 2nd PMT
    #         do_array_second = 1
    #         
    #         array_second = paquet_received # PMT 2
    #     else: # do_array_main = 1
    #         array_main = paquet_received # PMT 1 
    #         do_array_second = 0
    if array_main.size > 0:
        # print('array_main.size', array_main.size)
        max_arr = round(numpy.max(array_main))
        min_arr = round(numpy.min(array_main))
    else: min_arr=1; max_arr =2
    # # print(max_arr)
    useScale = [0, max_arr ]
    img_item_pg.setImage(array_main[:, :].T, autoLevels=False, levels=useScale, lut=useLut, autoDownsample=downsample)
    hist.setLevels(min_arr, max_arr)
    
    if isoLine is not None:
        isoLine.setValue(round(max_arr/2) )
    
    # if do_array_second:
    #     useScale_2nd = [0, round(numpy.max(array_second))]
    #     img_item_pg_2.setImage(array_second[::-1, :].T, autoLevels=False, levels=useScale_2nd, lut=useLut, autoDownsample=downsample)
    #     hist_2.setLevels(round(numpy.min(array_second)), round(numpy.max(array_second)))
    
    
    # matplotlib
    """
    fig_main.clf()
    ax1f2 = fig_main.add_subplot(121)
    ax2f2 = fig_main.add_subplot(122)
    ax1f2.cla()
    im2 = ax1f2.imshow(array_main,  cmap='Greys_r') # plot array
    fig_main.colorbar(im2, ax=ax1f2)
    
    canvas_main.draw()
    
    if nb_bins_hist>0:
        ax1f1.cla()
        ax1f1.hist(array_main.ravel(order='C'), bins = nb_bins_hist)
        ax1f1.set_title("Histogram PMT 1")
        
        ax1f1.set_ylabel("Number of pixels")
        
        ax1f1.locator_params(axis='x', nbins=6)
            
        canvas_hist.draw()
    """
