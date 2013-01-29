import pysecondary
import shelve
from PyQt4 import QtCore

def load(shelve, key, default=0):
    try:
        val = shelve[key]
    except KeyError:
        val = default
        shelve[key] = val
        shelve.sync()
    return val

class Model(QtCore.QThread):
    measured = QtCore.pyqtSignal()
    def __init__(self):
        QtCore.QThread.__init__(self)
        self.saved = shelve.open("secondary.db", writeback=True)
        self.startChannel = load(self.saved, 'start')
        self.length = load(self.saved, 'length')
        self.decays = load(self.saved, 'decays', [1.] * 4)
        self.levels = load(self.saved, 'levels', [4., 6., 9.])
        self.process = pysecondary.Secondary()

    def __call__(self, data):
        self.data = data
        print 'Secondary called'
        self.run()

    def run(self):
        print 'Secondary started'
        print self.data.shape
        print self.startChannel, self.length, 600
        self.process(self.data, self.startChannel, self.length, 600,
                            self.decays, self.levels)
        print 'Emitting secondary.measured'
        self.measured.emit()

    @property
    def diffs(self):
        return self.process.diffs

    def __del__(self):
        self.saved.close()

    def set_length(self, val):
        self.length = val
        self.saved['length'] = val
        self.saved.sync()

    def set_start(self, val):
        self.startChannel = val
        self.saved['start'] = val
        self.saved.sync()

    def set_decay(self, index, val):
        self.decays[index] = val
        self.saved['decays'][index] = val
        self.saved.sync()

    def set_level(self, index, val):
        self.levels[index] = val
        self.saved['levels'][index] = val
        self.saved.sync()
