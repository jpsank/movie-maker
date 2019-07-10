
import os
from config import *
import cv2


def pan_img(im, percent_x, percent_y, target_width, target_height):
    orig_height, orig_width = im.shape[:2]

    startx = int(percent_x * (orig_width - target_width))
    starty = int(percent_y * (orig_height - target_height))

    res = im[starty: starty + target_height, startx: startx + target_width]
    return res


def zoom_img(im, scale):
    orig_height, orig_width = im.shape[:2]
    res = cv2.resize(im, (int(orig_width/scale), int(orig_height/scale)))

    height, width = res.shape[:2]
    x, y = width/2, height/2
    res = res[int(y - orig_height/2): int(y + orig_height/2),
          int(x - orig_width/2): int(x + orig_width/2)]

    return res


def compare_proportions(width, height, resolution):
    ratio = width / height
    target_ratio = resolution[0] / resolution[1]

    wider, taller = False, False
    if ratio > target_ratio:
        wider = True
    elif ratio < target_ratio:
        taller = True
    return wider, taller


def constrain_img(im, resolution):
    height, width = im.shape[:2]

    wider, taller = compare_proportions(width, height, resolution)
    if wider:
        return resize_img(im, height=resolution[1])
    elif taller:
        return resize_img(im, width=resolution[0])
    else:
        return resize_img(im, *resolution)


def resize_img(im, width=None, height=None):
    h, w = im.shape[:2]

    if height is None:  # height not specified; keep proportional to width
        height = (width / w) * h
    elif width is None:  # width not specified; keep proportional to height
        width = (height / h) * w

    return cv2.resize(im, (int(width), int(height)))


class Effect:
    def __init__(self):
        self.i = 0
        self.length = 100  # length of effect in frames

    def update(self):
        self.i += 1/self.length
        self.i = 1 if self.i > 1 else self.i

    def __call__(self, *args, **kwargs): pass


class PanEffect(Effect):
    def __init__(self, *args):
        super().__init__()
        self.start_x, self.start_y, self.end_x, self.end_y = args

    def __call__(self, image):
        self.update()
        delta_pan_x = self.end_x - self.start_x
        pan_x = self.start_x + delta_pan_x * self.i
        delta_pan_y = self.end_y - self.start_y
        pan_y = self.start_y + delta_pan_y * self.i

        return pan_img(image, pan_x, pan_y, *RESOLUTION)


class ZoomEffect(Effect):
    def __init__(self, *args):
        super().__init__()
        self.zoom_initial, self.zoom_final = args

    def __call__(self, image):
        self.update()
        delta_zoom = self.zoom_final - self.zoom_initial
        z = self.zoom_initial + delta_zoom * self.i

        return zoom_img(image, z)


class ResizeEffect(Effect):
    def __init__(self, width=None, height=None):
        super().__init__()
        self.width, self.height = width, height

    def __call__(self, image):
        self.update()
        return resize_img(image, self.width, self.height)


class CropEffect(Effect):
    def __init__(self, *args):
        super().__init__()
        self.x, self.y, self.width, self.height = args

    def __call__(self, image):
        self.update()
        return image[self.y:self.y+self.height, self.x:self.x+self.width]


class ConstrainEffect(Effect):  # constrain image so that at least one of its dimensions matches those of movie
    def __init__(self, resolution):
        super().__init__()
        self.resolution = resolution

    def __call__(self, image):
        self.update()
        return constrain_img(image, self.resolution)


class Filter:
    def __init__(self, parent):
        self.parent = parent

    def __call__(self, path):
        return True


class ProximityFilter(Filter):
    def __init__(self, parent, margin=20):
        super().__init__(parent)
        self.margin = 20

    def __call__(self, path):
        if len(self.parent.slides) == 0:
            return True

        for slide in self.parent.slides:
            stat1 = os.stat(path).st_birthtime
            stat2 = os.stat(slide.clip.fp).st_birthtime
            if abs(stat2-stat1) <= self.margin:
                return False
        return True
