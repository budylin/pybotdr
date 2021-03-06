from PyQt4 import QtCore

import socket
import mysocket
import  pciedevsettings
import struct
import array
import numpy as np

HOST = "localhost"
#HOST = '192.168.1.223'    # The remote host
PCIEPORT = 32120


class PCIENetWorker(QtCore.QThread):
    measured = QtCore.pyqtSignal(pciedevsettings.PCIEResponse)

    def __init__(self, settings, parent=None):
        QtCore.QThread.__init__(self, parent)
        self.socket = mysocket.MySocket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        self.socket.connect((HOST, PCIEPORT))
        self.lock = QtCore.QMutex()
        self.settings = settings
        self.exiting = False

    def update(self, diff):
        self.lock.lock()
        self.settings[diff[0]] = diff[1]
        self.lock.unlock()

    def setPCIESettings(self, settings):
        self.lock.lock()
        self.settings = settings
        self.lock.unlock()
        
    def run(self):
        response = pciedevsettings.PCIEResponse()
        while not self.exiting:
            channel = struct.unpack("B", self.socket.recvall(1))[0]
            response.framelength = struct.unpack("H", self.socket.recvall(2))[0]
            response.framecount = struct.unpack("I", self.socket.recvall(4))[0]
            response.dacdata = struct.unpack("I", self.socket.recvall(4))[0]
            datasize = pciedevsettings.MAX_FRAME_LENGTH
            rawdata = self.socket.recvall(datasize, timeout=5)
           
            dacdata = pciedevsettings.dacdata(ch1amp=self.settings["ch1amp"],
                                              ch1shift=self.settings["ch1shift"],
                                              ch2amp=self.settings["ch2amp"],
                                              ch2shift=self.settings["ch2shift"])  
            self.lock.lock()
            self.socket.sendall(struct.pack("B", int(channel)))
            self.socket.sendall(struct.pack("H", int(self.settings["framelength"])))
            self.socket.sendall(struct.pack("I", self.settings["framecount"]))
            self.socket.sendall(struct.pack("I", dacdata))
            self.lock.unlock()
            
            data = array.array("I")
            data.fromstring(rawdata)
            data = np.array(data).astype(float) / response.framecount
            response.data = data
            self.measured.emit(response)        
    
    def stop(self):
        self.exiting = True
        self.wait()
        self.socket.close()
