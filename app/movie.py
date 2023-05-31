
import cv2
import numpy as np
from pydub import AudioSegment
import os
import random
from dataclasses import dataclass
import pickle
from tqdm import tqdm
from itertools import groupby

from config import *
from app.util import *
from app.media import *


def cluster_files_by_date(files: list[MediaFile], margin: int = 20):
    """ Sort and cluster files by date. """
    # Sort files by date
    files = sorted(files, key=lambda file: file.creation_date)

    # Cluster files by creation date
    clusters: list[list[MediaFile]] = []
    last_date = None
    for file in files:
        date = file.creation_date
        if last_date is None or date - last_date > margin:
            # Create new cluster if first file or if file is too far from previous file
            clusters.append([file])
        else:
            # Add to existing cluster
            clusters[-1].append(file)
        last_date = date
    return clusters


def choose_representatives(cluster: list[MediaFile]) -> list[MediaFile]:
    """ Choose representative files for cluster. """
    # Return all videos and first image
    image_found = False
    for file in cluster:
        if isinstance(file, VideoFile):
            yield file
        elif not image_found and isinstance(file, ImageFile):
            yield file
            image_found = True


def choose_representatives_by_laplacian(cluster: list[MediaFile]) -> list[MediaFile]:
    """ Choose representative files for cluster. """
    best_laplacian = None
    best: ImageFile = None
    for file in cluster:
        if isinstance(file, VideoFile):
            # Keep all videos
            yield file
        elif isinstance(file, ImageFile):
            # Load image to get laplacian
            file.load()
            laplacian = file.img.get_var_of_laplacian()

            # Choose image with highest laplacian
            if best_laplacian is None or laplacian > best_laplacian:
                best_laplacian = laplacian
                best = file
    if best is not None:
        yield best


@dataclass
class Movie:
    files: list[MediaFile]
    musics: list[AudioSegment]
    width: int = 640
    height: int = 480
    fps: int = 30

    # Slide duration parameters
    min_duration_img: int = 300  # Minimum duration of slide in ms
    min_duration_pan: int = 1000  # Minimum duration of panned slide in ms
    min_duration_video: int = 2000  # Minimum duration of video in ms
    min_duration_last: int = 4000  # Minimum duration of last slide in ms

    # Pan and zoom parameters
    zoom_pct: float = 0.08  # Zoom percentage
    prepan_scale: float = 1.1  # Scale before panning

    # TODO: Add transitions

    def export(self, path: str):
        """ Export movie to file. """
        ms_per_frame = 1/self.fps * 1000
        
        # Create video writer
        videowriter = cv2.VideoWriter(f"{path}.avi", cv2.VideoWriter_fourcc(*'MJPG'), self.fps, (self.width, self.height))
        
        # Set audio output
        music: AudioSegment = self.musics[music_idx := 0]

        # Iterate through slides
        t = 0  # Time in ms
        for i, file in tqdm(enumerate(self.files), desc="Exporting", unit="slides", total=len(self.files)):
            file.load()  # Make sure file data is loaded

            if isinstance(file, ImageFile):
                # We pan image in a certain direction if shape is different from movie shape
                ratio = file.img.width / file.img.height
                target_ratio = self.width / self.height
                pan_x = ratio > target_ratio
                pan_y = ratio < target_ratio

                # For panning/zooming
                even = i % 2 == 0
                r1, r2 = random.random(), random.random()

                # Determine minimum duration of image slide
                min_duration = self.min_duration_pan if pan_x or pan_y else self.min_duration_img
            
            elif isinstance(file, VideoFile):
                # Determine minimum duration of video slide
                min_duration = self.min_duration_video
                max_frames = file.get_frame_count()
            
            # Last slide is usually longer than other slides
            if i == len(self.files) - 1 and self.min_duration_last is not None:
                min_duration = max(self.min_duration_last, min_duration)
            
            # Determine actual duration of slide
            n_frames = 0
            duration_ms = 0
            while True:                
                if isinstance(file, VideoFile):
                    # If we have reached maximum duration, stop
                    if n_frames == max_frames or (file.audio and duration_ms >= file.audio.duration_seconds * 1000):
                        break

                # If we have reached the end of the music sample, add next music sample
                if t + duration_ms + ms_per_frame > len(music):
                    music_idx += 1
                    music += self.musics[music_idx % len(self.musics)]

                # If we have reached minimum duration and a spike in loudness, stop
                loudness = music[t + duration_ms: t + duration_ms + ms_per_frame].dBFS
                if duration_ms >= min_duration and loudness > music.dBFS:
                    break

                n_frames += 1
                duration_ms += ms_per_frame
            
            # Write slide to output
            start = t
            for n in range(n_frames):
                # Get next frame
                frame = next(file)

                # Break if no more frames
                if frame is None:
                    break

                # Pan/zoom if image
                if isinstance(file, ImageFile):
                    # Resize frame to contain slightly larger than movie resolution
                    frame = frame.resize_to_contain(
                        int(self.width * self.prepan_scale), int(self.height * self.prepan_scale))

                    # Alternate going from 0 to 1 and 1 to 0
                    pct = n / n_frames if even else 1 - n / n_frames
                    if pan_x:
                        frame = frame.pan(pct, 0, self.width, self.height)
                    elif pan_y:
                        frame = frame.pan(0, pct, self.width, self.height)
                    else:
                        frame = frame.pan(r1 * pct, r2 * pct, self.width, self.height)
                        frame = frame.zoom(1 - self.zoom_pct * pct)

                # Crop if video
                elif isinstance(file, VideoFile):
                    # Resize and crop frame to movie resolution
                    frame = frame.resize_to_contain(self.width, self.height)
                    frame = frame.crop(0, 0, self.width, self.height)
                
                # Write frame to output and update time
                videowriter.write(frame)
                t += ms_per_frame
                n += 1
            
            # If video, release video capture and overlay audio on music
            if isinstance(file, VideoFile):
                file.capture.release()

                if file.audio:
                    segment = file.audio[0: t - start]
                    music = music.overlay(segment, position=start)
 
        # Release video writer
        videowriter.release()
        
        # Export music
        music[0: t].export(f"{path}.wav", format="wav")

        # Merge video and audio
        print("Merging video and audio...")
        # cmd = ["ffmpeg", "-i", f"{path}.avi", "-i", f"{path}.wav", "-c:v", "copy", "-c:a", "aac", path]
        cmd = ["ffmpeg", "-y", 
               "-i", f"{path}.wav", 
               "-r", f"{self.fps}", 
               "-i", f"{path}.avi", 
               "-filter:a", "aresample=async=1", 
               "-c:a", "flac", 
               "-c:v", "copy", path]
        for line in shexecute(cmd):
            print(line, end="")

        # Delete temporary files
        os.remove(f"{path}.avi")
        os.remove(f"{path}.wav")
