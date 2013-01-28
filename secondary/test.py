import numpy as np
import pysecondary
import pylab as plt
import time
import os

n_channel = 10000
window = 1000
noise_sigma = 0.1
secondary = pysecondary.Secondary()
decays = [1, 4, 16, 32]
levs = [6., 7., 8.]
for i in range(100):
    data = np.random.randn(n_channel) * noise_sigma
    secondary(data, 0, n_channel, window, decays, levs)
data[:] = 0.
data[1000] = 1.

secondary(data, 0, n_channel, window, decays, levs)
print secondary.diffs[:,1000]

print dir(secondary)

plt.plot(secondary.diffs.T)
plt.figure(1)
plt.legend([str(el) for el in decays])
plt.show()

