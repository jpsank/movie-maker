import cv2
import numpy as np
from pydub import AudioSegment
import os
import random
import subprocess
import pickle

from config import *
import effects


def group_list(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]


def constrain(n, low, high):
    return high if n > high else low if n < low else n


def execute_cmd(cmd):
    print("\t", "Executing command... >", cmd)
    return subprocess.call(cmd, shell=True)


def print_adjust(columns, adjusts, end=None):
    string = [("{:<%s}" % adjusts[i]).format(c) if i < len(adjusts) else c for i, c in enumerate(columns)]
    print(''.join(string), end=end)


class Clip:
    def __init__(self, fp):
        self.fp = fp

    def read(self): pass
    def is_done(self): pass
    def release(self): pass


class ImageClip(Clip):
    def __init__(self, fp):
        super().__init__(fp)

        self.im = cv2.imread(fp)
        self.height, self.width = self.im.shape[:2]

    def read(self):
        return self.im

    def is_done(self):
        return False

    def release(self):
        del self.im


class VideoClip(Clip):
    def __init__(self, fp):
        super().__init__(fp)

        self.video = None
        try:
            self.audio = AudioSegment.from_file(self.fp)
        except Exception as e:
            self.audio = None

        self.next_frame = None

    def load(self):
        self.video = cv2.VideoCapture(self.fp)
        self.read()  # initially set next frame to first frame

    def read(self):  # return frame then set frame to next frame
        frame = self.next_frame
        ret, self.next_frame = self.video.read()
        return frame

    def is_done(self):
        return self.next_frame is None

    def has_audio(self):
        return self.audio is not None

    def release(self):
        self.video.release()
        del self.video
        del self.audio


class Slide:
    def __init__(self, clip):
        self.clip = clip
        self.duration = None
        self.effects = []

        self.i = 0

    def add_effect(self, function):
        self.effects.append(function)

    def step(self):
        if self.clip.is_done():
            return False
        frame = self.clip.read()

        for effect in self.effects:
            frame = effect(frame)

        self.i += 1
        return frame


class SlideList:
    def __init__(self):
        self.slides = []

    def __len__(self):
        return len(self.slides)

    def __iter__(self):
        return self.slides.__iter__()

    def __getitem__(self, item):
        return self.slides[item]

    def __setitem__(self, key, value):
        self.slides[key] = value

    def add_file(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext == ".jpg" or ext == ".jpeg":
            self.add_image(path)
        elif ext == ".mp4" or ext == ".mov":
            self.add_video(path)
        else:
            return False
        return True

    def add_image(self, path):
        even = len(self.slides) % 2 == 0

        slide = Slide(ImageClip(path))

        ratio = slide.clip.width/slide.clip.height
        target_ratio = STORE_RES[0]/STORE_RES[1]
        # image's proportions are wider than screen
        if ratio > target_ratio:
            slide.clip.im = effects.resize_img(slide.clip.im, height=STORE_RES[1])
            if even:
                slide.add_effect(effects.PanEffect(0,0, 1,0))
            else:
                slide.add_effect(effects.PanEffect(1,0, 0,0))
        # image's proportions are taller than screen
        elif ratio < target_ratio:
            slide.clip.im = effects.resize_img(slide.clip.im, width=STORE_RES[0])
            if even:
                slide.add_effect(effects.PanEffect(0,0, 0,1))
            else:
                slide.add_effect(effects.PanEffect(0,1, 0,0))
        # image has same proportions as screen
        else:
            slide.clip.im = effects.resize_img(slide.clip.im, width=STORE_RES[0], height=STORE_RES[1])
            if even:
                slide.add_effect(effects.PanEffect(0,0, random.random(),random.random()))
                slide.add_effect(effects.ZoomEffect(1, 0.8))
            else:
                slide.add_effect(effects.PanEffect(random.random(),random.random(), 0,0))
                slide.add_effect(effects.ZoomEffect(0.8, 1))

        self.slides.append(slide)

    def add_video(self, path):
        slide = Slide(VideoClip(path))

        slide.add_effect(effects.ConstrainEffect(RESOLUTION))
        slide.add_effect(effects.CropEffect(0, 0, *RESOLUTION))

        self.slides.append(slide)

    def sort(self, key=lambda s: os.stat(s.clip.fp).st_birthtime, reverse=False):
        self.slides = sorted(self.slides, key=key, reverse=reverse)


class Movie:
    def __init__(self, slide_list, music_fp=MUSIC_FP):
        self.slide_list = slide_list
        self.audio = AudioSegment.from_file(music_fp)

    def export(self, video_out_fp, audio_out_fp, min_image_duration=0.3, min_long_img_duration=1, min_video_duration=2):
        video_out = cv2.VideoWriter(video_out_fp, cv2.VideoWriter_fourcc(*'MJPG'), FPS, RESOLUTION)

        audio_out = self.audio

        ms_per_frame = 1/FPS * 1000  # seconds per frame * 1000 => milliseconds per frame
        len_music_ms = len(self.audio)
        loudness_threshold = self.audio.dBFS

        def frame_to_ms(f):
            return int(ms_per_frame*f)

        start_frame = 0
        current_frame = 0
        slide_idx = 0
        while slide_idx < len(self.slide_list):
            start_ms = frame_to_ms(start_frame)

            current_ms = frame_to_ms(current_frame)
            next_ms = frame_to_ms(current_frame+1)

            if next_ms >= len_music_ms:
                print("\nReached the end of music sample")
                break

            # print("Getting loudness...")
            current_loudness = self.audio[current_ms: next_ms].dBFS

            current_slide = self.slide_list[slide_idx]
            current_duration_ms = current_ms-start_ms

            print_adjust(["{} {}/{}".format(current_slide.clip.fp, slide_idx+1, len(self.slide_list)),
                          "{} seconds".format(round(current_duration_ms/1000, ndigits=1))],
                         [80],
                         end="\r")

            # print("Stepping slide...")
            time_for_next = False
            frame = None
            current_clip = current_slide.clip
            if isinstance(current_clip, ImageClip):
                frame = current_slide.step()
                if current_loudness > loudness_threshold:
                    if True:
                        if current_duration_ms > min_long_img_duration*1000:
                            time_for_next = True
                    else:
                        if current_duration_ms > min_image_duration*1000:
                            time_for_next = True
            elif isinstance(current_clip, VideoClip):
                if current_clip.video is None:
                    current_clip.load()
                frame = current_slide.step()
                if current_clip.is_done():
                    time_for_next = True
                elif current_loudness > loudness_threshold and current_duration_ms > min_video_duration*1000:
                    time_for_next = True

            if frame is None:
                raise Exception("Frame is invalid")
            if frame.shape[:2][::-1] != RESOLUTION:
                raise Exception("Frame is incorrect shape {}, should be {}".format(frame.shape[:2][::-1], RESOLUTION))

            # print("Writing frame... ")
            video_out.write(frame)
            # print("Done")

            if time_for_next:
                # print("Moving to next slide...")
                if isinstance(current_clip, VideoClip) and current_clip.has_audio():
                    audio_out = audio_out.overlay(current_clip.audio[:current_duration_ms], position=start_ms)

                current_clip.release()
                start_frame = current_frame
                slide_idx += 1

                print()

            current_frame += 1

        video_out.release()

        audio_out.export(audio_out_fp)

    def combine_movie(self, video_fp, audio_fp, out_fp):
        execute_cmd("ffmpeg -y -i {} -r 30 -i {} -filter:a aresample=async=1 -c:a flac -c:v copy {}".format(audio_fp, video_fp, out_fp))

        os.remove(video_fp)
        os.remove(audio_fp)


slide_list = None

if os.path.exists(SAVE_FP):
    print("Loading slide data...")
    with open(SAVE_FP, "rb") as f:
        slide_list = pickle.load(f)
else:
    print("Building slide data...")

    slide_list = SlideList()

    files = list(os.listdir(INPUT_DIR))[:60]
    for i, file in enumerate(files):
        print(file, "{}/{}".format(i+1, len(files)))
        path = os.path.join(INPUT_DIR, file)
        slide_list.add_file(path)

    slide_list.sort()

    print("Saving slide data...")
    with open(SAVE_FP, "wb") as f:
        pickle.dump(slide_list, f)

movie = Movie(slide_list)


print("Number of slides: {}".format(len(movie.slide_list)))
print("Exporting video and audio...")
movie.export("movie.avi", "audio.wav")

print("Combining and cleaning up...")
movie.combine_movie("movie.avi", "audio.wav", "movie.mkv")

