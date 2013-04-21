from ctypes import *

MAX_FRAME_LENGTH = 65520 * sizeof(c_uint32)

def dacdata(ch1amp, ch1shift, ch2amp, ch2shift):
    return ch1amp << 24 | ch1shift << 16 | ch2amp << 8 | ch2shift

def counts(ch1count, ch2count):
    return ch2count << 16 | ch1count
        
        
class PCIEResponse(object):
    pass
