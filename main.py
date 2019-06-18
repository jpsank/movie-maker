import cv2
import numpy as np
from pydub import AudioSegment
import os
import subprocess
import pickle

INPUT_DIR = "input/Thailand"  # directory containing photos (jpg/jpeg) and videos (mp4)
MUSIC_FP = "input/music/748911.mp3"  # audio file for movie music
SAVE_FP = "save.p"  # pickle file to save preprocessed photos and videos so loading is faster for successive runs

FPS = 30


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


class Slide:
    def __init__(self, fp, resolution):
        self.fp = fp
        self.resolution = resolution


class Image(Slide):
    def __init__(self, fp, resolution):
        super().__init__(fp, resolution)

        self.im = cv2.imread(self.fp)
        self.long = False
        self.f = 0

        self.resize()

    def resize(self):
        movie_width, movie_height = self.resolution

        height, width = self.im.shape[:2]
        if width > height:
            width = (movie_height / height) * width
            height = movie_height
            if width < movie_width:
                height = (movie_width/width)*height
                width = movie_width
        else:
            height = (movie_width / width) * height
            width = movie_width
            if height < movie_height:
                width = (movie_height/height)*width
                height = movie_height

        if height > movie_height or width > movie_width:
            self.long = True

        self.im = cv2.resize(self.im, (int(width), int(height)))
        # self.im = self.im[0:movie_height, 0:movie_width]

    def step(self):
        movie_width, movie_height = self.resolution
        height, width = self.im.shape[:2]
        if self.long:
            scroll_per_frame = 0.01

            start_h = int(constrain(self.f*scroll_per_frame,0,1)*(height-movie_height))
            start_w = int(constrain(self.f*scroll_per_frame,0,1)*(width-movie_width))
            roi = self.im[start_h: start_h+movie_height, start_w: start_w+movie_width]
        else:
            roi = self.im
        self.f += 1
        return roi

    def release(self):
        del self.im


class Video(Slide):
    def __init__(self, fp, resolution):
        super().__init__(fp, resolution)

        self.current_frame = None
        self.next_frame = None

        self.video = None
        try:
            self.audio = AudioSegment.from_file(self.fp)
        except Exception as e:
            print("Could not extract audio from {}".format(self.fp))
            self.audio = None

        self.current_f = 0

    def load_video(self):
        self.video = cv2.VideoCapture(self.fp)
        self.get_next_frame()

    def get_next_frame(self):
        ret, frame = self.video.read()
        if ret is True:
            movie_width, movie_height = self.resolution

            height, width = frame.shape[:2]
            if width > height:
                width = (movie_height / height) * width
                height = movie_height
            else:
                height = (movie_width / width) * height
                width = movie_width

            frame = cv2.resize(frame, (int(width), int(height)))
            # frame = frame[0:max_height, 0:max_width]

            scroll_per_frame = 0.01

            start_h = int(constrain(self.current_f * scroll_per_frame, 0, 1) * (height - movie_height))
            start_w = int(constrain(self.current_f * scroll_per_frame, 0, 1) * (width - movie_width))
            roi = frame[start_h: start_h + movie_height, start_w: start_w + movie_width]

            self.next_frame = roi
        else:
            self.next_frame = False

    def step(self):
        self.current_frame = self.next_frame
        self.get_next_frame()

        self.current_f += 1

        return self.current_frame

    def get_current_audio(self):
        if self.has_audio():
            ms_per_frame = 1/FPS * 1000  # milliseconds per frame
            current_audio = self.audio[:int(self.current_f * ms_per_frame)]
            return current_audio
        else:
            return None

    def has_audio(self):
        return self.audio is not None

    def is_done(self):
        return self.next_frame is False

    def release(self):
        self.video.release()
        del self.video
        del self.audio


class Movie:
    def __init__(self, resolution=(640, 480), music_fp=MUSIC_FP):
        self.slide_list = []
        self.resolution = resolution
        self.music_fp = music_fp

        self.music_audio = AudioSegment.from_file(self.music_fp)

    def init_from_saved(self, movie_saved):
        self.slide_list = movie_saved.slide_list
        self.resolution = movie_saved.resolution

    def check_last_same_time(self, fp, margin=20):
        if len(self.slide_list) == 0:
            return False
        last_fp = self.slide_list[-1].fp

        date1 = os.stat(fp).st_birthtime
        date2 = os.stat(last_fp).st_birthtime
        return abs(date1-date2) <= margin  # check whether dates are within ~margin~ seconds of each other

    def add_img(self, fp):
        if self.check_last_same_time(fp):
            return False
        image = Image(fp, self.resolution)
        self.slide_list.append(image)
        return True

    def add_video(self, fp):
        if self.check_last_same_time(fp):
            return False
        video = Video(fp, self.resolution)
        self.slide_list.append(video)
        return True

    def export(self, video_out_fp, audio_out_fp, min_image_duration=0.3, min_long_img_duration=1, min_video_duration=2):
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        video_out = cv2.VideoWriter(video_out_fp, fourcc, FPS, self.resolution)

        audio_out = self.music_audio

        ms_per_frame = 1/FPS * 1000  # seconds per frame * 1000 => milliseconds per frame
        len_music_ms = len(self.music_audio)
        loudness_threshold = self.music_audio.dBFS

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
            current_loudness = self.music_audio[current_ms: next_ms].dBFS

            current_slide = self.slide_list[slide_idx]
            current_duration_ms = current_ms-start_ms

            print_adjust(["{} {}/{}".format(current_slide.fp, slide_idx+1, len(self.slide_list)),
                          "{} seconds".format(round(current_duration_ms/1000, ndigits=1))],
                         [80],
                         end="\r")

            # print("Stepping slide...")
            time_for_next = False
            frame = None
            if isinstance(current_slide, Image):
                frame = current_slide.step()
                if current_loudness > loudness_threshold:
                    if current_slide.long:
                        if current_duration_ms > min_long_img_duration*1000:
                            time_for_next = True
                    else:
                        if current_duration_ms > min_image_duration*1000:
                            time_for_next = True
            elif isinstance(current_slide, Video):
                if current_slide.video is None:
                    current_slide.load_video()
                frame = current_slide.step()
                if current_slide.is_done():
                    time_for_next = True
                elif current_loudness > loudness_threshold and current_duration_ms > min_video_duration*1000:
                    time_for_next = True

            if frame is None:
                raise Exception("Frame is invalid")
            if frame.shape[:2][::-1] != self.resolution:
                raise Exception("Frame is incorrect shape {}, should be {}".format(frame.shape[:2][::-1],self.resolution))

            # print("Writing frame... ")
            video_out.write(frame)
            # print("Done")

            if time_for_next:
                # print("Moving to next slide...")
                if isinstance(current_slide, Video) and current_slide.has_audio():
                    audio_out = audio_out.overlay(current_slide.audio[:current_duration_ms], position=start_ms)

                current_slide.release()
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


movie = Movie()

if os.path.exists(SAVE_FP):
    print("Loading slide data...")
    with open(SAVE_FP, "rb") as f:
        movie.init_from_saved(pickle.load(f))
else:
    print("Building slide data...")

    list_dir = [os.path.join(INPUT_DIR,fn) for fn in os.listdir(INPUT_DIR)]
    list_dir = sorted(list_dir, key=lambda fp: os.stat(fp).st_birthtime)
    # list_dir = list_dir[:100]

    for i,fp in enumerate(list_dir):
        ext = os.path.splitext(fp)[1].lower()
        if ext.endswith(".jpg") or ext.endswith(".jpeg"):
            print("Adding image", fp, "{}/{}".format(i+1,len(list_dir)))
            if movie.add_img(fp) is False:
                print("Rejected")
        elif ext.endswith(".mp4") or ext.endswith("mov"):
            print("Adding video", fp, "{}/{}".format(i+1,len(list_dir)))
            if movie.add_video(fp) is False:
                print("Rejected")

    print("Saving slide data...")
    with open(SAVE_FP, "wb") as f:
        pickle.dump(movie, f)


print("Number of slides: {}".format(len(movie.slide_list)))
print("Exporting video and audio...")
movie.export("movie.avi", "audio.wav")

print("Combining and cleaning up...")
movie.combine_movie("movie.avi", "audio.wav", "movie.mkv")

