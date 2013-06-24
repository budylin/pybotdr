import sys
import ConfigParser
from PyQt4 import QtGui
from mainwindow import MainWindow

# this funciton supposed to run only once, so it's ok to import in it
# it tries to open usb device
def openUSB(usbsetting):
    try:
        from usbworker import USBWorker
    except ImportError:
        print "Failed to load module communicating with usb"
        return None
    try:
        usb = USBWorker(usbsetting)
    except:
        print "Failed to open USB device"
        return None
    return usb

def openDragon(pciesettings):
    import pcienetclient as pcie
    import socket
    try:
        pcieClient = pcie.PCIENetWorker(pciesettings)
    except socket.error:
        print "Failed to connect to Dragon"
        return None
    return pcieClient

def connectUSBManualControl(usb, wnd):
    widget = wnd.usbWidget
    widget.radioButton.toggled.connect(usb.setPID)
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

    wnd.setDIL_T.connect(usb.setDIL_T)
    wnd.setDIL_T_scan_time.connect(usb.setDIL_T_scan_time)
    wnd.usbMeasure.connect(usb.measure)

    connectUSBManualControl(usb, wnd)

def connectDragon(dragon, wnd):
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

def myprint(x):
    print x


class UpdateNotifier(object):
    def __init__(self, settings):
        self.settings = settings
        self.subscribers = {}
        for group in settings.keys():
            self.subscribers[group] = []
    def subscribe(self, group, subscriber):
        self.subscribers[group].append(subscriber)
    def update(self, group, diff, debugprint=False):
        if diff[0] in self.settings[group]:
            self.settings[group][diff[0]] = diff[1]
            for subscriber in self.subscribers[group]:
                subscriber(diff)
        if debugprint:
            print "Update {0} section {1}".format(group, diff)

def recieveupdates(state, wnd):
    widgets = dict(USB=wnd.usbWidget,
                   PCIE=wnd.pcieWidget,
                   DistanceCorrector=wnd.correctorWidget,
                   TimeScanner=wnd.scannerWidget,
                   DIL_TScanner=wnd.DILTScannerWidget,
                   Secondary=wnd.zone)
    for section in state.settings:
        widgets[section].updated.connect(
            lambda diff, name=section: state.update(name, diff))
        state.subscribe(section, widgets[section].update_state)

def updateconfig(config, section, update):
    config.set(section, update[0], str(update[1]))
    config.write(open("settings/all.ini", "w"))

def main(test):
    configfiles = set(["settings/all.ini" ])
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    parsedfiles = config.read(configfiles)
    print parsedfiles, config.sections()

    groups = config.sections()
    settings = dict([(section, convert(config.items(section))) for section in config.sections()])
    state = UpdateNotifier(settings)
    app = QtGui.QApplication(sys.argv)
    wnd = MainWindow(state)

    recieveupdates(state, wnd)
    state.subscribe("Secondary", wnd.secondary.update)
    for section in state.settings.keys():
        state.subscribe(section,
                        lambda diff, sect=section: updateconfig(config, sect, diff))

#    wnd.usbWidget.updated.connect(myprint)
    if not test:
        usb = openUSB(settings["USB"])
        if usb:
            connectUSB(usb, wnd)
            state.subscribe("USB", usb.update)

        dragon = openDragon(settings["PCIE"])
        if dragon:
            connectDragon(dragon, wnd)
            state.subscribe("PCIE", dragon.update)
            # TODO setting should be stored not in widget
            dragon.start()

    else:
        framelength = wnd.pcieWidget.framelength.value()
        ndots = wnd.DILTScannerWidget.nsteps.value()
        x = dummy(framelength, ndots)
        btn = QtGui.QPushButton("ref")
        btn.show()
        x.timer.timeout.connect(lambda: wnd.on_new_reflectogramm(x.ref()))
        btn.clicked.connect(lambda: x.toggle())


    wnd.show()
    sys.exit(app.exec_())
    config.write()

if __name__ == "__main__":
    import argparse
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    parser = argparse.ArgumentParser(prog='pybotdr')
    parser.add_argument('-t', '--test', action="store_true")
    opt = parser.parse_args()
    main(opt.test)

