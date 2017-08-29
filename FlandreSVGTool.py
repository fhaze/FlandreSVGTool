import os
import sys
from PyQt5 import QtCore, QtWidgets

from PyQt5.QtCore import QThread
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog

from svgToolMainWindow import Ui_MainWindow


class SvgTool(QMainWindow):

    class PresetMode(object):
        def __init__(self, id, name, baseWidth, baseHeight, isMaintainRatio, iosSizeList, androidSizeList, isMultiplier):
            self.id = id
            self.name = name
            self.baseWidth = baseWidth
            self.baseHeight = baseHeight
            self.isMaintainRatio = isMaintainRatio
            self.iosSizeList = iosSizeList
            self.androidSizeList = androidSizeList
            self.isMultiplier = isMultiplier

    iosSizeList = []
    androidSizeList = []
    isMultiplier = True
    inputFiles = []
    modes = [
        PresetMode(0, "Custom", "", "", True, [1, 2, 3], [1, 1.5, 2, 3], True),
        PresetMode(1, "iOS Launcher Icon", "", "", True, [29, 40, 50, 57, 58, 72, 76, 80, 87, 100, 114, 120, 144, 152, 167, 180], [], False),
        PresetMode(2, "Android Launcher Icon", 48, 48, True, [], [1, 1.5, 2, 3], True),
        PresetMode(3, "Store Icon", "", "", True, [1024], [512], False),
        PresetMode(4, "Button Icon", 16, 16, True, [1, 2, 3], [1, 1.5, 2, 3], True),
        PresetMode(5, "Big Button Icon", 24, 24, True, [1, 2, 3], [1, 1.5, 2, 3], True)
    ]

    def __init__(self, parent=None):
        super(SvgTool, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.btnCancel.setEnabled(False)
        self.ui.btnConvert.setEnabled(False)
        self.ui.labelImage.setPixmap(QPixmap("flandre.png"))

        self.ui.btnInputDir.clicked.connect(self.onBtnInputDir)
        self.ui.btnOutputDir.clicked.connect(self.onBtnOutputDir)
        self.ui.lineFilter.textChanged.connect(self.onLineFilterTextChanged)
        self.ui.lineWidth.textChanged.connect(self.onLineWidthChanged)
        self.ui.lineHeight.textChanged.connect(self.onLineHeightChanged)
        self.ui.comboBoxMode.currentIndexChanged.connect(self.onModeChanged)
        self.ui.checkBoxRatio.stateChanged.connect(self.onCheckBoxRatioChanged)
        self.ui.btnConvert.clicked.connect(self.onBtnConvert)
        self.ui.btnCancel.clicked.connect(self.onBtnCancel)

        self.populateModes()

    def onLineFilterTextChanged(self):
        self.refreshInputDirectory()

    def onBtnInputDir(self):
        file = str(QFileDialog.getExistingDirectory(self.ui.centralwidget, "Select input directory"))
        if file:
            self.ui.lineInputDir.setText(file)
            self.refreshInputDirectory()
            if not self.ui.lineOutputDir.text():
                self.ui.lineOutputDir.setText(file)

    def onBtnOutputDir(self):
        file = str(QFileDialog.getExistingDirectory(self.ui.centralwidget, "Select output directory"))
        if file:
            self.ui.lineOutputDir.setText(file)

    def onBtnConvert(self):
        try:
            if self.isMultiplier:
                w = int(self.ui.lineWidth.text())
                h = int(self.ui.lineHeight.text())

                if w <= 0 or h <= 0:
                    errormsg = QtWidgets.QMessageBox(self.ui.centralwidget)
                    errormsg.setIcon(QtWidgets.QMessageBox.Critical)
                    errormsg.setWindowTitle("Error")
                    errormsg.setText("Flandre says:")
                    errormsg.setInformativeText("\"Width and Height must be greater than 0, you moron!\"")
                    errormsg.show()
                    return

        except ValueError:
            errormsg = QtWidgets.QMessageBox(self.ui.centralwidget)
            errormsg.setIcon(QtWidgets.QMessageBox.Critical)
            errormsg.setWindowTitle("Error")
            errormsg.setText("Flandre says:")
            errormsg.setInformativeText("\"Width and Height must be numbers, you moron!\"")
            errormsg.show()
            return

        self.setUiInProgress(True)
        self.convertProgress = SvgConversion(
            self.inputFiles,
            self.ui.checkBoxAndroid.isChecked(),
            self.ui.checkBoxIos.isChecked(),
            self.androidSizeList,
            self.iosSizeList,
            self.ui.lineInputDir.text(),
            self.ui.lineOutputDir.text(),
            float(self.ui.lineWidth.text()),
            float(self.ui.lineHeight.text()),
            self.isMultiplier
        )
        self.convertProgress.sigSetProgress.connect(self.setProgress)
        self.convertProgress.sigSetProgressTotal.connect(self.setProgressTotal)
        self.convertProgress.sigSetStatusMessage.connect(self.setStatusMessage)
        self.convertProgress.sigSetUiInProgress.connect(self.setUiInProgress)
        self.convertProgress.start()

    def onBtnCancel(self):
        self.ui.btnCancel.setEnabled(False)
        self.convertProgress.cancel()

    def onModeChanged(self):
        index = self.ui.comboBoxMode.currentIndex()

        for mode in self.modes:
            if mode.id == index:
                self.ui.checkBoxRatio.setChecked(mode.isMaintainRatio)
                self.ui.lineWidth.setText(str(mode.baseWidth))
                self.ui.lineHeight.setText(str(mode.baseHeight))
                self.isMultiplier = mode.isMultiplier
                self.iosSizeList = mode.iosSizeList
                self.androidSizeList = mode.androidSizeList

                self.ui.checkBoxAndroid.setEnabled(len(mode.androidSizeList) != 0)
                self.ui.checkBoxAndroid.setChecked(len(mode.androidSizeList) != 0)

                self.ui.checkBoxIos.setEnabled(len(mode.iosSizeList) != 0)
                self.ui.checkBoxIos.setChecked(len(mode.iosSizeList) != 0)

                self.ui.checkBoxRatio.setEnabled(self.isMultiplier)
                self.ui.lineWidth.setEnabled(self.isMultiplier)
                self.ui.lineHeight.setEnabled(self.isMultiplier)
                break

    def onLineWidthChanged(self):
        if self.ui.checkBoxRatio.isChecked():
            self.ui.lineHeight.setText(self.ui.lineWidth.text())

    def onLineHeightChanged(self):
        if self.ui.checkBoxRatio.isChecked():
            self.ui.lineWidth.setText(self.ui.lineHeight.text())

    def onCheckBoxRatioChanged(self):
        if self.ui.checkBoxRatio.isChecked():
            self.ui.lineHeight.setText(self.ui.lineWidth.text())

    def setProgress(self, progress):
        self.ui.progressBar.setValue(progress)

    def setProgressTotal(self, progressTotal):
        self.ui.progressBarTotal.setValue(progressTotal)

    def setStatusMessage(self, statusMessage):
        self.ui.statusbar.showMessage(statusMessage)

    def refreshInputDirectory(self):
        if not str(self.ui.lineInputDir.text()):
            return

        self.inputFiles = []
        for file in os.listdir(self.ui.lineInputDir.text()):
            if self.ui.lineFilter.text().upper() in file.upper():
                if file.endswith(".svg"):
                    self.inputFiles.append(file)
        filelen = len(self.inputFiles)
        self.ui.labelFilter.setText("Found {0} svg file(s)".format(filelen))
        if filelen > 0:
            self.ui.btnConvert.setEnabled(True)
        else:
            self.ui.btnConvert.setEnabled(False)

    def setUiInProgress(self, state):
        self.ui.btnCancel.setEnabled(state)
        self.ui.btnConvert.setEnabled(not state)
        self.ui.btnInputDir.setEnabled(not state)
        self.ui.btnOutputDir.setEnabled(not state)

        if self.isMultiplier:
            self.ui.checkBoxRatio.setEnabled(not state)
            self.ui.lineWidth.setEnabled(not state)
            self.ui.lineHeight.setEnabled(not state)

        self.ui.lineFilter.setEnabled(not state)
        self.ui.checkBoxRatio.setEnabled(not state)
        self.ui.checkBoxAndroid.setEnabled(not state)
        self.ui.checkBoxIos.setEnabled(not state)
        self.ui.comboBoxMode.setEnabled(not state)

    def populateModes(self):
        for mode in self.modes:
            self.ui.comboBoxMode.addItem(mode.name, mode.id)


class SvgConversion(QThread):

    sigSetProgress = QtCore.pyqtSignal(float)
    sigSetProgressTotal = QtCore.pyqtSignal(float)
    sigSetStatusMessage = QtCore.pyqtSignal(str)
    sigSetUiInProgress = QtCore.pyqtSignal(bool)

    cancelToken = False

    def __init__(self, inputFiles, convertAndroid, convertIos, androidSizeList, iosSizeList, inputDir, outputDir, baseWidth, baseHeight, isMultiplier):
        super().__init__()
        self.inputFiles = inputFiles
        self.convertAndroid = convertAndroid
        self.convertIos = convertIos
        self.androidSizeList = androidSizeList
        self.iosSizeList = iosSizeList
        self.inputDir = inputDir
        self.outputDir = outputDir
        self.baseWidth = baseWidth
        self.baseHeight = baseHeight
        self.isMultiplier = isMultiplier

    def cancel(self):
        self.cancelToken = True

    def run(self):
        fileCurrent = 0
        fileCount = len(self.inputFiles)

        for file in self.inputFiles:
            if self.cancelToken:
                break

            convertCurrent = 0
            convertCount = 0

            if self.convertAndroid:
                convertCount += len(self.androidSizeList)
            if self.convertIos:
                convertCount += len(self.iosSizeList)

            fileCurrent += 1

            infile = "{0}/{1}".format(self.inputDir, file)
            self.sigSetProgressTotal.emit((fileCurrent / fileCount) * 100)

            if self.convertIos:
                self.sigSetStatusMessage.emit('Converting iOS({0}/{1}): "{2}"'.format(fileCurrent, fileCount, infile))
                for size in self.iosSizeList:
                    if self.cancelToken:
                        break

                    convertCurrent += 1

                    if self.isMultiplier:
                        if size == 3:
                            outfile = "{0}/iOS/Resources/{1}".format(self.outputDir,
                                                                     str.replace(file, ".svg", "@3x.png"))
                        elif size == 2:
                            outfile = "{0}/iOS/Resources/{1}".format(self.outputDir,
                                                                     str.replace(file, ".svg", "@2x.png"))
                        else:
                            outfile = "{0}/iOS/Resources/{1}".format(self.outputDir,
                                                                     str.replace(file, ".svg", ".png"))

                        width = size * int(self.baseWidth)
                        height = size * int(self.baseHeight)
                    else:
                        outfile = "{0}/iOS/Resource/{1}".format(self.outputDir, str.replace(file, ".svg", "_{0}.png".format(str(size))))

                        width = size
                        height = size

                    if os.path.isfile(outfile):
                        os.remove(outfile)

                    self.sigSetProgress.emit((convertCurrent / convertCount) * 100)
                    os.system('svg2png "{0}" -o "{1}" -w {2} -h {3}'.format(infile, outfile, width, height))

            if self.convertAndroid:
                self.sigSetStatusMessage.emit('Converting Droid({0}/{1}): "{2}"'.format(fileCurrent, fileCount, infile))
                for size in self.androidSizeList:
                    if self.cancelToken:
                        break

                    convertCurrent += 1

                    if self.isMultiplier:
                        if size == 3:
                            outfile = "{0}/Droid/Resources/drawable-xxhdpi/{1}".format(self.outputDir,
                                                                                       str.replace(file, ".svg", ".png"))
                        elif size == 2:
                            outfile = "{0}/Droid/Resources/drawable-xhdpi/{1}".format(self.outputDir,
                                                                                      str.replace(file, ".svg", ".png"))
                        elif size == 1.5:
                            outfile = "{0}/Droid/Resources/drawable-hdpi/{1}".format(self.outputDir,
                                                                                     str.replace(file, ".svg", ".png"))
                        else:
                            outfile = "{0}/Droid/Resources/drawable/{1}".format(self.outputDir,
                                                                                str.replace(file, ".svg", ".png"))

                        width = size * self.baseWidth
                        height = size * self.baseHeight
                    else:
                        outfile = "{0}/Droid/Resource/{1}".format(self.outputDir, str.replace(file, ".svg", "_{0}".format(str(size))))

                        width = size
                        height = size

                    if os.path.isfile(outfile):
                        os.remove(outfile)

                    self.sigSetProgress.emit((convertCurrent / convertCount) * 100)
                    os.system('svg2png "{0}" -o "{1}" -w {2} -h {3}'.format(infile, outfile, width, height))

        if self.cancelToken:
            self.sigSetProgress.emit(0)
            self.sigSetProgressTotal.emit(0)
            self.sigSetStatusMessage.emit("Flandre cancelled her job!")
            self.sigSetUiInProgress.emit(False)
            return

        self.sigSetStatusMessage.emit("Flandre finished her job!")
        self.sigSetUiInProgress.emit(False)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SvgTool()
    window.show()
    sys.exit(app.exec_())