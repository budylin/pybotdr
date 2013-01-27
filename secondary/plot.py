import sys
from numpy import loadtxt
from pylab import plot, show

names = sys.argv[1:]
if names:
    for name in names:
        x, y = loadtxt(name, unpack=True)
        plot(x, y)
    show()
