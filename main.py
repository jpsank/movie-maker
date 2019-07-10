import cv2
import numpy as np
from pydub import AudioSegment
import os
import random
import subprocess
import pickle

from config import *
import effects


def execute_cmd(cmd):
    print("\t", "Executing command... >", cmd)
    return subprocess.call(cmd, shell=True)


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
        self.long = False
        self.effects = []

        self.i = 0

    def add_effect(self, effect):
        self.effects.append(effect)

    def set_effects_length(self, length):
        for e in self.effects:
            e.length = length

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
        self.filters = []

    # Magic methods
    def __len__(self):
        return len(self.slides)

    def __iter__(self):
        return self.slides.__iter__()

    def __getitem__(self, item):
        return self.slides[item]

    def __setitem__(self, key, value):
        self.slides[key] = value

    # Adding slides to list
    def add_file(self, path):
        if not all(fil(path) for fil in self.filters):
            return False

        ext = os.path.splitext(path)[1].lower()
        if ext == ".jpg" or ext == ".jpeg":
            self.add_image(path)
        elif ext == ".mp4" or ext == ".mov":
            self.add_video(path)
        else:
            return False
        return True

    def add_image(self, path):
        slide = Slide(ImageClip(path))

        slide.clip.im = effects.constrain_img(slide.clip.im, STORE_RES)

        self.slides.append(slide)

    def add_video(self, path):
        slide = Slide(VideoClip(path))

        slide.add_effect(effects.ConstrainEffect(RESOLUTION))
        slide.add_effect(effects.CropEffect(0, 0, *RESOLUTION))

        self.slides.append(slide)

    # Manipulating slides in list
    def add_image_effects(self):
        for idx, slide in enumerate(self.slides):
            if isinstance(slide.clip, ImageClip):
                even = idx % 2 == 0

                wider, taller = effects.compare_proportions(slide.clip.width, slide.clip.height, STORE_RES)
                slide.long = wider or taller
                if wider:
                    if even:
                        slide.add_effect(effects.PanEffect(0, 0, 1, 0))
                    else:
                        slide.add_effect(effects.PanEffect(1, 0, 0, 0))
                elif taller:
                    if even:
                        slide.add_effect(effects.PanEffect(0, 0, 0, 1))
                    else:
                        slide.add_effect(effects.PanEffect(0, 1, 0, 0))
                else:
                    if even:
                        slide.add_effect(effects.PanEffect(0, 0, random.random(), random.random()))
                        slide.add_effect(effects.ZoomEffect(1, 0.9))
                    else:
                        slide.add_effect(effects.PanEffect(random.random(), random.random(), 0, 0))
                        slide.add_effect(effects.ZoomEffect(0.9, 1))

    def sort(self, key=lambda s: os.stat(s.clip.fp).st_birthtime, reverse=False):
        self.slides = sorted(self.slides, key=key, reverse=reverse)

    # Filters

    def add_filter(self, fil):
        self.filters.append(fil)


class Movie:
    def __init__(self, slide_list, music_fp=MUSIC_FP):
        self.slide_list = slide_list
        self.audio = AudioSegment.from_file(music_fp)

    def export(self, video_out_fp, audio_out_fp):
        video_out = cv2.VideoWriter(video_out_fp, cv2.VideoWriter_fourcc(*'MJPG'), FPS, RESOLUTION)
        audio_out = self.audio

        ms_per_frame = 1/FPS * 1000  # seconds per frame * 1000 => milliseconds per frame
        len_music_ms = len(self.audio)
        loudness_threshold = self.audio.dBFS

        done = False
        slide_idx = 0
        ms = 0
        while slide_idx < len(self.slide_list) and not done:
            slide = self.slide_list[slide_idx]

            # Determine minimum duration of slide
            min_duration = 0
            if isinstance(slide.clip, ImageClip):
                if slide.long:
                    min_duration = MIN_LONG_IMG_DURATION
                else:
                    min_duration = MIN_IMAGE_DURATION
            elif isinstance(slide.clip, VideoClip):
                if slide.clip.video is None:
                    slide.clip.load()
                min_duration = MIN_VIDEO_DURATION
            if MIN_LAST_DURATION is not None and slide_idx == len(self.slide_list)-1:
                min_duration = MIN_LAST_DURATION
            min_duration = min_duration*1000

            print("{} {}/{}".format(slide.clip.fp, slide_idx+1, len(self.slide_list)))

            # Determine actual duration of slide
            duration = 0
            frame_n = 0
            while True:
                frame_n += 1
                duration += ms_per_frame
                print("\t{} milliseconds".format(round(duration, ndigits=1)), end="\r")

                loudness = self.audio[ms+duration: ms+duration+ms_per_frame].dBFS
                if duration >= min_duration and loudness > loudness_threshold:
                    break
                if ms+duration >= len_music_ms:
                    done = True
                    print("\nReached the end of music sample")
                    break
            print()

            # Write slide to output
            slide.set_effects_length(frame_n)
            for n in range(frame_n):
                frame = slide.step()
                video_out.write(frame)
                if slide.clip.is_done():
                    duration = n*ms_per_frame
                    print("\tduration cut short to {} ms".format(round(duration, ndigits=1)))
                    break

            # Write slide audio to output
            if isinstance(slide.clip, VideoClip) and slide.clip.has_audio():
                audio_out = audio_out.overlay(slide.clip.audio[:duration], position=ms)

            # Release slide data from memory
            slide.clip.release()

            ms += duration
            slide_idx += 1

        audio_out = audio_out[:ms]
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
    # slide_list.add_filter(effects.ProximityFilter(slide_list))

    files = list(os.listdir(INPUT_DIR))
    for i, file in enumerate(files):
        print(file, "{}/{}".format(i+1, len(files)))
        path = os.path.join(INPUT_DIR, file)
        good = slide_list.add_file(path)
        if not good:
            print("\tfile not accepted")

    slide_list.sort()
    slide_list.add_image_effects()

    print("Saving slide data...")
    with open(SAVE_FP, "wb") as f:
        pickle.dump(slide_list, f)

movie = Movie(slide_list)


print("Number of slides: {}".format(len(movie.slide_list)))
print("Exporting video and audio...")
movie.export("movie.avi", "audio.wav")

print("Combining and cleaning up...")
movie.combine_movie("movie.avi", "audio.wav", "movie.mkv")

