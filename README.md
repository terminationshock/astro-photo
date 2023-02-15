# AstroPhoto

With this desktop application, you can post-process images taken through a telescope.

## Features

- Take an individual picture or a series of pictures from a USB camera.
- Capture dark images to be subtracted from the light images.
- Align all images using an algorithm to find clusters of bright pixels.
- Stack all images and export the result.

## Details

### Camera menu

The camera stream can be displayed using the _Live stream_ option, which will cause all other menu items to be disabled. To stop the camera stream, uncheck _Live stream_ again.

You can capture light and dark frames by clicking the appropriate menu items. Use the _Series_ option to toggle between capturing a single picture or a series of pictures.

### Frame menu

This menu offers actions related to the currently dispayed frame.

You can save or remove the current picture and navigate through the images.

Click _Fit_ to find the brightest pixel in the current frame and compute the center-of-mass of its pixel cluster. The result will be displayed as a blue marker. You can overwrite the position by clicking on the frame.

### All frames menu

If you hit the _Subtract master dark_ menu item, a master dark is created by adding all previously captured dark frames. Then, this master dark is subtracted from all light images.

With the _Fit_ entry, you can apply the fitting procedure to all frames (see above).

You can _Align_ all frames so that the fitted points will be on top of each other.

The final stacked image is produced with the _Sum_ menu item.

The program stores backups after each step, which you can restore if you click on _Load backup_.

## Dependencies

- Python: [NumPy](https://numpy.org/), [SciPy](https://scipy.org/), [matplotlib](https://matplotlib.org/), [wxPython](https://wxpython.org/), [OpenCV](https://opencv.org/)
- [GNU Fortran compiler](https://gcc.gnu.org/fortran/)

## Run

Build the Fortran helper library first with `make`. Then start the application with `./astrophoto.py`. If your camera is not reachable at `/dev/video0`, you can pass the correct stream index as command line argument.
