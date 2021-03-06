from PyQt4 import QtCore

from collections import namedtuple
import multiprocessing as mp
from multiprocessing.sharedctypes import SynchronizedArray
import ctypes
import time
import numpy as np
from dump import mydump
from pciedevsettings import PCIEResponse

Curve = namedtuple("Curve", "x y")

class Collector(QtCore.QObject):
    reflectogrammChanged = QtCore.pyqtSignal(np.ndarray)
    temperatureCurveChanged = QtCore.pyqtSignal(Curve)
    temperatureCurve2Changed = QtCore.pyqtSignal(Curve)
    spectraChanged = QtCore.pyqtSignal(Curve)
    spectraOnChipChanged = QtCore.pyqtSignal(tuple)
    sharedArrayChanged = QtCore.pyqtSignal(tuple)
    def __init__(self, reflen, speclen, parent=None):
        QtCore.QObject.__init__(self, parent)
        # always waits for reflectogramm, appending temp. measurements
        # only if needed
        self.waitingForTemperature = False
        self.firstScan = True
        self.temperatureIndex = 0           # for outer stabilization 
        self.reflectogrammLength = reflen
        self.spectraLength = speclen
        self.recreatecontainer()
        self.starttime = time.time()
        self.time = np.zeros(30000)
        self.temperature = np.zeros(30000)
        self.temperature2 = np.zeros(30000)
        self.nextIndex = (0, 0, 0, 0)
        self.collected = set([])
        self.inversion = -1
        
    def appendDragonResponse(self, response):
        response.data[:response.framelength] -= np.average(response.data[response.framelength-1000:response.framelength])
        #response.data[:4] = 0
        direction, scanNumber, polarisation, freqindex = self.nextIndex
        self.scanMatrix[direction, scanNumber, polarisation, :, freqindex] = \
            self.inversion * response.data[:response.framelength]
        self.reflectogrammChanged.emit(response.data[:response.framelength]) #?
        self.collected.add(scanNumber)
        #self.waitingForTemperature = True

    def time_from_start(self):
        return time.time() - self.starttime

    def appendUSBResponse(self, response):
        self.time[self.temperatureIndex] = self.time_from_start()
        self.temperature[self.temperatureIndex] = response.T1
        self.temperature2[self.temperatureIndex] = response.T2
        self.temperatureIndex += 1

        self.temperatureCurveChanged.emit(
            Curve(self.time[:self.temperatureIndex],
                  self.temperature[:self.temperatureIndex]))
        self.temperatureCurve2Changed.emit(
            Curve(self.time[:self.temperatureIndex],
                  self.temperature2[:self.temperatureIndex]))
        
        if self.temperatureIndex == 30000:
            for ar in self.time, self.temperature, self.temperature2:
                ar[:30000//2] = ar[30000//2:]
            
            self.temperatureIndex = 30000 // 2

        
    def appendOnChipTemperature(self, temp):
        self.onChipTemp[self.nextIndex] = temp
        upcurves = []
        downcurves = []
        for j in range(1):
            for i in range(3):
                upcurves.append(
                Curve(x=self.upOnChipTemp[i, j],
                    y=self.upScanMatrix[i, j])
                )

            for i in range(3):
                downcurves.append(
                Curve(x=self.downOnChipTemp[i, j],
                    y=self.downScanMatrix[i, j])
                )
        self.spectraOnChipChanged.emit((upcurves, downcurves))
    
    def savelastscan(self):
        direction, scanNumber, polarisation, freqindex = self.nextIndex
        if scanNumber == 0:
            return
        if scanNumber == 1:
            if 2 in self.collected:
                up_0 = self.scanMatrix[0, 2, 0]
                down_0 = self.scanMatrix[1, 2, 0]
            else:
                up_0 = self.scanMatrix[0, 0, 0]
                down_0 = self.scanMatrix[1, 0, 0]
        if scanNumber == 2:
            up_0 = self.scanMatrix[0, 1, 0]
            down_0 = self.scanMatrix[1, 1, 0]
        
        p = mp.Process(target=mydump, args=(up_0, down_0))
        p.start()

    def get_actual_temperature(self, period):
        eps = 0.1
        actual = np.logical_and(
                 (self.time >
                 (self.time_from_start() - period)),
                 (abs(self.time) > eps))

        moments = self.time[actual]
        if len(moments) == 0:
            return np.array([]), np.array([]), np.array([])
        else:
            return (moments, self.temperature[actual],
                    self.temperature2[actual])


    def clear(self):
        self.upScanMatrix[:] = 0
        self.downScanMatrix[:] = 0
        
        self.upOnChipTemp[:] = 0
        self.downOnChipTemp[:] = 0
        self.scanIndex = 0

        self.reflectogrammIndex = 0
        self.matrixIndex = 0
        self.firstScan = True
        
        self.time[:] = 0
        self.temperature[:] = 0
        self.temperature2[:] = 0
        self.temperatureIndex = 0
        
        self.collected = set([])
        
        self.topIndexes = np.array([])
        self.bottomIndexes = np.array([])
        self.extremums = np.array([])

        self.starttime = time.time()
    
    def recreatecontainer(self):
        # 2 -- up and down scans
        # 3 -- three of down and up scans
        # 1 -- 1 polarisation state
        # 
        shape = (2, 3, 1, self.reflectogrammLength, self.spectraLength)
        N = np.prod(shape)
        print "newshape", shape
        self.shared = mp.Array(ctypes.c_double, N, lock=False)
        self.sharedArrayChanged.emit((self.shared, shape))
        
        self.scanMatrix = np.ctypeslib.as_array(self.shared)
        self.scanMatrix.shape = shape

        self.upScanMatrix = self.scanMatrix[0]
        self.downScanMatrix = self.scanMatrix[1]

        self.upScanMatrix[:] = 123
        self.downScanMatrix[:] = 123
        
        self.onChipTemp = np.zeros((2, 3, 1, self.spectraLength), dtype=int)
        self.upOnChipTemp = self.onChipTemp[0]
        self.downOnChipTemp = self.onChipTemp[1]
        self.nextIndex = (0, 0, 0, 0)

    def setSpectraLength(self, length):
        if self.spectraLength != length:
            self.spectraLength = length
            self.recreatecontainer()
        
    def setReflectogrammLength(self, lenght):
        if self.reflectogrammLength != lenght:
            self.reflectogrammLength = lenght
            self.recreatecontainer()
            
    def setNextIndex(self, index):
        self.nextIndex = index

    def setInversion(self, inv):
        if inv:
            self.inversion = -1
        else:
            self.inversion = 1
