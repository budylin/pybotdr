import sys
import ConfigParser
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
    widget.PFGI_amplitude.valueChanged.connect(usb.setPFGI_amplitude)
    widget.PFGI_pedestal.valueChanged.connect(usb.setPFGI_pedestal)
    widget.PC4.toggled.connect(usb.setPC4)
    widget.PC5.toggled.connect(usb.setPC5)
    widget.DIL_I.valueChanged.connect(usb.setDIL_I)
    widget.DIL_T.valueChanged.connect(usb.setDIL_T)
    widget.PFGI_Tset.valueChanged.connect(usb.setPFGI_Tset)
    widget.PFGI_TscanAmp.valueChanged.connect(usb.setPFGI_TscanAmp)
    widget.PROM_hv.valueChanged.connect(usb.setPROM_hv)
    widget.PROM_shift.valueChanged.connect(usb.setPROM_shift)
    widget.FOL1_I.valueChanged.connect(usb.setFOL1_I)
    widget.FOL1_T.valueChanged.connect(usb.setFOL1_T)
    widget.FOL2_I.valueChanged.connect(usb.setFOL2_I)
    widget.FOL2_T.valueChanged.connect(usb.setFOL2_T)
    widget.A1.valueChanged.connect(usb.setA1)
    widget.A2.valueChanged.connect(usb.setA2)
    widget.A3.valueChanged.connect(usb.setA3)
    widget.B1.valueChanged.connect(usb.setB1)
    widget.B2.valueChanged.connect(usb.setB2)
    widget.B3.valueChanged.connect(usb.setB3)
    widget.C1.valueChanged.connect(usb.setC1)
    widget.C2.valueChanged.connect(usb.setC2)
    widget.C3.valueChanged.connect(usb.setC3)
    widget.T1set.valueChanged.connect(usb.setT1set)
    widget.T2set.valueChanged.connect(usb.setT2set)
    widget.T3set.valueChanged.connect(usb.setT3set)
    widget.radioButton.toggled.connect(usb.setPID)
    widget.PFGI_TscanPeriod.valueChanged.connect(usb.setPFGI_TscanPeriod)
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


def convert(items):
    result = {}
    for key, val in items:
        if val in ["True", "False"]:
            conv = val == "True"
        elif '.' in val:
            try:
                conv = float(val)
            except ValueError:
                conv = val
        else:
            try:
                conv = int(val)
            except ValueError:
                conv = val
        result[key] = conv
    return result


def main(test):
    configfiles = set(["settings/timescanner.ini",
                       "settings/DIL_Tscanner.ini",
                       "settings/distancecorrector.ini",
                       "settings/settings.ini",
                       "settings/pciedevsettings.ini"
                       ])
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    parsedfiles = config.read(configfiles)
    print parsedfiles, config.sections()
    app = QtGui.QApplication(sys.argv)
    wnd = MainWindow()

    wnd.pcieWidget.setstate(convert(config.items("PCIE")))
    wnd.DILTScannerWidget.setstate(convert(config.items("DIL_TScanner")))
    wnd.scannerWidget.setstate(convert(config.items("TimeScanner")))
    wnd.correctorWidget.setstate(convert(config.items("DistanceCorrector")))
    wnd.usbWidget.setstate(convert(config.items("General")))

    if test:
        framelength = wnd.pcieWidget.framelength.value()
        ndots = wnd.DILTScannerWidget.nsteps.value()
        x = dummy(framelength, ndots)
        btn = QtGui.QPushButton("ref")
        btn.show()
        x.timer.timeout.connect(lambda: wnd.on_new_reflectogramm(x.ref()))
        btn.clicked.connect(lambda: x.toggle())

    else:
        usb = openUSB()
        if usb:
            connectUSB(usb, wnd)

        dragon = openDragon()
        if dragon:
            connectDragon(dragon, wnd)
            # TODO setting should be stored not in widget
            dragon.setPCIESettings(wnd.pcieWidget.value())
            dragon.start()


    wnd.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(prog='pybotdr')
    parser.add_argument('-t', '--test', action="store_true")
    opt = parser.parse_args()
    main(opt.test)

