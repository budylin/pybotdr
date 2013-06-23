from PyQt4 import QtCore
import numpy as np

class Averager(QtCore.QThread):
    measured = QtCore.pyqtSignal(np.ndarray)
    def __init__(self, parent=None):
        QtCore.QObject.__init__(self, parent)
        self.distances = []
        self.number = 10
        self.averages = None

    def setNumber(self, number):
        self.number = number

    def appendDistances(self, distances):
        self.distances.append(distances)
        if len(self.distances) > self.number:
            self.distances.pop(0)
        print "averager has", len(self.distances),  "of", self.number,  "samples"
        if len(self.distances) >= self.number:
            self.start()
            self.wait()
            return self.averages

    def run(self):
        res = np.zeros(self.distances[-1].shape, dtype=float)
        for i in range(self.number):
            res += self.distances[-i - 1]
        res /= self.number
        self.averages = res
        self.measured.emit(res)

    def clear(self):
        self.distances = []

