#!/usr/bin/python3

import numpy as np
from scipy.optimize import leastsq
from scipy.ndimage.interpolation import shift
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
import matplotlib.pyplot as plt
import wx
import cv2
import time

class AstroFrame:
    FRAME_LIGHT = 0
    FRAME_DARK = 1
    FRAME_SUM = 2

    def __init__(self, image, description, frameId):
        self.original_image = image
        self.description = description
        self.frameId = frameId

        self.data = AstroFrame.brightness(self.original_image)
        self.height, self.width = self.data.shape
        self.image = self.original_image.copy()
        self.point = None
        self.offset = (0,0)
        self.movePoint = None
        self.dark = None

    @staticmethod
    def capture(stream, frameId, num=1):
        frames = []
        info = 'LIGHT'
        if frameId == AstroFrame.FRAME_DARK:
                info = ' DARK'

        cap = cv2.VideoCapture(stream)
        for n in range(num):
            ret, image = cap.read()
            if ret:
                frames.append(AstroFrame(image, '%s captured at %s' % (info, time.ctime()), frameId))

        cap.release()
        return frames

    def save(self, filename=None):
        if filename is None:
            filename = '%i.png' % (int(time.time()))
        plt.imsave(filename, self.image)

    @staticmethod
    def brightness(img):
        return 0.2126 * img[...,0] + 0.7152 * img[...,1] + 0.0722 * img[...,2]

    @staticmethod
    def _gaussian(height, center_x, center_y, width, offset):
        def gauss(x,y):
            return height*np.exp(-(((center_x-x)/width)**2+((center_y-y)/width)**2)) + offset
        return gauss

    def fit(self):
        if self.point is None:
            x, y = np.unravel_index(self.data.argmax(), self.data.shape)
        else:
            x, y = self.point
        height = self.data[int(round(x)),int(round(y))]
        offset = np.mean(self.data)
        params = height, x, y, 5., offset

        errorfunction = lambda p: np.ravel(AstroFrame._gaussian(*p)(*np.indices(self.data.shape)) - self.data)
        p, success = leastsq(errorfunction, params)
        self.point = (p[1], p[2])

    def setPoint(self, x, y):
        self.point = float(x) - self.offset[0], float(y) - self.offset[1]

    def isLightFrame(self):
        return self.frameId == AstroFrame.FRAME_LIGHT

    def pipeline(self):
        self.image = self.original_image.copy()

        if self.dark is not None:
            img = np.maximum(0, self.image.astype(np.float64) - self.dark.image.astype(np.float64))
            self.image = img.astype(np.uint8)

        if self.movePoint is not None:
            if self.point is None:
                self.fit()
            self.offset = (self.movePoint[0] - self.point[0], self.movePoint[1] - self.point[1])
            for i in range(3):
                self.image[...,i] = shift(self.image[...,i], self.offset)

    def move(self, point):
        self.movePoint = point
        self.pipeline()

    def subtract(self, dark):
        self.dark = dark
        self.pipeline()

    def getDrawPoint(self):
        if self.point is None:
            return None
        return self.point[0] + self.offset[0], self.point[1] + self.offset[1]

class FramePanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)
        self.figure = Figure()
        self.axes = self.figure.add_axes([0,0,1,1], facecolor='black')
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

        point = frame.getDrawPoint()
        if point is not None:
            self.axes.plot([point[1]], [point[0]], color='blue', marker='+', markersize=20)

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
        if self.frames[self.curr_frame].isLightFrame():
            func(self, *args, **kwargs)
    return inner

def drawAfter(func):
    def inner(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.drawFrame()
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
        wx.Frame.__init__(self, *args, **kwargs)
        self.frames = []
        self.curr_frame = -1
        self.source = 0

        self.initUI()

    def initUI(self):
        menubar = wx.MenuBar()

        camMenu = wx.Menu()
        item_cam = wx.MenuItem(camMenu, wx.ID_ANY, '&Toggle stream\tCtrl+C')
        item_light = wx.MenuItem(camMenu, wx.ID_NEW, 'Capture &light(s)\tCtrl+N')
        item_dark = wx.MenuItem(camMenu, wx.ID_ANY, 'Capture &dark(s)\tCtrl+D')
        camMenu.Append(item_cam)
        camMenu.AppendSeparator()
        camMenu.Append(item_light)
        camMenu.Append(item_dark)
        self.menuSeries = camMenu.AppendCheckItem(0, '&Series')
        menubar.Append(camMenu, '&Camera')

        frameMenu = wx.Menu()
        item_save = wx.MenuItem(frameMenu, wx.ID_SAVE, '&Save\tCtrl+S')
        item_close = wx.MenuItem(frameMenu, wx.ID_CLOSE, '&Remove\tCtrl+W')
        item_prev = wx.MenuItem(frameMenu, wx.ID_BACKWARD, '&Previous\tCtrl+LEFT')
        item_next = wx.MenuItem(frameMenu, wx.ID_FORWARD, '&Next\tCtrl+RIGHT')
        item_fit = wx.MenuItem(frameMenu, wx.ID_ANY, '&Fit\tCtrl+Shift+F')
        frameMenu.Append(item_save)
        frameMenu.Append(item_close)
        frameMenu.AppendSeparator()
        frameMenu.Append(item_prev)
        frameMenu.Append(item_next)
        frameMenu.AppendSeparator()
        frameMenu.Append(item_fit)
        menubar.Append(frameMenu, '&Frame')

        postMenu = wx.Menu()
        item_sub = wx.MenuItem(postMenu, wx.ID_ANY, 'Subtract master &dark\tCtrl+K')
        item_fit_all = wx.MenuItem(postMenu, wx.ID_ANY, '&Fit\tCtrl+F')
        item_align = wx.MenuItem(postMenu, wx.ID_ANY, '&Align\tCtrl+A')
        item_sum = wx.MenuItem(postMenu, wx.ID_ANY, '&Sum\tCtrl+T')
        postMenu.Append(item_sub)
        postMenu.Append(item_fit_all)
        postMenu.Append(item_align)
        postMenu.Append(item_sum)
        menubar.Append(postMenu, '&All frames')

        self.Bind(wx.EVT_MENU, self.onSourceSelect, item_cam)
        self.Bind(wx.EVT_MENU, self.onSave, item_save)
        self.Bind(wx.EVT_MENU, self.onClose, item_close)
        self.Bind(wx.EVT_MENU, self.onCaptureLight, item_light)
        self.Bind(wx.EVT_MENU, self.onCaptureDark, item_dark)
        self.Bind(wx.EVT_MENU, self.onPrev, item_prev)
        self.Bind(wx.EVT_MENU, self.onNext, item_next)
        self.Bind(wx.EVT_MENU, self.onSubtractDarks, item_sub)
        self.Bind(wx.EVT_MENU, self.onFit, item_fit)
        self.Bind(wx.EVT_MENU, self.onFitAll, item_fit_all)
        self.Bind(wx.EVT_MENU, self.onAlign, item_align)
        self.Bind(wx.EVT_MENU, self.onSum, item_sum)

        self.SetMenuBar(menubar)

        self.SetSize((800, 600))
        self.SetTitle('AstroPhoto')
        self.Centre()

        self.scroll = wx.ScrolledWindow(self)
        self.scroll.SetScrollRate(10, 10)
        self.scroll.EnableScrolling(True, True)

        self.status = wx.StatusBar(self)
        self.status.SetFieldsCount(3)
        self.status.SetStatusWidths([50, -1, 150])
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

    def drawFrame(self):
        if len(self.frames) > 0:
            self.framepanel.draw(self.frames[self.curr_frame])
            self.status.SetStatusText('%i' % self.curr_frame, 0)
            self.status.SetStatusText(self.frames[self.curr_frame].description, 1)
            p = self.frames[self.curr_frame].point
            if p is not None:
                self.status.SetStatusText('%3.2f; %3.2f' % p, 2)
        else:
            self.framepanel.clear()
            self.status.SetStatusText('', 0)
            self.status.SetStatusText('', 1)
            self.status.SetStatusText('', 2)
        self.scroll.Layout()

    @hasFrames
    @onlyLightFrame
    @drawAfter
    def onFrameClick(self, e):
        self.frames[self.curr_frame].setPoint(self.frames[self.curr_frame].height - e.y, e.x)

    @hasFrames
    @drawAfter
    def onPrev(self, e):
        self.curr_frame -= 1
        if self.curr_frame < 0:
            self.curr_frame = len(self.frames) - 1

    @hasFrames
    @drawAfter
    def onNext(self, e):
        self.curr_frame += 1
        if self.curr_frame >= len(self.frames):
            self.curr_frame = 0

    @hasFrames
    @onlyLightFrame
    @hourglass
    @drawAfter
    def onFit(self, e):
        self.statusInfo('Fitting light frame...')
        self.frames[self.curr_frame].fit()

    @hasFrames
    @hourglass
    @drawAfter
    def onFitAll(self, e):
        for n in self.framesById(AstroFrame.FRAME_LIGHT):
            self.statusInfo('Fitting light frames...')
            self.frames[n].fit()
            self.curr_frame = n
            self.drawFrame()

    @hasFrames
    @hourglass
    @drawAfter
    def onAlign(self, e):
        ns = self.framesById(AstroFrame.FRAME_LIGHT)
        for n in ns:
            self.statusInfo('Aligning light frames...')
            self.frames[n].move(self.frames[ns[0]].point)
            self.curr_frame = n
            self.drawFrame()

    @hasFrames
    def onSave(self, e):
        saveFileDialog = wx.FileDialog(self, "Save image file", "", "", \
                    "JPEG file (*.jpg)|*.jpg|PNG file (*.png)|*.png", \
                    wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        extensions = ['.jpg', '.png']

        if saveFileDialog.ShowModal() == wx.ID_CANCEL:
            return

        filename = saveFileDialog.GetPath()
        ext = extensions[saveFileDialog.GetFilterIndex()]
        if filename.lower()[-4:] != ext:
            filename += ext
        self.frames[self.curr_frame].save(filename)

    @hasFrames
    @drawAfter
    def onClose(self, e):
        self.frames.pop(self.curr_frame)
        self.curr_frame = min(len(self.frames) - 1, self.curr_frame)
        if len(self.frames) == 0:
            self.curr_frame = -1

    @hourglass
    @drawAfter
    def onSum(self, e):
        ns = self.framesById(AstroFrame.FRAME_LIGHT)
        if len(ns) > 0:
            self.curr_frame = len(self.frames)
            self.frames.append(self.addFrames(ns))

    @hourglass
    @drawAfter
    def onSubtractDarks(self, e):
        ns = self.framesById(AstroFrame.FRAME_DARK)
        if len(ns) > 0:
            self.statusInfo('Creating master dark...')
            dark = self.addFrames(ns)
            for n in self.framesById(AstroFrame.FRAME_LIGHT):
                self.statusInfo('Subtracting master dark...')
                self.frames[n].subtract(dark)
                self.curr_frame = n
                self.drawFrame()

    def onSourceSelect(self, e):
        self.source = 1 - self.source

    @hourglass
    @drawAfter
    def onCaptureLight(self, e):
        self.statusInfo('Capturing light frame(s)...')
        num = 1
        if self.menuSeries.IsChecked():
            num = 10
        frames = AstroFrame.capture(self.source, AstroFrame.FRAME_LIGHT, num)
        for frame in frames:
            self.curr_frame = len(self.frames)
            self.frames.append(frame)

    @hourglass
    @drawAfter
    def onCaptureDark(self, e):
        self.statusInfo('Capturing dark frame(s)...')
        num = 1
        if self.menuSeries.IsChecked():
            num = 10
        frames = AstroFrame.capture(self.source, AstroFrame.FRAME_DARK, num)
        for frame in frames:
            self.curr_frame = len(self.frames)
            self.frames.append(frame)

def main():
    ex = wx.App()
    AstroPhoto(None, style=wx.MAXIMIZE | wx.DEFAULT_FRAME_STYLE)
    ex.MainLoop()

if __name__ == '__main__':
    main()
