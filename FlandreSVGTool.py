import json
import os
import sys
import xml.etree.ElementTree

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
        PresetMode(1, "iOS Launcher Icon", 0, 0, True, [29, 40, 50, 57, 58, 72, 76, 80, 87, 100, 114, 120, 144, 152, 167, 180], [], False),
        PresetMode(2, "Android Launcher Icon", 48, 48, True, [], [1, 1.5, 2, 3], True),
        PresetMode(3, "Store Icon", 0, 0, True, [1024], [512], False),
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
            self.isMultiplier,
            self.ui.checkBoxXcassets.isChecked(),
            self.ui.checkBoxVS.isChecked()
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
        self.ui.checkBoxXcassets.setEnabled(not state)
        self.ui.checkBoxVS.setEnabled(not state)
        self.ui.comboBoxMode.setEnabled(not state)

        if len(self.iosSizeList) == 0:
            self.ui.checkBoxIos.setEnabled(False)
        if len(self.androidSizeList) == 0:
            self.ui.checkBoxAndroid.setEnabled(False)

    def populateModes(self):
        for mode in self.modes:
            self.ui.comboBoxMode.addItem(mode.name, mode.id)


class SvgConversion(QThread):

    sigSetProgress = QtCore.pyqtSignal(float)
    sigSetProgressTotal = QtCore.pyqtSignal(float)
    sigSetStatusMessage = QtCore.pyqtSignal(str)
    sigSetUiInProgress = QtCore.pyqtSignal(bool)

    cancelToken = False

    def __init__(self, inputFiles, convertAndroid, convertIos, androidSizeList, iosSizeList, inputDir, outputDir, baseWidth, baseHeight, isMultiplier, isXCAssets, isUpdateSolution):
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
        self.isXCAssets = isXCAssets
        self.isUpdateSolution = isUpdateSolution

    def cancel(self):
        self.cancelToken = True

    def run(self):
        fileCurrent = 0
        fileCount = len(self.inputFiles)

        self.createDirectories()

        for file in self.inputFiles:
            if self.cancelToken:
                break

            fileWithoutExt = str(file).replace(".svg", "")
            convertCurrent = 0
            convertCount = 0

            if self.convertAndroid:
                convertCount += len(self.androidSizeList)
            if self.convertIos:
                convertCount += len(self.iosSizeList)

            fileCurrent += 1

            infile = "{0}/{1}".format(self.inputDir, file)
            self.sigSetProgressTotal.emit((fileCurrent / fileCount) * 100)
            if self.isXCAssets:
                if self.isMultiplier:
                    contentjson = {
                        'images': [{'idiom': "universal"}],
                        'properties': {'template-rendering-intent': ""},
                        'info': {'version': 1, 'author': "xcode"}
                    }
                else:
                    contentjson = {
                        'images': [],
                        'info': {'version': 1, 'author': "xcode"}
                    }

            if self.convertIos:
                if self.isUpdateSolution:
                    xml.etree.ElementTree.register_namespace("", "http://schemas.microsoft.com/developer/msbuild/2003")
                    iOSSolution = self.findIosSolutionFile()
                    iOSSolutionXml = xml.etree.ElementTree.parse(iOSSolution)
                    root = iOSSolutionXml.getroot()
                    iositemgroup = root.findall("{http://schemas.microsoft.com/developer/msbuild/2003}ItemGroup")[1]

                self.sigSetStatusMessage.emit('Exporting iOS({0}/{1}): "{2}"'.format(fileCurrent, fileCount, infile))
                for size in self.iosSizeList:
                    if self.cancelToken:
                        break

                    convertCurrent += 1

                    if self.isMultiplier:
                        width = size * int(self.baseWidth)
                        height = size * int(self.baseHeight)

                        if size == 3:
                            outfilename = str.replace(file, ".svg", "@3x.png")
                        elif size == 2:
                            outfilename = str.replace(file, ".svg", "@2x.png")
                        else:
                            outfilename = str.replace(file, ".svg", ".png")
                    else:
                        width = size
                        height = size
                        outfilename = "{0}_{1}.png".format(str.replace(file, ".svg", ""), size)

                    if self.isXCAssets:
                        if self.isMultiplier:
                            iosXCAssets = "/Assets.xcassets/{0}.imageset".format(fileWithoutExt)
                            contentjson['images'].append(
                                {'scale': "{0}x".format(size), 'idiom': "universal", "filename": outfilename})
                        else:
                            iosXCAssets = "/Assets.xcassets/{0}.appiconset".format(fileWithoutExt)
                            elems = self.getiosappiconjson(outfilename, size)
                            for elem in elems:
                                contentjson['images'].append(elem)

                        outfile = "{0}/iOS{1}/{2}".format(self.outputDir, iosXCAssets, outfilename)
                        outcontentjson = "{0}/iOS{1}/{2}".format(self.outputDir, iosXCAssets, "Contents.json")

                        if not os.path.exists("{0}/iOS{1}".format(self.outputDir, iosXCAssets)):
                            os.makedirs("{0}/iOS{1}".format(self.outputDir, iosXCAssets))

                        if os.path.exists(outcontentjson):
                            os.remove(outcontentjson)

                        with open(outcontentjson, 'w') as outjson:
                            json.dump(contentjson, outjson)
                    else:
                        outfile = "{0}/iOS/Resources/{1}".format(self.outputDir, outfilename)

                    if self.isUpdateSolution:
                        doInclude = True
                        iosinclude = outfile.split("/iOS/")[1].replace("/", "\\").replace("@", "%40")

                        for item in iositemgroup:
                            if item.attrib["Include"] == iosinclude:
                                doInclude = False
                                break

                        if doInclude:
                            newitem = xml.etree.ElementTree.Element("ImageAsset")
                            newitem.set("Include", outfile.split("/iOS/")[1].replace("/", "\\"))
                            iositemgroup.append(newitem)
                            iOSSolutionXml.write(iOSSolution)

                    if os.path.isfile(outfile):
                        os.remove(outfile)

                    self.sigSetProgress.emit((convertCurrent / convertCount) * 100)
                    os.system('svg2png "{0}" -o "{1}" -w {2} -h {3}'.format(infile, outfile, width, height))

                if self.isXCAssets:
                    doInclude = True
                    ioscontentinclude = outcontentjson.split("/iOS/")[1]

                    for item in iositemgroup:
                        if item.attrib["Include"] == ioscontentinclude:
                            doInclude = False
                            break

                    if doInclude:
                        newitem = xml.etree.ElementTree.Element("ImageAsset")
                        newitem.set("Include", ioscontentinclude.replace("/", "\\"))
                        iositemgroup.append(newitem)
                        iOSSolutionXml.write(iOSSolution)

            if self.convertAndroid:
                if self.isUpdateSolution:
                    xml.etree.ElementTree.register_namespace("", "http://schemas.microsoft.com/developer/msbuild/2003")
                    androidSolution = self.findAndroidSolutionFile()
                    androidSolutionXml = xml.etree.ElementTree.parse(androidSolution)
                    root = androidSolutionXml.getroot()
                    androiditemgroup = root.findall("{http://schemas.microsoft.com/developer/msbuild/2003}ItemGroup")[3]

                self.sigSetStatusMessage.emit('Exporting Droid({0}/{1}): "{2}"'.format(fileCurrent, fileCount, infile))
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
                        outfile = "{0}/Droid/Resources/{1}".format(self.outputDir, str.replace(file, ".svg", "_{0}".format(str(size))))

                        width = size
                        height = size

                    if os.path.isfile(outfile):
                        os.remove(outfile)

                    if self.isUpdateSolution:
                        doInclude = True
                        androidinclude = outfile.split("/Droid/")[1].replace("/", "\\")

                        for item in androiditemgroup:
                            if item.attrib["Include"] == androidinclude:
                                doInclude = False
                                break

                        if doInclude:
                            newitem = xml.etree.ElementTree.Element("AndroidResource")
                            newitem.set("Include", outfile.split("/Droid/")[1].replace("/", "\\"))
                            androiditemgroup.append(newitem)
                            androidSolutionXml.write(androidSolution)

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

    def findAndroidSolutionFile(self):
        for file in os.listdir("{0}/Droid".format(self.outputDir)):
            if file.endswith(".csproj"):
                return "{0}/Droid/{1}".format(self.outputDir, file)

    def findIosSolutionFile(self):
        for file in os.listdir("{0}/iOS".format(self.outputDir)):
            if file.endswith(".csproj"):
                return "{0}/iOS/{1}".format(self.outputDir, file)

    def createDirectories(self):
        directories = [
            "/Droid",
            "/Droid/Resources",
            "/Droid/Resources/drawable",
            "/Droid/Resources/drawable-hdpi",
            "/Droid/Resources/drawable-xhdpi",
            "/Droid/Resources/drawable-xxhdpi",
            "/iOS"
        ]

        if self.isXCAssets:
            directories.append("/iOS/Assets.xcassets")
        else:
            directories.append("/iOS/Resources")

        for directory in directories:
            if not os.path.exists(self.outputDir + directory):
                os.makedirs(self.outputDir + directory)

    def getiosappiconjson(self, filename, size):
        elems = []
        baseelem = {"filename": filename}

        if size == 29:
            newelem = baseelem.copy()
            newelem["size"] = "29x29"
            newelem["scale"] = "1x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

            newelem = baseelem.copy()
            newelem["size"] = "29x29"
            newelem["scale"] = "1x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 40:
            newelem = baseelem.copy()
            newelem["size"] = "40x40"
            newelem["scale"] = "1x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 50:
            newelem = baseelem.copy()
            newelem["size"] = "50x50"
            newelem["scale"] = "1x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 57:
            newelem = baseelem.copy()
            newelem["size"] = "57x57"
            newelem["scale"] = "1x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

        elif size == 58:
            newelem = baseelem.copy()
            newelem["size"] = "29x29"
            newelem["scale"] = "2x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

            newelem = baseelem.copy()
            newelem["size"] = "29x29"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 72:
            newelem = baseelem.copy()
            newelem["size"] = "72x72"
            newelem["scale"] = "1x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 76:
            newelem = baseelem.copy()
            newelem["size"] = "76x76"
            newelem["scale"] = "1x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 80:
            newelem = baseelem.copy()
            newelem["size"] = "40x40"
            newelem["scale"] = "2x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

            newelem = baseelem.copy()
            newelem["size"] = "40x40"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 87:
            newelem = baseelem.copy()
            newelem["size"] = "29x29"
            newelem["scale"] = "3x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

        elif size == 100:
            newelem = baseelem.copy()
            newelem["size"] = "50x50"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 114:
            newelem = baseelem.copy()
            newelem["size"] = "57x57"
            newelem["scale"] = "2x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

        elif size == 120:
            newelem = baseelem.copy()
            newelem["size"] = "40x40"
            newelem["scale"] = "3x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

            newelem = baseelem.copy()
            newelem["size"] = "60x60"
            newelem["scale"] = "2x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

        elif size == 144:
            newelem = baseelem.copy()
            newelem["size"] = "72x72"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 152:
            newelem = baseelem.copy()
            newelem["size"] = "76x76"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 167:
            newelem = baseelem.copy()
            newelem["size"] = "83.5x83.5"
            newelem["scale"] = "2x"
            newelem["idiom"] = "ipad"
            elems.append(newelem)

        elif size == 180:
            newelem = baseelem.copy()
            newelem["size"] = "60x60"
            newelem["scale"] = "3x"
            newelem["idiom"] = "iphone"
            elems.append(newelem)

        return elems

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SvgTool()
    window.show()
    sys.exit(app.exec_())