import json

from aio_exporter.server.parser.base_parser import BaseParser
from aio_exporter.utils.video_utils import parser_audio
from aio_exporter.utils import get_work_dir
from loguru import logger
from pathlib import Path
from dotenv import load_dotenv

work_dir = get_work_dir()
load_dotenv(work_dir / '.env')
import os
import requests

token = os.getenv('SILICON_TOKEN')

class SenseVoiceSimpleParser(BaseParser):
    # 对视频使用公网接口简单的转换成 md
    def __init__(self):
        super().__init__()

    def parse(self , video_path):
        video_path = Path(video_path)

        # 首先转换成为 mp3
        # 利用 sencevoice 进行快速,简单的 asr
        mp4_file = list(video_path.glob('*.mp4'))[0]

        asr_file = mp4_file.with_suffix('.json')

        if asr_file.exists():
            with open(asr_file) as f:
                data = json.load(f)
                return data['text']

        mp3_file = mp4_file.with_suffix('.mp3')

        logger.info('cvt2mp3')
        parser_audio(mp4_file ,mp3_file)

        asr_result = self.asr(mp3_file)
        with open(asr_file , 'w') as f:
            json.dump( asr_result , f , indent=2 , ensure_ascii=False )

        return asr_result['text']



    def asr(self , mp3_file):

        url = "https://api.siliconflow.cn/v1/audio/transcriptions"

        # Open the file in binary mode
        with open(mp3_file, "rb") as audio_file:
            files = {
                "file": ("file.mp3", audio_file, "audio/mpeg"),  # Specify the file name and MIME type
            }
            data = {
                "model": "FunAudioLLM/SenseVoiceSmall"
            }
            headers = {
                "Authorization": f"Bearer {token}",
            }

            # Send the request
            response = requests.post(url, headers=headers, data=data, files=files)
            return response.json()


