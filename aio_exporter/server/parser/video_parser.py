from aio_exporter.server.parser.base_parser import BaseParser
from aio_exporter.utils.video_utils import parser_audio

from pathlib import Path

class SenseVoiceSimpleParser(BaseParser):
    # 对视频使用公网接口简单的转换成 md
    def __init__(self):
        super().__init__()

    def parse(self , video_path):
        video_path = Path(video_path)
        asr_result = video_path / 'asr_result.txt'
        if asr_result.exists():
            with open(asr_result) as f:
                raw = f.read()
                return raw
        # 首先转换成为 mp3
        # 利用 sencevoice 进行快速,简单的 asr
        parser_audio()
