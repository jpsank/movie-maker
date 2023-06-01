# movie-maker
Generate movie slideshows of your photos and videos that intuitively integrate with custom background music. Similar to Google Assistant's movie creation feature, but with more control over the output and number of photos/videos that can be included.

## About
As input, the program takes:
1. A folder containing all the photos (jpg, jpeg) and videos (mp4, mov).
2. A list of sound files for the background music (e.g. mp3). These files are concatenated together to form the background music for the movie.

The output is one video file (e.g. mp4, mkv) containing your new movie slideshow.

## Prerequisites
This program has only been tested on macOS.

You will need [FFmpeg](https://ffmpeg.org/) in order to run this program. You can install it with [Homebrew](https://brew.sh/): `brew install ffmpeg`.

You will need the python modules [scipy](https://www.scipy.org/install.html), [numpy](https://www.numpy.org/), [opencv](https://pypi.org/project/opencv-python/), and [pydub](https://github.com/jiaaro/pydub#installation) installed. You can install them by running `pipenv install` in the root directory of this project, or by running `pip install scipy numpy opencv-python pydub`.

## Usage
The main function is in the `app` module and can be run through its command-line interface:
```
Usage: python -m app [OPTIONS]

  Main function for creating movie.

Options:
  -i, --inputdir TEXT   Directory of input images and videos.  [required]
  -m, --music TEXT      List of music files to use.  [required]
  -o, --out TEXT        File path for output video.  [required]
  -w, --width INTEGER   Width of output video.
  -h, --height INTEGER  Height of output video.
  -f, --fps INTEGER     FPS of output video.
  -d                    Cluster and order files by date.
```
NOTE: The filepath inputs must be relative to their respective directories, specified in the `config.py` file.

## Features
- Slides transition to the beat of the background music.
- Photos and videos presented in order of time created.
- Photo slides pan and zoom so that the whole image is shown, and to add variety to the movie.
- Photos and videos can be filtered in pre-processing to remove blurry images and videos, and to remove photos taken too near one another in time (i.e. burst photos).

## TODO
- [ ] Prioritize photos and videos that are more interesting. For example, photos with **faces**, or photos that are more in focus, since sometimes the whole slideshow will be a bunch of random landscape photos. This could be done using a pre-trained neural network to detect faces, which would probably be easy with OpenCV.
- [x] Add more options for filtering photos and videos, since photos exported from iCloud or Google Photos may not include the original creation date in their metadata. In this case, we need some way to filter photos to remove duplicates and burst photos. One way to do this is to read the image data and compare it to the previous image, and if the images are too similar, remove the current image. This would be very slow if done in pre-processing, so it might be better to do this in real-time as the movie is being created.
- [ ] Add support for more file types, and for animated gifs.
- [ ] Add transition effects between slides. For example, a fade-to-black, crossfade, blur, or rotation effect between slides.
- [ ] More audio-visual effects? For example, panning and zoom speed could adjust to the beat of the music (would be kinda trippy).
- [ ] IMPORTANT: Now that lower-level photo/video file logic is streamlined in the latest overhaul, there's a lot of room for improvement in the higher-level logic. For example, the `export` function of the `Movie` class contains pretty much the entire process of generating the movie. This should be broken up into smaller functions, and the `Movie` class should be refactored to be more modular. A lot of the movie generation process is hardcoded in the `Movie` class and main function; this could be split up into more modular functions and classes – but I will have to figure out the best way to break up the process into pieces that fit together.
