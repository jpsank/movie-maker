
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


def constrain_img(im, max_width=None, max_height=None):
    height, width = im.shape[:2]

    if max_height is None:  # height not specified
        max_height = (max_width / width) * height
    elif max_width is None:  # width not specified
        max_width = (max_height / height) * width

    if max_width > width or max_height > height:
        return im

    return cv2.resize(im, (int(max_width), int(max_height)))


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
        self.speed = 0.01

    def __call__(self, *args, **kwargs):
        self.i += self.speed


class PanEffect(Effect):
    def __init__(self, *args):
        super().__init__()
        self.start_x, self.start_y, self.end_x, self.end_y = args

    def __call__(self, image):
        super().__call__()
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
        super().__call__()
        delta_zoom = self.zoom_final - self.zoom_initial
        z = self.zoom_initial + delta_zoom * self.i

        return zoom_img(image, z)


class ResizeEffect(Effect):
    def __init__(self, width=None, height=None):
        super().__init__()
        self.width, self.height = width, height

    def __call__(self, image):
        super().__call__()
        return resize_img(image, self.width, self.height)


class CropEffect(Effect):
    def __init__(self, *args):
        super().__init__()
        self.x, self.y, self.width, self.height = args

    def __call__(self, image):
        super().__call__()
        return image[self.y:self.y+self.height, self.x:self.x+self.width]


class ConstrainEffect(Effect):  # constrain image so that at least one of its dimensions matches those of movie
    def __init__(self, res):
        super().__init__()
        self.res = res

    def __call__(self, image):
        super().__call__()
        height, width = image.shape[:2]

        ratio = width / height
        target_ratio = self.res[0] / self.res[1]
        # image's proportions are wider than screen
        if ratio > target_ratio:
            return resize_img(image, height=self.res[1])
        # image's proportions are taller than screen
        elif ratio < target_ratio:
            return resize_img(image, width=self.res[0])
        # image has same proportions as screen
        else:
            return resize_img(image, *self.res)
