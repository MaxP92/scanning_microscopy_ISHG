# -*- coding: utf-8 -*-
"""
Created on Mon Apr 23 16:35:13 2018

@author: Maxime PINSARD
"""

## (analog galvos)

def calc_reversing_time_anlg_galvos(optimize, fun_flyback, A2, W2, W1, As, val, upper_bound):

    func = lambda x : fun_flyback(x, A2, W2, W1, As) - val
    
    # # x_initial_guess = 0.5
    solution = optimize.brentq(func, 0, upper_bound) # # in nb DAQ AO samples
        
    return solution  # # in nb DAQ AO samples
    

## (dig galvos)

def calc_reversing_time_galvos(optimize, numpy, induct_H, ohm_val, max_voltage, torque_cst, inertia, angle_range, time_by_line, x0_dflt):
    
    tau = induct_H/ohm_val # s
    max_current = max_voltage/ohm_val # A
    max_acceleration = 180/numpy.pi*(max_current*(torque_cst/inertia)) # deg/s^2
    
    average_angular_speed = angle_range/time_by_line # ziel, average angular speed (deg/s)
    
    ## fit exp. for reversing time (digital galvos)
    
    def func(x):
        return average_angular_speed-max_acceleration*(x+tau*(numpy.exp(-x/tau)-1))
    
    # use the Newton-Raphson method to find zero
    
    zero_func = optimize.newton(func, x0_dflt) # fprime=None, args=(), tol=1.48e-08, maxiter=50, fprime2=None)[source]
    
    # print('\n grad = %f, scale = %f, obj_mag = %f , range = %f, time_bl = %f \n' % (grad, scale, obj_mag, angle_range, time_by_line)) #img_pixel/(2*field_view/obj_mag
    # print('zero_func = ', zero_func)
    # print('\n grad = %f, line_speed.real = %f \n' % (grad,line_speed.real))
    # print('\n posX1 = %d, posY1  = %d,posX2 = %d\n' % (posX1 , posY1, posX2))
    reversing_time = 2*zero_func # umkehrzeit, aller-retour
    
    return reversing_time
    
def init_dig_galvos(serial, baud_rate_dig_galvos, timeout_dig_galvos, ressource_dig_galvos, dll_diggalvos_timing, path_computer):
   
    dll_tuple =() # init
    try:
        # # if not hasattr(self, 'shutter'):
        # # self.shutter = self.rm.open_resource(param_ini.ressource_shutter)
        dig_galvos = serial.Serial(ressource_dig_galvos, xonxoff=False, rtscts=False, baudrate=baud_rate_dig_galvos , bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE, timeout=timeout_dig_galvos, write_timeout = 2)
        
    except Exception as e: 
        if type(e) == serial.serialutil.SerialException:
            print(e, '\n ERROR : instr in used elsewhere')
        else:
            print('ERROR dig galvos', e)
        dig_galvos = None
    # else:
    # to check if the galvo indeed respond
    # galvo.write('R')
    # print(galvo.read())
    else: # def of library for reversing time and valid cycles if needed
        
        if dll_diggalvos_timing:            
            import ctypes, os
            
            pp=os.getcwd()
            if pp != os.path.join(path_computer, 'prog microscope '): os.chdir(os.path.join(path_computer, 'prog microscope 18'))
            from modules import _imicinitmp2
            
            path00 = '%s/Packages/validcycles+flbk_x64' % path_computer
            nm_lib = 'validcycles' #'valid_cycles' for only the validcycles without flyback
            
            # ******* open lib ************************************************************
            
            if (os.name != 'nt'):
                raise Exception("Your operating system is not supported. " \
                            "%s API only works on Windows."% nm_lib)  
            lib_valcycles = None
            try:
                filename = ctypes.util.find_library( nm_lib)
            except:
                filename = None
                        
            if (filename is not None):
                lib_valcycles = ctypes.windll.LoadLibrary(filename)
                print('Lib %s loaded by windll and util' %nm_lib)
            else:
                filename = "%s/%s.dll" % (path00, nm_lib)
                lib_valcycles = ctypes.CDLL(filename)
                print('Lib %s loaded by CDLL'%nm_lib)
                if (lib_valcycles is None):
                    filename = "%s/%s.dll" % (os.path.dirname(sys.argv[0]), nm_lib)
                    lib_valcycles = ctypes.windll.LoadLibrary(lib_valcycles)
                    print('Lib %s loaded by windll'% nm_lib)
                    if (lib_valcycles is None):
                        raise Exception("Could not find shared library %s."% nm_lib)
            
            _imicinitmp2.set_ctypes_argtypes_validcycles_mp(lib_valcycles) # load function properties
            
            # # print('validCycles loaded')
            
            # return lib_valcycles
            empty_int = (ctypes.c_uint32*1)()
            BOut_pt = ctypes.cast(empty_int, ctypes.POINTER(ctypes.c_uint32))
            D_pt =  ctypes.cast(empty_int, ctypes.POINTER(ctypes.c_uint32))
            
            empty_double = (ctypes.c_double*1)()
            calculated_at_time_S2xExp_Equation_pt = ctypes.cast(empty_double, ctypes.POINTER(ctypes.c_double))
            mechangle_pt =  ctypes.cast(empty_double, ctypes.POINTER(ctypes.c_double))
            
            dll_tuple = (lib_valcycles, BOut_pt, D_pt, calculated_at_time_S2xExp_Equation_pt, mechangle_pt)
        
    return dig_galvos, dll_tuple

def stop_reset_galvos_dig(galvo):
    
    """
    in case of problem with DIG galvos
    """
    msg='V 7,0' # reset galvos
    galvo.write(('%s\n'% msg).encode('ascii'))
    print(galvo.readline().decode()) # has to return 0


    
def list_galvos_func(galvos_reversing_time_script, time_by_point, galvo_rotation, img_pixel, obj_mag, field_view, AD_frequency, SM_cycle, SM_delay, ohm_val, induct_H, max_voltage, inertia, torque, bit_size_galvo, bits_16_36, center_x, center_y, new_sz_x, new_sz_y, nb_px_x, nb_px_y, scan_linse, numpy, optimize, center_galvo_x00, center_galvo_y00, unidirectional, turn_time_unidirek, dll_diggalvos_timing, dll_tuple):

    scan_array = []
    
    
    ## construct scan init

    rotate = galvo_rotation*numpy.pi/180 # 0, rad
    
    # only for IMAQ (a 500px square with a correspondance 600um)
    
    grad = obj_mag/scan_linse*180/numpy.pi #57.29 # # 
    
    if not unidirectional:
        nb_loops = round(nb_px_y/2)-1 # in bidirek, one line array contains one dir and one reverse
    else:
        nb_loops = nb_px_y-1

    SM_move_time = SM_cycle*SM_delay # s 
    
    scaling_galvo = bit_size_galvo/obj_mag # 1.61e-8 # skalierung m/bit
    new_scaling_galvo = scaling_galvo/bits_16_36
    
    use_scale_NIvision = 1
    if use_scale_NIvision:
   #  
        center_x_rotated = numpy.cos(rotate)*center_x + numpy.sin(rotate)*center_y
        center_y_rotated = -numpy.sin(rotate)*center_x + numpy.cos(rotate)*center_y
        
        center_x = center_x_rotated + 0.046 #- 0.1336 # offset oberved wrt to labview
        center_y = center_y_rotated -0.029 # + 0.1504 # offset oberved wrt to labview
        # center_x, y in mm !!
        
        # coef_punk = 5/6
        
        # empricically set values ...
        posX1 = round(-21/50*new_sz_x + 252 + 41/50*center_x*1000) # centerx in um
        # new_sz_x, new_sz_y in um
        posY1 = round(-21/50*new_sz_y + 252 - 41/50*center_y*1000)
        
        posX2 = round(posX1 + 41.85/50*new_sz_x) # new_sz_x in um
        posY2 = round(posY1 + 41.85/50*new_sz_y)
        
        scale = img_pixel/(2*field_view/obj_mag) #1.6667e6 # 2.5e6
        
    else:
        
        # all in um cobverted to m
        posX1 = center_x/1000 - new_sz_x/2*1e-6 # xmin
        posY1 = center_y/1000 - new_sz_y/2*1e-6 # ymin
        posX2 = posX1 + new_sz_x*1e-6 # xmax
        posY2 = posY1 + new_sz_y*1e-6 # ymax
        scale = 1
    
        
# transform coord.

    center_galvo_ini = center_galvo_x00 + 1j*center_galvo_y00  # in m !

    A = scale*numpy.e**(1j*rotate)

    pos_list = [posX1 + 1j*posY1, posX2 + 1j*posY1, posX1 + 1j*posY2]

# xyTransform
    for i in range(0,3):

        pos_temp = pos_list[i]
    
        pos_temp = pos_temp/A # as in xyTransform.VI, itself in DefineScan.VI, "Change scan value change"

        pos_temp = pos_temp + center_galvo_ini # as in xyTransform.VI, itself in DefineScan.VI, "Change scan value change"

        pos_list[i] = pos_temp

    pos_start = pos_list[0] # startPunkt
    #posY_start = pos_list[0].imag

    pos_fastend = pos_list[1]
    #posY_fastend = pos_list[1].imag

    pos_slowend = pos_list[2]
    #posY_slowend = pos_list[2].imag

    incr_line = (pos_slowend - pos_start)/nb_px_y # zeilenIncrement (m)

    time_by_line = nb_px_x*time_by_point # zeit_by_zeile

    line_speed = (pos_fastend - pos_start)/time_by_line # zeile m/s, COMPLEX

    angle_range = grad*time_by_line*(line_speed.real**2 + line_speed.imag**2)**(1/2) # lin. winkelbereich (deg.)
    
    # # print('x1', posX1)
    # # print('y1', posY1)
    # # print('startPunkt', pos_start)
    # # print('line_speed cx', line_speed)
    # # print('zeilenIncrement', incr_line)
    
    # # ********** End of Define Scan (Change scan part) ******************
    
    # # ********** Konstruiere scan stereeung ******************

    ## defining galvo_too_late & others in Konstruiere
    
    from itertools import chain
    def factors2(n):
        result = []
        ct=1
        # test 2 and all of the odd numbers
        # xrange instead of range avoids constructing the list
        for i in chain([2],range(3,n+1,2)):
            s = 0
            while n%i == 0:  #a good place for mod
                n /= i
                s += 1
            result.extend([i]*s) #avoid another for loop
            if n==1:
                
                for k in result:
                    ct=ct*k
                return ct
            

    # pi1 = BB_plus_x
    # pi2 = 2
    pixel_time = time_by_line/nb_px_x
    AD_by_px = round(AD_frequency*pixel_time) ## CC = oversampling
    AA = round(min(max(1, AD_frequency*SM_cycle), 1000000))
    if dll_diggalvos_timing: 
        lib_valcycles = dll_tuple[0]; BOut_pt= dll_tuple[1];  calculated_at_time_S2xExp_Equation_pt= dll_tuple[3]
        lib_valcycles.Galvo2(induct_H, angle_range, ohm_val, time_by_line, max_voltage, torque, inertia, dll_tuple[4], calculated_at_time_S2xExp_Equation_pt) 
        #double __cdecl Calculated_at_time_S2xExp_Equation= Galvo2(double InductHi, double angle_range_mech, 
        # double Ohm_i, double line_time, double maxVoltageI, double torqueI, 
        # double inertiaI, double *mechangle, 
        # double *Calculated_at_time_S2xExp_Equation);s
        # calculated_at_time_S2xExp_Equation_pt[0] = 2.385054948160588e-05 with these params angle_range_mech = 6.52124  line_time = 8e-3 # sec
        reversing_time = calculated_at_time_S2xExp_Equation_pt[0]
        # # print('reversing_time', reversing_time)
        BB_plus_x = numpy.uint16(0.49 + (time_by_line + reversing_time+turn_time_unidirek*unidirectional)/SM_cycle) # from Labview
        
        B_out = lib_valcycles.FindValidCycles(int(AA), BB_plus_x, int(AD_by_px) , BOut_pt, dll_tuple[2]) #(uint16_t AFix, uint32_t BX, uint32_t CFix, uint32_t *BOut, uint32_t *D)
        # # BOut = 804 with these 40, 803, 80
        # BOut can be passed either in return or in BOut_pt
        
    else:     
    ## fit exp. for reversing time
        x0_dflt = 1.2e-5
        reversing_time = galvos_reversing_time_script.calc_reversing_time_galvos(optimize, numpy, induct_H, ohm_val, max_voltage, torque, inertia, angle_range, time_by_line, x0_dflt)
        # # print('reversing_time', reversing_time)
        BB_plus_x = numpy.uint16(0.49 + (time_by_line + reversing_time+turn_time_unidirek*unidirectional)/SM_cycle)
        prod1 = AD_by_px*1*int(numpy.ceil((0.5 + BB_plus_x/(AD_by_px/AA)))); B_out = prod1/AA
    
    line_plus_turn = SM_cycle*B_out
    turn_time = line_plus_turn - time_by_line # should be 4e-5 s
        
    # turn_time = 8e-5 # !!!!
    galvo_too_late = turn_time - SM_cycle*int(int(turn_time/SM_cycle)) # in s
    galvo_too_far = galvo_too_late*line_speed
    
    # # print('292', turn_time*1e5, BB_plus_x, B_out, line_plus_turn, turn_time, galvo_too_late, reversing_time, angle_range, time_by_line, grad,time_by_line*(line_speed.real**2 + line_speed.imag**2)**(1/2), line_speed, int(AA), AD_by_px) #prod1, AA, AD_by_px, (0.5 + BB_plus_x/(AD_by_px/AA)))
    
    # print('galvo_too_late = %f, galvo_too_far.real = %f, galvo_too_far.imag = %f, turn_time = %f, SM_cycle= %f, line_plus_turn= %f, time_by_line= %f' % (galvo_too_late*1e20, galvo_too_far.real*1e20, galvo_too_far.imag*1e20, turn_time , SM_cycle, line_plus_turn, time_by_line))

    ## init _loop + 1st line


    # print(pos_start.real, pos_start.imag)
    # 
    # print('\n in list glavos, param FORCED for 700x700u 2u \n')
    
    def init_firstline_galvo(scan_array, nb_loops, line_speed, pos_start, new_scaling_galvo, start_time, time_by_line, SM_move_time, SM_cycle):
    
        scan_array.append([]) # create first row
        scan_array[0].extend(['AV',start_time,3,pos_start.real/new_scaling_galvo]) # fill 1st row
        scan_array.append([]) # create 2nd row
        scan_array[1].extend(['AV',start_time,4,pos_start.imag/new_scaling_galvo]) # fill 2nd row  
        scan_array.append([]) # create 3rd row
        scan_array[2].extend(['AI',start_time,3,line_speed.real/new_scaling_galvo*SM_cycle]) # fill 3rd row 
        scan_array.append([]) # create 4th row
        scan_array[3].extend(['AI',start_time,4,line_speed.imag/new_scaling_galvo*SM_cycle]) # fill 4th row
        scan_array.append([]) # create 5th row
        scan_array[4].extend(['AS',(start_time + SM_move_time)/SM_cycle,9,nb_loops]) # fill 
        scan_array.append([]) # create 6th row
        scan_array[5].extend(['AV',(start_time + SM_move_time)/SM_cycle,7,7]) # 7 is 111 in binary 
    # end of init _loop + 1st line
    # Actions : (AV = Abs, AI = Inc, AE = LoopEn, AS = LoopSt), 
    # Time, en 10us, ex : pour 4.8s taper 480 000
    # channel : 3 for X, 4 for Y, 9 for loop, 7 for digital
    # value (/s) est un integer signe
    
        return start_time + time_by_line

## 'line function'
# in vectorZuScanSteuerung

    def line_func_galvo(scan_array, start_time, time_by_line, new_scaling_galvo, line_speed, SM_cycle):
    
        scan_array.append([]) # create ct_th row
        N = len(scan_array)
        scan_array[N-1].extend(['AI',start_time/SM_cycle,3,line_speed.real/new_scaling_galvo*SM_cycle]) # fill 
        # apply positive value if odd iteration, negative if even
        scan_array.append([]) # create ct_th row
        scan_array[N].extend(['AI',start_time/SM_cycle,4,line_speed.imag/new_scaling_galvo*SM_cycle]) # fill 
        # apply positive value if odd iteration, negative if even
        
        return start_time + time_by_line # start_AD_raster[ct], in s
        
## 'turn' function
    
    def turn_func_galvo(scan_array, start_time, galvo_too_late, cond, corr_incr_line, SM_cycle, turn_time):
        # incr_line has always the same value !
    
        galvo_raster = start_time + galvo_too_late # in s
    
        if cond == 0: # 'turn' func on galvo_xy
            # # print('wlh', corr_incr_line, turn_time , galvo_too_late)
            corr_incr_line = corr_incr_line/(turn_time - galvo_too_late)
            scan_array.append([]) # create ct_th row
            N = len(scan_array)
            scan_array[N-1].extend(['AI',galvo_raster/SM_cycle,3,corr_incr_line.real/new_scaling_galvo*SM_cycle]) # fill  
        
            scan_array.append([]) # create ct_th row
            scan_array[N].extend(['AI',galvo_raster/SM_cycle,4,corr_incr_line.imag/new_scaling_galvo*SM_cycle]) # fill 
    
        elif cond == 1:  # 'turn' func on digitals
            scan_array.append([]) # create ct_th row
            N = len(scan_array)
            scan_array[N-1].extend(['AV',galvo_raster/SM_cycle,7,5])  # = 101 in binary, 7 for digital
        
            scan_array.append([]) # create ct_th row
            start_time = start_time + turn_time
            scan_array[N].extend(['AV',start_time/SM_cycle,7,7]) # = 111 in binary, 7 for digital 
            
        elif cond == 2:  # 'turn' func on digitals
            scan_array.append([]) # create ct_th row
            N = len(scan_array)
            scan_array[N-1].extend(['AV',start_time/SM_cycle,7,5])  # = 101 in binary, 7 for digital
        

## LoopEnd function

    def loop_end_middle_galvo(scan_array, start_time, SM_move_time, SM_cycle, turn_time, nb_loops, time_by_line, cond):
    # kind of 'turn' on Digital
# loop_end
        scan_array.append([]) # create ct_th row
        N = len(scan_array)
        
        if cond == 0:  # bidirek
            galvo_raster = (start_time + galvo_too_late) + SM_move_time - turn_time # 1723
            scan_array[N-1].extend(['AV',galvo_raster/SM_cycle,7,5])  # = 101 in binary, 7 for digital
    # AV,1723,7,5', 'AE,1727,9,0', 'AV,320111,7,7'
            galvo_raster = (start_time + galvo_too_late) + SM_move_time - turn_time # 1723
            galvo_raster = galvo_raster + turn_time # 1727
            scan_array.append([]) # create ct_th row
            scan_array[N].extend(['AE',galvo_raster/SM_cycle,9,0]) # AE = LoopEn, 9 for Loop
    
            start_time = start_time*nb_loops  # multiply time by nb_loops, ex 319992
            start_time0 = start_time +  SM_move_time #  320111
            scan_array.append([]) # create ct_th row
    # start_time = start_time + turn_time
            scan_array[N+1].extend(['AV',start_time0/SM_cycle,7,7]) # = 111 in binary, 7 for digital
            
        elif cond == 1:  # unidirek
            
            galvo_raster = start_time + SM_move_time # 954+119=1073
            scan_array[N-1].extend(['AE',galvo_raster/SM_cycle,9,0]) # AE = LoopEn, 9 for Loop
    
            start_time = start_time*nb_loops  # multiply time by nb_loops, ex 319992
            start_time = start_time +  SM_move_time #  320111
            scan_array.append([]) # create ct_th row
    # start_time = start_time + turn_time
            scan_array[N].extend(['AV',start_time/SM_cycle,7,7]) # = 111 in binary, 7 for digital

        return start_time + time_by_line # 'line_func' effect is corrected here

# up = loop_end

## EndEnd function

    def end_end_galvo(scan_array, start_time0, start_time, turn_time, time_by_line, SM_cycle):
        scan_array.append([]) # create ct_th row
        N = len(scan_array)
        scan_array[N-1].extend(['AI',start_time0/SM_cycle,3,0]) # AI = Inc., 3 = galvoX, at 321596
        scan_array.append([]) # create ct_th row
        scan_array[N].extend(['AI',start_time0/SM_cycle,4,0]) # AI = Inc., 4 = galvoY, at 321596
        scan_array.append([]) # create ct_th row
        scan_array[N+1].extend(['AV',start_time/SM_cycle,7,0]) # AV = Abs., 7 = Digital

## fill array of scan

#    start_AD_raster = []
    start_time = 0
#    ct = 0
    
    start_time = init_firstline_galvo(scan_array, nb_loops, line_speed, pos_start, new_scaling_galvo, start_time, time_by_line, SM_move_time, SM_cycle) # start_time = 800
    
    ## b1 : turn - line - turn
    if not unidirectional: # bidirek
        corr_incr_line = incr_line - (1 + 1j)*galvo_too_far # complex number, with a -
    else: # # unidirek
        corr_incr_line = incr_line - line_speed*time_by_line
        corr_incr_line -=  (1 + 1j)*galvo_too_far
    
    turn_func_galvo(scan_array, start_time, galvo_too_late, 0, corr_incr_line, SM_cycle, turn_time) # 'turn' func on galvo_xy

    start_time0 = start_time + turn_time # = 804
    # start_time0 because need to be used by line_func (and modified by it) and untouched by 2nd turn_func
    start_time = start_time + SM_move_time # 800+119 = 919 
    
    if not unidirectional: # bidirek
        
        # # will write the 3rd two AI
        start_time0 = line_func_galvo(scan_array, start_time0, time_by_line, new_scaling_galvo, -line_speed, SM_cycle) # line, be careful to have -linespeed and not linespeed, at 804. Return at 1604
        
        turn_func_galvo(scan_array, start_time, galvo_too_late, 1, corr_incr_line, SM_cycle, turn_time) # 'turn' func on digitals, at 919 
        
        corr_incr_line = incr_line + (1 + 1j)*galvo_too_far # complex number, with a +
        
        turn_func_galvo(scan_array, start_time0, galvo_too_late, 0, corr_incr_line, SM_cycle, turn_time) # 'turn' func on galvo_xy
        # at 1604
        # up = b1

        ## b2 : line - turn - line
        
        start_time = start_time0 + turn_time # = 1608
        
        line_func_galvo(scan_array, start_time, time_by_line, new_scaling_galvo, line_speed, SM_cycle) # line, be careful to have linespeed and not -linespeed # WARNING : start_time MUST NOT be assigned here, at 1608
    
        # LoopEnd, middle
        start_time = loop_end_middle_galvo(scan_array, start_time, SM_move_time, SM_cycle, turn_time, nb_loops, time_by_line, 0) # at 1608, return at 1608*199+800=320792
        # up = LoopEnd, middle
        
        corr_incr_line = incr_line - (1 + 1j)*galvo_too_far # complex number, with a -
        
        turn_func_galvo(scan_array, start_time, galvo_too_late, 0, corr_incr_line, SM_cycle, turn_time) # 'turn' func on galvo_xy
        
        start_time0 = start_time + turn_time # 320792 + 4 = 320796
        
        start_time0 = line_func_galvo(scan_array, start_time0, time_by_line, new_scaling_galvo, -line_speed, SM_cycle) # line, be careful to have -linespeed and not linespeed, at 320796, return at 321596
        
        start_time = start_time + SM_move_time # 320792 + 119 = 320911 
        
        turn_func_galvo(scan_array, start_time, galvo_too_late, 1, corr_incr_line, SM_cycle, turn_time) # 'turn' func on digitals, at 320911
        # up = b2
        start_time = start_time + turn_time + time_by_line # 320911 + 4 +800 = 321715

        
    else: # unidirek
    
        turn_func_galvo(scan_array, start_time + SM_move_time*SM_cycle, galvo_too_late, 2, corr_incr_line, SM_cycle, turn_time) # 'turn' func on digitals, at 919 
        start_time0_prev = start_time0

        # # will write the 3rd two AI
        start_time0 = line_func_galvo(scan_array, start_time0, time_by_line, new_scaling_galvo, line_speed, SM_cycle) # line, be careful to have -linespeed and not linespeed, at 804. Return at 1604
    
        # LoopEnd, middle
        start_time = loop_end_middle_galvo(scan_array, start_time0_prev, SM_move_time, SM_cycle, turn_time, nb_loops, time_by_line, 1) # at 1608, return at 1608*199+800=320792
        # up = LoopEnd, middle
        # print(start_time)
        start_time0 = start_time - SM_move_time
    
    
    # end_end
    # will print the last 3 rows
    end_end_galvo(scan_array, start_time0, start_time, turn_time, time_by_line, SM_cycle)
    # up = end_end
    
    list1 = ['C']
    
    # # print(unidirectional, scan_array)
    # # err
    
    for k in range(0, len(scan_array)):
        str_1 = ('%s,%d,%d,%d' % (scan_array[k][0], round(scan_array[k][1]), round(scan_array[k][2]), round(scan_array[k][3])))
        
        list1.append(str_1)
        
    time_fin = (scan_array[len(scan_array)-2][1])*SM_cycle # in s, it's indeed a + (see initGalvo)
    
    import fractions
    def lcm(a,b): 
        pow = max(int(numpy.ceil(numpy.log10(1/b))), int(numpy.ceil(numpy.log10(1/a))))+1
        a = round(a*10**pow)
        b = round(b*10**pow)
        return abs(a * b) / fractions.gcd(a,b)/10**pow
    
    
    time_point = time_fin + SM_cycle
    
    prod = lcm(1/AD_frequency, SM_cycle)
    xx = time_point/prod
    tot_time = prod*int(numpy.ceil(xx))
    
    ## forcing value of scan list
    
    # uncomment below if needed
    
    # list1 = ['C',
    # 'AV,0,3,0',
    # 'AV,0,4,16026487687',
    # 'AI,0,3,-22973927',
    # 'AI,0,4,-22973927',
    # 'AS,119,9,174',
    # 'AV,119,7,7',
    # 'AI,700,3,5743482',
    # 'AI,700,4,-5743482',
    # 'AI,708,3,22973927',
    # 'AI,708,4,22973927',
    # 'AV,819,7,5',
    # 'AV,827,7,7',
    # 'AI,1408,3,5743482',
    # 'AI,1408,4,-5743482',
    # 'AI,1416,3,-22973927',
    # 'AI,1416,4,-22973927',
    # 'AV,1527,7,5',
    # 'AE,1535,9,0',
    # 'AV,246503,7,7',
    # 'AI,247084,3,5743482',
    # 'AI,247084,4,-5743482',
    # 'AI,247092,3,22973927',
    # 'AI,247092,4,22973927',
    # 'AV,247203,7,5',
    # 'AV,247211,7,7',
    # 'AI,247792,3,0',
    # 'AI,247792,4,0',
    # 'AV,247911,7,0']
    
    # # 200x200um, 0.5um, 20us/px
    # list1 =['C',
    # 'AV,0,3,0',
    # 'AV,0,4,4531626340',
    # 'AI,0,3,-5733613',
    # 'AI,0,4,-5733613',
    # 'AS,119,9,199',
    # 'AV,119,7,7',
    # 'AI,800,3,2866807',
    # 'AI,800,4,-2866807',
    # 'AI,804,3,5733613',
    # 'AI,804,4,5733613',
    # 'AV,919,7,5',
    # 'AV,923,7,7',
    # 'AI,1604,3,2866807',
    # 'AI,1604,4,-2866807',
    # 'AI,1608,3,-5733613',
    # 'AI,1608,4,-5733613',
    # 'AV,1723,7,5',
    # 'AE,1727,9,0',
    # 'AV,320111,7,7',
    # 'AI,320792,3,2866807',
    # 'AI,320792,4,-2866807',
    # 'AI,320796,3,5733613',
    # 'AI,320796,4,5733613',
    # 'AV,320911,7,5',
    # 'AV,320915,7,7',
    # 'AI,321596,3,0',
    # 'AI,321596,4,0',
    # 'AV,321715,7,0']
    
    # # 400x400um, 1um
    # list1 = ['C',
    # 'AV,0,3,0',
    # 'AV,0,4,9173779755',
    # 'AI,0,3,-11536306',
    # 'AI,0,4,-11536306',
    # 'AS,119,9,199',
    # 'AV,119,7,7',
    # 'AI,800,3,5768153',
    # 'AI,800,4,-5768153',
    # 'AI,804,3,11536306',
    # 'AI,804,4,11536306',
    # 'AV,919,7,5',
    # 'AV,923,7,7',
    # 'AI,1604,3,5768153',
    # 'AI,1604,4,-5768153',
    # 'AI,1608,3,-11536306',
    # 'AI,1608,4,-11536306',
    # 'AV,1723,7,5',
    # 'AE,1727,9,0',
    # 'AV,320111,7,7',
    # 'AI,320792,3,5768153',
    # 'AI,320792,4,-5768153',
    # 'AI,320796,3,11536306',
    # 'AI,320796,4,11536306',
    # 'AV,320911,7,5',
    # 'AV,320915,7,7',
    # 'AI,321596,3,0',
    # 'AI,321596,4,0',
    # 'AV,321715,7,0']
    # 
    # tot_time = 321596*SM_cycle
    
    return list1, tot_time #, scan_array
    

    
    