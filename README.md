# scanning_microscopy_ISHG
Scanning microscope (orig. for nonlinear optical microscopy) to acquire images, with speciality for I-SHG microscopy

--- Infos ---
Testing in Windows (7) x64
Python x64 (but worked with x32), version 3.6 (worked with 3.4 and 3.5)
with Anaconda3 (all basic packages)
This API comprises previous uploads such as:
github.com/MaxP92/iMic-Till-python if you have a iMic microscope (not the case for Nikon, Olympus, Thorlabs etc.)
github.com/MaxP92/thorlabs_python_low-level if you have a Thorlabs XY stage (not the case for e.g. Prior or PI)

--- Needed ---
- Anaconda 5.1
- msl-loadlib (github.com/MSLNZ/msl-loadlib) if using Python x64
- pyQt5 (to include in a GUI, but not mandatory)
- pySerial
- pyqtgraph
- py nidaqmx (if using a NI acq. card)
- all libraries for devices (Thorlabs, PI, Ocean Optics etc.)
 !! CHECK the file to_install.txt !!

--- Best practices ---
create a folder "prog microscope 18" where all the GitHub files are located
create also a folder "Recycle imgs" (for the tmp cleaning)
create also a sub-folder "tmp" inside "prog microscope 18" for temporary files
The "var.txt" file is for saving some parameters, you need it

To run, use the "code.txt": in command prompt : 
cd *folder* 
python main_microscope.py
A GUI should appear if no errors

---- Files -----
list_controls.xlsx for a few variables used, wand what they mean
Control_microscope.pdf for a FULL DESCRIPTION of the software and controls

- 2 files of GUI (to open in Qt Designer to check them)
main_microscope.ui
scan_phase_shift_z_jobs.ui

- main_microscope.py just to control the launch
- in modules : gui_script.py is the main GUI control, call of other functions

You might consider only the scan functions : the Class in "scan_main_script.py" calls the laser-scanning (galvos) functions
The Class in "stage_xy_worker_script.py" contains "scan_stage_meth" for stage scanning
see PDF for details

---- I-SHG -----
You may find I-SHG (Interferometric SHG microscopy) details in this publication: 
https://www.osapublishing.org/oe/abstract.cfm?uri=oe-27-26-38435
doi:10.1364/OE.27.038435

Also, more details in the thesis: 

To treat the I-SHG data, refer to rep. 
**

-----------------
 
Consider saying thanks ! --> maxime.pinsard@outlook.com


--------------------------
Copyright to the code is held by the following parties:
Copyright (C) 2019 Maxime Pinsard, INRS-EMT Varennes

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation, version 2.1.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

- Name: scanning_microscopy_ISHG
- Version: 18
- Author: Maxime PINSARD
- Author-email: maxime.pinsard@outlook.com
        
- Platform: Windows
- Classifier: Intended Audience :: Science/Research
- Classifier: License :: OSI Approved :: MIT
- Classifier: Programming Language :: Python
- Classifier: Operating System :: Microsoft :: Windows
