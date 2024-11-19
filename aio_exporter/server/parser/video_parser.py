import json
import random

from aio_exporter.server.parser.base_parser import BaseParser
from aio_exporter.utils.video_utils import parser_audio
from aio_exporter.utils import get_work_dir
from loguru import logger
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from moviepy.video.io.VideoFileClip import VideoFileClip
from aio_exporter.utils import video_utils
from aio_exporter.utils import dl_models
from aio_exporter.utils.mllm import mllm_query
from urllib.parse import urljoin
from PIL import Image
import tempfile
import numpy as np


work_dir = get_work_dir()
load_dotenv(work_dir / '.env')
import os
import requests

token = os.getenv('API_KEY')



class SenseVoiceSimpleParser(BaseParser):
    # 对视频使用公网接口简单的转换成 md
    def __init__(self):
        super().__init__()

    def parse(self , video_path):
        video_path = Path(video_path)

        # 首先转换成为 mp3
        # 利用 sencevoice 进行快速,简单的 asr
        mp4_file = list(video_path.rglob('*.mp4'))[0]

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

        url = os.getenv('ASR_URL')

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
prompt = """
我将向你提供一段视频内容对应的音频的ASR语音识别的结果,该结果可能正确,也可能包含识别错误的内容。
同时,我会向你提供这段视频内容的一些截图,截图当中含有这段音频对应的视频片段的字幕内容。
请根据这些截图中的字幕内容,对ASR语音识别的结果进行修正。
1. 截图内容和ASR识别结果没有完全对应,你需要从截图当中的字幕中找到ASR语音识别结果对应的片段
2. 如果截图内容和ASR语音识别结果不匹配,你不需要修改ASR的结果
3. 视频当中可能存在错别字,因此你需要仔细判断是否需要对ASR结果进行修正

ASR语音识别结果:
<asr>
{asr_result}
</asr>

截图:
<image>

请根据截图中的字幕内容,对ASR语音识别的结果进行修正。
"""




class VideoParser(BaseParser):
    def __init__(self):
        super().__init__()

    def parse(self , video_path):

        base_url = 'http://127.0.0.1:56006'
        base_qwen2vl_url = 'http://127.0.0.1:11005/v1'
        video_path = Path(video_path)

        # 首先转换成为 mp3
        # 利用 sencevoice 进行快速,简单的 asr
        if video_path.is_dir():
            mp4_file = list(video_path.glob('*.mp4'))[0]
        else:
            mp4_file = video_path
        mp3_file = mp4_file.with_suffix('.mp3')
        if not mp3_file.exists():
            parser_audio(mp4_file, mp3_file)

        # model = 'SenseVoiceSmall'
        # model = 'Whisper-Large'
        asr_file = mp4_file.with_suffix('.asr.whisper.json')
        if not asr_file.exists():
            asr = dl_models.asr(
                mp3_file ,
                'Whisper-Large',
                os.getenv('ASR_URL_LOCAL')
            )
            with open(asr_file , 'w') as f:
                json.dump( asr , f , ensure_ascii=False)
        else:
            with open(asr_file , 'r') as f:
                asr = json.load(f)
        for sentence in tqdm(asr[4:]):
            s , e = sentence['offset_timestamp']
            mid = ( s + e ) / 2
            frame = video_utils.get_frame(
                mp4_file , mid
            )
            # 优先用 ocr 搞定大部分的问题
            ocr = dl_models.ocr(
                frame,
                'torchocr'
                , os.getenv('OCR_URL_LOCAL')
            )
            text_cat = ''.join([self._clean(tb['rec']) for tb in ocr])
            if self._clean(sentence['text']) in text_cat:
                # 说明发生了匹配
                continue

            # 尝试通过识别中间帧解决问题#
            # 可以把 frame 变小一点，减轻运算量
            out_mid = mllm_query(
                '<image>请识别图片当中的字幕内容。',
                [self.small_frame(frame)] ,
                url = os.getenv('QWEN2VL_URL_LOCAL')
            )
            if out_mid == sentence['text']:
                continue

            # 尝试拿到首尾两帧
            images = video_utils.interpolate(
                mp4_file, s, e, 2
            )

            out_ht = mllm_query(
                '<image><image>请识别如下多张视频截图当中的字幕内容。如果有重复的字幕，请去除重复项',
                [ self.small_frame(im) for im in images],
                base_qwen2vl_url
            )

            if self._clean(sentence['text']) in self._clean(out_ht) :
                # 说明只是字幕位置不对
                continue

            if len(out_ht.split(' ')) == 2:
                out_hmt = out_ht.split(' ')
                out_hmt = out_hmt[0] + out_mid + out_hmt[1]
                if self._clean(sentence['text']) in self._clean(out_hmt):
                    continue

            # 可能存在着跨帧的问题，此时考虑尝试抽取多帧结果
            # 如果 ocr 结果和 asr 结果不匹配
            rectified_result = self.rectify(
                mp4_file ,
                sentence['text'] ,
                s ,
                e,
                url = base_qwen2vl_url
            )
            if rectified_result == sentence['text']:
                continue
            print(sentence['text'] , rectified_result)

    def small_frame(self, frame , pix = 480):
        if min(frame.size) > pix:
            frame_small = frame.resize((int(frame.width * pix / min(frame.width, frame.height)), pix), Image.ANTIALIAS)
        else:
            frame_small = frame
        return frame_small


    def _clean(self, text):
        for spec in ['，',',','.','。','、','：',':','；','；','?','？']:
            text = text.replace(spec,'')
        text = text.replace(' ','')
        # 移除语气词
        for  spec in ['啊','呢','吧','的','那','得']:
            text = text.replace(spec , '')
        chinese_to_arabic = {
            '零': '0', '一': '1', '二': '2', '三': '3', '四': '4',
            '五': '5', '六': '6', '七': '7', '八': '8', '九': '9'
        }

        result = []
        for char in text:
            if char in chinese_to_arabic:
                result.append(chinese_to_arabic[char])
            else:
                result.append(char)
        text = ''.join(result)
        return text
    def rectify(self ,mp4_file , text , start , end , url):
        start = start - 0.5
        end = end + 0.5
        images = video_utils.interpolate(
            mp4_file , start , end  , 5
        )
        images = [self.small_frame(im , 720) for im in images]
        query = prompt.format(
            asr_result=text
        ).replace('<image>', '<image>' * len(images))

        response = mllm_query(
            query ,
            images ,
            url
        )
        return response









if __name__ == '__main__':
    from pathlib import Path

    parser = VideoParser()
    video_dir = ''
    videos = list(video_dir.rglob('*.mp4'))
    video = random.choice(videos)
    parser.parse(video)


