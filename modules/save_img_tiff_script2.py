# -*- coding: utf-8 -*-
"""
Created on Mon Oct 3 16:35:13 2016

@author: Maxime PINSARD
"""

def save_img_tiff2(os, subproc_call, path_save, list_row_selected, file_full_path_chosen, nb_field_table, save_meth, offset_table_img, pmt_txt_all, jobn, pack_saveRAM, shutil):
    """
    dict_tiff_really_disp ={ 270: 'ImageDescription', 272: 'Modelcamera',  33432: 'Copyright',  271: 'Camera', 305: 'Software', 315: 'Author'}
    """
    
    savefromRAM = pack_saveRAM[0]
    
    # print('file_full_path_chosen' , file_full_path_chosen)
    filename_no_ext = file_full_path_chosen[0][0:len(file_full_path_chosen[0])-4]
    # filename_no_ext = os.path.splitext(file_full_path_chosen)[0] # remove extension .tif from string
    filename_no_ext_folder = filename_no_ext
    current_dir = os.path.dirname(filename_no_ext) # the parent dir of the will-be created folder, also the dir for the stack tif
    # os.path.basename(str1)
        
    name_fdr = '%s_%s' % (jobn, list_row_selected[0].text())
        
    if round(len(list_row_selected)/nb_field_table) > 1: # no stack of folder for one file
        folder_img_indiv = ('%s/%s') % (current_dir, name_fdr)
        ct = 1
        while True:
            if not os.path.exists(folder_img_indiv):
                print(filename_no_ext_folder)
                os.makedirs(folder_img_indiv)
                break # outside this loop if succeed to create the folder
                
            else: # if the folder already exists
                folder_img_indiv = ('%s%d' % (folder_img_indiv[:-1], ct))
                ct += 1
            
    else: # 1 file
        folder_img_indiv = current_dir
        
    path_save = ('%s/tmp' % path_save)
    
    f = []
    for (dirpath, dirnames, filenames) in os.walk(path_save):
        f.extend(filenames) # list of files
        break

    if save_meth == 1: # save selected items
        
        index = list_row_selected[0].row() # get correct index in the list of name
        last_ind = round(len(list_row_selected)/nb_field_table)
        off_abs = index
        
    elif save_meth == 2: # save specified # of items
       
        index = list_row_selected[0] # get correct index in the list of name
        last_ind = list_row_selected[1]
        off_abs = index
        
    if savefromRAM: 
        _, pg_plot_scripts, datetime, numpy, PIL, param_ini, curr_row_img, list_arrays, self = pack_saveRAM
        # # print('aa3', curr_row_img)
        index = max(0, min(len(list_arrays) - offset_table_img - last_ind, index))
        last_ind = max(0, min(len(list_arrays) - offset_table_img - index, last_ind))
        

    folder_ll = [folder_img_indiv]
    pmt_c_prev = pmt_txt_all[0]
    pmt_diff_ll = [pmt_c_prev]
    # # print('afff', pmt_txt_all, )
    
    for i in range(index + offset_table_img , index + last_ind + offset_table_img):
        # # print(i, len(pmt_txt_all))
        try:
            pmt_c = f[i][-1-4]  # 4 for .tif
        except IndexError:
            print('indices', i-off_abs, '/',len(pmt_txt_all))
            pmt_c = '-1'
        # # print('afff2', pmt_c, i,off_abs)    
        if not(pmt_c in pmt_diff_ll): 
                         
            pmt_diff_ll.append(pmt_c)
            if pmt_txt_all.count(pmt_c) < 2:
                folder_ll.append(folder_ll[-1]) # last el
            else: # more than 1 image with this pmt
                folder_ll.append('%s/PMT%s' % (folder_img_indiv, pmt_c))
                os.makedirs(folder_ll[::-1][0])
        
        if pmt_c != pmt_c_prev:
            filename_no_ext_folder = filename_no_ext_folder[:len(filename_no_ext_folder)-1] + pmt_c
            # # print('d',  i,pmt_c, pmt_c_prev)
            pmt_c_prev = pmt_c
            
        # # print(filename_no_ext_folder)    
        folder_img_indiv = folder_ll[pmt_diff_ll.index(pmt_c)]
        
        new_dst_file_name = os.path.join(folder_img_indiv, (('%s_%d.tif') % (os.path.basename(filename_no_ext_folder), i)))
        
        if savefromRAM: # not classic
            
            pg_plot_scripts.display_save_img_gui_util (self, datetime, numpy, None,  None, None, PIL, os, param_ini, None, None, numpy.expand_dims(list_arrays[min(i,len(list_arrays)-1)], axis=0), [''], None, None, None, [False, curr_row_img, new_dst_file_name])   # # True for add new img (full func)
            # # jobs_scripts = img_hist_plot_mp = array_ishg_4d, array_ctr_3d, arrlist QtWidgets shutil, glob None
        else: 
            dst_file = os.path.join(folder_img_indiv, f[i])

            shutil.copy2(('%s/%s' % (path_save, f[i])), folder_img_indiv) # classic
            
            os.rename(dst_file, new_dst_file_name)
        
        # print('folder destination :', folder_img_indiv)
        # print('folder origin :', path_save, 'file ', f[i])
        # print('new_dst_file_name ', new_dst_file_name)
        # print('dst_file ', dst_file)
        
    # filename_no_ext = os.path.join(filename_no_ext_folder, os.path.basename(filename_no_ext))
    # for i in range(round(len(list_row_selected)/nb_field_table)):
    #     
    #     index = list_row_selected[i*nb_field_table].row() # get correct index in the list of name
    #     
    #     print(index)
    #     
    #     time_file = list_row_selected[3 + i*nb_field_table].text()
    #     
    #     current_pmt = list_row_selected[1 + i*nb_field_table].text()
    #     
    #     ImageDescription = ('PMT # %s ; obj %s; NA = %.2g ; scan_mode = %s ; Z_coarse = %.3g mm ; Z_piezo = %.3g um  ; X = %.3g mm, Y = %.3g mm ; exp_time = %d us ; size_x = %.3g um; size_y = %.3g um; stepX = %.3g um;  stepY = %.3g um  ; filter_top_pos = %d ; filter_bottom_pos = %d ; pos motor trans = %.3gum; time=%s ; name_set_up=%s ; model_camera=%s ; copyright=%s ; software=%s ; author=%s ;' % (current_pmt, objective_name, NA_obj, scan_mode, Z_coarse, Z_piezo, posX, posY, exp_time, size_x, size_y, stepX, stepY, filter_top_pos, filter_bottom_pos, pos_trans, time_file, name_camera, model_camera, copyright, software, author))
    #     
    #     dict_tiff_really_disp = { 270: ImageDescription} #,  271: name_camera, 272: model_camera,  33432: copyright, 305: software, 315: author} # useful to fill some tag of tiff, but makes ImageMagick bug
    #     
    #     result = PILImage.fromarray(list_arrays[index].astype(param_ini))
    #     name_final = ('%s_%s%d.tif' % (filename_no_ext, '0'*(len(str(round(len(list_row_selected)/nb_field_table)))-len(str(i+1))), i+1))
    #     
    #     result.save(name_final, tiffinfo= dict_tiff_really_disp)
    
    # conversion to a stack of images, and save it in current dir (not newly created folder)
    
    # # WARNING : has lead to some problemsin the past, so I advise to not use it
    '''
    2018.3.1 : tests
    lead to very bright images in a 1000+ frames stack, whereas individual images are ok
    what is strange is that with a call in python console, or in command prompt, this effect was not present...
    '''
    # if round(len(list_row_selected)/nb_field_table) > 1: # no stack of folder for one file
    #     subproc_call(('magick "%s/*.tif" "%s/%s.tif"' % (folder_img_indiv, current_dir, os.path.basename(filename_no_ext_folder))), shell=True)
    #     # double quote in path is for paths that contain spaces
    
        
    
    
    
    