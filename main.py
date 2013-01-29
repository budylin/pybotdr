import sys
from PyQt4 import QtGui
from mainwindow import MainWindow

# this funciton supposed to run only once, so it's ok to import in it
# it tries to open usb device
def openUSB():
    try:
        from usbworker import USBWorker
    except ImportError:
        print "Failed to load module communicating with usb"
        return None
    try:
        usb = USBWorker()
    except:
        print "Failed to open USB device"
        return None
    return usb

def openDragon():
    import pcienetclient as pcie
    import socket
    try:
        pcieClient = pcie.PCIENetWorker()
    except socket.error:
        print "Failed to connect to Dragon"
        return None
    return pcieClient

def connectUSBManualControl(usb, wnd):
    widget = wnd.usbWidget
    widget.spinBox.valueChanged.connect(usb.setPFGI_amplitude)
    widget.spinBox_2.valueChanged.connect(usb.setPFGI_pedestal)
    widget.checkBox.toggled.connect(usb.setPC4)
    widget.checkBox_2.toggled.connect(usb.setPC5)
    widget.spinBox_5.valueChanged.connect(usb.setDIL_I)
    widget.spinBox_6.valueChanged.connect(usb.setDIL_T)
    widget.spinBox_7.valueChanged.connect(usb.setPFGI_Tset)
    widget.PFGI_TscanAmp.valueChanged.connect(usb.setPFGI_TscanAmp)
    widget.spinBox_3.valueChanged.connect(usb.setPROM_hv)
    widget.spinBox_4.valueChanged.connect(usb.setPROM_shift)
    widget.spinBox_9.valueChanged.connect(usb.setFOL1_I)
    widget.spinBox_10.valueChanged.connect(usb.setFOL1_T)
    widget.spinBox_11.valueChanged.connect(usb.setFOL2_I)
    widget.spinBox_12.valueChanged.connect(usb.setFOL2_T)
    widget.spinBox_a1.valueChanged.connect(usb.setA1)
    widget.spinBox_a2.valueChanged.connect(usb.setA2)
    widget.spinBox_a3.valueChanged.connect(usb.setA3)
    widget.spinBox_b1.valueChanged.connect(usb.setB1)
    widget.spinBox_b2.valueChanged.connect(usb.setB2)
    widget.spinBox_b3.valueChanged.connect(usb.setB3)
    widget.spinBox_c1.valueChanged.connect(usb.setC1)
    widget.spinBox_c2.valueChanged.connect(usb.setC2)
    widget.spinBox_c3.valueChanged.connect(usb.setC3)
    widget.spinBox_t1.valueChanged.connect(usb.setT1set)
    widget.spinBox_t2.valueChanged.connect(usb.setT2set)
    widget.spinBox_t3.valueChanged.connect(usb.setT3set)
    widget.radioButton.toggled.connect(usb.setPID)
    widget.spinBox_TScanPeriod.valueChanged.connect(usb.setPFGI_TscanPeriod)
    widget.checkBox_3.toggled.connect(usb.setDiode)

    wnd.DILTScannerWidget.top.valueChanged.connect(usb.setDIL_T_scan_top)
    wnd.DILTScannerWidget.bottom.valueChanged.connect(usb.setDIL_T_scan_bottom)

    wnd.otherWidget.flashSTM.clicked.connect(usb.flash)

def connectUSB(usb, wnd):
    usb.measured.connect(wnd.usbWidget.showResponse)
    usb.statusChanged.connect(wnd.usbWidget.label_status.setText)
    # TODO for now collector is in window
    usb.measured.connect(wnd.collector.appendUSBResponse)

    # TODO starting settings are stored in widget value
    usb.setDIL_T_scan_top(wnd.DILTScannerWidget.top.value())
    usb.setDIL_T_scan_bottom(wnd.DILTScannerWidget.bottom.value())


    wnd.startUpScan.connect(usb.start_up_scan)
    wnd.startDownScan.connect(usb.start_down_scan)

    wnd.setPFGI_TscanAmp.connect(usb.setPFGI_TscanAmp)
    wnd.setDIL_T.connect(usb.setDIL_T)
    wnd.setDIL_T_scan_time.connect(usb.setDIL_T_scan_time)
    wnd.usbMeasure.connect(usb.measure)

    connectUSBManualControl(usb, wnd)

def connectDragon(dragon, wnd):
    wnd.pcieWidget.valueChanged.connect(dragon.setPCIESettings)
    dragon.measured.connect(wnd.on_new_reflectogramm)

class dummy(object):
    def __init__(self, framelength, steps):
        import numpy as np
        from PyQt4 import QtCore
        self.framelength = framelength
        self.steps = steps
        self.array = np.array([np.linspace(-3, 3, steps)] * framelength).T
        self.array = 100 * np.exp(-self.array*self.array)
        self.array[:,-1000:] = 0.
        self.i = 0
        self.going = False
        self.timer = QtCore.QTimer()
        self.randint = np.random.randint
        self.roll = np.roll

    def ref(self):
        shift = self.randint(11) - 5
        self.data = self.array[self.i]
        if self.i == self.steps - 1:
            self.array[:,1000] = self.roll(self.array[:,1000], shift)
        self.i = (self.i + 1) % self.steps
        return self

    def toggle(self):
        self.going = not self.going
        if self.going:
            self.timer.start(200)
        else:
            self.timer.stop()


def main(test):
    app = QtGui.QApplication(sys.argv)
    wnd = MainWindow()

    usb = openUSB()
    if usb:
        connectUSB(usb, wnd)
        wnd.updateUSBSettingsView(usb.usbSettings.file)

    dragon = openDragon()
    if dragon:
        connectDragon(dragon, wnd)
        # TODO setting should be stored not in widget
        dragon.setPCIESettings(wnd.pcieWidget.value())
        dragon.start()

    if test:
        framelength = wnd.pcieWidget.framelength.value()
        ndots = wnd.DILTScannerWidget.nsteps.value()
        x = dummy(framelength, ndots)
        btn = QtGui.QPushButton("ref")
        btn.show()
        x.timer.timeout.connect(lambda: wnd.on_new_reflectogramm(x.ref()))

        btn.clicked.connect(lambda: x.toggle())

    wnd.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog='pybotdr')
    parser.add_argument('-t', '--test', action="store_true")
    opt = parser.parse_args()
    main(opt.test)

