# -*- coding: utf-8 -*-
"""
Created on May 3rd 16:35:13 2018

@author: Maxime PINSARD
"""

from msl.loadlib import Server32
import ctypes #, time

path_computer = 'C:/Users/admin/Documents/Python'

path11 = '%s/Packages' % path_computer

class MyServer_imic(Server32):
    """A wrapper around any 32-bit C++ library
    uses version 0.4.1.dev0 and more
    """

    def __init__(self, host, port, quiet, **kwargs):
        # Load the 'cpp_lib32' shared-library file using ctypes.CDLL
        Server32.__init__(self, ('%s\\tillimic.dll' % path11), 'cdll', host, port, quiet)
        
    '''
    def add(self, a, b):
        # The Server32 class has a 'lib' attribute that is a reference to the ctypes.CDLL object.
     
    '''
        
    def close_imic(self, handle1_val):
  
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        errorcode = self.lib.IMIC_Close(handle1)
        
        if (hasattr(self, 'lib') and hasattr(self, 'handle1_val')):
            handle_lib = self.lib._handle # obtain the DLL handle
            ctypes.windll.kernel32.FreeLibrary(handle_lib)
            del self.lib, self.handle1_val
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
    
        # # return errorcode
        
    def open_lib(self):
        
        # if (hasattr(self, 'lib')):
        #     
        #     # self.imic_core.close_imic(self.lib_imic, self.handle1)
        #     handle_lib = self.lib._handle # obtain the DLL handle
        #     ctypes.windll.kernel32.FreeLibrary(handle_lib)
        #     del self.lib
        
        from modules import _imicinitmp2
        
        _imicinitmp2.set_ctypes_argtypes_mp(self.lib)
        
        return 0
    
    def OpenByRS232(self, port_imic):
        
        port_imic = port_imic.encode('utf-8')
        port_imic = ctypes.c_char_p(port_imic)
        
        handle1 = ctypes.c_void_p() # pointer
        
        errorcode = self.lib.IMIC_OpenByRS232(port_imic, ctypes.byref(handle1)) 
        
        if errorcode == 6:
            raise Exception("wrong handle\n")
        elif errorcode == 10:
            raise Exception("failed to open com port\n")
        
        return handle1.value
        
    def init_imic(self, handle1_val):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        # ******* (re)init imic *********************************************************************
        
        is_init_imic = ctypes.c_void_p()
        
        try:
            ee = self.lib.IMIC_IsInit (handle1, ctypes.byref(is_init_imic)) # ctypes.byref
        
        except Exception as e: # error seen by Python
            print("error :" , e)
            try_rld_lib_com = 1
            
        else: # no error seen by Python
            if ee != 0: # perhaps error seen by iMic  
                # # raise Exception("error : %d\n" % ee)
                print("error : %d\n" % ee)
                try_rld_lib_com = 1
            else: # no error
                try_rld_lib_com = 0
        
        if (try_rld_lib_com or not bool(is_init_imic)): # if not already initialised
        
        # int32_t IMIC_Init(int32_t handle, uint8_t *ips);
            
            print('Is initing iMic : wait 10sec ... \n')
            
            try:
                ee = self.lib.IMIC_Init (handle1, None)
            
            except Exception as e: # error seen by Python
                print("error when trying to init iMic:" , e)
                ee = 1 # != 0 so will reload
            
            if ee == 6:
                print("wrong handle\n") # raise Exception
            elif ee == 10:
                print("failed to open com port\n")
            elif ee == 11:
                print("Failed to initialise\n")
            elif ee == 0:   
                print("iMic initiated.\n")
                
        return ee
        
        
    def filter_pos_top_get(self, handle1_val):    
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        # filter 1 (filtre du haut)
        
        empty_int = (ctypes.c_int16*1)()
        posFilt_1_get = ctypes.cast(empty_int, ctypes.POINTER(ctypes.c_int16))
        
        errorcode = self.lib.IMIC_GetFilterChangerPos (handle1, 0, posFilt_1_get)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return posFilt_1_get[0]     

        
    def filter_pos_bottom_get(self,  handle1_val):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        # filter 2
        
        empty_int = (ctypes.c_int16*1)()
        posFilt_2_get = ctypes.cast(empty_int, ctypes.POINTER(ctypes.c_int16))
        
        errorcode = self.lib.IMIC_GetFilterChangerPos (handle1, 1, posFilt_2_get)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
        
        return posFilt_2_get[0]
        
    ## set
        
    def filter_pos_top_set( self,  handle1_val, posFilt_top):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        # # filter 1 (filtre top)
        
        errorcode = self.lib.IMIC_SetFilterChangerPosAbs (handle1, 0, posFilt_top)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return errorcode
            
    def filter_pos_bottom_set(self, handle1_val, posFilt_bottom):   
    
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        # # filter 2 (bottom)
        
        # # = 1 for mirror of stage path
        
        errorcode = self.lib.IMIC_SetFilterChangerPosAbs (handle1, 1, posFilt_bottom)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return errorcode
            
    def obj_choice_set(self,  handle1_val, obj_choice):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        if not (obj_choice == 0 or obj_choice == 1 or obj_choice == 2): # # #4 (3) is not safe
            obj_choice = 0
            print("obj turret out of range")
            
        # 0 = 20X, 1 = 40X
        errorcode = self.lib.IMIC_SetObjectiveTurretPosAbs(handle1, obj_choice)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return errorcode
        
    def obj_choice_get(self, handle1_val):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
    
        empty_int = (ctypes.c_int16*1)()
        choice_obj = ctypes.cast(empty_int, ctypes.POINTER(ctypes.c_int16))
        
        errorcode =  self.lib.IMIC_GetObjectiveTurretPos (handle1, choice_obj)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
    
        return choice_obj[0]
        
        
    def pos_Z_motor_set(self, handle1_val, posZ_motor):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
        
        # stage Z
        
        # zPosition1 = 20.235 # up to 20.5
        
        # upt to 1 000 000 000
        # init 2576980378
        
        max_Z_motor = 22 # mm
        
        if posZ_motor > max_Z_motor:
            posZ_motor = max_Z_motor
            print('max Z motor is %s' % max_Z_motor)
        elif posZ_motor < 0:
            posZ_motor = 0
            print('min Z motor is 0')
        
        errorcode = self.lib.IMIC_SetZPosAbs (handle1, 0, posZ_motor)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return errorcode
    
    def pos_Z_piezo_set(self, handle1_val, posZ_piezo):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer

        # piezo Z
        # max = .25 !!!!
        # upt to 1 000 000 000
        # init 2576980378
        
        if posZ_piezo > 0.25:
            posZ_piezo = 0.25
            print('max Z piezo is 0.25')
        elif posZ_piezo < 0:
            posZ_piezo = 0
            print('min Z piezo is 0')
        
        # # print('told piezoZ to go to', posZ_piezo)
        
        errorcode = self.lib.IMIC_SetZPosAbs (handle1, 1, posZ_piezo)
                
        if errorcode != 0:
            if errorcode == 12:
                raise Exception("unknown error")
            raise Exception("error : %d\n" % errorcode)
            
        return errorcode
    
    def step_Z_piezo(self, handle1_val, stepZ_piezo):  
    
        handle1 = ctypes.c_void_p(handle1_val) # pointer
    
        errorcode = self.lib.IMIC_SetZPosRel (handle1, 1, stepZ_piezo)
        if errorcode != 0:
            if errorcode == 12:
                raise Exception("unknown error")
            raise Exception("error : %d\n" % errorcode)
        return errorcode
    
            
    def pos_Z_motor_get(self,  handle1_val):
        
        handle1 = ctypes.c_void_p(handle1_val) # pointer
    
        # stage Z
        
        # posZ_mtr_got = empty_array_double.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
        # posZ_mtr_got = ctypes.cast([0.0], ctypes.POINTER(ctypes.c_double))
        empty_double = (ctypes.c_double*1)()
        posZ_mtr_got = ctypes.cast(empty_double, ctypes.POINTER(ctypes.c_double))
        
        errorcode = self.lib.IMIC_GetZPos (handle1, 0, posZ_mtr_got)
        
        if errorcode != 0:   
            
            if errorcode == 2:
                raise Exception("missing Z axis\n")
            else:
                raise Exception("error : %d\n" % errorcode)
        
        if posZ_mtr_got[0] == 0:
            print('PosZ is 0')
        else:
            pass
            # # print("Z motor (core)= %.3f" % posZ_mtr_got[0])
        
        return posZ_mtr_got[0] 
        
    def pos_Z_piezo_get( self, handle1_val):
    
        handle1 = ctypes.c_void_p(handle1_val) # pointer

        # piezo Z
        
        empty_double = (ctypes.c_double*1)()
        posZ_pz_got = ctypes.cast(empty_double, ctypes.POINTER(ctypes.c_double))
        
        errorcode = self.lib.IMIC_GetZPos (handle1, 1, posZ_pz_got)
        
        if errorcode != 0:   
            if errorcode == 2:
                raise Exception("missing Z axis\n")
            else:
                raise Exception("error : %d\n" % errorcode)
        
        if posZ_pz_got[0] == 0:
            print('PiezoZ is 0')
        else:
            pass
            # # print("Z piezo = %.3f" % posZ_pz_got[0])
        
        return posZ_pz_got[0]
        
    ## not used functions
    
    def pos_Z_motor_relative_set(self, handle1):
        
        zPositionRel = 10
        # upt to 1 000 000 000
        # init 2576980378
            # 1316134912
        
        errorcode = self.lib_imic.IMIC_SetZPosRel (handle1, 0, zPositionRel)
        # errorcode = lib.IMIC_SetZPosAbs (handle1, 0, 2576980378)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
    def number_filter_get(self, handle1):
    
        nb_filters = self.empty_array_int
        
        errorcode = self.lib_imic.IMIC_GetNumberOfFilterChangers (handle1, nb_filters)
                
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return nb_filters[0]
    
    def pos_XY_get(self,handle1): # surely with old PRIOR stage
            
        # int IMIC_GetXYPos (void  handle, double  xPosition, double  yPosition)
        
        # xPosition = ctypes.c_void_p()
        # yPosition  = ctypes.c_void_p()
        # use a pointer to a double (see getZ example)
        xPosition = self.empty_array_double
        yPosition = self.empty_array_double
            
        errorcode = self.lib_imic.IMIC_GetXYPos (handle1, xPosition, yPosition)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        return xPosition[0], yPosition[0]
    
    def pos_X_set( self, handle1, xPosition): # surely with old PRIOR stage
                    
        errorcode = self.lib_imic.IMIC_SetXPosAbs (handle1, xPosition)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        
            
    def pos_Y_set(self, handle1, yPosition): # surely with old PRIOR stage
            
        errorcode = self.lib_imic.IMIC_SetYPosAbs (handle1, yPosition)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
    def nb_Z_axes_get(self, handle1, znumber_axe):
    
        # Returns the current number of axes.
        # The indices are 0-based. Thus, the last legal index is number-1.
    
        # znumber_axes = ctypes.c_void_p()
        znumber_axe = self.empty_array_int
        
        errorcode = self.lib_imic.IMIC_GetNumberOfZAxes (handle1, znumber_axe)
        
        if errorcode != 0:   
            raise Exception("error : %d\n" % errorcode)
            
        print("Z nb axes = %d" % znumber_axes.value)
        
        return znumber_axe[0]

    
