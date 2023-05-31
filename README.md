# movie-maker
Generate movie slideshows of your photos and videos that intuitively integrate with custom background music. Similar to Google Assistant's movie creation feature, but with more control over the output and number of photos/videos that can be included.

## About
As input, the program takes:
1. A folder containing all the photos (jpg, jpeg) and videos (mp4, mov).
2. A list of sound files for the background music (mp3, etc.). These files are concatenated together to form the background music for the movie.

The output is one `.mkv` video file containing your new movie slideshow.

## Prerequisites
This program has only been tested on macOS.

You will need [FFmpeg](https://ffmpeg.org/) in order to run this program. You can install it with [Homebrew](https://brew.sh/):

You will need the python modules [scipy](https://www.scipy.org/install.html), [numpy](https://www.numpy.org/), [opencv](https://pypi.org/project/opencv-python/), and [pydub](https://github.com/jiaaro/pydub#installation) installed. You can install them by running `pipenv install` in the root directory of this project, or by running `pip install scipy numpy opencv-python pydub`.

## Usage
The main function is in the `app` module and can be run through its command-line interface:
```
Usage: python -m app [OPTIONS]

  Main function for creating movie.

Options:
  -i, --inputdir TEXT   Directory of input images and videos.
  -m, --music TEXT      List of music files to use.
  -o, --out TEXT        File path for output video.
  -w, --width INTEGER   Width of output video.
  -h, --height INTEGER  Height of output video.
  -f, --fps INTEGER     FPS of output video.
  -n                    Cluster files by name.
  -d                    Cluster files by date.
```
NOTE: The filepath inputs must be relative to their respective directories, specified in the `config.py` file.

## Features
- Slides transition to the beat of the background music.
- Photos and videos presented in order of time created.
- Photo slides pan and zoom so that the whole image is shown, and to add variety to the movie.
- Photos and videos can be filtered in pre-processing to remove blurry images and videos, and to remove photos taken too near one another in time (i.e. burst photos).

## TODO
- [ ] Add more options for filtering photos and videos, since photos exported from iCloud or Google Photos may not include the original creation date in their metadata. In this case, we need some way to filter photos to remove duplicates and burst photos. One way to do this is to read the image data and compare it to the previous image, and if the images are too similar, remove the current image. This would be very slow if done in pre-processing, so it might be better to do this in real-time as the movie is being created.
- [ ] Add support for more file types, and for animated gifs.
- [ ] Add transition effects between slides. For example, a fade-to-black, crossfade, blur, or rotation effect between slides.
- [ ] More audio-visual effects? For example, panning and zoom speed could adjust to the beat of the music (would be kinda trippy).
