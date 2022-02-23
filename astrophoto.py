#!/usr/bin/python3

# This file is part of AstroPhoto.
#
# AstroPhoto is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# AstroPhoto is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AstroPhoto.  If not, see <http://www.gnu.org/licenses/>.

import sys
import wx
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.pyplot import imsave
import cv2
import numpy as np
from scipy.ndimage.interpolation import shift
from astrofit import astrofit
import time
import pickle

class AstroFrame:
    FRAME_LIGHT = 0
    FRAME_DARK = 1
    FRAME_SUM = 2
    FRAME_LIVE = 3

    def __init__(self, image, description, frameId):
        self.originalImage = image
        self.description = description
        self.frameId = frameId

        self.data = AstroFrame.brightness(self.originalImage)
        self.width, self.height = self.data.shape
        self.image = self.originalImage.copy()
        self.point = None
        self.offset = (0,0)
        self.movePoint = None
        self.dark = None

    @staticmethod
    def capture(stream, frameId, num=1):
        frames = []
        info = 'LIGHT'
        if frameId == AstroFrame.FRAME_DARK:
            info = 'DARK'

        cap = cv2.VideoCapture(stream)
        for n in range(num):
            ok, image = cap.read()
            if ok:
                frames.append(AstroFrame(image, '%s captured at %s' % (info, time.ctime()), frameId))

        cap.release()
        return frames

    def save(self, filename=None):
        if filename is None:
            filename = '%i.png' % (int(time.time()))
        imsave(filename, self.image)

    @staticmethod
    def brightness(img):
        return (0.2126 * img[...,0] + 0.7152 * img[...,1] + 0.0722 * img[...,2]).transpose()

    def fit(self):
        x, y = -1., -1.
        if self.point is not None:
            x, y = self.point

        x, y = astrofit.fit(self.data, x, y)
        self.point = (x, y)

    def setPoint(self, x, y):
        self.point = float(x) - self.offset[0], float(y) - self.offset[1]

    def getPoint(self):
        if self.point is None:
            return None, None
        return self.point[0] + self.offset[0], self.point[1] + self.offset[1]

    def isLightFrame(self):
        return self.frameId == AstroFrame.FRAME_LIGHT

    def isNotDarkFrame(self):
        return self.frameId != AstroFrame.FRAME_DARK

    def pipeline(self):
        self.image = self.originalImage.copy()

        if self.dark is not None:
            img = np.maximum(0, self.image.astype(np.float64) - self.dark.image.astype(np.float64))
            self.image = img.astype(np.uint8)

        if self.movePoint is not None:
            self.offset = (self.movePoint[0] - self.point[0], self.movePoint[1] - self.point[1])
            for i in range(3):
                self.image[...,i] = shift(self.image[...,i], self.offset[::-1])

    def move(self, point):
        if point is not None:
            if self.point is None:
                self.fit()
            self.movePoint = point
            self.pipeline()

    def subtract(self, dark):
        self.dark = dark
        self.pipeline()

class FramePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.figure = Figure()
        self.figure.set_facecolor('black')
        self.axes = self.figure.add_axes([0,0,1,1])
        self.canvas = FigureCanvas(self, -1, self.figure)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.canvas, 1, wx.EXPAND)
        self.SetSizer(self.sizer)

        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.set_frame_on(False)
        self.Fit()

        self.cursor = wx.Cursor(wx.CURSOR_CROSS)
        self.canvas.SetCursor(self.cursor)

    def draw(self, frame):
        self.clear(draw=False)
        self.axes.imshow(frame.image)

        x, y = frame.getPoint()
        if x is not None and y is not None:
            self.axes.plot([x], [y], color='blue', marker='+', markersize=20)

        self.axes.plot([0,frame.width], [frame.height,frame.height], color='grey', linewidth=2, linestyle='-')
        self.axes.plot([frame.width,frame.width], [0,frame.height], color='grey', linewidth=2, linestyle='-')
        self.axes.margins(0, 0)

        self.figure.set_size_inches((frame.width / self.figure.dpi, frame.height / self.figure.dpi))
        self.canvas.SetMinSize((frame.width, frame.height))
        self.canvas.draw()

    def clear(self, draw=True):
        self.axes.clear()
        self.axes.set_xticks([])
        self.axes.set_yticks([])
        self.axes.set_frame_on(False)
        if draw:
            self.canvas.draw()

def hasFrames(func):
    def inner(self, *args, **kwargs):
        if len(self.frames) > 0:
            func(self, *args, **kwargs)
    return inner

def onlyLightFrame(func):
    def inner(self, *args, **kwargs):
        if self.frames[self.currFrame].isLightFrame():
            func(self, *args, **kwargs)
    return inner

def notDarkFrame(func):
    def inner(self, *args, **kwargs):
        if self.frames[self.currFrame].isNotDarkFrame():
            func(self, *args, **kwargs)
    return inner

def notLive(func):
    def inner(self, *args, **kwargs):
        if not self.itemLive.IsChecked():
            func(self, *args, **kwargs)
    return inner

def drawAfter(func):
    def inner(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.drawFrame()
    return inner

def backupAfter(func):
    def inner(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.saveBackup()
    return inner

def hourglass(func):
    def inner(self, *args, **kwargs):
        self.Enable(False)
        wx.BeginBusyCursor()
        wx.GetApp().Yield()
        func(self, *args, **kwargs)
        self.Enable(True)
        wx.EndBusyCursor()
    return inner

class AstroPhoto(wx.Frame):
    def __init__(self, *args, **kwargs):
        self.source = kwargs.pop('source')
        wx.Frame.__init__(self, *args, **kwargs)

        self.frames = []
        self.currFrame = -1

        self.initUI()

    def initUI(self):
        menubar = wx.MenuBar()

        camMenu = wx.Menu()
        itemLight = wx.MenuItem(camMenu, wx.ID_NEW, 'Capture &light(s)\tCtrl+N')
        itemDark = wx.MenuItem(camMenu, wx.ID_ANY, 'Capture &dark(s)\tCtrl+D')
        self.itemLive = camMenu.AppendCheckItem(0, 'L&ive stream\tCtrl+L')
        camMenu.AppendSeparator()
        camMenu.Append(itemLight)
        camMenu.Append(itemDark)
        self.itemSeries = camMenu.AppendCheckItem(1, '&Series')
        menubar.Append(camMenu, '&Camera')

        frameMenu = wx.Menu()
        itemSave = wx.MenuItem(frameMenu, wx.ID_SAVE, '&Save\tCtrl+S')
        itemClose = wx.MenuItem(frameMenu, wx.ID_CLOSE, '&Remove\tCtrl+W')
        itemPrev = wx.MenuItem(frameMenu, wx.ID_BACKWARD, '&Previous\tCtrl+LEFT')
        itemNext = wx.MenuItem(frameMenu, wx.ID_FORWARD, '&Next\tCtrl+RIGHT')
        itemFit = wx.MenuItem(frameMenu, wx.ID_ANY, '&Fit\tCtrl+Shift+F')
        frameMenu.Append(itemSave)
        frameMenu.Append(itemClose)
        frameMenu.AppendSeparator()
        frameMenu.Append(itemPrev)
        frameMenu.Append(itemNext)
        frameMenu.AppendSeparator()
        frameMenu.Append(itemFit)
        menubar.Append(frameMenu, '&Frame')

        postMenu = wx.Menu()
        itemSub = wx.MenuItem(postMenu, wx.ID_ANY, 'Subtract master &dark\tCtrl+K')
        itemFitAll = wx.MenuItem(postMenu, wx.ID_ANY, '&Fit\tCtrl+F')
        itemAlign = wx.MenuItem(postMenu, wx.ID_ANY, '&Align\tCtrl+A')
        itemSum = wx.MenuItem(postMenu, wx.ID_ANY, '&Sum\tCtrl+T')
        itemLoad = wx.MenuItem(postMenu, wx.ID_OPEN, '&Load backup\tCtrl+O')
        postMenu.Append(itemSub)
        postMenu.Append(itemFitAll)
        postMenu.Append(itemAlign)
        postMenu.Append(itemSum)
        postMenu.AppendSeparator()
        postMenu.Append(itemLoad)
        menubar.Append(postMenu, '&All frames')

        self.Bind(wx.EVT_MENU, self.onCaptureLight, itemLight)
        self.Bind(wx.EVT_MENU, self.onCaptureDark, itemDark)
        self.Bind(wx.EVT_MENU, self.onLive, self.itemLive)
        self.Bind(wx.EVT_MENU, self.onSave, itemSave)
        self.Bind(wx.EVT_MENU, self.onClose, itemClose)
        self.Bind(wx.EVT_MENU, self.onPrev, itemPrev)
        self.Bind(wx.EVT_MENU, self.onNext, itemNext)
        self.Bind(wx.EVT_MENU, self.onFit, itemFit)
        self.Bind(wx.EVT_MENU, self.onSubtractDarks, itemSub)
        self.Bind(wx.EVT_MENU, self.onFitAll, itemFitAll)
        self.Bind(wx.EVT_MENU, self.onAlign, itemAlign)
        self.Bind(wx.EVT_MENU, self.onSum, itemSum)
        self.Bind(wx.EVT_MENU, self.onLoadBackup, itemLoad)

        self.SetMenuBar(menubar)

        self.SetSize((800, 600))
        self.SetTitle('AstroPhoto')
        self.SetBackgroundColour('black')
        self.Centre()

        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetScrollRate(10, 10)
        self.scroll.EnableScrolling(True, True)

        self.status = wx.StatusBar(self)
        self.status.SetFieldsCount(3)
        self.status.SetStatusWidths([50, -1, 150])
        self.status.SetBackgroundColour('black')
        self.status.SetForegroundColour('white')
        self.SetStatusBar(self.status)

        vbox = wx.BoxSizer(wx.VERTICAL)
        self.framepanel = FramePanel(self.scroll)
        vbox.Add(self.framepanel)
        self.framepanel.canvas.mpl_connect('button_press_event', self.onFrameClick)

        self.scroll.SetSizer(vbox)

        self.Show(True)

    def framesById(self, frameId):
        return [n for n in range(len(self.frames)) if self.frames[n].frameId == frameId]

    def addFrames(self, indices):
        comp = np.zeros_like(self.frames[indices[0]].image, dtype=np.float64)
        for n in indices:
            comp += self.frames[n].image
        comp /= len(indices)
        comp = np.round(comp).astype(np.uint8)
        return AstroFrame(comp, 'SUM', AstroFrame.FRAME_SUM)

    def statusInfo(self, text):
        self.status.SetStatusText('', 0)
        self.status.SetStatusText(text, 1)
        self.status.SetStatusText('', 2)
        wx.GetApp().Yield()

    def drawFrame(self, updateStatus=True):
        if len(self.frames) > 0:
            self.framepanel.draw(self.frames[self.currFrame])
            if updateStatus:
                self.status.SetStatusText('%i' % self.currFrame, 0)
                self.status.SetStatusText(self.frames[self.currFrame].description, 1)
                p = self.frames[self.currFrame].point
                if p is not None:
                    self.status.SetStatusText('%3.2f; %3.2f' % p, 2)
        else:
            self.framepanel.clear()
            self.status.SetStatusText('', 0)
            self.status.SetStatusText('', 1)
            self.status.SetStatusText('', 2)
        self.scroll.Layout()

    @drawAfter
    def livePreview(self):
        self.status.SetStatusText('', 0)
        self.status.SetStatusText('LIVE camera %i' % self.source, 1)
        self.status.SetStatusText('', 2)

        cap = cv2.VideoCapture(self.source)
        ok, image = cap.read()
        if ok:
            self.framepanel.draw(AstroFrame(image, 'LIVE', AstroFrame.FRAME_LIVE))
            self.scroll.Layout()

        while ok and self.itemLive.IsChecked():
            ok, image = cap.read()
            if ok:
                self.framepanel.draw(AstroFrame(image, 'LIVE', AstroFrame.FRAME_LIVE))
            cv2.waitKey(50)
            wx.GetApp().Yield()
        cap.release()

    def saveBackup(self):
        with open('backup.dat', 'wb') as f:
            pickle.dump(self.frames, f)

    @notLive
    @drawAfter
    def onLoadBackup(self, e):
        with open('backup.dat', 'rb') as f:
            self.frames = pickle.load(f)
        self.currFrame = 0

    @notLive
    @hasFrames
    @onlyLightFrame
    @drawAfter
    @backupAfter
    def onFrameClick(self, e):
        self.frames[self.currFrame].setPoint(e.x, self.frames[self.currFrame].height - e.y)

    @notLive
    @hasFrames
    @drawAfter
    def onPrev(self, e):
        self.currFrame -= 1
        if self.currFrame < 0:
            self.currFrame = len(self.frames) - 1

    @notLive
    @hasFrames
    @drawAfter
    def onNext(self, e):
        self.currFrame += 1
        if self.currFrame >= len(self.frames):
            self.currFrame = 0

    @notLive
    @hasFrames
    @onlyLightFrame
    @hourglass
    @drawAfter
    @backupAfter
    def onFit(self, e):
        self.statusInfo('Fitting light frame...')
        self.frames[self.currFrame].fit()

    @notLive
    @hasFrames
    @hourglass
    @drawAfter
    @backupAfter
    def onFitAll(self, e):
        previousPoint = None
        for n in self.framesById(AstroFrame.FRAME_LIGHT):
            self.statusInfo('Fitting light frames...')
            if previousPoint is not None:
                self.frames[n].setPoint(*previousPoint)
            self.frames[n].fit()
            self.currFrame = n
            self.drawFrame(False)
            previousPoint = self.frames[n].getPoint()

    @notLive
    @hasFrames
    @hourglass
    @drawAfter
    @backupAfter
    def onAlign(self, e):
        ns = self.framesById(AstroFrame.FRAME_LIGHT)
        for n in ns:
            self.statusInfo('Aligning light frames...')
            self.frames[n].move(self.frames[ns[0]].getPoint())
            self.currFrame = n
            self.drawFrame(False)

    @notLive
    @hasFrames
    @notDarkFrame
    def onSave(self, e):
        saveFileDialog = wx.FileDialog(self, "Save image file", "", "", \
                    "PNG file (*.png)|*.png|JPEG file (*.jpg)|*.jpg", \
                    wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        extensions = ['.png', '.jpg']

        if saveFileDialog.ShowModal() == wx.ID_CANCEL:
            return

        filename = saveFileDialog.GetPath()
        ext = extensions[saveFileDialog.GetFilterIndex()]
        if filename.lower()[-4:] != ext:
            filename += ext
        self.frames[self.currFrame].save(filename)

    @notLive
    @hasFrames
    @drawAfter
    @backupAfter
    def onClose(self, e):
        self.frames.pop(self.currFrame)
        self.currFrame = min(len(self.frames) - 1, self.currFrame)
        if len(self.frames) == 0:
            self.currFrame = -1

    @notLive
    @hourglass
    @drawAfter
    @backupAfter
    def onSum(self, e):
        ns = self.framesById(AstroFrame.FRAME_LIGHT)
        if len(ns) > 0:
            self.currFrame = len(self.frames)
            self.frames.append(self.addFrames(ns))

    @notLive
    @hourglass
    @drawAfter
    @backupAfter
    def onSubtractDarks(self, e):
        ns = self.framesById(AstroFrame.FRAME_DARK)
        if len(ns) > 0:
            self.statusInfo('Creating master dark...')
            dark = self.addFrames(ns)
            for n in self.framesById(AstroFrame.FRAME_LIGHT):
                self.statusInfo('Subtracting master dark...')
                self.frames[n].subtract(dark)
                self.currFrame = n
                self.drawFrame(False)

    @notLive
    @hourglass
    @drawAfter
    @backupAfter
    def onCaptureLight(self, e):
        self.statusInfo('Capturing light frame(s)...')
        num = 1
        if self.itemSeries.IsChecked():
            num = 25
        frames = AstroFrame.capture(self.source, AstroFrame.FRAME_LIGHT, num)
        for frame in frames:
            self.currFrame = len(self.frames)
            self.frames.append(frame)

    @notLive
    @hourglass
    @drawAfter
    @backupAfter
    def onCaptureDark(self, e):
        self.statusInfo('Capturing dark frame(s)...')
        num = 1
        if self.itemSeries.IsChecked():
            num = 10
        frames = AstroFrame.capture(self.source, AstroFrame.FRAME_DARK, num)
        for frame in frames:
            self.currFrame = len(self.frames)
            self.frames.append(frame)

    def onLive(self, e):
        if self.itemLive.IsChecked():
            self.livePreview()

def main():
    ex = wx.App(True, filename='out.log')
    source = 0
    if len(sys.argv) > 1:
        source = int(sys.argv[1])
    AstroPhoto(None, source=source, style=wx.MAXIMIZE | wx.DEFAULT_FRAME_STYLE)
    ex.MainLoop()

if __name__ == '__main__':
    main()
