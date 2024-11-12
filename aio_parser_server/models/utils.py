import dotenv
from pathlib import Path
import os
import sys

def load_env():
    dotenv.load_dotenv(Path(__file__).parent.parent / '.env')


def load_ffmpeg():
    ffmpeg_path = os.getenv('FFMPEG_PATH')
    os.environ["PATH"] += os.pathsep + ffmpeg_path
    return

def load_torchocr():
    torchocr_path = os.getenv('TORCHOCR_PATH')
    sys.path.insert(0, str(torchocr_path))

