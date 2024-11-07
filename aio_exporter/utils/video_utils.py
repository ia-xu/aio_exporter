import os
from moviepy.video.io.VideoFileClip import VideoFileClip


def parser_audio(mp4_file , mp3_file):
    video_clip = VideoFileClip(str(mp4_file))
    audio_clip = video_clip.audio
    audio_clip.write_audiofile(str(mp3_file))

