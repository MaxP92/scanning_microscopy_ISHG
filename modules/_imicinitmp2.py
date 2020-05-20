# -*- coding: utf-8 -*-
"""
Created on May 11 09:35:13 2016

@author: Maxime PINSARD
""" 

# # 2016.5.11 Maxime PINSARD
# # from C to python

import ctypes

## from C to python

c_long = ctypes.c_long
c_char_p = ctypes.c_char_p
c_char = ctypes.c_char
c_int32= ctypes.c_int32
c_int= ctypes.c_int
# c_int_p = ctypes.c_int_p
c_uint8= ctypes.c_uint8
c_void_p = ctypes.c_void_p
c_longlong = ctypes.c_longlong
c_double= ctypes.c_double
c_int8 = ctypes.c_int8
c_int16 = ctypes.c_int16
c_bool = ctypes.c_bool
c_uint32 = ctypes.c_uint32
c_uint16 = ctypes.c_uint16
POINTER = ctypes.POINTER

#  useful link : http://www.southampton.ac.uk/~feeg6002/ipythonnotebooks/Introduction-ctypes.html

## ensure types

def set_ctypes_argtypes_mp(lib):

    lib.IMIC_OpenByRS232.argtypes = [c_char_p, c_void_p]
    lib.IMIC_OpenByRS232.restype = c_longlong
    
    lib.IMIC_IsInit.argtypes = [c_void_p, c_void_p]
    lib.IMIC_IsInit.restype = c_long
    
    lib.IMIC_Close.argtypes = [c_void_p] # !!
    lib.IMIC_Close.restypes = c_long

    lib.IMIC_GetObjectiveTurretPos.argtypes = [c_void_p, POINTER(c_int16)]
    lib.IMIC_GetObjectiveTurretPos.restype = c_long
    
    lib.IMIC_GetNumberOfZAxes.argtypes = [c_void_p, POINTER(c_int16)]
    lib.IMIC_GetNumberOfZAxes.restypes = c_long
    
    lib.IMIC_GetNumberOfFilterChangers.argtypes = [c_void_p, POINTER(c_int16)]
    lib.IMIC_GetNumberOfFilterChangers.restypes = c_long
    
    lib.IMIC_GetFilterChangerPos.argtypes = [c_void_p, c_int, POINTER(c_int16)]
    lib.IMIC_GetFilterChangerPos.restypes = c_long
    
    lib.IMIC_SetObjectiveTurretPosAbs.argtypes = [c_void_p, c_int]
    lib.IMIC_SetObjectiveTurretPosAbs.restype = c_long
    
    lib.IMIC_SetObjectiveTurretPosAbs.argtypes = [c_void_p, c_int]
    lib.IMIC_SetObjectiveTurretPosAbs.restype = c_long

    lib.IMIC_GetXYPos.argtypes = [c_void_p, POINTER(c_double), POINTER(c_double)]
    lib.IMIC_GetXYPos.restype = c_long

    lib.IMIC_GetZPos.argtypes = [c_void_p, c_int, POINTER(c_double)]
    lib.IMIC_GetZPos.restype = c_long
    
    lib.IMIC_SetXYPosAbs.argtypes = [c_void_p, c_double, c_double]
    lib.IMIC_SetXYPosAbs.restype = c_long

    lib.IMIC_SetZPosAbs.argtypes = [c_void_p, c_int, c_double]
    lib.IMIC_SetZPosAbs.restypes = c_long
    
    lib.IMIC_SetZPosRel.argtypes = [c_void_p, c_int, c_double]
    lib.IMIC_SetZPosRel.restypes = c_long

def set_ctypes_argtypes_validcycles_mp(lib):
    
    lib.FindValidCycles.argtypes =[c_uint16, c_uint32, c_uint32, POINTER(c_uint32), POINTER(c_uint32)] #(uint16_t AFix, uint32_t BX, uint32_t CFix, uint32_t *BOut, uint32_t *D)
    lib.FindValidCycles.restypes = c_uint32
    
    lib.Galvo2.argtypes =[c_double, c_double, c_double, c_double, c_double, c_double, c_double, POINTER(c_double), POINTER(c_double)] #(uint16_t AFix, uint32_t BX, uint32_t CFix, uint32_t *BOut, uint32_t *D)
    lib.Galvo2.restypes = c_double
#double __cdecl Calculated_at_time_S2xExp_Equation= Galvo2(double InductHi, double angle_range_mech, 
# double Ohm_i, double line_time, double maxVoltageI, double torqueI, 
# double inertiaI, double *mechangle, 
# double *Calculated_at_time_S2xExp_Equation);

    
    

