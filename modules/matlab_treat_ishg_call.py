# -*- coding: utf-8 -*-
"""
Created on Mon Sept 12 16:35:13 2019

@author: Maxime PINSARD
"""

from PyQt5.QtCore import QObject, pyqtSlot, pyqtSignal

class Matlab_treat(QObject):
    
    matlabGUI_treatphase_signal = pyqtSignal(int, int, int, str)
    test_GUI_signal = pyqtSignal()
    show_instance_signal = pyqtSignal()
    
    def __init__(self, sys, path_save): 
    
        super(Matlab_treat, self).__init__()
        self.sys= sys
        self.pth_sve = '%s/tmp' % path_save
        
    def start_matlab(self):
        if not hasattr(self,'engmatlab'):
            # from PyQt5 import QtWidgets
            
            if not ('matlab.engine'in self.sys.modules):
                import matlab.engine as matlabengine
                self.matlabengine=matlabengine
            else: self.matlabengine = self.sys.modules['matlab.engine']
            # # a build folder must appear
            print('starting Matlab...')
            self.engmatlab = self.matlabengine.start_matlab() # "-desktop"
            # self.engmatlab.desktop(nargout=0); # see instance
            self.engmatlab.cd(r'E:\MAXIME\codes Matlab\Codes_I-SHG')
            self.test_GUI_here()
    
    @pyqtSlot(int, int, int, str)
    def matlabGUI_treatphase(self, incr_ordr, nb_slice_per_step, ctr_mult,fldrnm):       
        self.engmatlab.cd(self.pth_sve)
        self.engmatlab.python_matlabGUI_treatphase(incr_ordr, nb_slice_per_step, ctr_mult,fldrnm, nargout=0); # keep ;
    
    @pyqtSlot()    
    def test_GUI_here(self):
        not_here = False
        if not hasattr(self,'engmatlab'): not_here = True
        else: 
            try: a=self.engmatlab.eval("findobj(allchild(groot), 'flat', 'type', 'figure','Name', 'I_SHG_GUI')", nargout=1) # find figures
            except self.matlabengine.engineerror.RejectedExecutionError: not_here = True
        if not_here: 
            self.engmatlab = self.matlabengine.start_matlab() # matlab stopped#print('lala')
            self.engmatlab.cd(r'E:\MAXIME\codes Matlab\Codes_I-SHG')
            a=self.engmatlab.eval("findobj(allchild(groot), 'flat', 'type', 'figure','Name', 'I_SHG_GUI')", nargout=1) # find figures
        b=self.engmatlab.get(a, 'Name')
        if (type(b) == str and b == 'I_SHG_GUI'): pass # GUI here
        else:  # # start GUI            
            print('starting GUI matlab...')
            self.engmatlab.I_SHG_GUI()
            print('...GUI + matlab ok.')
            
    def show_instance(self):
        self.engmatlab.desktop(nargout=0)
        
    def __del__(self):
        try: self.engmatlab.quit()
        except Exception as e: print(e)