
INPUT_DIR = "input/Thailand"  # directory containing photos (jpg/jpeg) and videos (mp4)
MUSIC_FP = "input/music/748911.mp3"  # audio file for movie music
SAVE_FP = "save.p"  # pickle file to save preprocessed photos and videos so loading is faster for successive runs

RESOLUTION = (640, 480)  # resolution of final output
STORE_RES = (800, 600)  # resolution to store images for processing (so zooming is full quality, etc)

FPS = 30  # might make things weird if changed


# Movie Parameters

MIN_IMAGE_DURATION = 0.3
MIN_LONG_IMG_DURATION = 1
MIN_VIDEO_DURATION = 2
MIN_LAST_DURATION = 4  # or None

