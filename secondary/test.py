import numpy as np
import pycorrmax
import pysecondary
import pylab as plt
import time
import os

base = '/Users/gleb/Data'
folders = ['2012-09-28T19-57-28.598174', '2012-09-28T20-00-39.748073',
           '2012-09-28T20-02-14.094110'][:-1]
names = ['up_0.txt', 'down_0.txt']
argmax = pycorrmax.Argmax()
secondary = pysecondary.Secondary()
first = True
t = time.time()
i = 0
for folder in folders:
    for name in names:
        fullname = os.path.join(base, folder)
        fullname = os.path.join(fullname, name)
        if fullname == '/Users/gleb/Data/2012-09-28T19-57-28.598174/down_0.txt':
            continue
        print "Loading.." + fullname
        data = np.genfromtxt(fullname, skip_header=50, skip_footer=52000)
        print "Calculating.."
        res, status = argmax(data)
        res_filt = np.loadtxt("{}.dat".format(i))
        if first:
            ref_filt = res_filt.copy()
            ref = res.copy()
        plt.figure(2)
#        plt.plot(res-ref, label=name)
        if not first:
            toplot = (res_filt - ref_filt)**2
            plt.hist(toplot, bins=1000, label="filtered {}".format(name))
        print "Calcuated in {}, {} {} errors".format(time.time() - t,
                                                     sum(status ==1), sum(status != 0))
        print status[np.logical_and(status != 0, status != 1)]

        sec = secondary(res)
        plt.figure(1)
        plt.plot(sec, 'o', label=name)
        first = False
        i += 1
plt.figure(1)
plt.legend()
plt.figure(2)
plt.legend()
plt.show()

