

whisper_model = None

import datetime
import json
import torch
from pydub import AudioSegment
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from datasets import load_dataset
import opencc
from dotenv import load_dotenv
from pathlib import Path
import os
from tqdm import tqdm
import tempfile

cc = opencc.OpenCC('t2s')
from aio_parser_server.models.utils import load_env , load_ffmpeg

load_env()
load_ffmpeg()

class WhisperModel:
    def __init__(self):
        local_rank = int(os.environ.get('LOCAL_RANK', 0))
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        model_path = os.getenv('WHISPER_MODEL_PATH')
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_path,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=False
        )

        if torch.cuda.is_available():
            model.cuda()

        device = f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu"
        processor = AutoProcessor.from_pretrained(model_path)
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
        self.pipe = pipe

    def recognize(self , file_path):

        sound = AudioSegment.from_file(str(file_path))

        # total length
        total_length = len(sound)
        # 初始化一个空列表来存储切分后的片段
        pbar = tqdm(total=total_length, unit='ms')

        all_chunks = []
        segment_length_ms = 30 * 1000
        offset = 0
        while (offset < total_length):
            end_time = offset + segment_length_ms
            segment = sound[offset:end_time]
            with tempfile.NamedTemporaryFile(suffix='.wav') as segment_f:
                segment.export(segment_f, format="wav")
                output = self.pipe(str(segment_f.name), return_timestamps=True)
                chunks = output['chunks']

            shift = 30
            if len(chunks) >= 3:
                # 回退一句话，避免最后一句话发生了截断
                chunks = chunks[:-2]
                shift = chunks[-1]['timestamp'][-1]
            # offset timestamp
            for idx in range(len(chunks)):
                chunk = chunks[idx]
                chunk['text'] = cc.convert(chunk['text'])
                chunk['offset_timestamp'] = (
                    round(chunk['timestamp'][0] + offset // 1000, 2), round(chunk['timestamp'][1] + offset // 1000, 2))
            offset += shift * 1000
            pbar.update(shift * 1000)
            all_chunks.extend(chunks)

        for idx, chunk in enumerate(all_chunks):
            start_time = self._format_time(chunk['offset_timestamp'][0])
            end_time = self._format_time(chunk['offset_timestamp'][1])
            chunk['vis'] = (start_time, end_time)

        return all_chunks

    def _format_time(self, seconds):
        return str(datetime.timedelta(seconds=seconds))

def init_whisper_model():
    global whisper_model
    if whisper_model is None:
        return WhisperModel()
