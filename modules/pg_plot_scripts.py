# -*- coding: utf-8 -*-
"""
Created on Mon Aug 07 16:35:13 2016

@author: Maxime PINSARD
"""

def pg_plot_init(self, pyqtgraph, numpy, param_ini):
    '''
    define all the pyqtgraph plots objects
    '''
    
    ## add plots
    
    self.LUT = self.LUT_2= None
    
    self.vb_plot_img = self.graphicsView_img.addPlot(row=0, col=0, rowspan=1, colspan=1) # graphicsView_img is a GraphicsLayoutWidget created in QtDesigner by promoting a GraphicsView to a GraphicsLayoutWidget (see doc)
    # Plot has a viewBox + axes
    self.vb_plot_img.setAspectLocked()
    self.img_item_pg = pyqtgraph.ImageItem()
    self.vb_plot_img.addItem(self.img_item_pg)
    
    self.graph1TxtMousePos = pyqtgraph.LabelItem(justify = 'left')
    # self.vb_plot_img.addItem(self.graph1TxtMousePos, ignoreBounds = True)
    self.graphicsView_img.addItem(self.graph1TxtMousePos) #, ignoreBounds = True)
    
    self.vb_plot_img_2 = self.graphicsView_img.addPlot(row=0, col=2, rowspan=1, colspan=1) # graphicsView_img is a GraphicsLayoutWidget created in QtDesigner by promoting a GraphicsView to a GraphicsLayoutWidget (see doc)
    self.vb_plot_img_2.setAspectLocked()
    self.img_item_pg_2 = pyqtgraph.ImageItem()
    self.vb_plot_img_2.addItem(self.img_item_pg_2)
    
    self.vb_real_pg = []
    vbs = [self.vb_plot_img, self.vb_plot_img_2]
    for vb in vbs:
        self.vb_real_pg.append(vb.getViewBox()) # real View box
        self.vb_real_pg[-1].setLimits(xMin = param_ini.xMin_pg, xMax = param_ini.xMax_pg, yMin = param_ini.yMin_pg, yMax = param_ini.yMax_pg, minXRange= param_ini.minXRange_pg, maxXRange= param_ini.maxXRange_pg, minYRange= param_ini.minYRange_pg, maxYRange= param_ini.maxYRange_pg)
        self.vb_real_pg[-1].invertY(True)
    
    # NOT REALLY POSSIBLE to put it under the graph
    # self.graph1TxtMousePos = pyqtgraph.TextItem(text = '0', color=(200, 200, 200), html=None, anchor=(-17, 11), border=None, fill=None, angle=0, rotateAxis=None)
    self.graph2TxtMousePos = pyqtgraph.LabelItem(justify = 'left')
    # self.vb_plot_img.addItem(self.graph1TxtMousePos, ignoreBounds = True)
    self.graphicsView_img.addItem(self.graph2TxtMousePos) #, ignoreBounds = True)
    
    ## Contrast/color control
    
    self.hist_1 = pyqtgraph.HistogramLUTItem()
    self.hist_1.setImageItem(self.img_item_pg)
    self.graphicsView_img.addItem(self.hist_1,row=0, col=1)
    
    self.hist_2 = pyqtgraph.HistogramLUTItem()
    self.hist_2.setImageItem(self.img_item_pg_2)
    self.graphicsView_img.addItem(self.hist_2,row=0, col=3)

    # self.vb_plot_img.setRange(QtCore.QRectF(0, 0, 512, 512))
    # self.vb_plot_img_2.setRange(QtCore.QRectF(0, 0, 512, 512))
    
    # # # Generate image data !!!!!!!!!!!!!!!!
    # # data = numpy.random.normal(size=(200, 100))
    # # data[20:80, 20:80] += 2.
    # # data = pyqtgraph.gaussianFilter(data, (3, 3))
    # # data += numpy.random.normal(size=(200, 100)) * 0.1
    # # self.img_item_pg.setImage(data)
    # # self.hist_1.setLevels(data.min(), data.max())
    
    isocurve = 0
    if isocurve:
        ## Isocurve drawing
        self.iso_pg = pyqtgraph.IsocurveItem(level=0, pen='g')
        self.iso_pg.setParentItem(self.img_item_pg)
        self.iso_pg.setZValue(10) #2**16)
        
        # Draggable line for setting isocurve level
        self.isoLine_pg = pyqtgraph.InfiniteLine(angle=0, movable=True, pen='g')
        self.hist_1.vb.addItem(self.isoLine_pg)
        self.hist_1.vb.setMouseEnabled(y=False) # makes user interaction a little easier
        self.isoLine_pg.setValue(0.8)
        self.isoLine_pg.setZValue(2**16) # bring iso line above contrast controls
        
        self.isoLine_pg.sigDragged.connect(self.updateIsocurve_meth)
    
    else:
        self.isoLine_pg = None
    
    ## Set a custom color map (fire ...)
    
    self.lut_grey = numpy.array(((0.0, 0.0, 0.0), (37.00000159442425, 37.00000159442425, 37.00000159442425), (82.00000271201134, 82.00000271201134, 82.00000271201134),(115.00000074505806, 115.00000074505806, 115.00000074505806), (150.0000062584877, 150.0000062584877, 150.0000062584877), (189.00000393390656, 189.00000393390656, 189.00000393390656), (217.0000022649765, 217.0000022649765, 217.0000022649765), (240.00000089406967, 240.00000089406967,240.00000089406967), (255.0, 255.0, 255.0)), dtype=numpy.ubyte)

    self.cmap_grey_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 9), color=self.lut_grey, mode= 'rgb')    
    
   #  # self.lut_grey = numpy.array(((0.0, 0.0, 0.0),  (255.0, 255.0, 255.0)), dtype=numpy.ubyte)

  ##   ##   self.cmap_grey_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 2), color=self.lut_grey, mode= 'rgb')
    
    self.lut_fire = numpy.array(((0.0, 0.0, 0.0), (65.840716885526078, 0.075555555555555556, 103.71784398432904), (93.112834775878227, 0.60444444444444445, 189.5019304967355), (114.03946685248927,2.0400000000000005, 242.51941165526415), (131.68143377105216, 4.8355555555555556, 253.60308331890971), (147.22431864335456, 9.4444444444444429, 220.83647796503186), (161.27616066858735, 16.320000000000004, 149.88523933458069), (174.19816302131315, 25.915555555555557, 53.017481158528625), (186.22566955175645, 38.684444444444445, 0.0), (197.52215065657828, 55.079999999999991, 0.0), (208.20662813657015, 75.555555555555543, 0.0), (218.36895383730717, 100.56444444444442, 0.0), (228.07893370497854, 130.56000000000003, 0.0), (237.39208074407199, 165.9955555555556, 0.0), (246.35340468522045, 207.32444444444445, 0.0), (255.0, 255.0, 0.0)), dtype=numpy.ubyte)
    self.cmap_fire_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 16), color=self.lut_fire, mode= 'rgb')  
       
    self.lut_cubehelix = numpy.array((
        (0.00000, 0.00000, 0.00000),
        (2.04510, 0.34680, 1.68810),
        (4.02390, 0.71145, 3.45015),
        (5.93385, 1.10160, 5.28360),
        (7.76730, 1.51470, 7.18335),
        (9.52935, 1.95585, 9.14685),
        (11.20980, 2.42505, 11.16645),
        (12.80865, 2.92485, 13.23960),
        (14.32590, 3.46035, 15.36120),
        (15.75645, 4.02900, 17.52615),
        (17.10030, 4.63590, 19.73190),
        (18.35490, 5.27850, 21.97080),
        (19.52025, 5.96445, 24.23775),
        (20.59635, 6.68865, 26.53020),
        (21.57810, 7.45875, 28.84305),
        (22.47060, 8.26965, 31.16865),
        (23.26875, 9.12900, 33.50445),
        (23.97510, 10.03170, 35.84280),
        (24.59220, 10.98030, 38.18115),
        (25.11750, 11.97735, 40.51185),
        (25.55100, 13.02030, 42.83235),
        (25.89780, 14.11425, 45.13755),
        (26.15535, 15.25410, 47.41980),
        (26.32620, 16.44240, 49.67655),
        (26.41545, 17.67915, 51.90270),
        (26.42055, 18.96180, 54.09060),
        (26.34660, 20.29545, 56.24025),
        (26.19615, 21.67500, 58.34655),
        (25.96920, 23.10045, 60.40185),
        (25.67085, 24.57180, 62.40360),
        (25.30620, 26.08905, 64.34670),
        (24.87525, 27.65220, 66.22860),
        (24.38055, 29.25615, 68.04675),
        (23.82975, 30.90090, 69.79350),
        (23.22540, 32.58900, 71.46885),
        (22.57005, 34.31535, 73.07025),
        (21.86880, 36.07995, 74.59005),
        (21.12420, 37.88025, 76.02825),
        (20.34390, 39.71370, 77.38485),
        (19.53045, 41.58030, 78.65220),
        (18.68895, 43.47750, 79.83030),
        (17.82195, 45.40530, 80.91660),
        (16.93710, 47.35860, 81.91110),
        (16.03695, 49.33485, 82.81125),
        (15.12915, 51.33660, 83.61450),
        (14.21625, 53.35620, 84.32085),
        (13.30335, 55.39365, 84.93030),
        (12.39555, 57.44640, 85.44030),
        (11.50050, 59.51190, 85.85085),
        (10.61820, 61.58760, 86.16450),
        (9.75630, 63.67095, 86.37615),
        (8.92245, 65.75940, 86.49090),
        (8.11665, 67.85040, 86.50620),
        (7.34655, 69.94140, 86.42460),
        (6.61470, 72.03240, 86.24865),
        (5.92875, 74.11575, 85.97580),
        (5.29380, 76.19145, 85.60860),
        (4.70985, 78.25695, 85.15215),
        (4.18455, 80.31225, 84.60390),
        (3.72300, 82.34970, 83.96895),
        (3.32775, 84.36930, 83.24985),
        (3.00135, 86.36595, 82.44660),
        (2.75145, 88.34220, 81.56430),
        (2.58060, 90.29295, 80.60550),
        (2.49135, 92.21565, 79.57275),
        (2.48625, 94.10520, 78.46860),
        (2.57040, 95.96415, 77.30070),
        (2.74890, 97.78995, 76.06650),
        (3.01920, 99.57495, 74.77620),
        (3.38895, 101.32425, 73.42980),
        (3.85815, 103.03020, 72.03240),
        (4.43190, 104.69280, 70.58910),
        (5.10765, 106.30950, 69.10500),
        (5.89050, 107.88030, 67.58265),
        (6.78300, 109.40265, 66.02715),
        (7.78260, 110.87655, 64.44360),
        (8.89440, 112.29690, 62.83710),
        (10.11840, 113.66370, 61.21275),
        (11.45205, 114.97695, 59.57310),
        (12.90300, 116.23410, 57.92835),
        (14.46360, 117.43260, 56.27850),
        (16.13895, 118.57755, 54.63120),
        (17.92650, 119.66130, 52.99155),
        (19.82880, 120.68640, 51.36465),
        (21.84075, 121.65285, 49.75305),
        (23.96490, 122.55810, 48.16695),
        (26.19870, 123.40470, 46.60635),
        (28.54215, 124.18755, 45.07890),
        (30.99015, 124.91175, 43.58970),
        (33.54525, 125.57475, 42.14385),
        (36.20235, 126.17400, 40.74390),
        (38.96145, 126.71715, 39.39750),
        (41.81745, 127.19655, 38.10720),
        (44.76780, 127.61985, 36.88065),
        (47.81250, 127.98195, 35.72040),
        (50.94645, 128.28795, 34.62900),
        (54.16710, 128.53530, 33.61410),
        (57.46935, 128.72655, 32.67825),
        (60.85320, 128.86170, 31.82400),
        (64.30845, 128.94330, 31.05900),
        (67.83765, 128.97390, 30.38325),
        (71.43315, 128.95095, 29.80185),
        (75.09240, 128.87955, 29.31735),
        (78.80775, 128.76225, 28.93485),
        (82.57920, 128.59650, 28.65690),
        (86.39655, 128.38740, 28.48350),
        (90.25980, 128.13495, 28.42230),
        (94.16385, 127.84425, 28.46820),
        (98.10105, 127.51275, 28.63140),
        (102.06885, 127.14810, 28.90935),
        (106.05960, 126.74775, 29.30205),
        (110.07075, 126.31680, 29.81460),
        (114.09465, 125.85525, 30.44955),
        (118.12620, 125.37075, 31.20435),
        (122.16285, 124.85820, 32.07900),
        (126.19695, 124.32780, 33.07605),
        (130.22340, 123.77700, 34.19805),
        (134.23710, 123.21090, 35.44245),
        (138.23295, 122.62950, 36.80670),
        (142.20585, 122.04045, 38.29590),
        (146.15070, 121.44120, 39.90495),
        (150.06240, 120.83685, 41.63640),
        (153.93585, 120.22995, 43.48770),
        (157.76340, 119.62560, 45.45630),
        (161.54250, 119.02380, 47.53965),
        (165.27060, 118.42710, 49.74030),
        (168.93750, 117.84060, 52.05315),
        (172.54320, 117.26430, 54.47565),
        (176.08005, 116.70330, 57.00780),
        (179.54550, 116.15760, 59.64450),
        (182.93700, 115.63230, 62.38320),
        (186.24435, 115.12995, 65.22390),
        (189.47010, 114.65310, 68.15895),
        (192.60660, 114.20175, 71.18580),
        (195.65385, 113.78100, 74.30445),
        (198.60420, 113.39340, 77.50725),
        (201.45510, 113.04150, 80.79165),
        (204.20655, 112.72530, 84.15510),
        (206.85090, 112.44735, 87.58995),
        (209.39070, 112.21275, 91.09365),
        (211.82085, 112.02150, 94.66365),
        (214.13880, 111.87615, 98.29230),
        (216.34455, 111.77670, 101.97450),
        (218.43300, 111.72570, 105.70770),
        (220.40670, 111.72570, 109.48680),
        (222.26055, 111.77925, 113.30415),
        (223.99455, 111.88635, 117.15975),
        (225.60870, 112.04955, 121.04340),
        (227.10045, 112.26885, 124.95255),
        (228.47235, 112.54680, 128.87955),
        (229.72440, 112.88085, 132.82185),
        (230.85150, 113.27610, 136.77435),
        (231.86130, 113.73255, 140.72940),
        (232.74870, 114.24765, 144.68445),
        (233.51625, 114.82650, 148.63185),
        (234.16395, 115.46655, 152.56650),
        (234.69690, 116.17035, 156.48585),
        (235.11255, 116.93535, 160.38225),
        (235.41345, 117.76410, 164.25060),
        (235.60215, 118.65405, 168.08580),
        (235.68120, 119.60775, 171.88530),
        (235.65315, 120.62265, 175.64400),
        (235.51800, 121.69875, 179.35425),
        (235.28340, 122.83605, 183.01350),
        (234.94680, 124.03455, 186.61665),
        (234.51585, 125.29425, 190.16115),
        (233.99055, 126.61005, 193.63935),
        (233.37600, 127.98450, 197.05125),
        (232.67730, 129.41505, 200.38920),
        (231.89445, 130.90170, 203.65065),
        (231.03510, 132.44190, 206.83305),
        (230.10180, 134.03310, 209.93130),
        (229.09965, 135.67785, 212.94540),
        (228.03120, 137.37105, 215.86770),
        (226.90155, 139.11015, 218.70075),
        (225.71835, 140.89515, 221.43690),
        (224.48160, 142.72350, 224.07615),
        (223.20150, 144.59520, 226.61595),
        (221.87805, 146.50515, 229.05375),
        (220.51635, 148.45335, 231.38955),
        (219.12660, 150.43470, 233.61825),
        (217.70880, 152.45175, 235.74240),
        (216.26805, 154.49685, 237.76200),
        (214.81200, 156.57255, 239.66940),
        (213.34575, 158.67120, 241.47225),
        (211.87185, 160.79280, 243.16290),
        (210.39540, 162.93735, 244.74645),
        (208.92660, 165.09720, 246.22290),
        (207.46290, 167.27235, 247.58715),
        (206.01705, 169.46280, 248.84685),
        (204.58650, 171.66090, 249.99690),
        (203.18145, 173.86920, 251.04240),
        (201.80445, 176.08005, 251.98335),
        (200.46060, 178.29345, 252.82230),
        (199.15500, 180.50430, 253.55925),
        (197.89020, 182.71515, 254.19420),
        (196.67385, 184.91835, 254.73480),
        (195.50595, 187.11390, 255.00000),
        (194.39415, 189.29925, 255.00000),
        (193.34100, 191.47185, 255.00000),
        (192.34905, 193.62660, 255.00000),
        (191.42595, 195.76605, 255.00000),
        (190.56915, 197.88255, 255.00000),
        (189.78885, 199.97610, 255.00000),
        (189.08250, 202.04670, 255.00000),
        (188.45265, 204.08925, 255.00000),
        (187.90695, 206.10120, 255.00000),
        (187.44540, 208.08255, 255.00000),
        (187.06800, 210.03075, 254.69145),
        (186.77985, 211.94580, 254.25285),
        (186.58095, 213.82260, 253.76580),
        (186.47385, 215.66115, 253.23795),
        (186.46110, 217.45890, 252.66930),
        (186.54015, 219.21840, 252.06750),
        (186.71610, 220.93200, 251.43765),
        (186.98385, 222.60480, 250.78485),
        (187.35105, 224.22915, 250.11165),
        (187.81260, 225.81015, 249.42315),
        (188.36850, 227.34525, 248.72700),
        (189.02130, 228.83190, 248.02575),
        (189.76845, 230.27010, 247.32705),
        (190.60995, 231.65985, 246.63090),
        (191.54325, 233.00115, 245.94750),
        (192.57090, 234.29400, 245.27940),
        (193.68525, 235.53585, 244.63170),
        (194.88885, 236.72925, 244.00695),
        (196.17915, 237.87420, 243.41535),
        (197.55105, 238.97325, 242.85435),
        (199.00710, 240.02130, 242.33415),
        (200.53965, 241.02090, 241.85730),
        (202.14870, 241.97460, 241.42635),
        (203.82915, 242.88495, 241.04640),
        (205.57845, 243.74685, 240.72510),
        (207.39660, 244.56540, 240.45990),
        (209.27340, 245.34315, 240.26100),
        (211.20885, 246.07755, 240.12585),
        (213.20040, 246.77115, 240.06210),
        (215.24040, 247.42650, 240.06975),
        (217.32375, 248.04615, 240.15645),
        (219.45045, 248.63010, 240.31965),
        (221.61285, 249.18090, 240.56445),
        (223.80840, 249.70110, 240.89340),
        (226.02945, 250.19325, 241.30905),
        (228.27090, 250.65480, 241.81140),
        (230.53020, 251.09340, 242.40300),
        (232.80225, 251.51160, 243.08385),
        (235.07940, 251.90685, 243.85650),
        (237.35655, 252.28680, 244.72350),
        (239.63115, 252.64890, 245.68230),
        (241.89810, 253.00080, 246.73545),
        (244.14975, 253.34250, 247.88295),
        (246.37845, 253.67655, 249.12225),
        (248.58420, 254.00805, 250.45335),
        (250.76190, 254.33700, 251.87880),
        (252.90135, 254.66595, 253.39350),
        (255.00000, 255.00000, 255.00000)),
        dtype=numpy.ubyte
    )
    
    self.lut_ocean = numpy.array(( (0.0, 127.5, 0.0), (0.0, 102.0, 17.0), (0.0, 76.5, 34.0), (0.0, 50.999999999999986, 51.0),  (0.0, 25.499999999999993, 68.0),(0.0, 0.0, 85.0),  (0.0, 25.50000000000002, 102.0),  (0.0, 50.999999999999986, 119.0), (0.0, 76.50000000000001, 136.0),  (0.0, 101.99999999999997, 153.0), (0.0, 127.5, 170.0),  (50.99999999999993, 152.99999999999997, 187.0),  (102.00000000000009, 178.50000000000006, 204.0),  (153.00000000000003, 204.0, 221.0),  (203.99999999999994, 229.49999999999997, 238.0), (255.0, 255.0, 255.0)), dtype=numpy.ubyte)
    
    self.cmap_ocean_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 16), color=self.lut_ocean, mode= 'rgb')  # # used in GUI with self !
    
    self.cmap_cubehelix_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 16), color=self.lut_cubehelix[::16], mode='rgb')#pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 256), color=lut_cubehelix, mode='rgb')
    
    self.lut_kryptonite = param_ini.lut_kryptonite # # used in GUI with self !
    
    self.cmap_krypto_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 16), color=self.lut_kryptonite[::16], mode= 'rgb')  # # used in GUI with self !
    
    from matplotlib import cm
    colormap_PiYG = cm.get_cmap("PiYG") ; colormap_PiYG._init() # mandatory
    self.lut_PiYG = numpy.ubyte((colormap_PiYG._lut * 255).view(numpy.ndarray))
    self.cmap_PiYG_pg = pyqtgraph.ColorMap(pos=numpy.linspace(0.0, 1.0, 16), color=self.lut_PiYG[:-16:16], mode='rgb')
    # use with LUT (change only the map, and not the LUTitem)
    # n_lut = 4096  # for uint16  or float
    # self.lut_grey_pg = cmap_grey_pg.getLookupTable(0.0, 1.0, n_lut, alpha=False)
    # self.lut_cubehelix_pg = cmap_cubehelix_pg.getLookupTable(0.0, 1.0, n_lut, alpha=False)
    # self.lut_fire_pg = cmap_fire_pg.getLookupTable(0.0, 1.0, n_lut, alpha=False)
    
    self.clrmap_choice_combo.currentIndexChanged.connect(self.updateClrmap_meth) # # used in GUI with self !
    self.clrmap2_choice_combo.currentIndexChanged.connect(self.updateClrmap_meth)
    
    # # isoLine_pg = self.isoLine_pg # !!!
    # # iso_pg = self.iso_pg 
    # # global isoLine_pg, iso_pg
    # # 
    # # return isoLine_pg, iso_pg
    
    ## ROIs
    
    self.roi_left_pg=pyqtgraph.RectROI(pos=[20, 20], size=[20, 20], centered=False, sideScalers=True, pen=(0,9), removable=True) # pos, size , centered(bool) If True, scale handles affect the ROI relative to its center, rather than its origin. ; sideScalers : extra-handlers
    
    self.roi_right_pg=pyqtgraph.RectROI(pos=[20, 20], size=[20, 20], centered=False, sideScalers=True, pen=(0,9), removable=True) # pos, size , centered(bool) If True, scale handles affect the ROI relative to its center, rather than its origin. ; sideScalers : extra-handlers
    
    def remove_roi_left():
        self.vb_plot_img.removeItem(self.roi_left_pg)
        self.vb_plot_img.removeItem(self.graph2TxtROI)

    def remove_roi_right():
        self.vb_plot_img_2.removeItem(self.roi_right_pg)
        self.vb_plot_img_2.removeItem(self.graph2TxtROI)
    
    self.roi_left_pg.sigRemoveRequested.connect(remove_roi_left)
    self.roi_right_pg.sigRemoveRequested.connect(remove_roi_right)
    
    self.graph2TxtROI = pyqtgraph.TextItem() #justify = 'right')#'center')
    # self.vb_plot_img.addItem(self.graph1TxtMousePos, ignoreBounds = True)
    
    #'''
    # works but not used
    def update_roi(roi):
        # a=roi.getArrayRegion(arr, img_item_pg)
        a=roi.pos() # lower-left corner.
        b=roi.size()
        self.graph2TxtROI.setText(('(%.1f, %.1f) ; (%.1fX%.1f) PX' % (a[0], a[1], b[0], b[1]) ), color = 'c') # , size = '9pt', bold=True,

        # # print(a, b)
    self.roi_left_pg.sigRegionChanged.connect(update_roi)
    self.roi_right_pg.sigRegionChanged.connect(update_roi)
    #'''
    
    ##  with only layout (OLD)
    
    # self.graphicsView = pyqtgraph.GraphicsView()
    # self.plot_layout.addWidget(self.graphicsView, 1, 0, 8, 1 ) # x, y, xspan, yspan
    # self.graphicsView_2 = pyqtgraph.GraphicsView()
    # self.plot_layout.addWidget(self.graphicsView_2, 1, 1, 8, 1 )
    # self.vb_plot_img = pyqtgraph.ViewBox()
    # self.vb_plot_img_2 = pyqtgraph.ViewBox()
    # self.graphicsView.setCentralItem(self.vb_plot_img)
    # self.graphicsView_2.setCentralItem(self.vb_plot_img_2)
    #self.graphicsView.setCentralItem(self.vb_plot_img)
    
    # with LUT bar (slow)
    # self.gradient_lut_1 = pyqtgraph.GradientWidget()
    # sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
    # sizePolicy.setHorizontalStretch(0)
    # sizePolicy.setVerticalStretch(0)
    # sizePolicy.setHeightForWidth(self.gradient_lut_1.sizePolicy().hasHeightForWidth())
    # self.gradient_lut_1.setSizePolicy(sizePolicy)
    # self.gradient_lut_1.setObjectName("gradient_lut_1")
    # self.gradient_lut_2 = pyqtgraph.GradientWidget()
    # self.gradient_lut_2.setSizePolicy(sizePolicy)
    # self.gradient_lut_2.setObjectName("gradient_lut_1")
    # self.plot_layout.addWidget(self.gradient_lut_1, 0, 0, 1, 1 )
    # self.plot_layout.addWidget(self.gradient_lut_2, 0, 1, 1, 1 )
    # self.gradient_lut_1.sigGradientChanged.connect(self.updateLUT)
    # self.gradient_lut_2.sigGradientChanged.connect(self.updateLUT)
    
    
    # Contrast/color control
    
    # self.graphicsView_hist_1 = pyqtgraph.GraphicsView()
    # self.graphicsView_hist_2 = pyqtgraph.GraphicsView()
    # self.plot_layout_hist.addWidget(self.graphicsView_hist_1, 0, 0, 1, 1 ) # x, y, xspan, yspan
    # self.plot_layout_hist.addWidget(self.graphicsView_hist_2, 1, 0, 1, 1 ) # x, y, xspan, yspan
    # vb_plot_hist_1 = pyqtgraph.ViewBox()
    # vb_plot_hist_2 = pyqtgraph.ViewBox()
    
    ## if using matplotlib
        
        
    # self.fig_main = matplotlib.figure.Figure()
    # self.canvas_main = FigureCanvasQTAgg(self.fig_main)
    # #self.plot_layout.addWidget(self.canvas_main) # plot_layout is a vertical layout widget in QT designer
    # 
    # fig_hist = matplotlib.figure.Figure()
    # self.ax1f1 = fig_hist.add_subplot(211)
    # self.ax2f1 = fig_hist.add_subplot(212)
    # self.canvas_hist = FigureCanvasQTAgg(fig_hist)
    # # self.plot_layout_hist.addWidget(self.canvas_hist) # plot_layout is a vertical layout widget in QT designer
    # 
    # # if using pyqtgraph
    
def roi_add(vb_plot, roi_pg, vb_pg, graph2TxtROI, pyqtgraph):
    '''
    ROI handle
    '''
    
    children=vb_plot.getViewBox().allChildren()
    
    for child in children:
        if child.__class__ == pyqtgraph.graphicsItems.ROI.RectROI: # there's already an ROI
            # # print('ok')
            return
    
    [xx, yy] = vb_pg.viewRange() # [[xmin, xmax], [ymin, ymax]]
    # print(xx, yy)
    offX00 = xx[0]
    offY00 = yy[0]
    fact = 1
    sx = round(((xx[1]+offX00) - (xx[0]-offX00))/fact ) #round((xx[1]-xx[0])/2)
    sy = round(((yy[1]+offY00) - (yy[0]-offY00))/fact  ) #round((yy[1]-yy[0])/2)
    
    roi_pg.setPos(pos= (round(((xx[1]+offX00) - (xx[0]-offX00))/2 - sx/2), round(((yy[1]+offY00) - (yy[0]-offY00))/2 - sy/2)), update=True, finish=True)  # lower left corner         
    roi_pg.setSize(size= (sx, sy), update=True, finish=True)

    vb_plot.addItem(roi_pg) # normally on ViewBox
    vb_plot.addItem(graph2TxtROI) 

    
def roi_use(roi, vb_pg, graph2TxtROI):
    
    [xx, yy] = vb_pg.viewRange() # [[xmin, xmax], [ymin, ymax]]
    a=roi.pos() # lower-left corner.
    b=roi.size()
    
    offX00 = xx[0]
    offY00 = yy[0]
    px_X= round(((xx[1]+offX00) - (xx[0]-offX00))) # size of the FULL window
    px_Y= round(((yy[1]+offY00) - (yy[0]-offY00)))
    # # print(round(a[0]+b[0]/2), round(((xx[1]+offX00) - (xx[0]-offX00))/2))
    offX = a[0] # #round(a[0]+b[0]/2) - round(((xx[1]+offX00) - (xx[0]-offX00))/2) # # sizeXroi + posROI00 - center of image
    offY = a[1] # # round(a[1]+b[1]/2) - round(((yy[1]+offY00) - (yy[0]-offY00))/2)
    numPXx = round(b[0]) #round(xx[1]-xx[0])
    numPXy = round(b[1]) #round(yy[1]-yy[0])
    
    vb_pg.removeItem(roi)
    vb_pg.removeItem(graph2TxtROI) 
    
    return offX, offY, numPXx, numPXy, px_X, px_Y
    
def display_save_img_gui_util(self, datetime, numpy, shutil, glob, QtWidgets, PIL, os, param_ini, jobs_scripts, img_hist_plot_mp, paquet_received, sat_value_list, array_ishg_4d, array_ctr_3d, arrlist, add_new_img):
    # # called by display_img_gui
    
    self.up_offset_pg = True # the ROi of pg will considered the img as updated
    
    # # date = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d')
    
    date_long = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d_%Hh%M.%S.%f')[:-3] # milliseconds are taken only to 3rd decimal
    self.date_long = date_long
    
    #obj_choice = str(self.objective_choice.currentText())
    obj_choice = 'obj%dX' % self.magn_obj_bx.value() # obj_choice[0:3]
    if self.scan_mode_str == 'static acq.': # size does not exist in static
        str_sz = '%dX%dpx' % (self.nbPX_X_ind.value(), self.nbPX_Y_ind.value()) if self.nbPX_X_ind.value()!=self.nbPX_Y_ind.value() else '%dpx^2' % self.nbPX_X_ind.value()
        size_prop = '%s_%.5gus' % (str_sz, self.dwll_time_edt.value())
    else:
        str_sz = '%.5gX%.5gum' % (self.sizeX_um_spbx.value(), self.sizeY_um_spbx.value()) if self.sizeX_um_spbx.value()!=self.sizeY_um_spbx.value() else '%.5gum^2' % self.sizeX_um_spbx.value()
        str_stp = '%.5gX%.5gum' % (self.stepX_um_edt.value(), self.stepY_um_edt.value()) if self.stepX_um_edt.value()!=self.stepY_um_edt.value() else '%.5gum^2' % self.stepX_um_edt.value()
        size_prop = '%s_%s' % (str_sz, str_stp)
    
    self.posZ_piezo = (self.posZ_piezo_edt_1.value() + self.posZ_piezo_edt_2.value()/10 + self.posZ_piezo_edt_3.value()/100 + self.posZ_piezo_edt_4.value()/1000 + self.posZ_piezo_edt_5.value()/10000)/1000 # in mm
    self.posZ_motor = self.posZ_motor_edt_1.value() + self.posZ_motor_edt_2.value()/10 + self.posZ_motor_edt_3.value()/100  + self.posZ_motor_edt_4.value()/1000 # in mm
    
    if self.posX_edt.isEnabled():
        posX = '%.3f' % self.posX_edt.value()
    else: # not enabled
        posX = 'N/A'
    if self.posY_edt.isEnabled():
        posY = '%.3f' % self.posY_edt.value()
    else: # not enabled
        posY = 'N/A'
    
    pos_trans = float(self.jobs_window.pos_motor_trans_edt.text()) # um
    pos_gp = float(self.jobs_window.pos_motor_phshft_edt.text()) # um
    pos_rot_tl = self.jobs_window.angle_polar_bx.value() # °
    pos_rot_newport = self.jobs_window.newport_polar_bx.value() # °
    pos_trans_str = '%.3f' % pos_trans if self.jobs_window.pos_motor_trans_edt.isEnabled() else 'N/A'
    if not self.jobs_window.pos_motor_phshft_edt.isEnabled(): pos_gp_str = 'N/A'
    else: pos_gp_str = '%.3f' % pos_gp
    if not self.jobs_window.angle_polar_bx.isEnabled(): pos_rot_tl_str = 'N/A'
    else: pos_rot_tl_str = '%.3f' % pos_rot_tl
    if not self.jobs_window.newport_polar_bx.isEnabled(): pos_rot_newport_str = 'N/A'
    else: pos_rot_newport_str = '%.3f' % pos_rot_newport
        
    if (self.spectro_connected and self.wlth_spectro_edt.text() != 'N/A'):  #time.sleep(0.1)
        wlth_str = '%.1f nm' % float(self.wlth_spectro_edt.text())
        fwhm_str = '%.1f nm' % float(self.fwhm_spectro_edt.text()) 
    else:
        wlth_str = self.wlth_spectro_edt.text()
        fwhm_str = self.fwhm_spectro_edt.text()
    
    acq_name = self.acq_name_edt.text() 
    if acq_name == param_ini.name_dflt00: acq_name = acqstr =''
    else: acqstr='\nname %s' % acq_name 
    
    card_lst = ['%.2fMHz' % (self.read_sample_rate_spnbx.value()/1e6), self.dev_to_use_AI_box.currentText(), 'ext_clk' if self.ext_smp_clk_chck.isChecked() else 'onbrd_clk']

    direcstr = 'unidirek' if self.unidirectional_current else 'bidirek'
    buffOFFstr = 'buffPX_offsetdir/rev %.1f/%.1f' % (self.read_buffer_offset_direct_current,  self.read_buffer_offset_reverse_current )
    yfstr = 'yfast' if self.y_fast_current else 'Xfast'
    uptmstr = 'upTime%.2fs' % self.update_time_current if self.stage_scan_mode != 1 else '' # no stg scn
    
    spec_str = ''
    scan_params_str= [self.scan_mode_str, direcstr, yfstr, buffOFFstr, uptmstr]; 
    if self.stage_scan_mode == 1: # stage scan
        scan_params_str.append('acc_offsetdir/rev %.2f/%.2f' % (self.dist_offset_current, self.dist_offset_rev_current))
        scan_params_str.append('vel_X/Y %.1f/%.1f' % (self.max_vel_x_current, self.max_vel_y_current))
        scan_params_str.append('accn_X/Y %.1f/%.1f' % (self.max_accn_x_current, self.max_accn_y_current))
        scan_params_str.append('profile/jerk %d/%d' % (self.profile_mode_stgXY_current, self.jerk_stgXY_current))
        scan_params_str.append('blocksteps %d&%d' % (self.stage_scn_block_moves_current, self.stagescn_wait_fast_current))
        spec_str1 = 'UND' if self.unidirectional_current else 'BID'
        spec_str2 = 'FAST' if self.profile_mode_stgXY_current == 1 else 'SAF'
        spec_str = spec_str1+spec_str2
    elif (self.stage_scan_mode == 0 or self.stage_scan_mode == 3): # galvo (any)  
        card_lst.append('pausetrig%d' % self.pause_trig_diggalvo_current)
        card_lst.append('methodtrig%d' % self.method_watch)
        card_lst.append('corr_sync %.1f' % (self.corr_sync_inPx_current))
        if self.stage_scan_mode == 3: # galvo anlg new
            scan_params_str.append('mulTrigFact %.2f' % (self.mult_trig_fact_anlg_galv_current))
            scan_params_str.append('eff_wvfrm %.1f' % (self.eff_wvfrm_an_galvos_current))
            scan_params_str.append('trigPercHyst %d' % (self.trig_perc_hyst_current))
            scan_params_str.append('offGalv %.1f/%.1f' % (self.off_fast_anlgGalvo_current, self.off_slow_anlgGalvo_current))

    scan_params_str0 = str(scan_params_str)
    card_str = str(card_lst)
    
    str_ishg = self.jobs_window.stmode_EOMph_cbBx.currentText() if self.jobs_window.stmode_EOMph_cbBx.currentIndex() > 0 else 'N/A'
    if self.ishg_EOM_AC[0]: str_ishg += str(self.ishg_EOM_AC)
    if self.jobs_window.stmode_EOMph_cbBx.currentIndex() == (self.jobs_window.stmode_EOMph_cbBx.count()-1): str_ishg += str(self.jobs_window.valHV_EOMph_spbx.value())
    
    ImageDescription_base = ( acqstr+'\nobj_exc %s %dX \nNA = %.3g \nZ_coarse = %.3f mm \nZ_piezo = %.3f um \nX = %s mm, Y = %s mm \nexp_time = %.3f us \nsize_x = %.3f um \nsize_y = %.3f um \nstepX = %.3f um \nstepY = %.3f um \noffX = %.2f um \noffY = %.2f um \nfilter_top_pos = %s \nfilter_bottom_pos = %s \npos motor trans = %sum \npos motor gp ps = %sum \npos motor polar = %sdeg \npos motor newport = %sdeg \ntime=%s \nwavelength spectro = %s \nFWHM spectro = %s \nCard = %s \nScan_params = %s \nishgParams = %s  \nname_set_up=%s \nmodel_camera=%s \ncopyright=%s \nsoftware=%s \nauthor=%s ' % (self.objective_name, self.magn_obj_bx.value(), self.eff_na_bx.value(), self.posZ_motor, self.posZ_piezo*1000, posX, posY, self.exp_time, self.sizeX_um_spbx.value(), self.sizeY_um_spbx.value(), self.stepX_um_edt.value(), self.stepY_um_edt.value(), self.center_x*1000, self.center_y*1000, self.posFilt_top, self.posFilt_bottom, pos_trans_str, pos_gp_str, pos_rot_tl_str, pos_rot_newport_str, date_long, wlth_str, fwhm_str, card_str, scan_params_str0, str_ishg, param_ini.name_camera, param_ini.model_camera, param_ini.copyright, param_ini.software, param_ini.author))  
        
    if self.count_avg_job is None: self.num_experiment+=1 # one experiment in addition each time it goes until here # not a job
    ct = 0; newdirpath = None
    for num_pmt in range(0, len(self.pmt_channel_list_current)):
        if self.pmt_channel_list_current[num_pmt] == 1:
            
            # # list_pmt = self.pmt_channel_list_current
        # paquet_received is a 3d array
            # # print('wlh', paquet_received.shape, num_pmt)

            if numpy.amin(paquet_received[ct,:,:])<0: # !!!
                # # paquet_received[ct,:,:] = paquet_received[ct,:,:] - numpy.amin(paquet_received[ct,:,:])
                wh = numpy.where(paquet_received[ct,:,:]<0)
                paquet_received[ct, wh[0], wh[1]] = 0
                                
            # # print(paquet_received[num_pmt,10:20,10:20])

            if num_pmt == 0:
                BWPMT_indic = self.BWPMT_indic_1.text()
                preAmpPMT_indic = self.preAmpPMT_indic_1.text()
                gainPMT = self.gainPMT_indic_1.text()
                bound_AI = self.bound_AI_1
                pmt_physMin = self.pmt1_physMin_spnbx.value()
                pmt_physMax = self.pmt1_physMax_spnbx.value()
                pre_amp_model_PMT = param_ini.pre_amp_model_PMT_1
            elif num_pmt == 1:
                BWPMT_indic = self.BWPMT_indic_2.text()
                preAmpPMT_indic = self.preAmpPMT_indic_2.text()
                gainPMT = self.gainPMT_indic_2.text()
                bound_AI = self.bound_AI_2
                pmt_physMin = self.pmt2_physMin_spnbx.value()
                pmt_physMax = self.pmt2_physMax_spnbx.value()
                pre_amp_model_PMT = param_ini.pre_amp_model_PMT_2
            elif num_pmt == 2:
                BWPMT_indic = self.BWPMT_indic_3.text()
                preAmpPMT_indic = self.preAmpPMT_indic_3.text()
                gainPMT = self.gainPMT_indic_3.text()
                bound_AI = self.bound_AI_3
                pmt_physMin = self.pmt3_physMin_spnbx.value()
                pmt_physMax = self.pmt3_physMax_spnbx.value()
                pre_amp_model_PMT = param_ini.pre_amp_model_PMT_3
            elif num_pmt == 3:
                BWPMT_indic = self.BWPMT_indic_4.text()
                preAmpPMT_indic = self.preAmpPMT_indic_4.text()
                gainPMT = self.gainPMT_indic_4.text()
                bound_AI = self.bound_AI_4
                pmt_physMin = self.pmt4_physMin_spnbx.value()
                pmt_physMax = self.pmt4_physMax_spnbx.value()
                pre_amp_model_PMT = param_ini.pre_amp_model_PMT_4
                
            if pre_amp_model_PMT == 'C7319':
                if BWPMT_indic == 'H':
                    if preAmpPMT_indic == '10^7': # highest gain, BW limited
                        BWPMT = 100 # kHz
                    else:
                        BWPMT = 200 # kHz
                else: # low BW
                    BWPMT = 20 # kHz
            
            mW_val_str = self.pwr_mW_edt.text()
            if not mW_val_str.replace('.','',1).isdigit(): # # not a float
                mW_val_str = ''
            
# #                 if param_ini.avg_px == 2:# 1 for averaging (range expanded in uint16) 
# # # 2 for averaging (range in phys. limit int16) 
# # # 0 for sum (int32)
# #                     max_val_dig_img = (min(bound_AI, pmt_physMax) - max(-bound_AI, pmt_physMin))/(2*bound_AI)*self.max_value_pixel # bound AI is always symmetrical for a DAQ card
# #                 else:
            
            if not add_new_img[0]: 
                rowPosition = curr_row_img= add_new_img[1]
            else: rowPosition = self.name_img_table.rowCount()

            # # print('sat_value_list', sat_value_list)
            if type(sat_value_list[num_pmt]) in (int, float): 
                max_val_dig_img = round(sat_value_list[num_pmt]) #*self.read_sample_rate_spnbx.value()*self.exp_time*1e-6 )
            elif self.name_img_table.item(rowPosition, param_ini.posSat_wrt0_tablemain) is not None:
                max_val_dig_img =  int(self.name_img_table.item(rowPosition, param_ini.posSat_wrt0_tablemain).text()) if rowPosition > 0 else 1
            else: max_val_dig_img =1
            
            count_to_mvolt = 1000*(2*bound_AI)/max_val_dig_img # in mV
            
            ImageDescription = ('PMT # %s \ngain PMT=%s \n[BW%dkHz, PreAmp%s(V/A), physimposed(%.3f, %.1f)V] \n1 count <-> mV = %.3f mV\nmax count digital = %d \nmW IN = %s; %s' % (num_pmt+1, gainPMT, BWPMT, preAmpPMT_indic, pmt_physMin, pmt_physMax, count_to_mvolt, max_val_dig_img, mW_val_str, ImageDescription_base))
            dict_tiff_really_disp = { 270: ImageDescription} #,  271: name_camera, 272: model_camera,  33432: copyright, 305: software, 315: author} # useful to fill some tag of tiff, but makes ImageMagick bug
            
            base_fname = '%s_%s_%s_%smW_%sVPM%d' % (acq_name, obj_choice, size_prop, mW_val_str, gainPMT, num_pmt+1) # always keep PMT at the end of the name !!
            fname = '%s_%s' % (date_long, base_fname) # for saving in temp
            # # fname_disp = '%s_%s' % (date, base_fname) # saving, disp
            fullname = '%s/tmp/%s' % (self.path_save, fname)
            
            if add_new_img[0]:
                self.name_img_table.insertRow(rowPosition)
    
                self.name_img_table.setItem(rowPosition , 1, QtWidgets.QTableWidgetItem(str(num_pmt+1)))
                self.name_img_table.setItem(rowPosition , 2, QtWidgets.QTableWidgetItem(fname))
                self.name_img_table.setItem(rowPosition , 0, QtWidgets.QTableWidgetItem(('%s' % self.num_experiment)))  # set experiment number
                self.name_img_table.setItem(rowPosition , 3, QtWidgets.QTableWidgetItem( str(['%.1fus' % self.exp_time, self.stage_scan_mode]+scan_params_str)))  # set scan params
                self.name_img_table.setItem(rowPosition , 4, QtWidgets.QTableWidgetItem(('%s' % size_prop)))  # set size
                self.name_img_table.setItem(rowPosition , 5, QtWidgets.QTableWidgetItem(('%.3f' % self.posX)))  # set X
                self.name_img_table.setItem(rowPosition , 6, QtWidgets.QTableWidgetItem(('%.3f' % self.posY)))  # set Y
                self.name_img_table.setItem(rowPosition , 7, QtWidgets.QTableWidgetItem(('%.3f' % self.posZ_motor)))  # set Z motor
                self.name_img_table.setItem(rowPosition , 8, QtWidgets.QTableWidgetItem(('%.3f' % (self.posZ_piezo*1000))))  # set Z piezo
                self.name_img_table.setItem(rowPosition , param_ini.posoffXY_wrt0_tablemain, QtWidgets.QTableWidgetItem(('%.3f; %.3f' % (self.center_x*1000, self.center_y*1000)))) # offset
                self.name_img_table.setItem(rowPosition , param_ini.pos_reducnblinesdisp_wrt0_tablemain, QtWidgets.QTableWidgetItem('1'))  # for disp, array is kept only at a certain fraction of his line number (tot%nb_lines), for memory save
                self.name_img_table.setItem(rowPosition , param_ini.postransmtr_wrt0_tablemain, QtWidgets.QTableWidgetItem(pos_trans_str))  # pos motor ps gp in um
                self.name_img_table.setItem(rowPosition , param_ini.posgpmtr_wrt0_tablemain, QtWidgets.QTableWidgetItem(pos_gp_str))  # pos motor ps gp in um
                self.name_img_table.setItem(rowPosition , param_ini.posTLpolarmtr_wrt0_tablemain, QtWidgets.QTableWidgetItem(pos_rot_tl_str))  # pos motor in °
                self.name_img_table.setItem(rowPosition , param_ini.posNPpolarmtr_wrt0_tablemain, QtWidgets.QTableWidgetItem(pos_rot_newport_str))  # pos motor in °
                self.name_img_table.setItem(rowPosition , param_ini.posCard_wrt0_tablemain, QtWidgets.QTableWidgetItem(card_str)) 
                self.name_img_table.setItem(rowPosition , param_ini.posishgfast_wrt0_tablemain, QtWidgets.QTableWidgetItem( str_ishg ))
                self.name_img_table.setItem(rowPosition , param_ini.posSat_wrt0_tablemain, QtWidgets.QTableWidgetItem( '%d' % max_val_dig_img))
                self.sat_val_spbx.setValue(max_val_dig_img)
                            
                if len(self.list_arrays) > 0:
                    arr_to_shrink = self.list_arrays[len(self.list_arrays)-1] # last el.
                    stepBinningX = int(numpy.ceil(arr_to_shrink.shape[1]/self.size_max_px_for_display))
                    stepBinningY = int(numpy.ceil(arr_to_shrink.shape[0]/self.size_max_px_for_display))
                    stepBinning = int(round((stepBinningX+stepBinningY)/2)*3/2)
                    if stepBinning >= 2:
                        arr_to_shrink = numpy.delete(numpy.delete(arr_to_shrink, numpy.s_[::stepBinning], 1), numpy.s_[::stepBinning], 0) #; print(arr.shape)
                        self.name_img_table.setItem(rowPosition-1 , param_ini.pos_reducnblinesdisp_wrt0_tablemain, QtWidgets.QTableWidgetItem(str(stepBinning)))  # for disp, array is kept only at a certain fraction of his line number (tot%nb_lines), for memory save
                    self.list_arrays[len(self.list_arrays)-1] = arr_to_shrink # # arr_to_shrink[::stepBinning, ::stepBinning].astype(param_ini.bits_save_img)
            
                    # # only few pixels are conserved (up to a max total size) to allow to display fast and to avoid MemoryErrors (happens for >5000 imgs 400x400 uint16 otherwise)
                self.list_arrays.append(paquet_received[ct, :, :].astype(param_ini.bits_save_img)) 
                standard_save = True # dflt
                if self.ishg_EOM_AC[0]: # EOM ph fast
                    if (array_ishg_4d is not None or arrlist is not None):
                        standard_save = False
                        newdirpath = jobs_scripts.EOMph_pltsave_meth(PIL, numpy, os, paquet_received[ct,:,:], array_ishg_4d, array_ctr_3d, arrlist, dict_tiff_really_disp, fname, self.path_save, ct, self.read_sample_rate_spnbx.value()*1e-6, sum(self.pmt_channel_list_current), [img_hist_plot_mp, self.img_item_pg_2, self.hist_2, self.lut_PiYG], acq_name, self.ishg_EOM_AC, ImageDescription, spec_str, size_prop, newdirpath, ct)
                        nb_cmap = param_ini.nb_cmap_ishg
                        clrmap_choice_combo= self.clrmap2_choice_combo
                    else: print('did not receive paquet for ishg fast with data : will save only sumSHG!\n') # not normal
                if standard_save: # # standard
                    if (self.jobs_window.treatmatlab_chck.isChecked() and self.count_avg_job is not None and (not self.jobs_window.ps_fast_radio.isChecked() or self.ishg_EOM_AC[0])): # job, treatmatlab so need to put job in one folder
                        newdirpath='%s/tmp/%s_%s' % (self.path_save, fname[:21], self.acq_name_edt.text()) # just the date fname
                        if (self.path_tmp_job is None or len(self.path_tmp_job)<3):  # first frame
                            self.path_tmp_job = newdirpath
                            if ((self.count_job_ps ==1 or self.count_job_polar==1) and (self.count_job_ps+ self.count_job_polar)<=2): 
                                os.makedirs(self.path_tmp_job)  #  # or self.count_job_Z_stack==1
                                # really be sure
                        
                        fullname = '%s/%s' % (self.path_tmp_job, fname); newdirpath = self.path_tmp_job
                        # print('aaafaf', self.path_tmp_job)
                    save_PIL (PIL, param_ini, paquet_received[ct,:,:], fullname , dict_tiff_really_disp) 
                    nb_cmap = self.cmap_curr[num_pmt]
                    clrmap_choice_combo = self.clrmap2_choice_combo if num_pmt%2 else self.clrmap_choice_combo
                
                if len(self.list_arrays) > param_ini.list_arrays_max_length:
                    self.name_img_table.removeRow(0) # oldest element
                    del self.list_arrays[0]
                    files = glob.glob(('%s/tmp/*' % self.path_save))
                    shutil.copy2(files[0], self.path_recycle)
                    print('list arrays` length is over %d elmts : I erased the oldest one (reboot the GUI to set the counter to 0, if possible)' % param_ini.list_arrays_max_length) 
                    
                if clrmap_choice_combo.currentIndex() != nb_cmap:
                    clrmap_choice_combo.blockSignals(True)
                    clrmap_choice_combo.setCurrentIndex(nb_cmap)
                    clrmap_choice_combo.blockSignals(False)
                    
                if num_pmt % 2: # num_pmt odd
                    img_item_pg = self.img_item_pg_2
                    hist = self.hist_2
                    LUT = self.LUT_2
                
                else: # even 
                    img_item_pg = self.img_item_pg
                    hist = self.hist_1
                    LUT = self.LUT
                    
                img_hist_plot_mp.plot_img_hist(numpy, LUT, paquet_received[ct,:,:], img_item_pg, hist, self.isoLine_pg) 
                    
                self.updateClrmap_meth(-1) # -1 to tell its not a slot call
                
                if (self.jobs_window.treatmatlab_chck.isChecked() and self.ishg_EOM_AC[0] in (1,11)): # send to matlab ISHG
                    
                    incr_ordr = 1; nb_slice_per_step =5; ctr_mult=8; # fast ISHG
                    self.worker_matlab.matlabGUI_treatphase_signal.emit(incr_ordr, nb_slice_per_step, ctr_mult, newdirpath)
                
                ct += 1
                
            else: # just save
                save_PIL (PIL, param_ini, paquet_received[ct,:,:], add_new_img[2] , dict_tiff_really_disp) 

    #self.name_img_table.setItem(rowPosition , 1, QtWidgets.QTableWidgetItem("text2"))
    #self.name_img_table.setItem(rowPosition , 2, QtWidgets.QTableWidgetItem("text3"))
    
    self.nb_bins_hist = self.nb_bins_hist_box.value()
  
def save_PIL (PIL, param_ini, data, fullname , dict_tiff_really_disp): 
    # # result = PIL.Image.fromarray(self.list_arrays[len(self.list_arrays)-1])
    # # print('sdaf', data.shape, data.flags, param_ini.bits_save_img)
    result = PIL.Image.fromarray(data.astype(param_ini.bits_save_img))
    result.save(('%s.tif' % fullname), tiffinfo= dict_tiff_really_disp)
    # # print('sadafa', ('%s.tif' % fullname))