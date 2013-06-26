import numpy as np
import time
from distances import dataFromShared

# returns list on indexes of insane spectra
def check_spectra_insanity(submatrix_index, data_reg):
    submatrix = dataFromShared()[submatrix_index]
    data = submatrix[0,data_reg[0]:data_reg[1]]
    data[data < -1] = 0
    noise = submatrix[0,-500:-400]
    noise_amp = np.max(noise) - np.min(noise)
    data_amp = np.max(data, axis=1) - np.min(data, axis=1)
    insane = data_amp < noise_amp * 5 + 1e-7
    return list(np.arange(len(insane))[insane])


def check_stability(times, temps, targets, stab_time, maxdev=10):
    if not len(times) or max(times) - min(times) < stab_time:
        return False
    devs = np.array(temps) - np.array(targets).reshape(-1, 1)
    return np.max(np.abs(devs)) < maxdev

class Search(object):
    def __init__(self, beg, end, step, dt, setter):
        self.xs = range(beg, end, step)
        self.iterator = iter(self.xs)
        self.ups = []
        self.downs = []
        self.setter = setter
        self.phase = "forward"
        self.for_max = None
        self.back_max = None
        self.dt = dt
        self.prev_time = time.time()
        self.step = step
        setter(self.iterator.next())

    def new_data(self, data):
        if not time.time() - self.prev_time < self.dt:
            self.prev_time = time.time()
            return self.set_response(data)

    def set_response(self, data):
        if self.phase == "forward":
            self.ups.append(np.std(data))
            try:
                self.setter(self.iterator.next())
            except StopIteration:
                self.iterator = iter(self.xs[::-1])
                self.phase = "backward"
        elif self.phase == "backward":
            self.downs.append(np.std(data))
            try:
                self.setter(self.iterator.next())
            except StopIteration:
                self.downs.reverse()
                upmax = np.argmax(self.ups)
                downmax = np.argmax(self.downs)
                print upmax, downmax
                self.phase = "finished"
                low = min(self.xs[upmax], self.xs[downmax]) - self.step
                hi = max(self.xs[upmax], self.xs[downmax]) + self.step
                return low, hi
        elif self.phase == "finished":
            raise StopIteration

_search = None
def init_search(beg, end, step, dt, setter):
    global _search
    _search = Search(beg, end, step, dt, setter)

def search(data):
    global _search
    return _search.new_data(data)
