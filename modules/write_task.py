# -*- coding: utf-8 -*-
"""
Created on Tue May 1 09:35:13 2018

@author: Maxime PINSARD
"""
    
## go to init pos

def galvo_goToPos_byWrite(nidaqmx, analog_output_daq_to_galvos, meth_write, fact, y_fast, volt_fast, volt_slow, sample_rate_galvos, min_val_volt_galvos, max_val_volt_galvos, bits_write, use_volt_not_raw_write, time, numpy):
     # # **** Go to initial pos *****
     
    min_ao = analog_output_daq_to_galvos.channels.ao_min 
    max_ao = analog_output_daq_to_galvos.channels.ao_max    
    
    if max(volt_fast, volt_slow) > max_ao:
        if max(volt_fast, volt_slow) > max_val_volt_galvos:
            raise Exception('Max voltage to write is too high for the galvos and the DAQ (%.1f/%.1f)' % (max(volt_fast, volt_slow), max_val_volt_galvos))
        else:
            analog_output_daq_to_galvos.channels.ao_max = max_val_volt_galvos
            
    if min(volt_fast, volt_slow) < min_ao:
        if min(volt_fast, volt_slow) < min_val_volt_galvos:
            raise Exception('Max voltage to write is too high for the galvos and the DAQ (%.1f/%.1f)' % (max(volt_fast, volt_slow), min_val_volt_galvos))
        else:
            analog_output_daq_to_galvos.channels.ao_min = min_val_volt_galvos
     
    analog_output_daq_to_galvos.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
    analog_output_daq_to_galvos.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # start faster the Task
     
    if ('analog_output_daq_to_galvos' in locals() and analog_output_daq_to_galvos is not None):
        analog_output_daq_to_galvos.stop() # clear task
    samps_chan_temp = 1*fact # 
    
    regen_mode = analog_output_daq_to_galvos.out_stream.regen_mode
    analog_output_daq_to_galvos.out_stream.regen_mode = nidaqmx.constants.RegenerationMode.DONT_ALLOW_REGENERATION # it will generate only the first point in buffer
    xfer_req_cond = analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond
    
    buf = analog_output_daq_to_galvos.out_stream.output_buf_size

    if not (analog_output_daq_to_galvos.timing.samp_quant_samp_mode == nidaqmx.constants.AcquisitionType.CONTINUOUS):
        samps = analog_output_daq_to_galvos.timing.samp_quant_samp_per_chan
        analog_output_daq_to_galvos.out_stream.output_buf_size = samps_chan_temp 
        analog_output_daq_to_galvos.timing.samp_quant_samp_per_chan = samps_chan_temp
    else:
        analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = nidaqmx.constants.OutputDataTransferCondition.ON_BOARD_MEMORY_EMPTY
        print(analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond)
    
    if buf < samps_chan_temp:
        
        analog_output_daq_to_galvos.out_stream.output_buf_size += samps_chan_temp

    if use_volt_not_raw_write:
        pos_fast = volt_fast
        pos_slow = volt_slow
        typenp = numpy.float64
        
    else: # use int 16
        pos_fast = conv_volt2int16(volt_fast, min_ao, max_ao, bits_write)
        pos_slow = conv_volt2int16(volt_slow, min_ao, max_ao, bits_write)
        typenp = numpy.int16
    
    if not y_fast:
        init_pos = numpy.array([[pos_fast]*fact, [pos_slow]*fact], dtype = typenp) #
    # # analog_output_daq_to_galvos.write(init_pos, auto_start = True)
    meth_write(init_pos, timeout=0)
    analog_output_daq_to_galvos.start() 
    if not (analog_output_daq_to_galvos.timing.samp_quant_samp_mode == nidaqmx.constants.AcquisitionType.CONTINUOUS):
        analog_output_daq_to_galvos.wait_until_done(samps_chan_temp/sample_rate_galvos) 
    else:
        time.sleep(5/100) # 5 ms
    try:
        analog_output_daq_to_galvos.stop()
    except Exception as err:
        if err.error_type != nidaqmx.error_codes.DAQmxErrors.GEN_STOPPED_TO_PREVENT_REGEN_OF_OLD_SAMPLES:
            print(err)
        else: # not happy because the Task stopped and all samples were generated so samples could have been generated again in the mean time
            pass
    print('I have been to init pos')  
    analog_output_daq_to_galvos.out_stream.regen_mode = regen_mode # reset previous
    analog_output_daq_to_galvos.out_stream.output_buf_size = buf
    if not (analog_output_daq_to_galvos.timing.samp_quant_samp_mode == nidaqmx.constants.AcquisitionType.CONTINUOUS):
        analog_output_daq_to_galvos.timing.samp_quant_samp_per_chan = samps
    else:
        analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = xfer_req_cond
    analog_output_daq_to_galvos.stop() # 2nd to be sure
        
## write raster scan
 
def write_arrays_AO(analog_output_daq_to_galvos, meth_write, write_scan_before, use_velocity_trigger,  unidirectional, angle_rot_degree, cos_angle, sin_angle, one_scan_pattern_vect, line_slow_daq_vect, line_slow_daq_vect_last, correct_unidirektionnal, shape_reverse_movement, sample_rate_galvos, y_fast, nb_pts_daq_one_pattern, nb_line_prewrite, tolerance_nb_write_to_stop, nidaqmx, numpy, time, sideWrite_writeAcq_pipe, use_volt_not_raw_write, bits_write, daq_pos_max_slow, daq_pos_min_slow, nb_px_slow ):
       
    analog_output_daq_to_galvos.control(nidaqmx.constants.TaskMode.TASK_UNRESERVE) # empty the buffer
    analog_output_daq_to_galvos.control(nidaqmx.constants.TaskMode.TASK_COMMIT) # start faster the Task
    analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = nidaqmx.constants.OutputDataTransferCondition.ON_BOARD_MEMORY_EMPTY # is reset after an unreserve ...
    #analog_output_daq_to_galvos.channels.ao_data_xfer_req_cond = nidaqmx.constants.OutputDataTransferCondition.ON_BOARD_MEMORY_HALF_FULL_OR_LESS # is reset after an unreserve ...
    #min_ao = analog_output_daq_to_galvos.channels.ao_min 
    #max_ao = analog_output_daq_to_galvos.channels.ao_max
    
    line_x_dir = one_scan_pattern_vect
    line_y = line_slow_daq_vect
    
    plot_wvfrm = 0
    if plot_wvfrm:
        array_pos_X_shaft_tot=numpy.empty((0))
        array_pos_Y_shaft_tot=numpy.empty((0))
    
    if write_scan_before:
        start_auto_flag = False
        
    else:
        start_auto_flag = True
        # gen_per_chan_prev = analog_output_daq_to_galvos.out_stream.total_samp_per_chan_generated
        gen_per_chan_prev = 0
        if gen_per_chan_prev >= 2**32-1: #bug
            gen_per_chan_prev = 0
        
        nb_points_already_gen_min = nb_pts_daq_one_pattern
        # fact_begin = 2
        # if blink_after_scan:
        #     nb_points_already_gen_min = round(nb_pts_blinking/fact_begin) # for LIVE write
        # 
        # else:
        #     nb_points_already_gen_min = round(nb_pts_daq_one_pattern/fact_begin) # the Task will start in the loop, at first line
        
        nb_line_prewrite = min(nb_line_prewrite, nb_px_slow-1)
        # # print(nb_line_prewrite)
    
    arr_write = numpy.zeros((2,nb_pts_daq_one_pattern), dtype=numpy.int16)
    
    st_time_write_pos = time.time()

    for jj in range(nb_px_slow):
        
        fact_step_slow = jj/(nb_px_slow - 1)*(daq_pos_max_slow - daq_pos_min_slow)
        
        # # print('buf_size AO ', y_fast, unidirectional) #buf_size)

        if (unidirectional or ((jj+1) % 2)): # always if unidirek or jj even (0th line...) if bidirek
            if not y_fast:
                line_x = line_x_dir
    
        else:  # bidirek odd, order of vector is reversed
            if not y_fast:
                line_x = line_x_rev
        
        if not y_fast:
            
            if angle_rot_degree == 0: # don't loose time
                arr_write[0,:] = line_x
                if jj == nb_px_slow-1: # last one
                    arr_write[1,:] = line_slow_daq_vect_last
                else:
                    arr_write[1,:] = (line_y+fact_step_slow)
            else:
                arr_write[0,:] = line_x*cos_angle + (line_y+fact_step_slow)*sin_angle
                arr_write[1,:] = -line_x*sin_angle + (line_y+fact_step_slow)*cos_angle
        
        if write_scan_before:
            meth_write(arr_write, timeout=0) # the fastest, auto-start is False
            
            if plot_wvfrm:
                array_pos_X_shaft_tot = numpy.concatenate((array_pos_X_shaft_tot, arr_write[0,:])) 
                array_pos_Y_shaft_tot = numpy.concatenate((array_pos_Y_shaft_tot, arr_write[1,:]))
        
        else:  # write in LIVE
        
            if jj < nb_line_prewrite:
                # if not blink_after_scan:
                meth_write(arr_write, timeout=0) # there is a "continue" after
                    # the writer does NOT start the Task
                continue # to next iteration
                
            elif jj == nb_line_prewrite: # generation begins, and array is already prepared to be written !
                # # print('here')
                sideWrite_writeAcq_pipe.send(True) # tell the Acq that the pre-write is finished
                
                order_received = sideWrite_writeAcq_pipe.recv() # blocks until receive something
                
                if order_received == -1:
                    print('Poison-pill detected in write_process')
                    return False # False to quit the Process
                    # # break # outside big while loop, end of process
                    
                elif order_received == 0: # = 0
                    
                    print('Order to stop detected in write_process')
                    return True
                
                else: # go scan !
                    
                    analog_output_daq_to_galvos.start()
                # explicit start in all cases to avoid the problem of implicit start/stop in a loop
                # if not blink_after_scan:

            # writing in LIVE
            while True:
                
                nb_gen = analog_output_daq_to_galvos.out_stream.total_samp_per_chan_generated
                if ((nb_gen - gen_per_chan_prev) >= nb_points_already_gen_min):
                    if ((nb_gen - gen_per_chan_prev) != nb_points_already_gen_min):
                        print((nb_gen - gen_per_chan_prev))
                    gen_per_chan_prev = nb_gen
                    meth_write(arr_write, timeout= nb_pts_daq_one_pattern/sample_rate_galvos ) # the fastest
                    break
                else:
                    continue # not necessary
    
    print('Space remained in buffer ', analog_output_daq_to_galvos.out_stream.space_avail, '/', analog_output_daq_to_galvos.timing.samp_quant_samp_per_chan) 
    
    if write_scan_before:
        pass
    else: # write in live
        try:
            gen_per_chan_prev = 0
            while True:
                nb_gen = analog_output_daq_to_galvos.out_stream.total_samp_per_chan_generated

                print(nb_gen)
                tol = 2
                    
                gen_per_chan_prev = nb_gen
                if ((nb_gen >= nb_pts_daq_one_pattern*nb_px_slow )):
                    
                    break
                elif (nb_gen == gen_per_chan_prev) and (nb_gen >= nb_pts_daq_one_pattern*nb_px_slow  - tolerance_nb_write_to_stop):
                    
                    time.sleep(5/1000) # to allow final samps to be written
                    break
            analog_output_daq_to_galvos.stop()
        except Exception as err:
            if err.error_type != nidaqmx.error_codes.DAQmxErrors.GEN_STOPPED_TO_PREVENT_REGEN_OF_OLD_SAMPLES:
                print(err)
            else: # not happy because the Task stopped and all samples were generated so samples could have been generated again in the mean time
                pass
            
    print("--- %.6f seconds write time" % ((time.time() - st_time_write_pos)))
    
    if plot_wvfrm:
        import matplotlib.pyplot as plt
        print('array_pos_X_shaft_tot ', min(array_pos_X_shaft_tot),max(array_pos_X_shaft_tot))
        print('array_pos_Y_shaft_tot ', min(array_pos_Y_shaft_tot),max(array_pos_Y_shaft_tot))
        plt.close()
        plt.figure()
        plt.plot(array_pos_X_shaft_tot)
        plt.show(False)
        plt.figure()
        # plt.plot(array_pos_X_shaft_tot, array_pos_Y_shaft_tot)
        plt.plot(array_pos_Y_shaft_tot)
        plt.show(False)
        
        
    return True # return is used for LIVE write, True if the function has finished
        
import multiprocessing
class Write_live_AO_process(multiprocessing.Process):

    """
    class used to write live
    """

    def __init__(self, sideWrite_writeAcq_pipe):
    
        multiprocessing.Process.__init__(self)

        self.sideWrite_writeAcq_pipe = sideWrite_writeAcq_pipe
        
    def run(self):
        
        import numpy, time
        from modules import daq_control_mp2
        import nidaqmx
        import nidaqmx.stream_writers
        write_scan_before = 0 # by definition
        nb_ao_channel = 2 # X and Y
        
        while True: # loop on imgs
        
            order_received = self.sideWrite_writeAcq_pipe.recv() # blocks until receive something
            
            if order_received[0] == -1:
                print('Poison-pill detected in write_process')
                break # outside big while loop, end of process
                
            elif order_received[0] == 0: # = 0
                
                print('Order to stop detected in write_process')
                continue
                
            else: 
                if len(order_received) > 1: # new parameters
                    if ('analog_output_daq_to_galvos' in locals()):
                        analog_output_daq_to_galvos.close() # clear task
                        
                    write_scan_before, unidirectional, correct_unidirektionnal, shape_reverse_movement, nb_ao_channel, duration_one_line_real, duration_one_line_imposed, sample_rate_AO_wanted, sample_rate_AO_min_imposed, volt_pos_min_withDeadTime_fast, volt_pos_max_withDeadTime_fast, volt_pos_min_fast, volt_pos_max_fast, small_angle_step, nb_px_slow, volt_pos_blink, volt_begin_fast, volt_end_fast, volt_pos_min_slow, volt_pos_max_slow, use_velocity_trigger, blink_after_scan, min_val_volt_galvos, max_val_volt_galvos, duration_scan_prewrite_in_buffer, device_to_use, use_volt_not_raw_write, dev_list, ext_ref_AO_range = order_received[1][:28]
        
                    analog_output_daq_to_galvos, meth_write, nb_pts_daq_one_pattern, nb_points_fast, nb_points_return, nb_points_turn, buffer_write_size, shape_reverse_movement, correct_unidirektionnal, nb_pts_blinking, nb_pts_blinking_end , sample_rate_galvos, nb_line_prewrite, time_expected_sec = daq_control_mp2.define_AO_write_Task(nidaqmx, write_scan_before, unidirectional, correct_unidirektionnal, shape_reverse_movement, nb_ao_channel, duration_one_line_real, duration_one_line_imposed, sample_rate_AO_wanted, sample_rate_AO_min_imposed, volt_pos_min_withDeadTime_fast, volt_pos_max_withDeadTime_fast, volt_pos_max_fast, small_angle_step, nb_px_slow, volt_pos_blink, volt_begin_fast, volt_end_fast, volt_pos_min_slow, volt_pos_max_slow, use_velocity_trigger, blink_after_scan, min_val_volt_galvos, max_val_volt_galvos, duration_scan_prewrite_in_buffer, device_to_use, time_expected_sec, use_volt_not_raw_write, dev_list, numpy,None, [''], 0, [''], ext_ref_AO_range, None)
                
                angle_rot_degree, cos_angle, sin_angle, volt_begin_slow, volt_end_slow, y_fast, tolerance_nb_write_to_stop = order_received[1][28:]
                
                bits_write = analog_output_daq_to_galvos.channels.ao_resolution

                galvo_goToPos_byWrite(nidaqmx, analog_output_daq_to_galvos, meth_write, 4, y_fast, volt_fast_ini, volt_begin_slow, sample_rate_galvos, min_val_volt_galvos, max_val_volt_galvos, bits_write, use_volt_not_raw_write,  time, numpy)
                
                write_arrays_AO(analog_output_daq_to_galvos, meth_write, write_scan_before, use_velocity_trigger,  unidirectional, angle_rot_degree, cos_angle, sin_angle, volt_pos_min_withDeadTime_fast, volt_pos_max_withDeadTime_fast, volt_pos_min_fast, volt_pos_max_fast, volt_pos_min_slow, volt_pos_max_slow, nb_points_fast, nb_points_return, nb_points_turn, nb_pts_blinking, nb_pts_blinking_end, nb_px_slow, blink_after_scan, volt_begin_fast, volt_end_fast, volt_begin_slow, volt_end_slow, volt_pos_blink, correct_unidirektionnal, shape_reverse_movement, sample_rate_galvos, y_fast, nb_pts_daq_one_pattern, nb_line_prewrite, tolerance_nb_write_to_stop, nidaqmx, numpy, time, self.sideWrite_writeAcq_pipe, use_volt_not_raw_write, bits_write )

        
        if ('analog_output_daq_to_galvos' in locals()):
            analog_output_daq_to_galvos.close() # clear task
        
def conv_volt2int16(volt_1, min_ao, max_ao, bits_write):
    return round((volt_1-min_ao)*(2**(bits_write)-1)/(max_ao-min_ao)-2**(bits_write-1))
    
def conv_int16tovolt(daq_1, min_ao, max_ao, bits_write):
    return (daq_1 + 2**(bits_write-1))*(max_ao-min_ao)/(2**(bits_write)-1) + min_ao
