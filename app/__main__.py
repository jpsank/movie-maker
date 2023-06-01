
""" Main file for creating movie. """

import cv2
import numpy as np
from pydub import AudioSegment
import os
import random
from dataclasses import dataclass
import pickle
import click

from config import *
from app.util import *
from app.movie import *


@click.command()
@click.option("--inputdir", "-i", required=True, help="Directory of input images and videos.")
@click.option("--music", "-m", multiple=True, required=True, help="List of music files or directories to use.")
@click.option("--out", "-o", required=True, help="File path for output video.")
@click.option("--width", "-w", default=640, help="Width of output video.")
@click.option("--height", "-h", default=480, help="Height of output video.")
@click.option("--fps", "-f", default=30, help="FPS of output video.")
@click.option("-d", is_flag=True, help="Cluster and order files by date.")
def main(inputdir, music, out, width, height, fps, d):
    """ Main function for creating movie. """

    # Convert to absolute paths
    inputdir = os.path.join(MEDIADIR, inputdir)
    music = [os.path.join(AUDIODIR, m) for m in music]
    out = os.path.join(OUTDIR, out)

    # Load music files
    musics = []
    for path in music:
        if os.path.isdir(path):
            for file in os.listdir(path):
                if is_audio(fp := os.path.join(path, file)):
                    musics.append(AudioSegment.from_file(fp))
        elif is_audio(path):
            musics.append(AudioSegment.from_file(path))

    # Preload image and video files from input directory
    files: list[MediaFile] = []
    for file in os.listdir(inputdir):
        path = os.path.join(inputdir, file)
        if is_image(path):
            files.append(ImageFile(path))
        elif is_video(path):
            files.append(VideoFile(path))
        else:
            print(f"Warning: Unknown file type: {path}")
    print(f"Total # of photos and videos: {len(files)}")

    if d:
        # Sort and cluster files by date
        clusters = cluster_files_by_date(files)
        print(f"      # of clusters: {len(clusters)}")

        # Choose representative files from each cluster
        files = [file for cluster in clusters for file in choose_representatives(cluster)]
    else:
        # Sort files by name (assumes files are named sequentially)
        files = sorted(files, key=lambda file: int(file.name))

    # Create movie object
    print(f"Final # of photos and videos: {len(files)}")
    movie = Movie(files, musics, width, height, fps)

    # Create movie
    movie.export(out)


if __name__ == "__main__":
    main()
