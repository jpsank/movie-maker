""" Configuration file for movie maker. """
import os

basedir = os.path.dirname(os.path.abspath(__file__))
DATADIR = os.path.join(basedir, "data")  # directory to store data
AUDIODIR = os.path.join(DATADIR, "audio")  # directory containing music files
MEDIADIR = os.path.join(DATADIR, "media")  # directory containing photos (jpg/jpeg) and videos (mp4)
OUTDIR = os.path.join(DATADIR, "out")  # directory to store output files

# TODO: What to do with this?
STORE_RES = (800, 600)   # resolution to store images for processing (so zooming is full quality, etc)

# Movie Parameters
MIN_IMAGE_DURATION = 0.3
MIN_LONG_IMG_DURATION = 1
MIN_VIDEO_DURATION = 2
MIN_LAST_DURATION = 4  # or None

