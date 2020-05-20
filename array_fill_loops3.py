# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""
# # fill_array_scan_2b

def maxj_readline_func(expand_data_to_fit_line, nb_px_fast, offset, nb_el_line_list, ct_i, ishg_EOM_AC_flag, ovrsmp_ph, oversampling00, oversampling, method_fast, numpy):
    # # only if read_duration_lines
   
    if (method_fast and expand_data_to_fit_line):
        max_j = int(round(nb_px_fast - offset)) # # max_j is the whole line
        oversampling = int(round((nb_el_line_list[ct_i]/nb_px_fast))) # round
        if ishg_EOM_AC_flag: # iSHG fast, special case
            ovrsmp_ph = round(ovrsmp_ph/oversampling00*oversampling)
    else: # method_slow or not expand_data_to_fit_line
        max_j =  int(min(round(round(nb_el_line_list[ct_i]/oversampling - offset)), nb_px_fast)) # # added int 2019.06.12
    # # print('offsetl11', offset, max_j, nb_px_fast)
    return max_j, oversampling, ovrsmp_ph
    
def extract_onePXorline_from_buffer(numpy, method_is_fast, use_volt_not_raw, use_median, data, num_pmt, pack_param, min_val_volt_list, max_val_volt_list, max_value_pixel, ct):
    
    if not method_is_fast: # slow (usually line by line)
        [ind_data_down, ind_data_up, axis_sum, avg_px] = pack_param
        # # print('walla 26', axis_sum)

        if ind_data_down < numpy.size(data, 1):
            if use_volt_not_raw:
                avg_val = numpy.round((numpy.sum(data[num_pmt, ind_data_down: ind_data_up ]- min_val_volt_list[ct], axis=axis_sum))) #/len(data[0, ind_data_down: ind_data_up ]) - min_val_volt_list[ct])/(max_val_volt_list[ct] - min_val_volt_list[ct])*(max_value_pixel)) # it's faster to use sum rather than mean                                 
            else:  # min_val_volt_list is in int16
                if use_median:
                    avg_val = numpy.median(data[num_pmt, ind_data_down: ind_data_up ] - min_val_volt_list[ct], axis=axis_sum)/(max_val_volt_list[ct]-min_val_volt_list[ct])*max_value_pixel
                else: # avg
                    avg_val = numpy.sum(data[num_pmt, ind_data_down: ind_data_up ]- min_val_volt_list[ct], axis=axis_sum)  #numpy.round( /len(data[0, ind_data_down: ind_data_up ]) /(max_val_volt_list[ct]-min_val_volt_list[ct])*max_value_pixel # is in uint
            if (avg_px and not use_median):
                avg_val = round(avg_val/len(data[0, ind_data_down: ind_data_up ])/(max_val_volt_list[ct]-min_val_volt_list[ct])*max_value_pixel)
        else:
            avg_val = 0
                
        return avg_val
        
    else: # fast : many lines
        [slice_data, oversampling, avg_px, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D ] = pack_param
        # # print('walou', data[num_pmt, slice_data].reshape(-1, round(oversampling))[:, slice_dead_samps].shape, oversampling, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D, slice_data, data.shape )
        # # prod = (len(data[0, :oversampling][ slice_dead_samps])*len(data[0, slice_data])/oversampling)
        # # print(prod)
        # # err
        # # slice_dead_samps is used for ISHG, otherwise the whole vect
        if use_volt_not_raw:
            arr_xfast = numpy.round(numpy.sum((data[num_pmt, slice_data].reshape(-1, int(round(oversampling))))[:, slice_dead_samps].reshape(reshpr_samps_perps_ishg) - min_val_volt_list[ct], axis=1)).reshape(reshpr_arr3D) # slice_data = : # /(max_val_volt_list[ct]-min_val_volt_list[ct])*(max_value_pixel-1)

        else:
            # # print('!!', min_val_volt_list[ct], numpy.amin(data), slice_data, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D)
            # # reshpr_samps_perps_ishg is NONE if no ISHG !!!!
            if use_median:
               arr_xfast = (numpy.median((data[num_pmt, slice_data].reshape(-1, int(round(oversampling))))[:, slice_dead_samps].reshape(reshpr_samps_perps_ishg), axis=1)-min_val_volt_list[ct])/(max_val_volt_list[ct]-min_val_volt_list[ct])*max_value_pixel.reshape(reshpr_arr3D)
            else: # avg or sum
                # # print('ct!!!l59',num_pmt,slice_data, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D) #"data.shape, ct, num_pmt, slice_data, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D)
                arr_xfast = numpy.sum((data[num_pmt, slice_data].reshape(-1, int(round(oversampling))))[:, slice_dead_samps].reshape(reshpr_samps_perps_ishg) - min_val_volt_list[ct], axis=1).reshape(reshpr_arr3D)  # numpy.round((numpy.mean(data[num_pmt, slice_data].reshape(-1, round(oversampling)), axis=1)-min_val_volt_list[ct])/(max_val_volt_list[ct]-min_val_volt_list[ct])*((max_value_pixel-1)/2)).reshape(reshpr_arr3D) # is in uint
            
        if (avg_px and not use_median):
            fact = max_value_pixel/oversampling/(max_val_volt_list[ct]-min_val_volt_list[ct])
            arr_xfast = numpy.round(arr_xfast*fact)       
            
        return arr_xfast     
        
def fast_array_onebuffer(numpy, range_forloop_pmt, y_fast, array_Nd, missing_samps_atendnotright_bidirek, buffer_manylines_samesize, scan_mode, unidirectional, i, use_volt_not_raw, use_median, data, min_val_volt_list, max_val_volt_list, max_value_pixel, pack_param, st_i, st_i_b, end_i_b, nb_px_fast, nb_ph, frst_j, max_j, reshpr_arr3D, ind_pmt):
    
    if array_Nd.ndim >= 4: # # ishg fast
        a = list(reshpr_arr3D); a.append(nb_ph)
        reshpr_arr3D = tuple(a) # # append to a tuple ...
    pack_param[-1] = reshpr_arr3D
    norm_dir = 1; st_ip = 0
    if not unidirectional: # k bidirek only
        if buffer_manylines_samesize: # static acq. or acq. with all buffer's line are the same size
            if ((st_i+1) % 2): # st_i is even
                st_ip = 0 #st_i
            else:  # st_i is odd
                st_ip = 1 #st_i+1
        else:
            st_ip = 0 #st_i
        if (missing_samps_atendnotright_bidirek and ((i % 2) or buffer_manylines_samesize)): # i is odd ( 1st line ...) DECREASING (bidirek)
            norm_dir = 0   
    
    if norm_dir:  # direct dir.      
        range_j = numpy.s_[frst_j:max_j] # # frst_j = 0 for standard
    else: # reverse
        range_j = numpy.s_[nb_px_fast-max_j: nb_px_fast-frst_j]
    range_ii = numpy.s_[st_i_b:end_i_b] # range_j is range_j
    if y_fast: # yfast
        range_ii00 = range_ii; range_ii = range_j
        range_j = range_ii00 # 
    
    ct = 0
    for num_pmt in range_forloop_pmt:
        # # print('num pmt', num_pmt)          
        if (len(range_forloop_pmt)==1 and len(num_pmt)==1): # only one PMT
            num_pmt = 0
        # # range_forloop_pmt = [0,1] for 2pmts with different offsets
        arr_xfast = extract_onePXorline_from_buffer(numpy, True, use_volt_not_raw, use_median, data, num_pmt, pack_param, min_val_volt_list, max_val_volt_list, max_value_pixel, ct) # # true for fast
        if (not unidirectional and ((i % 2) or buffer_manylines_samesize)): # i is odd ( 1st line ...) DECREASING (bidirek)
            print('pmtsss', ind_pmt,arr_xfast.shape) 
            if arr_xfast.ndim >= 3: # # many PMTS
                arr_xfast[ind_pmt, st_ip::2, :] = arr_xfast[ind_pmt, st_ip::2, ::-1] # step is the last el.
            else: arr_xfast[ind_pmt, :] = arr_xfast[ind_pmt, ::-1] # step is the last el.
                
            # # ind_pmt is here for indexing if 2 PMTs are used at same time, otherwise None
            # # if len(reshpr_arr3D) >= 3: # # many PMTS
            # #     # # print(arr_xfast.shape, reshpr_arr3D)
            # #     arr_xfast = numpy.roll(arr_xfast, round(len(arr_xfast[0])/2), axis=2) #numpy.squeeze(arr_xfast) # takes time ?? 

        #'''
        # # print(range_j.shape, arr_xfast.shape, array_3d[num_pmt, st_i_b:end_i_b, range_j].shape, array_3d[num_pmt, st_i_b:end_i_b, :max_j].shape)
        #'''  
        # # print('num pmt', num_pmt, arr_xfast.shape) 
    
        if y_fast:    
            arr_xfast = arr_xfast.T
            # if indices overpass data's limits, it just return 0 (sum([]) = 0), no error raised
        
        if array_Nd.ndim >= 4: # # ishg with one  or many PMT
            array_Nd[num_pmt, range_ii, range_j, :] = arr_xfast #  # axis1 is phshft
        else: # # standard
            array_Nd[num_pmt, range_ii, range_j] = arr_xfast # array is passed by reference
        
        ct+=1
        # # a=numpy.amin(arr_xfast)
        # # if a<0:
        # #     print('arr2!!', a)


def ishg_EOM_fill_func(nb_ph, nb_samps_perphsft, data, array_ishg_4d, ramp_offset_nbsamps_list, pack_ind , oversampling, ovrsmp_ph, num_pmt, meth_fast_fill, use_volt_not_raw, use_median, avg_px, min_val_volt_list, max_val_volt_list, max_value_pixel, ct, range_forloop_pmt, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D, ind_pmt, numpy):
    '''
    contact maxime.pinsard@outlook.com, or legare@emt.inrs.ca to obtain this fast I-SHG fill function
    '''
    print('\n \n ERROR : contact code owner to unlock !')
    raise(ValueError) 
    
    

def func_resize_arr(kk,  max_j_list, data, ovrsamp_temp, nblines, str_add, slice_data, tup_pb, num):
    old_m = max_j_list[kk]
    max_j_list[kk] =  int(len(data[0, slice_data])/ovrsamp_temp/nblines) # by ref
    print('warning: (%s, kk=%d) I had to decrease the number of columns to %d (was %d) because exposure_time*rate %s was over nb_samps in buffer!' % (num, kk, max_j_list[kk], old_m,  str_add), tup_pb)

    # # print(len(data[0, slice_data]), ovrsamp_temp,nblines)
    return kk-1 # # redo this

def fill_array_scan_good2(avg_px, nb_px_fast, nb_lines_treat, oversampling, data, array_3d, array_ishg_4d, numpy, max_val_volt_list, st_i, end_i, max_j_list00, verbose,  nb_pmt_channel, max_value_pixel, y_fast, unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse, min_val_volt_list, use_volt_not_raw, use_median, range_forloop_pmt, nb_el_line_list, scan_mode, expand_data_to_fit_line, missing_samps_atendnotright_bidirek, skip_behavior, ishg_EOM_AC_insamps):
    '''
    Used in static acq. (several full lines per packet)
    Used in stage scan (line by line)
    Used with galvos & line time measure (line by line)
    '''
    # # print('arr1!!',method_fast)
    # # print('arr1!!', unidirectional, method_fast, read_buffer_offset_direct, read_buffer_offset_reverse)#numpy.amin(array_ishg_4d), max_j_list00)
    max_j_list = max_j_list00 # list( # not to change max_j_list00  ?
    ind_data_packet = 0
    off_b = max_data_beg = 0
    read_buffer_offset_reverse = read_buffer_offset_reverse*(-1) # -1 very important !!!
    # # print('unidirectional', unidirectional, read_buffer_offset_direct, read_buffer_offset_reverse)
    # # print('range_forloop_pmt', range_forloop_pmt, data.shape, numpy.mean(data[0]), numpy.mean(data[1]))
    # # print('oversampling in fillloop', oversampling)
    oversampling00 = oversampling # to keep
    slice_dead_dflt = slice(None)
    ishg_EOM_AC_flag = (ishg_EOM_AC_insamps[0] and array_ishg_4d is not None) # ishg_EOM_AC_insamps[0] ==2 --> array_ishg_4d None !!
    # # print('ishg_EOM_AC_flag', ishg_EOM_AC_flag, array_3d,  array_ishg_4d)
    if ishg_EOM_AC_flag:
         # # ishg_EOM_AC_insamps is [flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime] with the times in nb smps !!
        ramp_offset_nbsamps_list = ishg_EOM_AC_insamps[-2] # # list of offset, in samps
        nb_ph = ishg_EOM_AC_insamps[2]; nb_samps_perphsft = ishg_EOM_AC_insamps[5]
        ovrsmp_ph = ishg_EOM_AC_insamps[-1][1] # # oversampling for the phase-shifts, ramp_time00 + dead_time_begin + dead_time_end
        # # only for FAST
        # # see EOMph_nb_samps_phpixel_meth
        end_slice = -ramp_offset_nbsamps_list[2] if ramp_offset_nbsamps_list[2] != 0 else None # no other way to say "end" as in Matlab
        slice_dead_samps = numpy.s_[ramp_offset_nbsamps_list[1]+ramp_offset_nbsamps_list[0]:end_slice]
        off_begline_eom = ramp_offset_nbsamps_list[3]
        if off_begline_eom > 0: data = data[:, :, off_begline_eom:] if data.ndim == 3 else data[:, off_begline_eom:] # erase samples at beginning of lines (stabilization of eom)
        
    else:
        ramp_offset_nbsamps_list = [0, 0, 0, 0] # dflt
        ovrsmp_ph = float('Inf') # very high value not to be considered

    if (skip_behavior is not None and skip_behavior[2] is not None):
        # # skip_behavior is [nb_skip,  pause_trigger_diggalvo,  callback_notmeasline, unirek_skip_half_of_lines]
        nb_skip = skip_behavior[0]
        read_duration_lines = not skip_behavior[2]
        unirek_skip_half_of_lines = skip_behavior[-1]
    else: read_duration_lines = unirek_skip_half_of_lines = nb_skip = False # # static, stage, or mode without sync 
    buffer_manylines_samesize = (scan_mode == -1 or (scan_mode == -2 and not read_duration_lines) or (scan_mode == 1 and skip_behavior[1] and not read_duration_lines)) # # static or anlg galvos with callback each lines (no measure)
    
    dim1 = 2 if data.ndim == 3 else 1
    # print('dim1', max_j_list[0])
    if numpy.size(data, dim1) < round(oversampling)*max_j_list[0]: # not enough samples
        if data.ndim == 3: arradd = numpy.zeros((numpy.size(data,0), numpy.size(data,1), round(oversampling)*max_j_list[0]-numpy.size(data, 2)))
        else: arradd = numpy.zeros((numpy.size(data,0), round(oversampling)*max_j_list[0]-numpy.size(data, 1)))
        data=numpy.concatenate((data, arradd), axis=dim1) # # add some zeros to not loose any samples
    
    if buffer_manylines_samesize: # # need to reshape data 
        if data.ndim == 3: # # galvos with callback line-by-line, the lines being stored in the 3rd dimension
            # # data is (nb_PMT, nb_line_inpacket, nb_samples_oneline)
            # # else, if too many samples, it will be croped anyway !!
            st=max(0,round(nb_skip))
            data = data[:, :, st:(round(oversampling)*max_j_list[0]+st)].reshape((numpy.size(data,0), round(oversampling)*max_j_list[0]*numpy.size(data,1))) 
            # # data is now (nb_PMT, nb_samples_oneline*nb_line_inpacket) croped to round(oversampling)*max_j_list[0] for each lines
            # # otherwise nb_rows = 1 !
            # # print('dsd', round(oversampling)*max_j_list[0], data.shape)
        # # else:  # # ndim2, static
        if (numpy.size(data, -1)/oversampling < (end_i-st_i)*max_j_list[0]): max_j_list[0] = int(numpy.size(data, -1)/(oversampling*(end_i-st_i))) # # do not treat last columns if not enough samples in the array # data = data[:, :round(oversampling)*max_j_list[0]] # because of off_begline_eom !!
        if (ishg_EOM_AC_flag and (numpy.size(data, -1)/ovrsmp_ph < (end_i-st_i)*max_j_list[1])): max_j_list[1] = int(numpy.size(data, -1)/(ovrsmp_ph*(end_i-st_i))) # # do not treat last columns if not enough samples in the array # because of off_begline_eom !!
        if len(data[0]) % round(oversampling): # # not a divider
            data = data[:, :(end_i-st_i)*round(oversampling)*max_j_list[0]]
                    
    if (method_fast == 1 or method_fast == 12):
        
        if buffer_manylines_samesize: # static acq. or anlg galvo with callback , each buffer is excatly the same size
            st_i_b = st_i ; end_i_b = end_i
            # # max_data_end = numpy.size(data,1) # # WARNING : max_data_end is never reached in the array, last value of :max_data_end is max_data_end-1 !!
        # # max_data = numpy.s_[:max_data_end]

        ct_i = 0
        for i in range(st_i, min(end_i, nb_lines_treat)): # ind_disp in (1, nb_it_full+1)
        # for static acq: no loop, all lines treated at once (break after)
            if (scan_mode != -2 or not unidirectional or not unirek_skip_half_of_lines or (i+1) % 2):  # i is even ( 0th line ...)
            # #  for anlg galvos 9-2), if unidirek one acq over 2 are garbaged
                
                if (ct_i > 0 and scan_mode == 1 and nb_el_line_list[ct_i] < nb_el_line_list[ct_i-1]/2): # # scan_mode == 1 is galvos digital
                    print('unusual line time of # el:', nb_el_line_list[ct_i], 'compared to', nb_el_line_list[ct_i-1] ) # unusual line time

                if (unidirectional or ((i+1) % 2)): # i is even ( 0th line ...) INCREASING
                    offset = read_buffer_offset_direct
                else: # k is odd DECREASING (only for bidirek)
                    offset = read_buffer_offset_reverse
                if (scan_mode == -2 and unidirectional and unirek_skip_half_of_lines): # # anlg galvos AND undirek AND effectively have to skip half of the lines
                    off_b = - int(numpy.floor(i/2))
                
                if not buffer_manylines_samesize: # stage scan or galvos, line by line fill (each line can be slightly different in size)
                    st_i_b = i + off_b ; end_i_b = i+1 + off_b
                    
                if read_duration_lines:
                    max_j_list00 = max_j_list # # conserve
                    max_j_list[0], oversampling, _ = maxj_readline_func(expand_data_to_fit_line, nb_px_fast, ( offset) , nb_el_line_list, ct_i, False, None, oversampling00, oversampling, True, numpy) # # standard
                    # max(abs(read_buffer_offset_reverse),read_buffer_offset_direct)
                    if ishg_EOM_AC_flag: # # ishg fast
                        if max_j_list00[0] == max_j_list00[1]: # # oversampling fits ramptime_tot
                            max_j_list[1] = max_j_list[0]
                        else: # # oversampling DO NOT fits ramptime_tot
                            max_j_list[1], oversampling, ovrsmp_ph = maxj_readline_func(expand_data_to_fit_line, max_j_list[1], (offset), nb_el_line_list, ct_i, True, ovrsmp_ph, ovrsmp_ph, ovrsmp_ph, True, numpy) # # ishg 4D # # indeed 3 times ovrsmp_ph
                    nb_el = int(round(nb_el_line_list[ct_i]))    
                    if ind_data_packet + nb_el > len(data[0]): # pass all elements of the line, even the unused ones# int(round(max_j*oversampling)+round(offset*oversampling))+ind_data_packet > len(data[0]): # not enough samples left in the buffer
                        # print(int(round(max_j*oversampling)+round(offset*oversampling))+ind_data_packet, len(data[0]), ind_data_packet)
                        # not enough smp in buffer to treat COMPLETELY (fill + reject) this line
                        break # outside 'for' loop on i

                kk = kk_abs = -1 # set to +1 just after
                while kk < len(max_j_list)-1: # # 0 = standard and 1= ishg if needed
                    kk+=1; kk_abs+=1
                    if kk == 0: # standard, otherwise do only array ISHG
                        if array_3d is not None: ovrsamp_temp = oversampling  # # try ihg k=1 if array None
                        else: continue
                        str_add = ''
                    elif kk == 1: # # iSHG fast, special case 
                        if ishg_EOM_AC_flag: ovrsamp_temp = ovrsmp_ph  # # fill if ishg, else no # # there's an array to treat 
                        else: continue # will end # no treat ishg
                        str_add = '(+dead times)'
                    # # if not buffer_manylines_samesize: # galvos (or stage forced) : each buffer is slightly different in size
                    if offset != 0:  max_j_list[kk] -=  int(abs(offset )) # !!!
                    max_data_end = round(max_j_list[kk]*round(ovrsamp_temp)*(end_i_b-st_i_b)) # # will be int after
                    # # !! ovrsamp needs to be rund, otherwise max_data_end will not be a multiple of round(oversamp) for after !!
                    # # WARNING : max_data_end is never reached in the array, last value of :max_data_end is max_data_end-1 !!
                    # # print('a3d', ovrsamp_temp,offset )
                    max_data_beg = 0
                    if not buffer_manylines_samesize: # # otherwise the offset must not be set at the beginnig of each big buffer, but of each lines ...
                        ind00 = ind_data_packet + int(round(offset*ovrsamp_temp)) # offset can be < 0 !!
                        max_data_beg = max(ind00, max_data_beg) # ramp_offset_nbsamps_list[0]
                        if read_duration_lines:
                            max_data_end += max_data_beg  # # increase it !
                            # # because the slice here is not including the unused samples in the window
                            add = min(0, ind00)
                        else: add =ind00
                        max_data_end += add #min(0, ind00)  # # if ind00 < 0, has to remove it to max_data_end also
                    if kk == 1: # # iSHG fast, special case, corrects the max_data_end
                        max_data_end = min((max_data_end-max_data_beg)-(max_data_end-max_data_beg)%ovrsmp_ph+ max_data_beg, max_data_end) # # if the requested ramp samples are too large for the array, adjust the good number of columns
                    # # print('max_data_beg', max_data_beg, max_data_end)
    
                    if max_data_end == 0: # unlikely
                        max_data_end = len(data[0])
                    if max_data_end <= max_data_beg:
                        print('ERROR!, slice_data will contain 0 element !')
                        raise(ValueError)
                    
                    # # print('range_forloop_pmt', range_forloop_pmt, type(range_forloop_pmt), max_j_list[kk],round(ovrsamp_temp),(end_i_b-st_i_b))
                    if (len(range_forloop_pmt)==1 and len(range_forloop_pmt[0])>1): # many PMTs same time
                        reshpr_arr3D = (len(range_forloop_pmt[0]), (end_i_b-st_i_b), max_j_list[kk])
                        ind_pmt = range_forloop_pmt[0] # # ind_pmt is here for indexing if 2 PMTs are used at same time, otherwise None
                        if kk == 1: reshpr_samps_perps_ishg = ((end_i_b-st_i_b)*max_j_list[kk]*nb_ph*nb_pmt_channel, nb_samps_perphsft)
                    # elif len(range_forloop_pmt)>1: # many PMTs treated one after another
                    #     
                    else: # # one PMT
                        reshpr_arr3D = ((end_i_b-st_i_b), max_j_list[kk])
                        ind_pmt = 0 if nb_pmt_channel > 1 else None # # ind_pmt is here for indexing if 2 PMTs are used at same time, otherwise None
                        if kk == 1: reshpr_samps_perps_ishg = ((end_i_b-st_i_b)*max_j_list[kk]*nb_ph, nb_samps_perphsft) # # no *nb_pmt_channel !!!
                        
                    slice_data = numpy.s_[max_data_beg:int(max_data_end)] # # WARNING : max_data_end is never reached in the array, last value of :max_data_end is max_data_end-1 !!
                    # # print(max_data_end, max_j_list[kk], kk)
                    if kk == 0: # # array3D
                        prod_reshpr = numpy.prod(reshpr_arr3D)*round(oversampling) # # for check err only
                        prod = len(data[0, slice_data]) # # for check err only
                        if nb_pmt_channel > 1: prod_reshpr = prod_reshpr*nb_pmt_channel  # # for check err only
                        tuple_reshpr_ishg = (max_j_list[kk], 1, round(oversampling)) # # for disp err only
                        slice_dead = slice_dead_dflt # # for disp err only
                    elif kk == 1: # # not enough samples in the buffer ! # # ishg fast
                        if max_data_end > len(data[0]):
                            if kk_abs < 2:# should be maximum 1 normally
                                kk=func_resize_arr(kk,  max_j_list, data, ovrsmp_ph, (end_i_b-st_i_b), str_add, slice_data, (max_data_end , len(data[0])), '1st') # max_j_list by ref
                                continue # # redo this
                            else: # not to do it infinitely
                                print('ERROR1, tried too many times to resize array to fit the nb samples in buffer !', max_data_end , len(data[0])) 
                        tuple_reshpr_ishg = (max_j_list[kk], nb_ph, nb_samps_perphsft)
                        # # print('slice_data', slice_data, max_data_end, max_j, ovrsmp_ph, data.shape)
                        # # print('adaff', ovrsmp_ph, slice_dead_samps, slice_data) #(end_i_b-st_i_b),max_j_list[kk],nb_ph,nb_pmt_channel, nb_samps_perphsft)
                        prod_reshpr = numpy.prod(reshpr_samps_perps_ishg) # # for check err only
                        if (ind_pmt is None or ind_pmt == 0): prod_reshpr = prod_reshpr*nb_pmt_channel # # pmts are treated one by one
                        prod = (len(data[0, :ovrsmp_ph][ slice_dead_samps])*len(data[0, slice_data])/ovrsmp_ph)
                        slice_dead = slice_dead_samps # # for check err only
                    if nb_pmt_channel > 1: prod = prod*nb_pmt_channel  # # for check err only

                    if prod_reshpr != prod:
                        # # print(len(data[0, :ovrsmp_ph][ slice_dead_samps]), len(data[0, slice_data]), ovrsmp_ph)
                        str_lit ='nbcol*nb_ph, nb_samps_ps)'; str_num = '%d*%d, %d)'; 
                        str_while = 'while ovrsmp_ph[slice_dead_samps]*data[slice_data]/ovrsmp_ph '
                        tuple_while = (ovrsamp_temp, ); str_tupwhile = '%d *'
                        if (end_i_b-st_i_b) > 1: str_lit = 'nblinebuff*'+str_lit; str_num='%d*'+str_num; tuple_reshpr_ishg = ((end_i_b-st_i_b),) + tuple_reshpr_ishg
                        if nb_pmt_channel>1: 
                            str_lit = 'nbPM*'+str_lit; str_num='%d*'+str_num; tuple_reshpr_ishg = (nb_pmt_channel, ) + tuple_reshpr_ishg 
                            str_while = 'nbPM*' + str_while; tuple_while = (nb_pmt_channel,)+tuple_while; str_tupwhile = '%d*'+str_tupwhile
                        print(kk, 'WARN : ('+str_lit+', ('+str_num % tuple_reshpr_ishg, ' =', prod_reshpr, str_while, str_tupwhile % tuple_while, slice_dead,  slice_data, ' =', prod, '!! ', 'nbcol', max_j_list, 'datashape=', data.shape)
                        # # if kk == 1: # # ishg fast
                        if kk_abs < 2:# should be maximum 1 normally
                            kk=func_resize_arr(kk,  max_j_list, data, ovrsamp_temp, (end_i_b-st_i_b), str_add, slice_data, (prod_reshpr,  prod), '2nd') # max_j_list by ref
                            continue # # redo this
                        else:
                            print('ERROR2, tried too many times to resize array to fit the nb samples in buffer !')
                            raise(ValueError)
                        # # elif kk ==0: raise(ValueError)
                    
                    if kk == 0: # standard, otherwise do only array ISHG
                        # print('arr32!!', numpy.amin(array_3d),range_forloop_pmt, y_fast,  missing_samps_atendnotright_bidirek, buffer_manylines_samesize, scan_mode, unidirectional, i, use_volt_not_raw, use_median, min_val_volt_list, max_val_volt_list, max_value_pixel, [slice_data, oversampling, avg_px, slice(None), None, None], st_i, st_i_b, end_i_b, nb_px_fast, None, 0, max_j_list[kk] )
                        fast_array_onebuffer(numpy, range_forloop_pmt, y_fast, array_3d,  missing_samps_atendnotright_bidirek, buffer_manylines_samesize, scan_mode, unidirectional, i, use_volt_not_raw, use_median, data, min_val_volt_list, max_val_volt_list, max_value_pixel, [slice_data, oversampling, avg_px, slice_dead_dflt, None, None], st_i, st_i_b, end_i_b, nb_px_fast, None, 0, max_j_list[kk], reshpr_arr3D, ind_pmt)  # # slice after rehsp, reshpr_samps_perps_ishg, reshpr
                        # # last none is nb_ph
                        
                    elif kk == 1: # iSHG fast, special case

                        ishg_EOM_fill_func(nb_ph, nb_samps_perphsft, data,  array_ishg_4d, ramp_offset_nbsamps_list, [buffer_manylines_samesize, scan_mode, y_fast, unidirectional, missing_samps_atendnotright_bidirek, i , slice_data, st_i, st_i_b, end_i_b, nb_px_fast, 0, max_j_list[kk]], None, ovrsmp_ph, None, True, use_volt_not_raw, use_median, avg_px, min_val_volt_list, max_val_volt_list, max_value_pixel, 0, range_forloop_pmt, slice_dead_samps, reshpr_samps_perps_ishg, reshpr_arr3D, ind_pmt, numpy) # # array passed by ref
                        # # True for Fast
            
            if buffer_manylines_samesize: # static acq.
                break # no loop, all lines treated at once        
            elif read_duration_lines:
                nb_skip1 = nb_skip[ct_i] if type(nb_skip) == numpy.ndarray else nb_skip
                # # print(nb_skip1)
                nb_el = int(round(nb_skip1 + nb_el_line_list[ct_i])) # pass all elements of the line, even the unused ones
                # # print(nb_el)

                if method_fast == 1: # fastest
                    ind_data_packet += nb_el
                    # # print(ind_data_packet ,  nb_el)
                else: # 1-2, delete takes a lot of time !!
                    data = numpy.delete(data, numpy.s_[:nb_el], 1) # delete done line, and the unused samples at the end of the line
            ct_i += 1
    
    
    else: # method slow
        '''
        # # VERSION pixel by pixel : VERY SLOW !
        # time was 0.39 sec per block of 160000*400/3 = 21333333 elts
        # with above method, time was 0.04 sec !
        # it's for methods like in stage scan where the number of pixels to put on each lines can change from line to line
        '''

        ct_i = 0
        for i in range(st_i, min(end_i, nb_lines_treat)): # ind_disp in (1, nb_it_full+1)
        
            offset = read_buffer_offset_direct if (unidirectional or ((i+1) % 2)) else read_buffer_offset_reverse  # k is odd DECREASING (only for bidirek)
            # k is even ( 0th line ...) INCREASING
        
            if (scan_mode != -2 or not unidirectional or not unirek_skip_half_of_lines or (i+1) % 2):  # i is even ( 0th line ...)
            # #  for anlg galvos, if unidirek one acq over 2 are garbaged
            
                if (scan_mode == -2 and unidirectional and unirek_skip_half_of_lines): # # anlg galvos AND undirek AND effectively have to skip half of the lines
                    i -= int(numpy.floor(i/2))
                    
                if read_duration_lines:
                    max_j_list00 = max_j_list # # conserve
                    max_j_list[0], _, _ = maxj_readline_func(expand_data_to_fit_line, nb_px_fast, offset, nb_el_line_list, ct_i, False, None, oversampling00, oversampling, False, numpy) # # standard
                    if ishg_EOM_AC_flag: # # ishg fast
                        if max_j_list00[0] == max_j_list00[1]: # # oversampling fits ramptime_tot
                            max_j_list[1] = max_j_list[0]
                        else: # # oversampling DO NOT fits ramptime_tot
                            max_j_list[1], _, _ = maxj_readline_func(expand_data_to_fit_line, max_j_list[1], offset, nb_el_line_list, ct_i, True, ovrsmp_ph, ovrsmp_ph, ovrsmp_ph, False, numpy) # # ishg 4D # # indeed 3 times ovrsmp_ph
                    
                    nb_el = int(round(nb_el_line_list[ct_i]))
                    # # print(ind_data_packet + nb_el, len(data[0]), ct_i, len(nb_el_line_list))
                    if ind_data_packet + nb_el > len(data[0]): # pass all elements of the line, even the unused ones# int(round(max_j*oversampling)+round(offset*oversampling))+ind_data_packet > len(data[0]): # not enough samples left in the buffer
                        # print(int(round(max_j*oversampling)+round(offset*oversampling))+ind_data_packet, len(data[0]), ind_data_packet)
                        # not enough smp in buffer to treat COMPLETELY (fill + reject) this line
                        break # outside 'for' loop on i
                # # if read_duration_lines:
                # #     # # print(nb_el_line_list[ct_i])
                # #     max_j_list00 = max_j_list # # conserve
                # #     max_j_list[0], _, _ = maxj_readline_func(expand_data_to_fit_line, nb_px_fast, 0, nb_el_line_list, ct_i, ishg_EOM_AC_flag, ovrsmp_ph, oversampling00, oversampling, False, numpy) # # standard # # false for Slow
                # #     if ishg_EOM_AC_flag: # # ishg fast
                # #         if max_j_list00[0] == max_j_list00[1]: # # oversampling fits ramptime_tot
                # #             max_j_list[1] = max_j_list[0]
                # #         else: # # oversampling DO NOT fits ramptime_tot
                # #             max_j_list[1], _, _ = maxj_readline_func(expand_data_to_fit_line, max_j_list[1], offset, nb_el_line_list, ct_i, ishg_EOM_AC_flag, ovrsmp_ph, ovrsmp_ph, ovrsmp_ph, False, numpy) # # ishg 4D # # indeed 3 times ovrsmp_ph
                    ct_i_b = 0
                else:
                    ct_i_b = ct_i
                
                # # print('offset!!', offset)
    
                for j in range(0, max(max_j_list)): # # max_j_list[0] is max_j standard
                
                    for kk in range(2): # # only one kk for standard (2 if ishg)
                        if kk == 0: # standard, otherwise do only array ISHG
                            if (array_3d is not None and j<max_j_list[0]): ovrsamp_temp = oversampling  # # try ihg k=1 if array None
                            else: continue
                            # str_add = ''
                        elif kk == 1: # # iSHG fast, special case 
                            if (array_ishg_4d is not None and j<max_j_list[1]): ovrsamp_temp = ovrsmp_ph  # # fill if ishg, else no # # there's an array to treat 
                            else: continue # will end # no treat ishg
                
                        if (unidirectional or ((i+1) % 2)): # k is even ( 0th line ...) INCREASING
                            ind_j = j
                        else: # k is odd DECREASING (only for bidirek)
                            ind_j = max_j_list[kk]-1 - j
                        if not y_fast:
                            ii = i; jj = j
                        else: # yfast
                            ii = j; jj = i

                        lintime = 0
                                # # print(kk)
                            # max_data_end = int(round(max_j_list[kk]*ovrsamp_temp))
                        # # if kk == 1: # # iSHG fast, special case
                        # #     max_data_end = min(max_data_end-max_data_end%ovrsmp_ph, ovrsmp_ph*(end_i_b-st_i_b)*max_j_list[kk]) # # if the requested ramp samples are too large for the array, adjust the good number of columns
                        # # !!
                        ind_data_down = max(0, round((ind_j+offset + ct_i_b*max_j_list[kk])*oversampling), lintime) + ind_data_packet
                        ind_data_up = min(len(data[0]), ind_data_down+round(oversampling))
                        
                        if ind_data_up > ind_data_down: # otherwise gonna be an empty vect
                        
                            # # print('range_forloop_pmt', range_forloop_pmt)
                            ct = 0
                            for num_pmt in range_forloop_pmt: 
                                if (len(range_forloop_pmt)==1 and len(num_pmt)==1): # only one PMT
                                    num_pmt = 0
                                    axis_sum = 0
                                elif len(range_forloop_pmt)>1:# many PMTs
                                    axis_sum = 0
                                else: axis_sum = 1 # many PMTs same gain
                                    
        
                                if (kk == 0 and array_3d is not None): # otherwise do only array ISHG
                                    array_3d[num_pmt, ii, jj] = extract_onePXorline_from_buffer(numpy, (method_fast == 1 or method_fast == 12), use_volt_not_raw, use_median, data, num_pmt, [ind_data_down, ind_data_up, axis_sum, avg_px], min_val_volt_list, max_val_volt_list, max_value_pixel, ct)
                                # if i == st_i or i == end_i-1:
                                #     print(round((ind_j+offset + ct_i*())*oversampling))
                                
                                elif (kk == 1 and ishg_EOM_AC_flag and array_ishg_4d is not None and j < max_j_list[1]): # iSHG fast,m special case
                                # # max_j_list[1] is max_j_ishg (=  if oversampling fits ramptimetot)
                                    ishg_EOM_fill_func(nb_ph, nb_samps_perphsft, data,  array_ishg_4d, ramp_offset_nbsamps_list, [ind_data_down, ii, jj, axis_sum], oversampling, ovrsmp_ph, num_pmt, False, use_volt_not_raw, use_median, avg_px, min_val_volt_list, max_val_volt_list, max_value_pixel, ct, None, None, None, None, None, numpy) # # array passed by ref
                                    # # False for Slow
                                    # # Nones are range_forloop_pmt, slice_dead_samps, reshpr_samps_perps_ishg    
                                ct+=1
                                
            if read_duration_lines:
                nb_skip1 = nb_skip[ct_i] if type(nb_skip) == numpy.ndarray else nb_skip
                nb_el = int(round(nb_skip1 + nb_el_line_list[ct_i])) # pass all elements of the line, even the unused ones 
                if method_fast in (0, 22): # fastest
                    ind_data_packet += nb_el
                else: # 22         
                    data = numpy.delete(data, numpy.s_[:nb_el], 1) # delete done line, and the unused samples at the end of the line
            ct_i += 1
    
    return ind_data_packet, ct_i
    
def fill_array_scan_digital2(avg_px, size_fast, size_slow, unidirectional, oversampling, data, array_3d, numpy, max_val_volt_list, ind_data_total, verbose, max_value_pixel, nb_pmt_channel, y_fast, min_val_volt_list, use_volt_not_raw, use_median, range_forloop_pmt, lower_lim, nb_skip):
    
    # # print('unidirectional', unidirectional)

    #ind1=0 
    ind_data = 0
    while True:
            
        i = int(numpy.floor(ind_data_total/oversampling/size_fast))
        
        if (ind_data > len(data[0]) or i>size_slow-1): # nb columns
            break
        
        if (unidirectional or ((i+1) % 2)): # i is even ( 0th line ...) INCREASING
            ind_j = int(numpy.floor(ind_data_total/oversampling)) % size_fast
        else: # i is odd DECREASING
            ind_j = size_fast-1 - (int(numpy.floor(ind_data_total/oversampling)) % size_fast)
        # print(i, ind_j)
            
        ct = 0
        for num_pmt in range_forloop_pmt:
            if len(range_forloop_pmt)==1:
                num_pmt = 0
                
            if use_volt_not_raw:
                avg_val = round(numpy.sum(data[num_pmt, ind_data:ind_data+oversampling ]- min_val_volt_list[ct])) # /oversampling - min_val_volt_list[ct])/(max_val_volt_list[ct]-min_val_volt_list[ct])*(max_value_pixel)) # it's faster to use sum rather than mean 
            else: # raw int16, # min_val_volt_list is in int16 !!
                if use_median:
                    avg_val = round(numpy.median(data[num_pmt, ind_data:ind_data+oversampling ]- min_val_volt_list[ct])/(max_val_volt_list[ct]-min_val_volt_list[ct])*((max_value_pixel-1)/2))
                else: # avg
                    avg_val = numpy.sum(data[num_pmt, ind_data:ind_data+oversampling ]- min_val_volt_list[ct]) #/oversampling )/(max_val_volt_list[ct]-min_val_volt_list[ct])*((max_value_pixel-1)/2) # is in uint
                    # already int
            if (avg_px and not use_median):  
                avg_val = round(avg_val*max_value_pixel/oversampling/(max_val_volt_list[ct]-min_val_volt_list[ct])  )
            
            if y_fast:
                array_3d[num_pmt, ind_j, i] = avg_val
            else: # x-fast
                array_3d[num_pmt, i, ind_j] = avg_val

            ct+=1
            
        ind_data += oversampling
        ind_data_total += oversampling
        if (((int(numpy.floor(ind_data_total/oversampling)) % size_fast) == 0) and i > 0): # FILL with 2 first points added 
            # # ind1+=1    
            # # print('walou', ind1) 
            ind_data += int(round(nb_skip*oversampling))
            # ind_data_total += 2*oversampling
            
        if ind_data+oversampling > lower_lim*oversampling: # if next ind_data is to be more than threshold
            break # outside j-loop
            
        
    return ind_data_total
