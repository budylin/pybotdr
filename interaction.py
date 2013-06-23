import pyinteraction
from PyQt4 import QtCore

class Model(QtCore.QThread):
    measured = QtCore.pyqtSignal()
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.process = pyinteraction.Interaction()

    def __call__(self, data):
        self.data = data
        print 'Interaction called'
        self.run()
        self.wait()

    def run(self):
        print 'Interaction started'
        print 'Data shape', self.data.shape
        self.process(self.data)
        print 'Emitting interaction.measured'
        self.measured.emit()
