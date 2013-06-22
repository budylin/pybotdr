import pysecondary
from PyQt4 import QtCore

class Model(QtCore.QThread):
    measured = QtCore.pyqtSignal()
    def __init__(self, state):
        QtCore.QThread.__init__(self)
        self.startChannel = state['start']
        self.length = state['length']
        decnames = ["decay{}".format(i) for i in range(4)]
        self.decays = [state[name] for name in decnames]
        levnames = ["level{}".format(i) for i in range(3)]
        self.levels = [state[name] for name in levnames]
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

    def update(self, diff):
        if diff[0] in ['length', 'start']:
            getattr(self, 'set_' + diff[0])(diff[1])
        elif 'decay' in diff[0]:
            getattr(self, 'set_decay')(int(diff[0][-1]), diff[1])
        elif 'level' in diff[0]:
            getattr(self, 'set_level')(int(diff[0][-1]), diff[1])
        else:
            raise AttributeError("Model has no {} attribute".format(diff[0]))

    @property
    def diffs(self):
        return self.process.diffs

    def set_length(self, val):
        self.length = val

    def set_start(self, val):
        self.startChannel = val

    def set_decay(self, index, val):
        self.decays[index] = val

    def set_level(self, index, val):
        self.levels[index] = val
