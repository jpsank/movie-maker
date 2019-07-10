# movie-maker
Generate movie slideshows of your photos and videos that intuitively integrate with custom background music. Similar to Google Assistant's movie creation feature

## About
This program takes two inputs: 
1. A folder containing all the video (mp4, mov) and image (jpg, jpeg) files
2. A sound file for the background music (mp3, etc.)

The output is one mkv video file containing your new movie: `movie.mkv`

Features include:
- Image and video slides' durations coincide with beat in background music
- Photos and videos in movie ordered by time created
- Panning and zooming effects on image slides (more effects can be added easily)
- Pan and zoom effects fix problem where the image is too wide or too tall for the output resolution
- Filtering images and videos such that a photo taken too near another in time (i.e. burst photos) is not included in the movie
- Filtering images such that blurry images are not included in the movie

## Prerequisites
This program has only been tested on macOS

You will need [FFmpeg](https://ffmpeg.org/) in order to do cool things with audio and video files

You will need the python modules [scipy](https://www.scipy.org/install.html), [numpy](https://www.numpy.org/), [opencv](https://pypi.org/project/opencv-python/), and [pydub](https://github.com/jiaaro/pydub#installation) to do cooler things with image, video, and audio data

## Usage
For now, change the hyper-parameters in `config.py` and then run the `main.py` file:
```
python3 main.py
```

