
import numpy as np
from moviepy.editor import *
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

        self.scroll = False
        self.clip = None

    def resize(self):
        movie_width, movie_height = self.resolution
        width, height = self.clip.size

        if width > movie_width and height > movie_height:
            if width > height:
                self.clip = self.clip.resize(height=movie_height)
            else:
                self.clip = self.clip.resize(width=movie_width)
        else:
            if width > height:
                self.clip = self.clip.resize(height=movie_height)
            else:
                self.clip = self.clip.resize(width=movie_width)

        width, height = self.clip.size
        if width > movie_width:
            self.scroll = True
            self.clip = vfx.scroll(self.clip, w=movie_width, h=movie_height, x_speed=100)
        elif height > movie_height:
            self.scroll = True
            self.clip = vfx.scroll(self.clip, w=movie_width, h=movie_height, y_speed=100)

    def set_duration(self, s):
        self.clip = self.clip.set_duration(s)


class ImageSlide(Slide):
    def __init__(self, fp, resolution):
        super().__init__(fp, resolution)

        self.clip = ImageClip(self.fp)

        self.resize()


class VideoSlide(Slide):
    def __init__(self, fp, resolution):
        super().__init__(fp, resolution)

        self.clip = VideoFileClip(self.fp)

        self.resize()

    def get_audio(self):
        return self.clip.audio


class Movie:
    def __init__(self, resolution=(640, 480), music_fp=MUSIC_FP):
        self.slide_list = []
        self.resolution = resolution
        self.music_fp = music_fp

        self.music_audio = AudioFileClip(self.music_fp)

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
        image = ImageSlide(fp, self.resolution)
        self.slide_list.append(image)
        return True

    def add_video(self, fp):
        if self.check_last_same_time(fp):
            return False
        video = VideoSlide(fp, self.resolution)
        self.slide_list.append(video)
        return True

    def export(self, out_fp, min_image_duration=0.3, min_long_img_duration=1, min_video_duration=2):

        music_array = np.mean(self.music_audio.to_soundarray(), 1)
        loudness_threshold = np.mean(music_array[music_array > 0])
        print(loudness_threshold)

        slide_idx = 0
        current_duration = 0
        for loudness in music_array:
            if slide_idx >= len(self.slide_list):
                print("Finished")
                break

            current_slide = self.slide_list[slide_idx]

            time_for_next = False

            if isinstance(current_slide, ImageSlide):
                if loudness > loudness_threshold:
                    if current_slide.scroll:
                        if current_duration > min_long_img_duration:
                            time_for_next = True
                    else:
                        if current_duration > min_image_duration:
                            time_for_next = True
            elif isinstance(current_slide, VideoSlide):
                if loudness > loudness_threshold and current_duration > min_video_duration:
                    time_for_next = True
                if current_duration >= current_slide.clip.duration:
                    current_duration = current_slide.clip.duration
                    time_for_next = True

            if time_for_next:
                print(current_slide.fp, slide_idx, "done")
                self.slide_list[slide_idx].set_duration(current_duration)

                slide_idx += 1
                current_duration = 0
            else:
                current_duration += 1 / self.music_audio.fps

        clips_list = [s.clip for s in self.slide_list]

        video = concatenate_videoclips(clips_list)
        audio = CompositeAudioClip([video.audio, self.music_audio.set_duration(video.duration)])
        audio = afx.audio_fadeout(audio, 0.5)

        video = video.set_audio(audio)
        video.write_videofile(out_fp, codec="libx264", audio_codec="aac")


movie = Movie()

if os.path.exists(SAVE_FP):
    print("Loading slide data...")
    with open(SAVE_FP, "rb") as f:
        movie.init_from_saved(pickle.load(f))
else:
    print("Building slide data...")

    list_dir = [os.path.join(INPUT_DIR,fn) for fn in os.listdir(INPUT_DIR)]
    list_dir = sorted(list_dir, key=lambda fp: os.stat(fp).st_birthtime)
    # list_dir = list_dir[:50]

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

    # print("Saving slide data...")
    # with open(SAVE_FP, "wb") as f:
    #     pickle.dump(movie, f)


print("Number of slides: {}".format(len(movie.slide_list)))
print("Exporting movie...")
movie.export("movie.mp4")

