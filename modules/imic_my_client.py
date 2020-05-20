# -*- coding: utf-8 -*-
"""
Created on May 3rd 16:35:13 2018

@author: Maxime PINSARD
"""


# import os
# import sys
# 
# path11 = 'C:\\Users\\admin\\Documents\\Python\\Essais\\iMic 64 bits'
# sys.path.append(path11 )
# 
# os.chdir(path11 )

from msl.loadlib import Client64

class MyClient_imic(Client64):
    """Send a request to 'MyServer' to execute the methods and get the response.
    uses version 0.4.1.dev0 and more
    """

    def __init__(self):
        # Use the default '127.0.0.1' address to start the 'my_server.py' module
        Client64.__init__(self, module32='modules/imic_my_server')
     
    '''
    def add(self, a, b):
        # The Client64 class has a 'request32' method to send a request to the 32-bit server.
        # Send the 'a' and 'b' arguments to the 'add' method in MyServer.
        return self.request32('add', a, b)
    '''   
    
    def close_imic(self, handle1_val):
  
        self.request32('close_imic', handle1_val) # return ee
        
    def open_lib(self):
        
        return self.request32('open_lib') # return 0
    
    def OpenByRS232(self, port_imic):
        
        return self.request32('OpenByRS232', port_imic) # handle1
    
    def init_imic(self, handle1_val):
        
        return self.request32('init_imic', handle1_val) # return ee
        
        
    def filter_pos_top_get( self, handle1_val):    
        
        return self.request32('filter_pos_top_get', handle1_val) # posFilt_1_get.value
        
        
    def filter_pos_bottom_get( self, handle1_val):
        
         return self.request32('filter_pos_bottom_get', handle1_val) # posFilt_2_get.value
         
    ## set
        
    def filter_pos_top_set( self,  handle1_val, posFilt_top):
        
        return self.request32('filter_pos_top_set', handle1_val, posFilt_top) #  return errorcode
 
    def filter_pos_bottom_set(self, handle1_val, posFilt_bottom):   
    
        return self.request32('filter_pos_bottom_set', handle1_val, posFilt_bottom) #  return errorcode
            
    def obj_choice_set(self,  handle1_val, obj_choice):
        
        return self.request32('obj_choice_set', handle1_val, obj_choice) #  return errorcode
        
    def obj_choice_get(self, handle1_val):
        
        return self.request32('obj_choice_get', handle1_val) #return choice_obj[0]

    def pos_Z_motor_set(self, handle1_val, posZ_motor):
        
        return self.request32('pos_Z_motor_set', handle1_val, posZ_motor) #  return errorcode
    
    def pos_Z_piezo_set(self, handle1_val, posZ_piezo):
        
        return self.request32('pos_Z_piezo_set', handle1_val, posZ_piezo) #  return errorcode
    
    def step_Z_piezo(self, handle1_val, stepZ_piezo):
        
        return self.request32('step_Z_piezo', handle1_val, stepZ_piezo) #  return errorcode
            
    def pos_Z_motor_get(self,  handle1_val):
        
        return self.request32('pos_Z_motor_get', handle1_val) # return posZ_mtr_got[0] 
        
    def pos_Z_piezo_get( self, handle1_val):
    
        return self.request32('pos_Z_piezo_get', handle1_val) # return posZ_pz_got[0]
     
    def cleanup_subprocess( self):
        self._cleanup_subprocess()

