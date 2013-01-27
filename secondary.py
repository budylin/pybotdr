import pysecondary
import shelve

def load(shelve, key, default=0):
    try:
        val = shelve[key]
    except KeyError:
        val = default
        shelve[key] = val
        shelve.sync()
    return val

class Model:
    def __init__(self):
        self.saved = shelve.open("secondary.db", writeback=True)
        self.start = load(self.saved, 'start')
        self.length = load(self.saved, 'length')
        self.decays = load(self.saved, 'decays', [1.] * 4)
        self.levels = load(self.saved, 'levels', [4., 6., 9.])
        self.process = pysecondary.Secondary()

    def __call__(self, data):
        return self.process(data, self.start, self.length, 600,
                            self.decays, self.levels)

    def __del__(self):
        self.saved.close()

    def set_length(self, val):
        self.length = val
        self.saved['length'] = val
        self.saved.sync()

    def set_start(self, val):
        self.start = val
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
