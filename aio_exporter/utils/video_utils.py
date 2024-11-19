import os
from moviepy.video.io.VideoFileClip import VideoFileClip
import requests
from moviepy.video.io.VideoFileClip import VideoFileClip
from PIL import Image
import tempfile
import numpy as np


def parser_audio(mp4_file , mp3_file):
    video_clip = VideoFileClip(str(mp4_file))
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(str(mp3_file))




def get_frame(mp4_file , frame_time ):
    video_clip = VideoFileClip(str(mp4_file))
    frame = video_clip.get_frame(frame_time)
    frame = Image.fromarray(frame)
    return frame


def interpolate(mp4_file , start , end , num):
    video_clip = VideoFileClip(str(mp4_file))
    images = []
    for frame_t in np.linspace(start, end, num):
        frame = video_clip.get_frame(frame_t)
        frame = Image.fromarray(frame)
        images.append(frame)
    return images




