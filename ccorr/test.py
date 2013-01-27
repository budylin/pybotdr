import numpy as np
import pycorrmax
import pylab as plt
import time

argmax = pycorrmax.Argmax()
print "Loading.."
data = np.loadtxt('/Users/gleb/Data/2012-09-10T17-17-37.249072/down_0.txt')
print "Calculating.."
plt.figure(1)
for i in range(0, 40000, 1000):
    plt.plot(data[i])
plt.figure(2)
for i in range(1):
    t = time.time()
    res, status = argmax(data)
    print "Calcuated in {}, {} {} errors".format(time.time() - t,
                                                 sum(status ==1), sum(status != 0))
    print status[np.logical_and(status != 0, status != 1)]
plt.plot(res)
plt.show()

