from PyQt4 import Qt, QtCore, QtGui, uic, Qwt5 as Qwt
from collector import Collector
import  pciedevsettings
import plots
from usbdev import USBSettings
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
STARTING_N_SP_DOT = 100
EXTERNAL_STABILIZATION_TIME = 5 * 60
INNER_STABILIZATION_TIME = 1

Base, Form = uic.loadUiType("window.ui")
class MainWindow(Base, Form):
    startUpScan = QtCore.pyqtSignal()
    startDownScan = QtCore.pyqtSignal()
    setPFGI_TscanAmp = QtCore.pyqtSignal(int)
    setDIL_T = QtCore.pyqtSignal(int)
    setDIL_T_scan_time = QtCore.pyqtSignal(int)
    usbMeasure = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(Base, self).__init__(parent)
        self.setupUi(self)


        self.nonthermo = uic.loadUi("nonthermo.ui")
        self.otherWidget = uic.loadUi("other.ui")
        self.scannerSelect = uic.loadUi("scannerselect.ui")
        self.zone = uic.loadUi("zone.ui")
        self.usbWidget = USBWidget()
        self.pcieWidget = DragonWidget()
        self.correctorWidget = CorrectorWidget()
        self.scannerWidget = ScannerWidget()
        self.scannerWidget.groupBox.setTitle("On chip scanner")
        self.DILTScannerWidget = ScannerWidget(name="DIL_Tscanner")
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

        dragonrect = QtCore.QRectF(0, plots.SIGNAL_BOT, 8*6144,
                                   plots.SIGNAL_TOP - plots.SIGNAL_BOT)
        self.dragonplot = plots.Plot(dragonrect, self)
        self.temperatureplot = plots.TempPlot()
        self.spectraplot = plots.SlicePlot(self)
        self.distanceplot = plots.Plot(QtCore.QRectF(0, -500, 8*6144, 2*500),
                                       self, zeroed=True, points=True,
                                       lines=True, levels=[0,0,1000,1000],
                                       ncurves=8)
        self.plots.addWidget(self.spectraplot, 0, 0, 1, 1)
        self.plots.addWidget(self.temperatureplot, 0, 1)
        self.plots.addWidget(self.dragonplot, 1, 1)
        self.plots.addWidget(self.distanceplot, 1, 0, 1, 1)


        self.collector = Collector(65520, self.scannerWidget.nsteps.value())
        self.memoryupdater = MemoryUpdater(self)
        self.correlator = Correlator(self)
        self.maximizer = Maximizer(self)
        self.secondary = secondary.Model()
        self.connectSecondary()
        self.corraverager = Averager(self)
        self.correlator.measured.connect(self.corraverager.appendDistances)
        self.appraverager = Averager(self)
#        self.approximator.measured.connect(self.appraverager.appendDistances)

        self.scanner = scanner.TimeScanner(n=self.scannerWidget.nsteps.value())
        self.DIL_Tscanner = scanner.TimeScanner(n=self.DILTScannerWidget.nsteps.value())
        #self.DIL_Tscanner.changeTemperature.connect(self.usbWorker.setDIL_T)

        self.connectScanerWidget()
        self.connectOtherWidget()
        #TODO: self.pushButton.clicked.connect(CLEAR_TEMP_PLOT)

        self.scanner.setTop(self.scannerWidget.top.value())
        self.scanner.setBottom(self.scannerWidget.bottom.value())
        self.scanner.setNdot(self.scannerWidget.nsteps.value())

        self.DIL_Tscanner.setTop(self.DILTScannerWidget.top.value())
        self.DIL_Tscanner.setBottom(self.DILTScannerWidget.bottom.value())
        self.DIL_Tscanner.setNdot(self.DILTScannerWidget.nsteps.value())


        self.corraverager.setNumber(self.scannerWidget.averageNumber.value())


        self.spectraplot.setChannel(self.otherWidget.plotChannel.value())

        self.corrector = DistanceCorrector(self)
        self.connectCorrectorWidget()
        self.corrector.setTargetDistance(self.correctorWidget.distance.value())
        self.corrector.setA(self.correctorWidget.A.value())
        self.corrector.setEnabled(self.correctorWidget.enabled.isChecked())
        self.corrector.setChannel(self.correctorWidget.channel.value())
        self.corrector.setReaction(self.usbWidget.spinBox_6.value())

        self.maximizer.measured.connect(self.corrector.appendDistances)
        self.corrector.correct.connect(self.usbWidget.spinBox_6.setValue)
        self.usbWidget.spinBox_6.valueChanged.connect(self.corrector.setReaction)



        self.temperatureplot.t0 = lambda v:self.temperatureplot.myplot(v, 0)
        self.temperatureplot.t1 = lambda v:self.temperatureplot.myplot(v, 1)

        self.collector.temperatureCurveChanged.connect(self.temperatureplot.t0)
        self.collector.temperatureCurve2Changed.connect(self.temperatureplot.t1)


        self.collector.setReflectogrammLength(self.pcieWidget.framelength.value())


        self.status = "waiting"
        self.start = time.time()
        self.time_prev = time.time()
        self.search_list = list(range(20000, 40000, 100))
        self.resp_amp = []
        self.laserscanner = "DIL"
        self.enablePulseScanner(True)
        self.scannerSelect.pulse.toggled.connect(self.enablePulseScanner)
        if self.scannerSelect.pulse.isChecked():
            self.maximizer.set_bottom(self.scannerWidget.bottom.value())
            self.maximizer.set_dt(self.scannerWidget.dt())
        else:
            self.maximizer.set_bottom(self.DILTScannerWidget.bottom.value())
            self.maximizer.set_dt(self.DILTScannerWidget.dt())


        #WARNING old code! revision may be needed
        #self.collector.reflectogrammChanged.connect(self.dragonplot.myplot)
        self.collector.spectraOnChipChanged.connect(self.spectraplot.setData)
        #self.collector.spectraChanged.connect(mypeakdetection)

        # This connections must be replaced with clear code
        self.collector.sharedArrayChanged.connect(self.memoryupdater.updateShared)
        self.memoryupdater.updated.connect(self.correlator.update)
        #self.scanner.dtChanged.connect(self.correlator.setDt)
        #self.scanner.dtChanged.connect(self.approximator.setDt)

        self.memoryupdater.updateShared((self.collector.shared, (2,) + self.collector.upScanMatrix.shape))
        #self.correlator.setDt(65535. / self.scannerWidget.nsteps.value())
        self.correlator.setDt(1.)
        self.correlator.measured.connect(self.distanceplot.myplot)

        #self.approximator.measured.connect(lambda t: self.distanceplot.myplot(t, n=1))

        self.scannerWidget.averageNumber.valueChanged.connect(self.corraverager.setNumber)
        self.scannerWidget.averageNumber.valueChanged.connect(self.appraverager.setNumber)

        self.distanceplot.d2 = lambda t: self.distanceplot.myplot(t, n=3)
        self.distanceplot.d3 = lambda t: self.distanceplot.myplot(t, n=4)
        self.corraverager.measured.connect(self.distanceplot.d2)
        #self.appraverager.measured.connect(lambda t: self.distanceplot.myplot(t, n=3))


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
        self.scanner.scanPositionChanged.connect(self.scannerWidget.position.setNum)
        self.scannerWidget.dtChanged.connect(self.maximizer.set_dt)
        self.scannerWidget.bottom.valueChanged.connect(
            self.maximizer.set_bottom)
        self.DILTScannerWidget.dtChanged.connect(self.maximizer.set_dt)
        self.DILTScannerWidget.bottom.valueChanged.connect(
            self.maximizer.set_bottom)

        self.sender = Sender()
        self.correlator.submatrix_processed.connect(
            lambda res: self.sender.send_data(res, 0))


    def on_new_reflectogramm(self, pcie_dev_response):
        data = pcie_dev_response.data
        data = data[:pcie_dev_response.framelength]
        self.dragonplot.myplot(data)
        if self.status == "waiting":
            print "Waiting.."
            if time.time() - self.start > EXTERNAL_STABILIZATION_TIME:
                self.status = "searching"
                self.setPFGI_TscanAmp.emit(32000)
                self.setDIL_T.emit(self.search_list[-1])

        elif self.status == "searching":
            print "Searching.."
            if time.time() - self.time_prev > INNER_STABILIZATION_TIME:
                self.time_prev = time.time()
                try:
                    next_T = self.search_list.pop()
                except IndexError:
                    max_dev, temperature = sorted(self.resp_amp)[-1]
                    self.setDIL_T.emit(temperature)
                    print "Setting DIL_T to %d" % temperature
                    self.startaccuratetimescan(True, 25000)
                    self.scannerWidget.accurateScan.blockSignals(True)
                    self.scannerWidget.accurateScan.setChecked(True)
                    self.scannerWidget.accurateScan.blockSignals(False)
                else:
                    self.resp_amp.append((np.std(data), next_T))
                    self.setDIL_T.emit(self.search_list[-1])
                    print "Setting DIL_T to %d" % self.search_list[-1]

        elif self.status == "scanning":
            self.collector.appendDragonResponse(pcie_dev_response)
            submatrix_to_process = None
            if self.laserscanner == "DIL":
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
            if self.laserscanner == "cont":
                self.collector.appendOnChipTemperature(
                    self.scanner.scan_position)
                self.scanner.scan()
                self.collector.setNextIndex(self.scanner.pos)
                self.setPFGI_TscanAmp.emit(self.scanner.targetT)
                if (self.scanner.top_reached or
                    self.scanner.bottom_reached):
                    submatrix_to_process = self.scanner.lastsubmatrix
            if submatrix_to_process is not None:
#                self.approximator.process_submatrix(submatrix_to_process)
                self.correlator.process_submatrix(submatrix_to_process)
                self.maximizer.process_submatrix(submatrix_to_process)
#                self.chebyshev.process_submatrix(submatrix_to_process)


    def change_scan_time(self):
        framelength = self.pcieWidget.framelength.value()
        framecount = self.pcieWidget.framecount.value()
        ndot = self.DILTScannerWidget.nsteps.value()
        time = 2 * framelength * framecount * ndot / 133000000
        print "Estimated scan time is ", time, " seconds"
        self.setDIL_T_scan_time.emit(time)


    def enablePulseScanner(self, val):
        self.DILTScannerWidget.setEnabled(not val)
        self.scannerWidget.setEnabled(val)
        if val:
            print "scanning with pulse"
            if self.status == "scanning":
                self.start_DILT_scan(False)
            self.collector.setSpectraLength(self.scanner.ndot)
        else:
            print "scanning with cont"
            self.collector.setSpectraLength(self.DIL_Tscanner.ndot)
            if self.status == "scanning":
                self.startaccuratetimescan(False)


    def saveView(self):
        savepath = "/home/dts050511/dumps/" + datetime.now().isoformat().replace(":", "-") + ".png"
        QtGui.QPixmap.grabWidget(self).save(savepath)


    def timerEvent(self, timer):
        if timer.timerId() == self.measuretimer:
            self.usbMeasure.emit()

    def startaccuratetimescan(self, val, wait_time=5000):
        if val:
            self.setPFGI_TscanAmp.emit(self.scanner.bot)
            self.conttimer = QtCore.QTimer()
            self.conttimer.setSingleShot(True)
            self.conttimer.setInterval(wait_time)
            self.conttimer.timeout.connect(self._cont)
            self.conttimer.start()
            self.secondary = secondary.Model()
            self.connectSecondary()
            print "wait 5 sec.."

        else:
            print "stopping pulsed scan"
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
            print "stopping cont scan"
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
        print event.key()
        print "123"
        if event.key() == QtCore.Qt.Key_F1:
            print "F1 pressed"
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
        print "started"
        self.status = "scanning"
        self.laserscanner = "cont"
        self.collector.clear()
        print "cleared"
        self.scanner.reset()
        print "reset"
        self.collector.setNextIndex(self.scanner.pos)

    def _cont_DILT(self):
        print "started"
        self.status = "scanning"
        self.laserscanner = "DIL"
        self.collector.clear()
        self.DIL_Tscanner.reset()
        self.collector.setNextIndex(self.DIL_Tscanner.pos)
        self.startUpScan()

    def connectSecondary(self):
        self.correlator.measured.connect(lambda x: self.secondary(x[0]))
        self.zone.start.setValue(self.secondary.start)
        self.zone.length.setValue(self.secondary.length)
        for i in range(4):
            widget = getattr(self.zone, 'dec%d' % i)
            widget.setValue(self.secondary.decays[i])
        for i in range(3):
            widget = getattr(self.zone, 'lev%d' % i)
            widget.setValue(self.secondary.levels[i])

        self.zone.start.valueChanged.connect(self.secondary.set_start)
        self.zone.length.valueChanged.connect(self.secondary.set_length)
        self.zone.dec0.valueChanged.connect(
            lambda val: self.secondary.set_decay(0, val))
        self.zone.dec1.valueChanged.connect(
            lambda val: self.secondary.set_decay(1, val))
        self.zone.dec2.valueChanged.connect(
            lambda val: self.secondary.set_decay(2, val))
        self.zone.dec3.valueChanged.connect(
            lambda val: self.secondary.set_decay(3, val))
        self.zone.lev0.valueChanged.connect(
            lambda val: self.secondary.set_level(0, val))
        self.zone.lev1.valueChanged.connect(
            lambda val: self.secondary.set_level(1, val))
        self.zone.lev2.valueChanged.connect(
            lambda val: self.secondary.set_level(2, val))

    def connectCorrectorWidget(self):
        self.correctorWidget.A.valueChanged.connect(self.corrector.setA)
        self.correctorWidget.channel.valueChanged.connect(self.corrector.setChannel)
        self.correctorWidget.enabled.toggled.connect(self.corrector.setEnabled)
        self.correctorWidget.distance.valueChanged.connect(self.corrector.setTargetDistance)

    def connectScanerWidget(self):
        self.scannerWidget.top.valueChanged.connect(self.scanner.setTop)
        self.scannerWidget.bottom.valueChanged.connect(self.scanner.setBottom)
        self.scannerWidget.nsteps.valueChanged.connect(self.scanner.setNdot)
        self.scannerWidget.accurateScan.clicked.connect(self.startaccuratetimescan)

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


    def updateUSBSettingsView(self, file):
        widget = self.usbWidget
        widget.spinBox_a1.setValue(file.value("A1").toInt()[0])
        widget.spinBox_a2.setValue(file.value("A2").toInt()[0])
        widget.spinBox_a3.setValue(file.value("A3").toInt()[0])
        widget.spinBox_b1.setValue(file.value("B1").toInt()[0])
        widget.spinBox_b2.setValue(file.value("B2").toInt()[0])
        widget.spinBox_b3.setValue(file.value("B3").toInt()[0])
        widget.spinBox_c1.setValue(file.value("C1").toInt()[0])
        widget.spinBox_c2.setValue(file.value("C2").toInt()[0])
        widget.spinBox_c3.setValue(file.value("C3").toInt()[0])
        widget.spinBox_t1.setValue(file.value("T1set").toInt()[0])
        widget.spinBox_t2.setValue(file.value("T2set").toInt()[0])
        widget.spinBox_t3.setValue(file.value("T3set").toInt()[0])
        widget.checkBox.setChecked(file.value("PC4").toBool())
        widget.checkBox_2.setChecked(file.value("PC5").toBool())
        widget.spinBox.setValue(file.value("PFGI_amplitude").toInt()[0])
        widget.spinBox_2.setValue(file.value("PFGI_pedestal").toInt()[0])
        widget.spinBox_3.setValue(file.value("PROM_hv").toInt()[0])
        widget.spinBox_4.setValue(file.value("PROM_shift").toInt()[0])
        widget.spinBox_5.setValue(file.value("DIL_I").toInt()[0])
        widget.spinBox_6.setValue(file.value("DIL_T").toInt()[0])
        widget.spinBox_7.setValue(file.value("PFGI_Tset").toInt()[0])
        widget.PFGI_TscanAmp.setValue(file.value("PFGI_TscanAmp").toInt()[0])
        widget.spinBox_TScanPeriod.setValue(
            file.value("PFGI_TscanPeriod").toInt()[0])
        widget.spinBox_9.setValue(file.value("FOL1_I").toInt()[0])
        widget.spinBox_10.setValue(file.value("FOL1_T").toInt()[0])
        widget.spinBox_11.setValue(file.value("FOL2_I").toInt()[0])
        widget.spinBox_12.setValue(file.value("FOL2_T").toInt()[0])

    def start_FOL2_oscilation(self):
        self.killTimer(self.FOL2timer)
        self.FOL2timer = self.startTimer(self.usbWidget.FOL2_period.value())

    def closeEvent(self, event):
        self.sender.stop()

BaseUSB, FormUSB = uic.loadUiType("botdrmainwindow.ui")
class USBWidget(BaseUSB, FormUSB):
    valuesChanged = QtCore.pyqtSignal(USBSettings)
    def __init__(self, parent=None):
        super(BaseUSB, self).__init__(parent)
        self.setupUi(self)

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
        self.label_19.setText(str(response.temp_C))


import pickle
DragomBase, DragonForm = uic.loadUiType("dragon.ui")
class DragonWidget(DragomBase, DragonForm):
    valueChanged = QtCore.pyqtSignal(pciedevsettings.PCIESettings)
    def __init__(self, parent=None):
        super(DragomBase, self).__init__(parent)
        self.setupUi(self)
        try:
            self._value = pickle.load(open("pciesettings.ini", "r"))
        except IOError:
            self._value = self.value()
        else:
            for name in ["ch1amp", "ch1shift", "ch1count", "ch2amp",
                         "ch2count", "ch2shift", "framelength", "framecount"]:
                self.__dict__[name].setValue(self._value.__dict__[name])

        for widget in [ self.ch1amp, self.ch1shift, self.ch1count,
                        self.ch2amp, self.ch2count, self.ch2shift,
                        self.framelength, self.framecount]:
            widget.valueChanged.connect(self.rereadValue)
        self.framelength.editingFinished.connect(self.selfCorrect)

    def selfCorrect(self):
        val = self.framelength.value()
        if val % 6 != 0:
            self.framelength.setValue(val // 6 * 6)

    def value(self):
        return pciedevsettings.PCIESettings(
            ch1amp = self.ch1amp.value(),
            ch1count = self.ch1count.value(),
            ch1shift = self.ch1shift.value(),
            ch2amp = self.ch2amp.value(),
            ch2count = self.ch2count.value(),
            ch2shift = self.ch2shift.value(),
            framelength = self.framelength.value(),
            framecount = self.framecount.value())

    def rereadValue(self):
        val = self.value()
        if val != self._value:
            pickle.dump(val, open("pciesettings.ini", "w"))
            self._value = val
            self.valueChanged.emit(val)


ScannerBase, ScannerForm = uic.loadUiType("timescanner.ui")
class ScannerWidget(ScannerBase, ScannerForm):
    dtChanged = QtCore.pyqtSignal(float)
    def __init__(self, parent=None, name="timescaner"):
        super(ScannerBase, self).__init__(parent)
        self.setupUi(self)

        self.valueable = ["top", "bottom", "averageNumber", "nsteps"]
        self.checkable = []
        self.textabel = ["position"]
        self.name = name

        try:
            f = open("%s.ini" % self.name, "r")
        except IOError:
            pass
        else:
            state = pickle.load(f)
            self.setstate(state)
            f.close()

        for widget in [self.__dict__[x] for x in self.valueable]:
            widget.valueChanged.connect(self.savestate)
        for widget in [self.__dict__[x] for x in self.checkable]:
            widget.stateChanged.connect(self.savestate)

        dt_emitter = lambda x: self.dtChanged.emit(self.dt())
        for widget in [self.top, self.bottom, self.nsteps]:
            widget.valueChanged.connect(dt_emitter)

    def dt(self):
        return (float(self.top.value() - self.bottom.value()) /
              (self.nsteps.value() + 1))

    def setstate(self, state):
        for key in self.valueable:
            self.__dict__[key].setValue(state[key])
        for key in self.checkable:
            self.__dict__[key].setChecked(state[key])

    def getstate(self):
        return dict(zip(self.valueable, [self.__dict__[key].value() for key in self.valueable]))

    def savestate(self):
        state = self.getstate()
        with open("%s.ini" % self.name, "w") as f:
            pickle.dump(state, f)




CorrectorBase, CorrectorForm = uic.loadUiType("distancecorrector.ui")
class CorrectorWidget(CorrectorBase, CorrectorForm):
    def __init__(self, parent=None):
        super(CorrectorBase, self).__init__(parent)
        self.setupUi(self)

        self.valueable = ["channel", "distance", "A"]
        self.checkable = ["enabled"]

        try:
            f = open("distancecorrector.ini", "r")
        except IOError:
            pass
        else:
            state = pickle.load(f)
            self.setstate(state)
            f.close()

        for widget in [self.__dict__[x] for x in self.valueable]:
            widget.valueChanged.connect(self.savestate)
        for widget in [self.__dict__[x] for x in self.checkable]:
            widget.stateChanged.connect(self.savestate)


    def setstate(self, state):
        for key in self.valueable:
            self.__dict__[key].setValue(state[key])
        for key in self.checkable:
            self.__dict__[key].setChecked(state[key])

    def getstate(self):
        return {"enabled": self.enabled.isChecked(),
                "channel": self.channel.value(),
                "distance": self.distance.value(),
                "A": self.A.value()
                }

    def savestate(self):
        state = self.getstate()
        with open("distancecorrector.ini", "w") as f:
            pickle.dump(state, f)
