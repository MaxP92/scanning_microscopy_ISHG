# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2016

@author: Maxime PINSARD
"""

import math, sys, numpy

## General GUI

name_camera = 'iMic Till Photonics'
model_camera = 'PMT Hamamatsu'
copyright = 'CC GPL'
software = 'python %s' % sys.version[0:31]
author = 'Maxime PINSARD'

nb_field_table = 4 # number of fields in the table qtablewidget for disp of names
posoffXY_wrt0_tablemain = 9 # offset X and Y
postransmtr_wrt0_tablemain = 10 # pos trans motor
posgpmtr_wrt0_tablemain = 11 # pos glass plate mtr TL
posTLpolarmtr_wrt0_tablemain = 12 # thorlabs
posNPpolarmtr_wrt0_tablemain = 13 # newport
posCard_wrt0_tablemain = 14 # acq card
posishgfast_wrt0_tablemain = 15 # ishgfast
pos_reducnblinesdisp_wrt0_tablemain = 16 # for disp, array is kept only at a certain fraction of his line number (tot%nb_lines), for memory save
posSat_wrt0_tablemain = 17 # sat value
name_dflt00 = 'untitled'
nb_cmap_ishg = 5

width_ImgDispGui = 1000
height_ImgDispGui = 700

max_size_recycle_Mo = 3000 # in Mo, 3Go
size_dflt_onefile = 0.314 # Mo, corresponding to a small image uint16 400x400PX

time_out_discon_sec = 2 # s, wait for instr to respond after order to quit
time_out_quit_qthreads_ms = 1000 # ms, wait for thread to quit

update_time = 0.33 # s, (blocksize) in InitImage

## PMT parameters

# pmt_channel = 2 # 1 for 1 channel ai0, 2 for 2 channels, 0 for ai1 only
# !! warning : even if it's coerced by the AI Task, keep the real min max values because they are used physically in the image 16bits conversion

# default
min_val_volt_list = [-0.095, -0.171, -0.095, -0.095] #-0.16# for now there are 4 PMTs
# -0.11 corresponds to a 500Ohm terminator, and the classic set-up (axis photonics ampli + R6357 and C7319). The max is then 10V.
max_val_volt_list = [10]*4 # seems to be 13 ! But is putting the range into:
# 40/4096/13*2**16 = 49 resolution (12 bits)
# 20/4096/10*2**16 = 32
# # 500 Ohm termination puts it close to 10V 

minval_volt_wrtgain_list = [[0, -0.120, -0.177], [200, -0.120, -0.177], [500, -0.100, -0.125], [700, 0.100, 0.100]] # measured with light outside the lab box, but main light is off

pre_amp_model_PMT_1 = 'C7319'
pre_amp_model_PMT_2 = 'C7319'
pre_amp_model_PMT_3 = 'C7319'
pre_amp_model_PMT_4 = 'C7319'

## Image parameters

avg_px = 0 # 1 for averaging (range expanded in uint16) 
# 2 for averaging (range in phys. limit int16) 
# 0 for sum (int32)

magn_obj_dflt = 20 # # can change it to 40
eff_na_20X = 0.75 # olympus
eff_na_40X = 1.15 # olympus

max_value_pixel_6259 = 2**16-1 # u16 bits = from 0 to 2^16-1
max_value_pixel_6110 = 2**12-1 # the 6110 is 12 bits read 

calibration_volt_6259 = 10.55/10
calibration_volt_6110 = 1 

use_volt_not_raw = 0
use_median = 0 # use an average dflt, or use a median to turn the oversampled into px

if use_volt_not_raw:
    type_data_read_temp = numpy.float64 # for AnlgReadF64
    precision_float_numpy = numpy.float32 # for array_3D
else: # uint16
    type_data_read_temp = numpy.int16 # for read into 16bits, the native format
    if avg_px == 0:
        precision_float_numpy = numpy.int32 # for array_3D # not uint !!
    else:
        precision_float_numpy = numpy.int16 # # for array_3D # not uint !!
         
bits_save_img = numpy.uint32
    
# because 2^E <= abs(X) < 2^(E+1) with E = 15 (worst case, meaning X is between 65000 and sat)
# if you use float16, precision is 2**(15-10) = 2**(5)=32 --> not good
# if you use float32, precision is 2**(15-23) = 2**(-8) = 4e-3 --> fair
# precision in practical at (1e-2)e4 = 1e2 --> limit !!!
# if you use float (float64), precision is 2**(15-52) = 7e-12 (highest value can be 2**16-1) --> too precise
# because 2^E <= abs(X) < 2^(E+1) with E = 13 (more classical case, meaning X is between 8000 and 16000)
# if you use float16, precision is 2**(13-10) = 2**(3)= 8 --> not good
# if you use float32, precision is 2**(13-23) = 2**(-10) = 1e-3 --> fair
#precision in practical at (1e-2)e4 = 1e2 --> limit !!!
# if you use float (float64), precision is 2**(10-52) = 2e-13  --> too precise
size_max_px_for_display = 400 # in PX
list_arrays_max_length = 9000 # 20000 is supposed to be closed to MemoryError

min_disp_perc = 0.95 # min displayed is 95% of the minimum
max_disp_perc = 1.05 # max displayed is 105% of the maximum

size_um_fov_20X = 400 # um
size_um_fov_40X = 200 # um

offsetX00_digGalvos = 0.07 #-0.11 # mm
offsetY00_digGalvos = -0.03 #0.052 # mm

offsetX00_anlgGalvos = 0. # mm
offsetY00_anlgGalvos = 0. # mm

offsetX00_stgscn = 0. # mm
offsetY00_stgscn = 0. # mm

nb_img_cont_dflt = 50

## imic parameters

port_imic ="com9"
empty_top_slider_pos = 0
empty_bottom_slider_pos = 0
mddle_top_slider_pos = 1
block_bottom_slider_pos = 2
mirrordirect_bottom_slider_pos = 1
str_top_slider_posmiddle = '50:50 BSW20R vis.' #'glass 170um unc.'
wait_time_chg_filter_sec = 2 # sec, < 1sec it does not block but vibrations appear
max_pos_Z_motor = 21.999
speed_motorZ_imic = 2 # mm/s
max_range_pz_imic = 0.25 # mm

"""
uses msl_loadlib version 0.4.1.dev0 and more
"""

## PI stage 

PI_conn_meth = 'rs232' # # 'usb'
if PI_conn_meth == 'rs232':
    PI_comport = 5 #17
    PI_baud = 57600
PI_CONTROLLERNAME = 'E-709'
PIezo_USB_ID = '0118071285'
PI_SERVOMODE = True # 1 = servo on (closed-loop operation) ; 0 = open-loop (servo OFF)
# # open loop resolution (0.4nm) is a lower value than the closed loop resolution (0.7nm) due to the noise of the sensor signal. Open loop is subject to hysteresis, meaning the position could be off by up to 15%. When operated in closed loop, the hysteresis is compensated for, and virtually eliminated.
use_PI_notimic = True # false to use the imic piezo (broken)
max_range_PI = 0.2 # mm

if use_PI_notimic:
    max_range_piezoZ = max_range_PI
else: # iMic
    max_range_piezoZ = max_range_pz_imic
    
PI_pack = [PI_conn_meth, PI_comport,  PI_baud, PI_SERVOMODE , PI_CONTROLLERNAME, max_range_PI]

## Analog-to-digital (ADC) DAQ card (NI) parameters

time_out = 2.0 # s
time_out_sync = 0.2 # as in labview
time_by_point = 20e-6 # s. by point

max_size_np_array = 2.5e6 # MemoryError at 10e6 for 2 big arrays, here I put a value safe so that max exp_time for a 500x500 px image is 1ms at max rate

meas_fact_forMaxBufferDAQ_add = 8.5 # measured (actually 8.4116)
max_buf_size_daq_AO_theo = round((2**32/(2*2)-2)) 
max_buf_size_AO_abs = int(max_buf_size_daq_AO_theo/meas_fact_forMaxBufferDAQ_add) + 1 # max buffer write alone measured

def calc_max_buf_size(nb_pmt_channel):
    # the theo value leads to error when commit the Task
    max_buffer_size_daq_read_theo = round((2**32/(2*nb_pmt_channel)-2))
    max_buffer_size_daq_read_abs = int(max_buffer_size_daq_read_theo/meas_fact_forMaxBufferDAQ_add) # max buffer allocated 1 chan abs (measured)
    max_buffer_AI_2chansW_chanR = int(max_buffer_size_daq_read_abs/3)
    max_buf_size_AO_chanR_2chansW = int(max_buffer_size_daq_read_abs/3) # there will be two chans at this buffer, so in theory it is x2
    return max_buffer_AI_2chansW_chanR, max_buf_size_AO_chanR_2chansW

max_divider_master_rate_daq = 3355443200 # 20e6/3355443200 measured smallest sample rate, for galvos
master_rate_daq_normal = 20e6
max_rate_multiRead_DAQ6110 = 5e6 # in datasheet
max_rate_multiRead_DAQ6259 = 1e6 # in datasheet
max_rate_multiRead_DAQCard = max_rate_multiRead_DAQ6110

# for stage scan
nbPreTriggerSamps_min_dflt = 10 # empirical value, 2 leads to some sporadic bugs in buffer
safety_nb_px_anlgScn = 200 #2 # 
safety_mult_stgscn = 1.2
eff_wfrm_anlggalv_dflt = 75 # #  %
# # read_buffer_offset_max = 0
# other
safety_fact_stgScn = 2 # I try to allocate an array twice as large, to be sure that the allocation of the real array will be fine
trig_src_end_chan_6110 = 'ai3'
trig_src_end_chan_6259 = 'ai0'
term_toExp_Ctr0Gate_forAnlgCompEvent_6110 = 'PFI9'
term_toExp_forAnlgCompEvent_6110 = 'Ctr0Gate' # Ctr0Gate is the ONLY relay for AnlgCompEvent via PFI9 for 6110. Otherwise, Ctr0Source via PFI8 or CTR1Source via PFI3 (Ctr1Gate cannot be exported)
ext_smpclk_end = 'PFI1'
smp_rate_AI_dflt = 4e6
ext_smpclk_minRate = 0.04e6 # Hz, lock-in has an output rate from 48 to 96kHz
ext_smpclk_maxRate = 0.1e6 # Hz, lock-in has an output rate from 48 to 96kHz

sample_rate_max_6259 = 1.0e6 # 1.25e6 is not recommended

use_RSE = 1 # otherwise diff of two channels

min_pulse_width_digfltr_6259_0 = 125e-9 # s, You Can Select:  0.000000,  2.560000e-3,  6.425000e-6,  125.0e-9
min_pulse_width_digfltr_6259 = 6.425000e-6 # s, You Can Select:  0.000000,  2.560000e-3,  6.425000e-6,  125.0e-9
min_pulse_width_digfltr_6259_2 = 2.560000e-3 # s

name_list_AI_tasks = ['read_AI_01']
name_list_trigctrl_tasks = ['trigctrl_01']
name_list_AO_tasks = ['write_AO_01']
name_list_watcher_tasks = ['watcher_01']
name_list_wr_dumb_tasks = ['wr_dumb_01']

factor_trigger_chan = 2 #3/1.4331
num_ctrdflt = 0

max_szarray_readAI_callbk = int(3e6) # over this size total of numpy array, the callback is too slow and bugs

## Digital Galvos parameters

galvo_rotation = 135 # deg
rotate = galvo_rotation*math.pi/180 # 0, rad
img_pixel = 500 # for labview, the size of the zone to define the scan

field_view = 0.006 # radius im Zwischenbild (intermediate image)
turn_time_unidirek = 0.0015 # # sec, as in labview

center_galvo_x00 = 2*-16.6442e-21 # corr. to zepto meter, center galvo SENSIBLE
center_galvo_y00 = 2*212.132e-6 # corr. to micro meter, is the double in LV ??

SM_cycle = 1e-5 # s
SM_delay = 119 # (number of cycles), galvo.delay, in Digital mode
scan_linse = 0.03500368  # in m, meaning 35mm focal for the SL

# really related to the galvos themselves
ohm_val = 4.1
induct_H = 9.8e-5
max_voltage = 23.0 # (V?)
inertia = 0.025 # g/cm^2
torque = 25000.0 # dyn cm/A

bit_size_galvo = 6.44e-7 # 
bits_16_36 = round(2**36/2**16) #1048576

time_base_ext = 0 # define if the digital galvos use an external time_base or internal (change a bit the sync value !!)

# if timebase_ext is 1
clock_galvo_digital = 8000000 # Hz # 10000000
min_timebase_div = 2 # in AD card
timebase_src_end = 'PFI1'
delay_trig = 0.000005 # 5e-6 s

trig_src_name_dig_galvos = 'PFI0'

max_offset_x_digGalvo = 2 # mm
max_offset_y_digGalvo = 2 # mm

eff_loss_dig_galvos = 0.16 # in unidrek mode

# # ********************************************
# # ----- digital galvos connection parameters--
# # ********************************************

ressource_dig_galvos = 'COM8'
baud_rate_dig_galvos= 57600
# # bits_galvo = 8
# # parity_galvo = constants.Parity.none
# # stop_bit_galvo = constants.StopBits.one
# # flow_control_galvo= 0
timeout_dig_galvos = 2# sec 2000 ms
# # read_termination_dig_galvo  = '\n'
# # write_termination_dig_galvo = read_termination_dig_galvo

last_buff_smallest_poss = True # # for dig galvos, last buffer will have the min number of lines (if bug)

numdev_watchTrig_diggalv = 0
nb_skip_sync_dig_pausetrig_measline_dflt = 1.0 # # use measure linetime with pausetrig (dig galvos)
nb_skip_sync_dig_recaststtrig_dflt = 2.0 # # use start trig and sync by calc (standard labview, dig galvos)
nb_skip_sync_dig_pausetrig_callback_dflt = 0 # # use pausetrig to callback each lines (dig galvos)

eff_unid_diggalvos = 0.84 # # dig galvos effciency for unidirek is estimated at 84% (5.7/6.8)

dll_diggalvos_timing = True # # if the code uses the DLL for galvo timing (with ctypes). Useful for unusual exposure times or scans.

## Anlg galvos new

# # 1 for 6259 and 0 for 6110
num_dev_AO = 1 # the device to write samples to move the galvos
num_dev_anlgTrig = 1 # the device used to just convert the analog trigger into a digital trigger
num_dev_watcherTrig = 1 # the device used to callback if trigger paused, or control trigger temporal width

term_trig_name_digital = 'PFI0' # can be any PFI
term_trig_name_6110 = term_trig_name_digital # on 6110, the PFI0 port can be used for analog AND digital triggers
term_trig_name_6259 = 'APFI0' # on 6259, the APFI0 port can be used for analog trigger (digital is on PFI0)

term_6110_clckExt = 'PFI7'
term_6110_trigExt = 'PFI9'
term_6259_clckExt = 'PFI7'
term_6259_trigExt = 'PFI9'

term_DI = 'port0/line0' # for 6259 only available, 6110 does not support changedetection, but it could be done with its sample_clock (on any PFI)
term_do = 'port0/line0' # # for  6259, available are any PFI, CTR1 OUT, CTR0OUT, FREQ OUT, P0. For 6110, any P0.0-7

trig_src_end_term_toExp_toWatcher = 'PFI8' # used only if different terminals have to be used for export to watcher and AI (usually unused) 
trig_src_end_toExp_toDIWatcher = 'PFI5' # # for digital input (not very used)

method_watch = 4 # 4 for counter out, 1 for chg detect (6259 only), 6 for counter input with possibility of dig. filter
# 7: # counter input to MEASURE the line time; # # !! is already changeable on the GUI's front-end
# 6: # counter input for callback, that counts the falling triggers edges
# 4 counter OUTPUT retriggerable that makes a pulse (for callback) each time the st trigger = pause trigger of read task is asserted
# 5 -
# 3  anlg trig watches itself (2 cards): callback on sample clock of an AI task (on other card), whose clock is the analogComparisonEvent of the main read
# 2 : DI with sample clock detect (callback on sample clock), has the drawback to have to set the rate,  FOR 6110 only
# 1 : DI with a callback on CHANGE_DETECTION_EVENT  # for 6259 only
use_callbacks = 1
export_smpclk = 0
export_trigger = 1
DI_parallel_watcher = 0 # use a digital input that watch the trigger and callback a send via Pipe when change on it 
DO_parallel_trigger = 0 # use a home-made pause trigger : an alg Task monitor it, and send a DO that acts as a digital trigger

use_chan_trigger = 1 # 0 to use a terminal port, 1 to use a channel

lvl_trigger_not_win = 2  # 1 for lvl anlg, 0 for window anlg, 2 for reject only vibration on top of the waveform
safety_lvl_trig_max_fact = 1.05 # fact to divide the max anlg lvl thres.
safety_fact_chan_trig = 1.1 # for the bound of anlg trigger read, if channel
# # triggerAddSafeFactor_imposed = 2# 1.1 # multiply by this factor the target voltages to be sure to get eventually outside the scan window
# # smp_rate_trig = 1e6 # sample rate used if an independant AI Task is anlg triggered, and export its trigger
use_dig_fltr_onAlgCmpEv = False  #False #False # use a digital filter on the counter output that watch the trig for it not to callback when jitter
use_trigger_anlgcompEv_onFallingEdges = True # using falling edges avoid inversion of terminal
# # print('!!!!! use_trigger_anlgcompEv_onFallingEdges is' , use_trigger_anlgcompEv_onFallingEdges)
use_diff_terms_expAI_expWatch = False #False ## use explictly different terminals to export trigger signal to AI and to watcher (from trigCtrl). Use it if it improves
add_nb_lines_safe = 2 # # ask the soft to read the time of N lines, but acquire samples of n+2 lines to be sure enough samples are acquired

hyst_trig_min_advised = 20/1000 # V, min. hysteresis for lvl trigger

if num_dev_anlgTrig == 0: # 6110
    if use_chan_trigger:
        factor_trigger = factor_trigger_chan
    else: # use a terminal port PFI0 directly
        factor_trigger = 1/0.35
else: # 6259
    if use_chan_trigger:
        factor_trigger = 1.97
    else: # use a terminal port APFI0 directly
        factor_trigger = 2.09 #2 #2.09 #2.55

angle_rot_degree_new_galvos = 0 #45
#!! If posX is used as trigger, need to re-define the trigger level(s) 
#every line, which cannot be done while the Task is running !

use_velocity_trigger = 0 # not use pos but vel. trigger

force_buffer_small = 1 # buffer the smallest possible (according to fact) : can avoid latencies
fact_buffer_anlgGalvo = 4 # buffer small is fact*nb_samps_line : has to be at least 2
time_buffer_tobeCorrect = 1 # sec, if large buffer chosen : buffer AI can contain samples max up to this duration (rate dependant)

sample_rate_min_6110 = 0.1e6 # 100kHz is minimum rate for 6110
sample_rate_min_6259 = 0 # 0 is minimum rate for 6259

# # ********************************************
# # --------- scan params ------------------
# # ********************************************

smallest_OS_sleep = 20e-3 # on windows smallest sleep can be 13ms

nb_lines_acumm_acq = None # None means that the code will take teh value calculated with update rate

msg_warning_ifstop_taskundone = '\nWarning 200010 occurred.\n\nFinite acquisition or generation has been stopped before the requested number of samples were acquired or generated.'
# # NOt used (temporarily ??)

shape_reverse_movement = 0 # add some points on the reverse of galvos speed, to smooth
correct_unidirektionnal = 1 # 1 for a smooth return, 2 for acting as if it was a bidirek scan
skip_first_read = 0 # when the acq. bugs, it's often due to 1st line so this command just throw it away
blink_after_scan = 1
volt_pos_blink = -4.9 # min_val_volt_galvos # voltage to set at each new img beginning

fact_data = 2 # size of the array to contains line = fact*nb_samples_expected

# # ********************************************
# # --------- AO write params ------------------
# # ********************************************

min_val_volt_galvos = -10 # V
max_val_volt_galvos = 10 # V
# The system is set for +-10V <-> +-10° mechanical
safety_ao_gen_fact = 1.05 # multiply the max expected range by this value to be safe (for 6259)
ext_ref_AO_range = True # for 6259, use an external src on APFI0 for determining the range of AO generation: need another AO (from 6110 ?) to supply a voltage
if (not use_chan_trigger and ext_ref_AO_range): # cannot be used if APFI0 is used as anlg trigger
    ext_ref_AO_range = not ext_ref_AO_range # set to False, not explicitly because don't want it to change

offset_y_deg_00 = 0 #0.8 #0.25 #0.75 # fast
offset_x_deg_00 = 0  #-0.3 # -0.3 #0.35 # slow

use_volt_not_raw_write = 0
repeatability_galvos_V = 8e-6/math.pi*180 # in ° or V 
timeout_galvo = 2000 # ms 

bits_write = 16 # always, for both cards

nb_ao_channel = 2 # X and Y

tolerance_nb_write_to_stop = 2 # it's possible that the AO Task won't output all the samples requested, so set a tolerance to consider the Task as done (2 is good)
write_scan_before_anlg = 1 # 0 to write scan in LIVE (for long scans)
duration_scan_prewrite_in_buffer=0.5 # sec, if write in LIVE

security_noise_factor = 1.15 # empirical

small_angle_step_response_us = 200 # us
smAngStpResp_safeFac = 5 # fact for small angle step response in reality
settling_time_galvo_us = smAngStpResp_safeFac*small_angle_step_response_us # # us,  Ts is the 0 – 99% settling time for a critically damped system to a step input.
divider_settling_time_avoid_step_dflt = 25 # must be between 20 and 100
# # put a low value if you want to test long scans !
lower_bound_divider_settling_time_avoid_step = 20
upper_bound_divider_settling_time_avoid_step = 100

limit_small_step_angle_measured = 0.8 # ° or V

smpRate_SafFact = 1 # empirical
sample_rate_AO_min_imposed = 1/small_angle_step_response_us*1e6*smpRate_SafFact # always the same rate, goes faster does not help long exposure times, for short exposure times the limit is just the angle range and the small_angle_step_response

BW_full_scale_galvos = 200 # Hz, for a square wave, or sawtooth, or triangular
BW_small_steps_galvos = 1000 # Hz
# is not limited here
small_angle_step = (max_val_volt_galvos - min_val_volt_galvos)/100 # 1%

# # ********************************************
# # ------- galvos hardware --------------------
# # ********************************************

rotor_inertia = 0.125 # gm*cm2, +/-10% 
mirror_inertia = 0.3 # gm*cm2
total_inertia = rotor_inertia + mirror_inertia
torque_constant = 6.17e4 # Dyne-cm/Amp, +/-10%
induct_coil_H = 180e-6 # 180 μH, +/-10%
ohm_coil_val = 2.79 # Ohms, +/-10%
max_rms_current_one_axis = 3.9 # Amp, see specs of 6220H
max_ddp = max_val_volt_galvos # ohm_coil_val*peak_current #
revers_time_meth = 2 # 2 = imposed ; # 0 like the digital galvos, and 1 calculated with theory
# calculate max acceleration of galvos using the peak current (1), or calculate the optimal (0), or impose it (2)

scan_lens_mm = 45 # the scan lens just after the galvos to demagnify the scan and expand the beam (with tube lens)

ai_readposX_anlggalvo = 'ai2'
ai_readposY_anlggalvo = 'ai3'

## APT parameters

motor_rot_ID = 83842617 # motor rot WP thorlabs
motor_phshft_ID = 83815617 # motor phshft thorlabs (rot plate)
motor_trans_ID = 83815160 # trans Thorlabs T-cube

pos_max_phshft_um = 27900 # 27.9 mm

dist_mm_typical_phshft = 0.07 # # 0.07 mm = 1deg with rot. vet mtr

bound_mtr_rot_plate = 24 # mm
bound_mtr_trans = 27.9 # mm

max_acc_KC_dflt =  4 # # mm/s2
max_vel_KC_dflt =  2.6 # # mm/sec

max_acc_TC_dflt =  0.5 # # mm/s2
max_vel_TC_dflt =  0.5 # # mm/sec

## stage XY Thorlabs

motorX_ID = 94828766 # motor X thorlabs stage with APT
motorY_ID = 94828767 # with APT

use_serial_not_ftdi = 1 # 0 for USB ftdi
XYstage_comport = 'COM4'
motorXY_SN = '73828765'

trig_src_name_stgscan = 'PFI2' 

# for fast motor
prof_mode = 1 # dflt, 2 for S-curve and 1 for trapez
trigout_maxvelreached = 1 # 2 for 'In motion', 1 for 'Max Vel. Reached', 0 for off
    
# for slow motor, or normal use

prof_mode_slow = 1 # 2 for S-curve and 0 or 1 for trapez
jerk_mms3_slow = 10000 # mm/s3
jerk_mms3 = 10000 #10000001*2.2 #10000#0.0108 # mm/s3
jerk_mms3_trapez = 10000 # mm/s3, good default value
# if prof_mode == 1: # trapez
#     jerk_mms3 = jerk_mms3_trapez # no jerk if trapez, but 0 is a dengerous value for S-curve so 1
if jerk_mms3 > 10000001*2.2:
    jerk_mms3 = 10000001*2.2
elif jerk_mms3 < 0.01:
    jerk_mms3 = 0.01

time_out_stageXY = 0.0 # in s, waiting for completion uses 'while' loops, to listen for stop order or to wait for very long moves, so this value has to be small. it's not 0 because the reaction time of a human user is not infinitely short anyway, and a non zero value ensure a non too long while loop

block_slow_stgXY_before_return = 0 # for unidirek, block after slow movem, or not --> allow return fast move to start directly 

min_posX = 0.01 # mm
max_posX = 109.99 # mm

min_posY = 0.01 # mm
max_posY = 74.99 # mm

bnd_posXY_l = [min_posX, max_posX, min_posY, max_posY]; max_val_pxl_l = [max_value_pixel_6110, max_value_pixel_6259 ]

acc_max = 1800 # mm/s2
acc_dflt = 500 # mm/s2
vel_dflt = 8 # mm/s
limitwait_move_time = 2 # sec, the limit of time user will consider waiting for an init move (in stage scan) without touching the motor speed/accn (if move time goes over it, the speed will be increased to dflt value and reset after move) 

# # ------- PID parameters ---------

# For X
Kp_pos_val_toset = 300 # dflt 150
Ki_pos_val_toset = 175  # dflt 175
Ilim_pos_val_toset = 200000 # dflt 200000
Kd_pos_val_toset = 1000 # dflt 500
DerTime_pos_val_toset = 5 # dflt 5
OutGain_pos_val_toset = 6554 # dflt 6554
VelFeedFwd_pos_val_toset = 0 # dflt 0
AccFeedFwd_pos_val_toset = 1000 # dflt 1000
PosErrLim_pos_val_toset = 20000 # dflt 20000

# For Y
Kp_pos_val2_toset = 300 # dflt 65
Ki_pos_val2_toset  = 175 # dflt 115
Ilim_pos_val2_toset = 200000 # dflt 200000
Kd_pos_val2_toset  = 1000 # dflt 500
DerTime_pos_val2_toset = 5 # dflt 5
OutGain_pos_val2_toset = 3277 # dflt 3277
VelFeedFwd_pos_val2_toset = 0 # dflt 0
AccFeedFwd_pos_val2_toset = 1000 # dflt 1000
PosErrLim_pos_val2_toset = 20000 # dflt 20000

PID_scn_lst = [Kp_pos_val_toset, Ki_pos_val_toset, Ilim_pos_val_toset, Kd_pos_val_toset, DerTime_pos_val_toset, OutGain_pos_val_toset, VelFeedFwd_pos_val_toset, AccFeedFwd_pos_val_toset, PosErrLim_pos_val_toset, Kp_pos_val2_toset, Ki_pos_val2_toset, Ilim_pos_val2_toset, Kd_pos_val2_toset, DerTime_pos_val2_toset, OutGain_pos_val2_toset, VelFeedFwd_pos_val2_toset, AccFeedFwd_pos_val2_toset, PosErrLim_pos_val2_toset]

# default
Kp_pos_val_dflt = 150
Kp_pos_val_dflt_y = 65
Ki_pos_val_dflt = 175 
Ki_pos_val_dflt_y = 115
Ilim_pos_val_dflt = 200000
Kd_pos_val_dflt =  500
DerTime_pos_val_dflt =  5
OutGain_pos_val_dflt =  6554
OutGain_pos_val_dflt_y = 3277
VelFeedFwd_pos_val_dflt =  0
AccFeedFwd_pos_val_dflt =  1000
PosErrLim_pos_val_dflt = 20000

PID_dflt_lst = [Kp_pos_val_dflt,  Ki_pos_val_dflt, Ilim_pos_val_dflt, Kd_pos_val_dflt, DerTime_pos_val_dflt, OutGain_pos_val_dflt, VelFeedFwd_pos_val_dflt, AccFeedFwd_pos_val_dflt, PosErrLim_pos_val_dflt, Kp_pos_val_dflt_y, Ki_pos_val_dflt_y, Ilim_pos_val_dflt, Kd_pos_val_dflt, DerTime_pos_val_dflt, OutGain_pos_val_dflt_y, VelFeedFwd_pos_val_dflt, AccFeedFwd_pos_val_dflt, PosErrLim_pos_val_dflt]

notXY_homed_msg = 'You should home the motors first ... I`m not going on further (what did you expect?)\n'
tolerance_speed_accn_diff_real_value = 1.01 # # 1%
min_speedslow = (1000*1e-3*acc_max/2)**0.5 # 1 #mm/s
tol_speed_flbck = 0.1 # ie 10%
method_fast_stgscn = True # # was very tested with False only, but True is significant if large scan, or many PMTs, or ishg fast, or the 3

stock_data_to_avoid_buff_corrupt = True # # store data in list in func, rather than in queue memory to avoid corruptions if accumulation in queue
    
## Spectro parameters

wait_time_spectro_seconds = 0.5 # s, update time of the spectro disp value ; min_exptime_msec = 3.8 # msec
upper_bound_expected = 20 # delta nm
lwr_bound_expected = 20 # delta nm
upper_bound_window = 90 # delta nm
lower_bound_window = 90 # delta nm
integration_time_spectro_microsec = 100000 # in us
wlgth_center_expected_nm = 810 # nm

path_save_spectro = r'C:\Users\admin\Desktop'
lwr_bound_exp_shgjob = 400 # # for the max (unimportant)
upr_bound_exp_shgjob = 410 # # for the max (unimportant)
lower_bound_shgjob = 395 # # crop
upper_bound_shgjob = 415 # # crop
save_live_frog_calib = False
save_big_frog_calib = True 
save_excel_frog_calib = 0 # # .mat
fast_acq_frog = True # # slow version does not keep up with the motor movement
min_exptime_msec = 3.8 # msec # # supposed to be 0.01msec but maybe the filling of arrays takes time ??

## jobs parameters

time_change_Z = 1 # s
time_change_ps = 1 # s
time_change_polar = 1 # s
use_piezo_for_Z_stack = 0 # default TEMPORARY TO ) IF NO PIEZO
list_ps_separator = ' ; ' # the different phase-shifts are separated by this sign in a string
list_Z_separator = ' ; ' # same
list_stgscn_separator = ' ; ' # same
list_polar_separator = ' ; ' # same
list_ishgfast_separator = ' ; ' # same
repeat_posWrtEnd_jobTable = -1 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
average_posWrtEnd_jobTable = -2 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
zstck_posWrtEnd_jobTable = -3 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
ps_posWrtEnd_jobTable = -5 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
psmtr_posWrtEnd_jobTable = -6 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
transmtrs_posWrtEnd_jobTable = -8 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
polarmtrs_posWrtEnd_jobTable = -7 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
polar_posWrtEnd_jobTable = -4 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
shutteruse_posWrtEnd_jobTable = -9 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
ishgfastuse_posWrtEnd_jobTable = -10 # in the job table, each job has its parameters stored in a specific case, in a column at a integer with respect to (wrt) the last element
centerX_posWrt0_jobTable = 17 # in the job table, each parameter is stored in a specific case
centerY_posWrt0_jobTable = 18 # in the job table, each parameter is stored in a specific case
imicOther_posWrt0_jobTable = 19 # in the job table, each parameter is stored in a specific case
dwllTime_posWrt0_jobTable = 20 # in the job table, each parameter is stored in a specific case
listStgScan_posWrt0_jobTable = 21 # in the job table, each parameter is stored in a specific case
totTime_posWrt0_jobTable = 22 # in the job table, each parameter is stored in a specific case
mode_posWrt0_jobTable = 23 # in the job table, each parameter is stored in a specific case
szX_posWrt0_jobTable = 8 # in the job table, each parameter is stored in a specific case
szY_posWrt0_jobTable = 9 # in the job table, each parameter is stored in a specific case
stX_posWrt0_jobTable = 10 # in the job table, each parameter is stored in a specific case
stY_posWrt0_jobTable = 11 # in the job table, each parameter is stored in a specific case
nbstXmos_posWrt0_jobTable = 12 # in the job table, each parameter is stored in a specific case
nbstYmos_posWrt0_jobTable = 13 # in the job table, each parameter is stored in a specific case
bstXmos_posWrt0_jobTable = 14 # in the job table, each parameter is stored in a specific case
bstYmos_posWrt0_jobTable = 15 # in the job table, each parameter is stored in a specific case
mosaic_posWrt0_jobTable = 16 # in the job table, each parameter is stored in a specific case
pmts_posWrt0_jobTable = 5 # in the job table, each parameter is stored in a specific case
mtrZ_posWrt0_jobTable = 6 # in the job table, each parameter is stored in a specific case
pzZ_posWrt0_jobTable = 7 # in the job table, each parameter is stored in a specific case
nbfr_posWrt0_jobTable = 4 # nb frames
name_dcvolt = 'DCvolt'
name_trans = 'trans'
name_rot = 'rot'
    
calib_ps_name_job = 'calibPS'
zstck_name_job = 'Z-stack (Z)'
ps_name_job = 'Ph-shft (φ)'
polar_name_job = 'Polar (P)' # 3
z_ps_name_job = 'Zφ' #13
ps_zstck_name_job = 'φZ' # 4
ps_polar_name_job = 'φP' # 14
polar_ps_name_job = 'Pφ' # 15
polar_zstck_name_job = 'PZ' # 5
z_polar_name_job = 'ZP' #12
XYmosaic_name_job = 'XY mosaic (XYm)' # 6
nomtr_name_job = 'no mtr' # 18

mosaic_job_num = 6  # mosaic or not (1 image)
nomtr_job_num_wrtend = 0

#  ----- calib fast -----
res_theo_calibfast_deg = 30 # deg meaning 6 points by slope of cos
# # phi = 2pi*nu*delta_t with delta_t = δL*(1/vg1-1/vg2)
# # δx = δL/sin(α) = phi/(2pi*nu)/(1/vg1-1/vg2)/sin(α)
# lambda = lambda_shg car c'est elle qui est déphasée in fine
alpha_calc_deg = 18 # ° # # angle of calcite prism
divider_lines_calib_fast = 1 # # into how many lines of scan to divide the main line of calib fast (avoid one big line)
vg1 = 1.79e8 # # m/sec in calcite for 810/405nm (1.90e8 for 1064nm)
vg2 = 1.95e8 # # m/sec in calcite for 810/405nm (1.99e8 for 1064nm)
add_modulo_2pi_calib_ps = False # # used before for mtr trans to ensure steps are high enough
nb_pass_calcites = 4 # # 2 for double pass, 4 for quadruple pass, 1 single pass

exec_dflt = "importlib.reload(sys.modules['modules.acq_stage_script5'])"

## shutter parameters

ressource_shutter = 'COM2'
baud_rate_shutter_dflt = 9600 # don't change this value ! it's the rate that the controller use when turned on
baud_rate_shutter= 115200 # 9600 # 9600 is not enough if close time is under 200ms
bits_shutter = 8
flow_control_shutter= 0 # hardware control ?
timeout_shutter = 1 # sec # 1000 # ms
read_termination_shutter  = '\r'
write_termination_shutter = '\r'
t_shutter_trans = 5*20 # ms , # TO in the doc
t_understand_order = 8*20 # ms, # max(TI, TDR) 20ms in the doc

## newport parameters

newportstage_comport = 'COM1'
motornewport_SN = 'ESP1' # just an indicator

## EOM phase

sec_proc_forishgfill = False #True # # start a second Process for filling or ishg array
flag_impose_ramptime_as_exptime = False # # impose the exp_time of image to be equal to the ramp_time (including dead_times !!) e.g. ramp200us, dead30+20 --> exptime = 250 us
# # if False, the image size of array4Dishg only will be redefined to fit ramp time (not standard SHG)
# # if True, exp_time adjusted so less problems
# # warning: if exp_time != ramp_time+dead_times, the image might be deformed due to the fact that it already divided the physical size Slow into M pixels, that will never fit the N new pixels of Fast (pixels not squares but rectangles). 
ramptime_EOMph_0 = 2000 # # usec
ramptime_EOMph_1 = 220 # # usec
ramptime_EOMph_2 = 20 # # usec
beg_dt_us_mode0 = 60; end_dt_us_mode0 = 140 ; line_dt_us_mode0 = 0 # usec
beg_dt_us_mode1 = 30; end_dt_us_mode1 = 0.0 ; line_dt_us_mode1 = 40 #usec
beg_dt_us_mode2 = 2.0; end_dt_us_mode2 = 0.80 ; line_dt_us_mode2 = 1.6  #usec
mode_eom_dflt = 2 # 2 for 20us, 1 for 200us 
eom_cycles_times = [[ramptime_EOMph_0, beg_dt_us_mode0, end_dt_us_mode0, line_dt_us_mode0], [ramptime_EOMph_1, beg_dt_us_mode1, end_dt_us_mode1, line_dt_us_mode1], [ramptime_EOMph_2, beg_dt_us_mode2, end_dt_us_mode2, line_dt_us_mode2]] # # sec
rmp_time_sec_dflt = eom_cycles_times[mode_eom_dflt][0]*1e-6 # # sec
beg_dt_sec_dflt = eom_cycles_times[mode_eom_dflt][1]*1e-6; end_dt_sec_dflt = eom_cycles_times[mode_eom_dflt][2]*1e-6
line_dt_us_dflt =  eom_cycles_times[mode_eom_dflt][3]*1e-6
ishg_EOM_AC_dflt = [False, rmp_time_sec_dflt, 31, 260, 1360, 1, (0, beg_dt_sec_dflt, end_dt_sec_dflt, line_dt_us_dflt), (flag_impose_ramptime_as_exptime, 0)] # flag, ramp time sec00, step theo(deg), Vpi, VMax, nb_samps_perphsft, offset_samps, (flag_impose_ramptime_as_exptime, taskmttrtrigout)
 # # ishg_EOM_AC_insamps will be [flag, nb_samps_ramp00, nb phsft, Vpi, VMax, nb_samps_perphsft, offset_samps, flag_impose_ramptime_as_exptime] with the times in nb smps !!
dfltmodesave_fastishg = 0 # 0 for save arrays, 1 for save buffers only no treat live, 2 for save both (and treat live)
tolerance_change_nbphsft = 20 # up to this difference ratio (with nb ph) in % 
precision_float_ishg = precision_float_numpy # for array_4D
exploit_all_acqsamps = False
# # True will set the p-s step to maximize the number of samps used (max nb of p-s, min step)
# # False = impose the samps used to exactly match the wanted p-s step (min number of p-s., exact step, unused samples)

ps_step_closest_possible_so_lstsamps_inddtime = True # # no effect if exploit_all_acqsamps is True
# # True means p-s step will be the closest possible to asked value, with perhaps the last samples of last p-s taken in the deadtime if not enough in the ramp
# # False means that the p-s will try to be closest to asked, but without the use of samples from deadtime: instead, a less good value might be chosen and some sample will be unused in the ramp. 
# # ps_step_closest_possible_so_lstsamps_inddtime = 2 means to not have samples unused in ramp at all

add_nb_ps = 0 # # manual increase of nb of phsft (- to remove)

# # instr
EOMphAxis_comport = 'COM19'
EOMph_baudrate = 9600
time_out_EOMph = 2 # sec
write_termination_EOMph = '\r\n' # 
# # don't change these !!!
msg_getStatusEOM = 8701
msg_stopEOM = 8702
msg_stModeEOM = 8703 # + 00 01 02 03 for mode (3 = DC), 00 = 2000us
msg_getStatusVoltageEOM = '0501' # because of 1st 0
msg_ONVoltageEOM = '0502' # # only for HV module, does not apply to crystal !
msg_OFFVoltageEOM = '0503' # # only for HV module, does not apply to crystal !
msg_SetVoltageEOM = '0504' # + LSB + MSB
msg_ReadVoltageEOM = '0505'
code_resp_getstatus = '(87010001)'
# # a string not int because of 1st 0
code_resp_getHV = '(0505000001)' # # OFF
code_resp_getHVvar = '(0503000001)' # # standby
code_resp_getHVon = '(0504000001)'
code_resp_getHVval = '(0504000005)' # # =0 getval
code_resp_getHVval2 = '(0503000005)' # # standby getVal
code_resp_getHVval3 = '(0505000005)' # # nomode ? getVal
code_resp_mode1 = code_resp_getHVon + '(8203000001)' + code_resp_getHVon # # 

# # because stage scn trigger is not very clean
nametask_mtr_trigout_list = ['mtr_trigout_01'] 
ctr_src_trigger_trigout_EOMph = 'PFI4' # # can be 3, 4, 8 or 9
cntr_chan_name_trigout_EOMph = 'ctr0' # # for EOMph
pulsewidth_ctroutEOM_sec = 400e-9 # sec

use_same_CO_for_EOMphtrig = True
mtr_trigout_retriggerable_stage = 0 # # 1 for rettrig, 0 for st/stop each line !!! 0 is the good parameters to avoid false triggering !!

## scan

size_um_dflt = 200 # um
step_ref_val_stage = 1 #um
step_ref_val_galvo = 0.5 # um


## pyqtgraph

xMin_pg = -100
xMax_pg = 10000
yMin_pg = -100
yMax_pg = 10000
minXRange_pg= 1
maxXRange_pg= xMax_pg-xMin_pg
minYRange_pg= 1
maxYRange_pg= yMax_pg-yMin_pg

# # lut_kryptonite = numpy.array(((0,0,0), (0,33,0), (0,66,0), (0,99,0), (0,132,8), (0,168,41), (0,203,74), (0,238,107), (16,255,141), (49,255,176), (82,255,211), (115,255,246), (150,255,255), (185,255,255), (220,255,255), (255,255,255)), dtype=numpy.ubyte)

lut_kryptonite = numpy.array(((0,0,0), (0,2,0), (0,4,0), (0,6,0), (0,8,0), (0,10,0), (0,12,0), (0,14,0), (0,16,0), (0,17,0), (0,19,0), (0,21,0), (0,23,0), (0,25,0), (0,27,0), (0,29,0), (0,31,0), (0,33,0), (0,35,0), (0,37,0), (0,39,0), (0,41,0), (0,43,0), (0,45,0), (0,47,0), (0,48,0), (0,50,0), (0,52,0), (0,54,0), (0,56,0), (0,58,0), (0,60,0), (0,62,0), (0,64,0), (0,66,0), (0,68,0), (0,70,0), (0,72,0), (0,74,0), (0,76,0), (0,78,0), (0,80,0), (0,81,0), (0,83,0), (0,85,0), (0,87,0), (0,89,0), (0,91,0), (0,93,0), (0,95,0), (0,97,0), (0,99,0), (0,101,0), (0,103,0), (0,105,0), (0,107,0), (0,109,0), (0,111,0), (0,112,0), (0,114,0), (0,116,0), (0,118,0), (0,120,0), (0,122,0), (0,124,0), (0,126,2), (0,128,4), (0,130,6), (0,132,8), (0,135,10), (0,137,12), (0,139,14), (0,141,16), (0,143,18), (0,145,20), (0,147,22), (0,149,24), (0,151,26), (0,153,28), (0,155,30), (0,157,32), (0,159,33), (0,161,35), (0,164,37), (0,166,39), (0,168,41), (0,170,43), (0,172,45), (0,174,47), (0,176,49), (0,178,51), (0,180,53), (0,182,55), (0,184,57), (0,186,59), (0,188,61), (0,190,63), (0,193,64), (0,195,66), (0,197,68), (0,199,70), (0,201,72), (0,203,74), (0,205,76), (0,207,78), (0,209,80), (0,211,82), (0,213,84), (0,215,86), (0,217,88), (0,220,90), (0,222,92), (0,224,94), (0,226,96), (0,228,97), (0,230,99), (0,232,101), (0,234,103), (0,236,105), (0,238,107), (0,240,109), (0,242,111), (0,244,113), (0,246,115), (0,249,117), (0,251,119), (0,253,121), (0,255,123), (1,255,125), (3,255,127), (5,255,129), (7,255,131), (9,255,133), (11,255,135), (13,255,137), (15,255,139), (16,255,141), (18,255,143), (20,255,145), (22,255,147), (24,255,149), (26,255,151), (28,255,154), (30,255,156), (32,255,158), (34,255,160), (36,255,162), (38,255,164), (40,255,166), (42,255,168), (44,255,170), (46,255,172), (48,255,174), (49,255,176), (51,255,178), (53,255,180), (55,255,182), (57,255,184), (59,255,186), (61,255,189), (63,255,191), (65,255,193), (67,255,195), (69,255,197), (71,255,199), (73,255,201), (75,255,203), (77,255,205), (79,255,207), (80,255,209),(82,255,211), (84,255,213), (86,255,215), (88,255,217), (90,255,219), (92,255,222), (94,255,224), (96,255,226), (98,255,228), (100,255,230), (102,255,232), (104,255,234), (106,255,236), (108,255,238), (110,255,240), (112,255,242), (113,255,244), (115,255,246), (117,255,248), (119,255,250), (121,255,252), (123,255,254), (125,255,255), (127,255,255), (129,255,255), (131,255,255), (133,255,255), (135,255,255), (138,255,255), (140,255,255), (142,255,255), (144,255,255), (146,255,255), (148,255,255), (150,255,255), (152,255,255), (154,255,255), (156,255,255), (158,255,255), (160,255,255), (162,255,255), (164,255,255),(166,255,255), (168,255,255), (171,255,255), (173,255,255), (175,255,255), (177,255,255),(179,255,255),(181,255,255), (183,255,255), (185,255,255), (187,255,255), (189,255,255), (191,255,255),(193,255,255),(195,255,255), (197,255,255), (199,255,255), (201,255,255), (203,255,255), (206,255,255), (208,255,255), (210,255,255), (212,255,255), (214,255,255), (216,255,255), (218,255,255), (220,255,255), (222,255,255), (224,255,255), (226,255,255), (228,255,255), (230,255,255), (232,255,255), (234,255,255), (236,255,255), (239,255,255), (241,255,255), (243,255,255), (245,255,255), (247,255,255), (249,255,255), (251,255,255), (253,255,255), (255,255,255)), dtype=numpy.ubyte)



    