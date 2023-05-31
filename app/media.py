
import cv2
import numpy as np
from pydub import AudioSegment
import os
import random
from dataclasses import dataclass
from abc import ABC, abstractmethod

from config import *
from app.util import *

class Image(np.ndarray):
    """ Wrapper class for images. """

    def __new__(cls, mat: np.ndarray):
        return mat.view(cls)

    @property
    def width(self) -> int: return self.shape[1]
    
    @property
    def height(self) -> int: return self.shape[0]

    def resize(self, target_width: int = None, target_height: int = None) -> 'Image':
        """
        Resize image to specified width or height, keeping aspect ratio.
        :param target_width: width to resize to, or None to keep proportional to height
        :param target_height: height to resize to, or None to keep proportional to width
        :return: resized image
        """
        if target_height is None:
            # Height not specified; keep proportional to width
            target_height = int((target_width / self.width) * self.height)
        elif target_width is None:
            # Width not specified; keep proportional to height
            target_width = int((target_height / self.height) * self.width)

        return Image(cv2.resize(self, (target_width, target_height)))
    
    def resize_to_contain(self, target_width: int, target_height: int) -> 'Image':
        """ Resize image such that target width and height are contained fittingly within the image. """
        ratio = self.width / self.height
        target_ratio = target_width / target_height
        
        if ratio > target_ratio:
            # Image is wider than target; resize to target height
            return self.resize(target_height=target_height)
        elif ratio < target_ratio:
            # Image is taller than target; resize to target width
            return self.resize(target_width=target_width)
        else:
            # Image is same ratio as target; resize to target
            return self.resize(target_width=target_width, target_height=target_height)

    def crop(self, x, y, width, height) -> 'Image':
        return Image(self[y: y+height, x: x+width])
    
    def crop_middle(self, width, height) -> 'Image':
        return self.crop(int(self.width/2 - width/2), int(self.height/2 - height/2), width, height)

    def pan(self, percent_x, percent_y, target_width, target_height) -> 'Image':
        startx = int(percent_x * (self.width - target_width))
        starty = int(percent_y * (self.height - target_height))
        return self.crop(startx, starty, target_width, target_height)

    def zoom(self, scale) -> 'Image':
        # Increase size of image
        bigger = self.resize(int(self.width / scale), int(self.height / scale))

        # Crop to original size (centered)
        return bigger.crop(
            int(bigger.width/2 - self.width/2), int(bigger.height/2 - self.height/2), self.width, self.height)
        
    def rotate(self, angle) -> 'Image':
        M = cv2.getRotationMatrix2D((self.width/2, self.height/2), angle, 1)
        return Image(cv2.warpAffine(self, M, (self.width, self.height)))
        
    def grayscale(self) -> 'Image':
        return Image(cv2.cvtColor(self.mat, cv2.COLOR_BGR2GRAY))
    
    def blur(self, kernel_size) -> 'Image':
        return Image(cv2.blur(self, (kernel_size, kernel_size)))
    
    def sharpen(self) -> 'Image':
        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
        return Image(cv2.filter2D(self, -1, kernel))
    
    def add_noise(self, amount) -> 'Image':
        noise = np.random.randint(0, 255, (self.height, self.width))
        return Image(cv2.addWeighted(self, 1 - amount, noise, amount, 0))
    
    def add_text(self, text, x, y, font=cv2.FONT_HERSHEY_SIMPLEX, font_scale=1, color=(0,0,0), thickness=2) -> 'Image':
        return Image(cv2.putText(self, text, (x,y), font, font_scale, color, thickness, cv2.LINE_AA))
    
    def add_border(self, color=(0,0,0), thickness=2) -> 'Image':
        return Image(
            cv2.copyMakeBorder(self, thickness, thickness, thickness, thickness, cv2.BORDER_CONSTANT, value=color))
    
    def get_var_of_laplacian(self) -> float:
        return cv2.Laplacian(self, cv2.CV_64F).var()
    
    def save(self, path: str):
        cv2.imwrite(path, self)


@dataclass
class MediaFile(ABC):
    """ Abstract base class for image and video files. """

    path: str
    _loaded: bool = False

    @abstractmethod
    def load(self):
        """ Load file data. """
        if self._loaded: return
        self._loaded = True

    @abstractmethod
    def __next__(self) -> Image:
        """ For streaming; return next frame. """
        pass

    @property
    def name(self) -> str:
        """ Return name of file (without extension). """
        return os.path.splitext(os.path.basename(self.path))[0]

    @property
    def creation_date(self) -> int:
        """ Return creation date of image. """
        return creation_date(self.path)


@dataclass
class ImageFile(MediaFile):
    """ Class for image files. """

    img: Image = None

    def load(self):
        """ Load image from file. """
        super().load()
        self.img = Image(cv2.imread(self.path))
    
    def __next__(self) -> Image:
        """ Return image. """
        assert self._loaded, "Image not loaded"
        return self.img


@dataclass
class VideoFile(MediaFile):
    """ Class for video files. """

    capture: cv2.VideoCapture = None
    audio: AudioSegment = None

    def load(self):
        """ Load video and audio from file. """
        super().load()
        self.capture = cv2.VideoCapture(self.path)
        try:
            self.audio = AudioSegment.from_file(self.path)
        except Exception as e:  # TODO: Handle this better
            print(f"Error loading audio from video {self.path}:", e)

    def __next__(self) -> Image:
        """ Return next frame of video. """
        assert self._loaded, "Video not loaded"
        success, frame = self.capture.read()
        if not success:
            raise StopIteration
        return Image(frame)

    @property
    def width(self) -> int:
        return self.capture.get(cv2.CAP_PROP_FRAME_WIDTH)

    @property
    def height(self) -> int:
        return self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    @property
    def fps(self) -> int:
        return self.capture.get(cv2.CAP_PROP_FPS)
    
    def set_frame(self, frame_num):
        self.capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
    
    def set_time(self, time):
        self.capture.set(cv2.CAP_PROP_POS_MSEC, time)
    
    def set_percent(self, percent):
        time = percent * self.get_duration()
        self.set_time(time)
    
    def get_frame_count(self):
        return self.capture.get(cv2.CAP_PROP_FRAME_COUNT)

    def get_duration(self):
        return self.get_frame_count() / self.fps


def is_image(path: str) -> bool:
    """ Return True if path is image file. """
    return os.path.isfile(path) and os.path.splitext(path)[1] in {".jpg", ".jpeg"}

def is_video(path: str) -> bool:
    """ Return True if path is video file. """
    return os.path.isfile(path) and os.path.splitext(path)[1] in {".mp4", ".mov"}

