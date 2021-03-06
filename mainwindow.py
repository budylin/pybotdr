from PyQt4 import Qt, QtCore, QtGui, uic, Qwt5 as Qwt
from collector import Collector
import  pciedevsettings
import plots
import time
import scanner
from datetime import datetime
import dump
from distances import (Correlator, Maximizer, MemoryUpdater)
from averager import Averager
from distancecorrector import DistanceCorrector
from sender import Sender
import secondary
import numpy as np
import logic
import sys
try:
    import interaction
    is_interactive = True
except ImportError as e:
    print "Failed to establish interaction with data-server"
    print e
    is_interactive = False


STARTING_N_SP_DOT = 100
EXT_STAB_TIME = 10
INT_STAB_RATE = 1. / 100.
SEARCH_STEP = 100
SEARCH_TOP = 40000
SEARCH_BOT = 20000
REF_LEN = 65520

Base, Form = uic.loadUiType("window.ui")
class MainWindow(Base, Form):
    startUpScan = QtCore.pyqtSignal()
    startDownScan = QtCore.pyqtSignal()
    setDIL_T = QtCore.pyqtSignal(int)
    setDIL_T_scan_time = QtCore.pyqtSignal(int)
    usbMeasure = QtCore.pyqtSignal()
    def __init__(self, state, parent=None):
        super(Base, self).__init__(parent)
        self.setupUi(self)

        self.state = state
        settings = state.settings
        self.nonthermo = uic.loadUi("nonthermo.ui")
        self.otherWidget = uic.loadUi("other.ui")
        self.scannerSelect = uic.loadUi("scannerselect.ui")
        self.zone = SecondaryWidget(settings["Secondary"])
        self.usbWidget = USBWidget(settings["USB"])
        self.pcieWidget = DragonWidget(settings["PCIE"])
        self.correctorWidget = CorrectorWidget(settings["DistanceCorrector"])
        self.scannerWidget = ScannerWidget(settings["TimeScanner"])
        self.scannerWidget.groupBox.setTitle("On chip scanner")
        self.DILTScannerWidget = ScannerWidget(settings["DIL_TScanner"],
                                               name="DIL_Tscanner")
        self.DILTScannerWidget.groupBox.setTitle("DIL_T scanner")

        self.scannerSelect.layout().insertWidget(1, self.scannerWidget)
        self.scannerSelect.layout().insertWidget(3, self.DILTScannerWidget)
        self.nonthermo.layout().addWidget(self.scannerSelect, 0, 0, 3, 1)
        self.nonthermo.layout().addWidget(self.otherWidget, 2, 1, 1, 1)
        self.nonthermo.layout().addWidget(self.zone, 0, 1, 1, 1)
        self.nonthermo.layout().addWidget(self.correctorWidget, 1, 1, 1, 1)

        self.usbWidget.tabWidget.insertTab(2, self.nonthermo, "Scanning setup")
        self.usbWidget.tabWidget.insertTab(3, self.pcieWidget, "Dragon")
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Maximum,
                                       QtGui.QSizePolicy.Preferred)
        self.usbWidget.setSizePolicy(sizePolicy)
        self.settings.addWidget(self.usbWidget, 0, 0, 1, 1)

        dragonrect = QtCore.QRectF(0, plots.SIGNAL_BOT, REF_LEN,
                                   plots.SIGNAL_TOP - plots.SIGNAL_BOT)
        self.dragonplot = plots.Plot(dragonrect, self)
        self.temperatureplot = plots.TempPlot()
        self.spectraplot = plots.SlicePlot(self)
        self.distanceplot = plots.Plot(QtCore.QRectF(0, -500, REF_LEN, 2*500),
                                       self, zeroed=True, points=True,
                                       lines=True, levels=[0,0,1000,1000],
                                       ncurves=8)
        self.diffsPlot = plots.Plot(QtCore.QRectF(0, -500, REF_LEN, 2*500),
                                    self, zeroed=False, points=True,
                                    lines=True, levels=[0,0,1000,1000],
                                    ncurves=8)

        self.graphTabs = QtGui.QTabWidget(self)

        self.primaryGraphs = uic.loadUi("nonthermo.ui")
        self.primaryGraphs.layout().addWidget(self.spectraplot, 0, 0, 1, 1)
        self.primaryGraphs.layout().addWidget(self.temperatureplot, 0, 1)
        self.primaryGraphs.layout().addWidget(self.dragonplot, 1, 1)
        self.primaryGraphs.layout().addWidget(self.distanceplot, 1, 0, 1, 1)
        self.graphTabs.insertTab(0, self.primaryGraphs, "primary")

        self.secondaryGraphs = uic.loadUi("nonthermo.ui")
        self.secondaryGraphs.layout().addWidget(self.diffsPlot, 0, 0, 1, 1)
        self.graphTabs.insertTab(1, self.secondaryGraphs, "secondary")

        self.plots.addWidget(self.graphTabs, 0,0,1,1)

#TODO: Further init code does not describe window but program logic.
# It should be separated.


        self.PFGITscanner = scanner.TimeScanner(settings["TimeScanner"])
        self.DIL_Tscanner = scanner.TimeScanner(settings["DIL_TScanner"])


        self.collector = Collector(65520, settings["TimeScanner"]["nsteps"])
        self.memoryupdater = MemoryUpdater(self)
        self.correlator = Correlator(self)
        self.maximizer = Maximizer(self)
        self.secondary = secondary.Model(settings["Secondary"])
        if is_interactive:
            self.interaction = interaction.Model()
        self.corraverager = Averager(self)
        self.corraverager.setNumber(settings["TimeScanner"]["averageNumber"])

        self.connectScanerWidget()
        self.connectOtherWidget()

        self.spectraplot.setChannel(self.otherWidget.plotChannel.value())

        self.corrector = DistanceCorrector(self)
        self.connectCorrectorWidget()
        corrector_settings = state.settings["DistanceCorrector"]
        self.corrector.setTargetDistance(corrector_settings["distance"])
        self.corrector.setA(corrector_settings["A"])
        self.corrector.setEnabled(corrector_settings["enabled"])
        self.corrector.setChannel(corrector_settings["channel"])
        self.corrector.setReaction(settings["USB"]["DIL_T"])

        self.maximizer.measured.connect(self.corrector.appendDistances)
        self.corrector.correct.connect(lambda val: self.state.update("USB", ("DIL_T", val)))
        state.subscribe("USB",
            lambda diff: None if diff[0] != "DIL_T" else self.corrector.setReaction(diff[1]))



        self.temperatureplot.t0 = lambda v:self.temperatureplot.myplot(v, 0)
        self.temperatureplot.t1 = lambda v:self.temperatureplot.myplot(v, 1)

        self.collector.temperatureCurveChanged.connect(self.temperatureplot.t0)
        self.collector.temperatureCurve2Changed.connect(self.temperatureplot.t1)


        self.collector.setReflectogrammLength(state.settings["PCIE"]["framelength"])


        self.status = "waiting"
        self.start = time.time()
        self.time_prev = time.time()
        self.resp_amp = []
        self.laserscanner = "PFGIT"
        self.enablePFGITscanner(True)
        self.scannerSelect.PFGIT.toggled.connect(self.enablePFGITscanner)
        if self.scannerSelect.PFGIT.isChecked():
            print "PFGIT enabled"
            self.maximizer.set_bottom(self.scannerWidget.bottom.value())
            self.maximizer.set_dt(self.scannerWidget.dt())
        else:
            print "DILT enabled"
            self.maximizer.set_bottom(self.DILTScannerWidget.bottom.value())
            self.maximizer.set_dt(self.DILTScannerWidget.dt())


        #WARNING old code! revision may be needed
        #self.collector.reflectogrammChanged.connect(self.dragonplot.myplot)
        self.collector.spectraOnChipChanged.connect(self.spectraplot.setData)

        # This connections must be replaced with clear code
        self.collector.sharedArrayChanged.connect(self.memoryupdater.updateShared)
        self.memoryupdater.updated.connect(self.correlator.update)

        self.memoryupdater.updateShared((self.collector.shared, (2,) + self.collector.upScanMatrix.shape))
        self.correlator.setDt(1.)
        self.correlator.measured.connect(self.distanceplot.myplot)


        self.scannerWidget.averageNumber.valueChanged.connect(self.corraverager.setNumber)

        self.distanceplot.d2 = lambda t: self.distanceplot.myplot(t, n=3)
        self.distanceplot.d3 = lambda t: self.distanceplot.myplot(t, n=4)
        self.corraverager.measured.connect(self.distanceplot.d2)


        self.pcieWidget.framelength.valueChanged.connect(self.collector.setReflectogrammLength)

        self.measuretimer = self.startTimer(1000)
        #self.FOL2timer = self.startTimer(self.usbWidget.FOL2_period.value())

        self.pcieWidget.framelength.valueChanged.connect(self.change_scan_time)
        self.pcieWidget.framecount.valueChanged.connect(self.change_scan_time)
        self.DILTScannerWidget.nsteps.valueChanged.connect(self.change_scan_time)

        self.change_scan_time()

        self.showMaximized()
        self.plotsOnly = False
        self.plotsFreezed = False

        self.DILTScannerWidget.nsteps.valueChanged.connect(self.collector.setSpectraLength)
        self.DIL_Tscanner.scanPositionChanged.connect(self.DILTScannerWidget.position.setNum)
        self.scannerWidget.nsteps.valueChanged.connect(self.collector.setSpectraLength)
        self.PFGITscanner.scanPositionChanged.connect(self.scannerWidget.position.setNum)
        self.scannerWidget.dtChanged.connect(self.maximizer.set_dt)
        self.scannerWidget.bottom.valueChanged.connect(
            self.maximizer.set_bottom)
        self.otherWidget.work.toggled.connect(self.on_work)

    def on_work(self, val):
        if not val:
            self.status = "idle"
        else:
            self.status = "waiting"


    def on_wait(self, data):
        t, T1, T2 = self.collector.get_actual_temperature(2 * EXT_STAB_TIME)
        targets = [self.state.settings["USB"]["T1set"],
                   self.state.settings["USB"]["T2set"]]
        if logic.check_stability(t, [T1, T2], targets, EXT_STAB_TIME):
            self.status = "searching"
            self.state.update("PCIE", ("framecount", 200))
            print "Searching"
            middle = (self.state.settings["TimeScanner"]["top"] +
                      self.state.settings["TimeScanner"]["bottom"]) / 2
            self.state.update("USB", ("PFGI_TscanAmp", middle))
            setter = lambda x: self.state.update("USB", ("DIL_T", x))
            dt = INT_STAB_RATE * SEARCH_STEP / 3
            logic.init_search(SEARCH_BOT, SEARCH_TOP, SEARCH_STEP,
                              dt, setter)

    def on_scan(self, pcie_dev_response):
        self.collector.appendDragonResponse(pcie_dev_response)
        submatrix_to_process = None
        if self.laserscanner == "DILT":
            self.collector.appendOnChipTemperature(
                self.DIL_Tscanner.scan_position)
            self.DIL_Tscanner.scan()
            self.collector.setNextIndex(self.DIL_Tscanner.pos)
            if self.DIL_Tscanner.top_reached:
                self.startDownScan.emit()
            elif self.DIL_Tscanner.bottom_reached:
                self.startUpScan.emit()
            if (self.DIL_Tscanner.top_reached or
                self.DIL_Tscanner.bottom_reached):
                submatrix_to_process = self.DIL_Tscanner.lastsubmatrix
        if self.laserscanner == "PFGIT":
            self.collector.appendOnChipTemperature(
                self.PFGITscanner.scan_position)
            self.PFGITscanner.scan()
            self.collector.setNextIndex(self.PFGITscanner.pos)
            self.state.update("USB", ("PFGI_TscanAmp", self.PFGITscanner.targetT))
            if (self.PFGITscanner.top_reached or
                self.PFGITscanner.bottom_reached):
                submatrix_to_process = self.PFGITscanner.lastsubmatrix
        if submatrix_to_process is not None:
            self.start_processing(submatrix_to_process)

    def start_processing(self, submatrix):
        data_reg = [self.state.settings["Secondary"]["start"],
                    self.state.settings["Secondary"]["length"]]
        insane_inds = logic.check_spectra_insanity(submatrix, data_reg)
        if insane_inds:
            print "Insane channels:", insane_inds
            if len(insane_inds) == self.state.settings["Secondary"]["length"]:
                print "All specrta are broken, searching"
                self.status = "searching"
            return
        primary = self.correlator.process_submatrix(submatrix)
        self.maximizer.process_submatrix(submatrix)
        averages = self.corraverager.appendDistances(primary)
        if averages is not None:
            self.secondary(averages[0])
            self.process_secondary()
            if is_interactive:
                self.interaction(self.secondary.process.results)

    def on_search(self, data):
        t, T1, T2 = self.collector.get_actual_temperature(2 * EXT_STAB_TIME)
        targets = [self.state.settings["USB"]["T1set"],
                   self.state.settings["USB"]["T2set"]]
        if not logic.check_stability(t, [T1, T2], targets, EXT_STAB_TIME):
            return
        new_range = logic.search(data)
        if new_range is None:
            return
        print "New search range", new_range
        bot, top = new_range
        if top - bot > 10:
            setter = lambda x: self.state.update("USB", ("DIL_T", x))
            step = max(1,
                       SEARCH_STEP * (bot - top) / (SEARCH_BOT - SEARCH_TOP))
            dt = INT_STAB_RATE * step
            logic.init_search(bot, top, step, dt, setter)
        else:
            mid = int((bot + top) / 2)
            self.state.update("USB", ("DIL_T", mid))
            self.state.update("PCIE", ("framecount", 1000))
            print "Setting DIL_T to %d" % mid
            self.start_PFGIT_scan(True, 25000)
            self.scannerWidget.accurateScan.blockSignals(True)
            self.scannerWidget.accurateScan.setChecked(True)
            self.scannerWidget.accurateScan.blockSignals(False)
            self.status = "preparing_scan"

    def on_new_reflectogramm(self, pcie_dev_response):
        data = pcie_dev_response.data
        data = data[:pcie_dev_response.framelength]
        self.dragonplot.myplot(data)
        if self.status == "waiting":
            self.on_wait(data)
        elif self.status == "searching":
            self.on_search(data)
        elif self.status == "scanning":
            self.on_scan(pcie_dev_response)
        elif self.status == "idle":
            pass

    def change_scan_time(self):
        framelength = self.pcieWidget.framelength.value()
        framecount = self.pcieWidget.framecount.value()
        ndot = self.DILTScannerWidget.nsteps.value()
        time = 2 * framelength * framecount * ndot / 133000000
        print "Estimated scan time is ", time, " seconds"
        self.setDIL_T_scan_time.emit(time)


    def enablePFGITscanner(self, val):
        self.DILTScannerWidget.setEnabled(not val)
        self.scannerWidget.setEnabled(val)
        if val:
            print "scanning with PFGIT"
            if self.status == "scanning":
                self.start_DILT_scan(False)
            self.collector.setSpectraLength(self.PFGITscanner.ndot)
        else:
            print "scanning with DILT"
            self.collector.setSpectraLength(self.DIL_Tscanner.ndot)
            if self.status == "scanning":
                self.startaccuratetimescan(False)


    def saveView(self):
        savepath = "/home/dts050511/dumps/" + datetime.now().isoformat().replace(":", "-") + ".png"
        QtGui.QPixmap.grabWidget(self).save(savepath)


    def timerEvent(self, timer):
        if timer.timerId() == self.measuretimer:
            self.usbMeasure.emit()

    def start_PFGIT_scan(self, val, wait_time=5000):
        if val:
            self.state.update("USB", ("PFGI_TscanAmp", self.PFGITscanner.bot))
            self.conttimer = QtCore.QTimer()
            self.conttimer.setSingleShot(True)
            self.conttimer.setInterval(wait_time)
            self.conttimer.timeout.connect(self._cont)
            self.conttimer.start()
            print "wait {0} sec..".format(int(wait_time / 1000))

        else:
            print "stopping PFGIT scan"
            if not self.status == "scanning":
                self.conttimer.timeout.disconnect(self._cont)
            else:
                self.status = "idle"

    def start_DILT_scan(self, val):
        if val:
            self.setDIL_T.emit(self.DIL_Tscanner.bot)
            self.conttimer = QtCore.QTimer()
            self.conttimer.setSingleShot(True)
            self.conttimer.setInterval(5000)
            self.conttimer.timeout.connect(self._cont_DILT)
            self.conttimer.start()
            print "wait 5 sec.."

        else:
            print "stopping DILT scan"
            if not self.status == "scanning":
                self.conttimer.timeout.disconnect(self._cont_DILT)
            else:
                self.status = "idle"

    def mouseDoubleClickEvent(self, event):
        widgets = [self.usbWidget]
        if self.plotsOnly:
            for w in widgets:
                w.show()
            self.plotsOnly = False
        else:
            for w in widgets:
                w.hide()
            self.plotsOnly = True

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_F1:
            self.freezeGraphs()
        super(Base, self).keyPressEvent(event)

    def freezeGraphs(self):
        if self.plotsFreezed:
            self.collector.reflectogrammChanged.connect(self.dragonplot.myplot)
            self.collector.spectraOnChipChanged.connect(self.spectraplot.setData)
            self.collector.temperatureCurveChanged.connect(self.temperatureplot.t0)
            self.collector.temperatureCurve2Changed.connect(self.temperatureplot.t1)
            self.correlator.measured.connect(self.distanceplot.myplot)
            self.corraverager.measured.connect(self.distanceplot.d2)
        else:
            self.collector.reflectogrammChanged.disconnect(self.dragonplot.myplot)
            self.collector.spectraOnChipChanged.disconnect(self.spectraplot.setData)
            self.collector.temperatureCurveChanged.disconnect(self.temperatureplot.t0)
            self.collector.temperatureCurve2Changed.disconnect(self.temperatureplot.t1)
            self.correlator.measured.disconnect(self.distanceplot.myplot)
            self.corraverager.measured.disconnect(self.distanceplot.d2)

        self.plotsFreezed = not self.plotsFreezed

    def _cont(self):
        print "started scanning with PFGIT"
        self.status = "scanning"
        self.laserscanner = "PFGIT"
        self.collector.clear()
        self.PFGITscanner.reset()
        self.collector.setNextIndex(self.PFGITscanner.pos)

    def _cont_DILT(self):
        print "started scanning with DILT"
        self.status = "scanning"
        self.laserscanner = "DIL"
        self.collector.clear()
        self.DIL_Tscanner.reset()
        self.collector.setNextIndex(self.DIL_Tscanner.pos)
        self.startUpScan()

    def process_secondary(self):
        for i in range(4):
            diff = self.secondary.diffs[i] - (i - 1.5) * 20
            self.diffsPlot.myplot(diff, n=i)

        print self.secondary.results.shape
        print self.secondary.results[:,990:1010]
        print self.secondary.results[:,10990:11010]
        print np.sum(self.secondary.results, axis=1)

    def connectCorrectorWidget(self):
        self.correctorWidget.A.valueChanged.connect(self.corrector.setA)
        self.correctorWidget.channel.valueChanged.connect(self.corrector.setChannel)
        self.correctorWidget.enabled.toggled.connect(self.corrector.setEnabled)
        self.correctorWidget.distance.valueChanged.connect(self.corrector.setTargetDistance)

    def connectScanerWidget(self):
        self.scannerWidget.top.valueChanged.connect(self.PFGITscanner.setTop)
        self.scannerWidget.bottom.valueChanged.connect(self.PFGITscanner.setBottom)
        self.scannerWidget.nsteps.valueChanged.connect(self.PFGITscanner.setNdot)
        self.scannerWidget.accurateScan.clicked.connect(self.start_PFGIT_scan)

        self.DILTScannerWidget.top.valueChanged.connect(self.DIL_Tscanner.setTop)
        self.DILTScannerWidget.bottom.valueChanged.connect(self.DIL_Tscanner.setBottom)
        self.DILTScannerWidget.nsteps.valueChanged.connect(self.DIL_Tscanner.setNdot)
        self.DILTScannerWidget.accurateScan.clicked.connect(self.start_DILT_scan)




    def connectOtherWidget(self):
        self.otherWidget.plotChannel.valueChanged.connect(self.spectraplot.setChannel)
        self.otherWidget.saveData.clicked.connect(self.collector.savelastscan)
        self.otherWidget.saveView.clicked.connect(self.saveView)
        self.otherWidget.inverse.toggled.connect(
            self.collector.setInversion)

    def start_FOL2_oscilation(self):
        self.killTimer(self.FOL2timer)
        self.FOL2timer = self.startTimer(self.usbWidget.FOL2_period.value())

    def closeEvent(self, event):
        pass

def setstate(obj, state):
    for key in obj.valueables:
        obj.__dict__[key].setValue(state[key])
    for key in obj.checkables:
        obj.__dict__[key].setChecked(state[key])

def connect_update(obj):
    for valueable in obj.valueables:
        getattr(obj, valueable).valueChanged.connect(
                    lambda value, name=valueable: obj.updated.emit((name, value)))
# made the code work properly, do not really unsderstand default argument.
# here is equivalent:
# code = """obj.{name}.valueChanged.connect(
#               lambda value: obj.updated.emit(('{name}', value)))"""
# eval(code.format(name=valueable), dict(obj=obj))
    for checkable in obj.checkables:
        obj.__dict__[checkable].toggled.connect(
                    lambda checked, name=checkable: obj.updated.emit((name, checked)))

class Updateable:
    def update_state(self, diff):
        self.blockSignals(True)
        if diff[0] in self.valueables:
            self.__dict__[diff[0]].setValue(diff[1])
        if diff[0] in self.checkables:
            self.__dict__[diff[0]].setChecked(diff[1])
        self.blockSignals(False)

BaseUSB, FormUSB = uic.loadUiType("botdrmainwindow.ui")
class USBWidget(BaseUSB, FormUSB, Updateable):
    updated = QtCore.pyqtSignal(tuple)

    valueables = ["A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3",
                 "T1set", "T2set", "T3set", "PFGI_amplitude",
                 "PFGI_pedestal", "PROM_hv", "PROM_shift",
                 "DIL_I", "DIL_T", "PFGI_Tset", "PFGI_TscanAmp",
                 "PFGI_TscanPeriod", "FOL1_I", "FOL1_T", "FOL2_I", "FOL2_T"]
    checkables = ["PC4", "PC5"]

    def __init__(self, state, parent=None):
        super(BaseUSB, self).__init__(parent)
        self.setupUi(self)
        setstate(self, state)
        connect_update(self)

    def showResponse(self, response):
        self.label_t1.setText(str(response.T1))
        self.label_t2.setText(str(response.T2))
        self.label_t3.setText(str(response.T3))
        self.label_r1.setText(str(response.R1))
        self.label_r2.setText(str(response.R2))
        self.label_r3.setText(str(response.R3))
        self.label_f1.setText(str(response.F1))
        self.label_f2.setText(str(response.F2))
        self.label_f3.setText(str(response.F3))
        self.label_19.setText("{0:.2f}".format(response.temp_C))

import pickle




DragomBase, DragonForm = uic.loadUiType("dragon.ui")
class DragonWidget(DragomBase, DragonForm, Updateable):
    updated = QtCore.pyqtSignal(tuple)

    valueables = ["ch1amp", "ch1shift", "ch1count", "ch2amp",
                 "ch2count", "ch2shift", "framelength", "framecount"]
    checkables = []

    def __init__(self, state, parent=None):
        super(DragomBase, self).__init__(parent)
        self.setupUi(self)
        setstate(self, state)
        connect_update(self)


ScannerBase, ScannerForm = uic.loadUiType("timescanner.ui")
class ScannerWidget(ScannerBase, ScannerForm, Updateable):
    dtChanged = QtCore.pyqtSignal(float)
    updated = QtCore.pyqtSignal(tuple)
    valueables = ["top", "bottom", "averageNumber", "nsteps"]
    checkables = []

    def __init__(self, state, parent=None, name="timescaner"):
        super(ScannerBase, self).__init__(parent)
        self.setupUi(self)
        connect_update(self)
        self.textabel = ["position"]
        setstate(self, state)
        dt_emitter = lambda x: self.dtChanged.emit(self.dt())
        for widget in [self.top, self.bottom, self.nsteps]:
            widget.valueChanged.connect(dt_emitter)

    def dt(self):
        return (float(self.top.value() - self.bottom.value()) /
              (self.nsteps.value() - 1))


CorrectorBase, CorrectorForm = uic.loadUiType("distancecorrector.ui")
class CorrectorWidget(CorrectorBase, CorrectorForm, Updateable):
    updated = QtCore.pyqtSignal(tuple)
    valueables = ["channel", "distance", "A"]
    checkables = ["enabled"]
    def __init__(self, state, parent=None):
        super(CorrectorBase, self).__init__(parent)
        self.setupUi(self)
        setstate(self, state)
        connect_update(self)

ZoneBase, ZoneForm = uic.loadUiType("zone.ui")
class SecondaryWidget(ZoneBase, ZoneForm, Updateable):
    updated = QtCore.pyqtSignal(tuple)
    valueables = (['start', 'length'] + ['decay{0}'.format(i) for i in range(4)] +
                  ['level{0}'.format(i) for i in range(3)])
    checkables = []
    def __init__(self, state, parent=None):
        super(ZoneBase, self).__init__(parent)
        self.setupUi(self)
        setstate(self, state)
        connect_update(self)
