import cv2
import numpy as np
from scipy.io import wavfile
import os, time, re, json
import subprocess
import pickle

INPUT_DIR = "input/Thailand"  # directory containing photos (jpg) and videos (mp4)
MUSIC_FP = "input/music/748911.wav"  # audio file (wav) for movie music
SAVE_FP = "save.p"  # pickle file to save preprocessed photos and videos so loading is faster for successive runs


def group_list(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]


def constrain(n, low, high):
    return high if n > high else low if n < low else n


def execute_cmd(cmd):
    print("\t", "Executing command... >", cmd)
    return subprocess.call(cmd, shell=True)


class Image:
    def __init__(self, fp, resolution):
        self.fp = fp
        self.resolution = resolution
        self.im = cv2.imread(self.fp)

        self.resize()

        self.f = 0

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

        self.im = cv2.resize(self.im, (int(width), int(height)))
        self.im = self.im[0:movie_height, 0:movie_width]

    def step(self):
        scroll_per_frame = 0.1
        movie_width, movie_height = self.resolution
        height, width = self.im.shape[:2]

        start_h = int(constrain(self.f*scroll_per_frame,0,1)*(height-movie_height))
        start_w = int(constrain(self.f*scroll_per_frame,0,1)*(width-movie_width))
        roi = self.im[start_h: start_h+movie_height, start_w: start_w+movie_width]

        self.f += 1
        return roi

    def release(self):
        del self.im


class Video:
    def __init__(self, fp, resolution):
        self.fp = fp
        self.resolution = resolution
        self.cap = None

        self.current_frame = None
        self.next_frame = None

        self.audio_fs, self.audio_data = self.load_audio()
        self.current_audio = None

        self.f = 0

    def load_audio(self):
        temp_fp = "temp.wav"

        execute_cmd("ffmpeg -i {} -ab 160k -ac 2 -ar 44100 -vn {}".format(self.fp, temp_fp))

        if os.path.exists(temp_fp):
            fs, data = wavfile.read(temp_fp)

            os.remove(temp_fp)
            return fs, data
        else:
            print("Warning: no audio data for {}".format(self.fp))
            return None, None

    def load_video(self):
        self.cap = cv2.VideoCapture(self.fp)

        self.get_next_frame()

    def get_next_frame(self):
        ret, frame = self.cap.read()
        if ret is True:
            max_width, max_height = self.resolution

            height, width = frame.shape[:2]
            if width > height:
                width = (max_height / height) * width
                height = max_height
            else:
                height = (max_width / width) * height
                width = max_width

            frame = cv2.resize(frame, (int(width), int(height)))
            frame = frame[0:max_height, 0:max_width]

            self.next_frame = frame
        else:
            self.next_frame = False

    def step(self, fps=30):
        if self.has_audio():
            samples_per_frame = int(1/fps * self.audio_fs)
            self.current_audio = self.audio_data[self.f*samples_per_frame: (self.f+1)*samples_per_frame]

        self.current_frame = self.next_frame
        self.get_next_frame()

        self.f += 1

        return self.current_frame

    def has_audio(self):
        return self.audio_data is not None

    def is_done(self):
        return self.next_frame is False

    def release(self):
        self.cap.release()


class Movie:
    def __init__(self, resolution=(640, 480), music_fp=MUSIC_FP):
        self.movie_map = []
        self.resolution = resolution
        self.music_fp = music_fp

        self.music_fs, self.music_data = self.set_music(self.music_fp)

    def set_music(self, fp):
        fs, data = wavfile.read(fp)  # fs = samples per second
        # data = np.mean(data, 1)  # average left and right channels

        # median = np.median(data)
        # data = data > median  # data indicates whether each sample is greater than median
        return fs, data

    def init_from_saved(self, movie_saved):
        self.movie_map = movie_saved.movie_map
        self.resolution = movie_saved.resolution

    def check_last_same_time(self, fp, margin=10):
        if len(self.movie_map) == 0:
            return False
        last_fp = self.movie_map[-1].fp

        date1 = os.stat(fp).st_birthtime
        date2 = os.stat(last_fp).st_birthtime
        return abs(date1-date2) < margin  # check whether dates are within ~margin~ seconds of each other

    def add_img(self, fp):
        if self.check_last_same_time(fp):
            return False
        image = Image(fp, self.resolution)
        self.movie_map.append(image)
        return True

    def add_video(self, fp):
        if self.check_last_same_time(fp):
            return False
        video = Video(fp, self.resolution)
        self.movie_map.append(video)
        return True

    def export(self, video_out_fp, audio_out_fp, fps=30, min_image_duration=0.25, min_video_duration=2):
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        out = cv2.VideoWriter(video_out_fp, fourcc, fps, self.resolution)

        audio_out = np.array(self.music_data)

        samples_per_frame = int(1/fps * self.music_fs)  # seconds per frame * samples per second => samples per frame
        music_threshold = np.mean(self.music_data[self.music_data > 0])
        print(music_threshold)

        current_duration = 0
        i = 0
        frame_n = 0
        sample_n = 0
        while i < len(self.movie_map) and frame_n*samples_per_frame < len(self.music_data):
            sample_start = sample_n
            sample_end = sample_start + samples_per_frame
            current_sample = self.music_data[sample_start: sample_end]

            current = self.movie_map[i]
            print(current.fp)
            current_music = np.mean(current_sample[current_sample > 0])
            current_duration += 1

            time_for_next = False
            frame = None
            if isinstance(current, Image):
                frame = current.step()
                if current_music > music_threshold and current_duration > min_image_duration*fps:
                    time_for_next = True
            elif isinstance(current, Video):
                if current.cap is None:
                    current.load_video()
                frame = current.step()
                if current.is_done():
                    time_for_next = True
                elif current_music > music_threshold and current_duration > min_video_duration*fps:
                    time_for_next = True

                if current.has_audio():
                    assert current.audio_fs == self.music_fs
                    audio_out[sample_start: sample_end] = 0.5*current_sample + 0.5*current.current_audio

            if frame is None:
                raise Exception("frame is None")
            if frame.shape[:2][::-1] != self.resolution:
                raise Exception("frame is incorrect shape {}, should be {}".format(frame.shape[:2][::-1],self.resolution))

            out.write(frame)

            if time_for_next:
                current.release()
                i += 1
                current_duration = 0

            frame_n += 1
            sample_n += samples_per_frame

        out.release()

        wavfile.write(audio_out_fp, self.music_fs, audio_out)

    def combine_movie(self, video_fp, audio_fp, out_fp):
        execute_cmd("ffmpeg -y -i {} -r 30 -i {} -filter:a aresample=async=1 -c:a flac -c:v copy {}".format(audio_fp, video_fp, out_fp))

        os.remove(video_fp)
        os.remove(audio_fp)


movie = Movie()

if os.path.exists(SAVE_FP):
    print("Loading movie map...")
    with open(SAVE_FP, "rb") as f:
        movie.init_from_saved(pickle.load(f))
else:
    print("Building movie map...")

    list_dir = [os.path.join(INPUT_DIR,fn) for fn in os.listdir(INPUT_DIR)]
    list_dir = sorted(list_dir, key=lambda fp: os.stat(fp).st_birthtime)
    # list_dir = list_dir[:100]

    for i,fp in enumerate(list_dir):
        if fp.endswith(".jpg"):
            print("Adding image", fp, "{}/{}".format(i,len(list_dir)))
            if movie.add_img(fp) is False:
                print("Rejected")
        elif fp.endswith(".mp4"):
            print("Adding video", fp, "{}/{}".format(i,len(list_dir)))
            if movie.add_video(fp) is False:
                print("Rejected")

    print("Saving movie map...")
    with open(SAVE_FP, "wb") as f:
        pickle.dump(movie, f)


print("Exporting video and audio...")
movie.export("movie.avi", "audio.wav")

print("Combining and cleaning up...")
movie.combine_movie("movie.avi", "audio.wav", "movie.mkv")

