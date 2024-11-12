import os
import shutil
import time
import numpy as np
import torch
import torchaudio
from loguru import logger
from funasr import AutoModel
from funasr.utils.load_utils import load_audio_text_image_video, extract_fbank
from funasr.utils.datadir_writer import DatadirWriter
from funasr.models.sense_voice.model import SenseVoiceSmall
from funasr.register import tables
from aio_parser_server.models.utils import load_ffmpeg , load_env
from pathlib import Path
from mmengine import Config
import datetime
load_env()
load_ffmpeg()

sencevoice_model = None

def convert_timestamp(
        frames: list[int],
        subsampling_factor: int = 6,
        frame_shift: float = 10
):
    return [f * subsampling_factor * frame_shift for f in frames]


@tables.register("model_classes", "SenseVoiceSmallWithTimestamp")
class SenseVoiceSmallWithTimestamp(SenseVoiceSmall):
    """CTC-attention hybrid Encoder-Decoder model"""

    def inference(
            self,
            data_in,
            data_lengths=None,
            key: list = ["wav_file_tmp_name"],
            tokenizer=None,
            frontend=None,
            **kwargs,
    ):
        # import ipdb;ipdb.set_trace()
        meta_data = {}
        if (
                isinstance(data_in, torch.Tensor) and kwargs.get("data_type", "sound") == "fbank"
        ):  # fbank
            speech, speech_lengths = data_in, data_lengths
            if len(speech.shape) < 3:
                speech = speech[None, :, :]
            if speech_lengths is None:
                speech_lengths = speech.shape[1]
        else:
            # extract fbank feats
            time1 = time.perf_counter()
            audio_sample_list = load_audio_text_image_video(
                data_in,
                fs=frontend.fs,
                audio_fs=kwargs.get("fs", 16000),
                data_type=kwargs.get("data_type", "sound"),
                tokenizer=tokenizer,
            )
            time2 = time.perf_counter()
            meta_data["load_data"] = f"{time2 - time1:0.3f}"
            speech, speech_lengths = extract_fbank(
                audio_sample_list, data_type=kwargs.get("data_type", "sound"), frontend=frontend
            )
            time3 = time.perf_counter()
            meta_data["extract_feat"] = f"{time3 - time2:0.3f}"
            meta_data["batch_data_time"] = (
                    speech_lengths.sum().item() * frontend.frame_shift * frontend.lfr_n / 1000
            )

        speech = speech.to(device=kwargs["device"])
        speech_lengths = speech_lengths.to(device=kwargs["device"])

        language = kwargs.get("language", "auto")
        language_query = self.embed(
            torch.LongTensor([[self.lid_dict[language] if language in self.lid_dict else 0]]).to(
                speech.device
            )
        ).repeat(speech.size(0), 1, 1)

        use_itn = kwargs.get("use_itn", False)
        textnorm = kwargs.get("text_norm", None)
        if textnorm is None:
            textnorm = "withitn" if use_itn else "woitn"
        textnorm_query = self.embed(
            torch.LongTensor([[self.textnorm_dict[textnorm]]]).to(speech.device)
        ).repeat(speech.size(0), 1, 1)
        speech = torch.cat((textnorm_query, speech), dim=1)
        speech_lengths += 1

        event_emo_query = self.embed(torch.LongTensor([[1, 2]]).to(speech.device)).repeat(
            speech.size(0), 1, 1
        )
        input_query = torch.cat((language_query, event_emo_query), dim=1)
        speech = torch.cat((input_query, speech), dim=1)
        speech_lengths += 3

        # Encoder
        encoder_out, encoder_out_lens = self.encoder(speech, speech_lengths)
        if isinstance(encoder_out, tuple):
            encoder_out = encoder_out[0]

        # c. Passed the encoder result and the beam search
        ctc_logits = self.ctc.log_softmax(encoder_out)
        if kwargs.get("ban_emo_unk", False):
            ctc_logits[:, :, self.emo_dict["unk"]] = -float("inf")

        results = []
        b, n, d = encoder_out.size()
        if isinstance(key[0], (list, tuple)):
            key = key[0]
        if len(key) < b:
            key = key * b
        for i in range(b):
            x = ctc_logits[i, 4: encoder_out_lens[i].item(), :]

            yseq = x.argmax(dim=-1)
            scores = x.max(dim=-1)[0].exp()

            token_spans = torchaudio.functional.merge_tokens(yseq, scores, blank=self.blank_id)

            ibest_writer = None
            if kwargs.get("output_dir") is not None:
                if not hasattr(self, "writer"):
                    self.writer = DatadirWriter(kwargs.get("output_dir"))
                ibest_writer = self.writer[f"1best_recog"]

            token_int = []
            timestamp = []
            for token_span in token_spans:
                token_int.append(token_span.token)
                timestamp.append(convert_timestamp([token_span.start, token_span.end]))

            # Change integer-ids to tokens
            token = [tokenizer.ids2tokens(t) for t in token_int]
            token_ = [_ for _ in token if _.strip()]
            timestamp_ = [t for _ , t in zip(token , timestamp) if _.strip() ]
            text = " ".join(token_)
            timestamp = timestamp_
            # if text.split() != text.split(' '):
            #     print('hello')
            result_i = {"key": key[i], "text": text, "timestamp": timestamp}
            results.append(result_i)

            if ibest_writer is not None:
                ibest_writer["text"][key[i]] = text

        return results, meta_data


class SenceVoiceModel:
    def __init__(self):
        local_rank = int(os.environ.get('LOCAL_RANK', 0))
        asr_model = os.getenv('SENCEVOICE_ASR_MODEL')
        vad_model = os.getenv('VAD_MODEL')
        punc_model = os.getenv('PUNC_MODEL')

        # 加载使用上面的 SenseVoiceSmallWithTimestamp
        if Path(asr_model).exists():
            config_file = Path(asr_model) / 'config.yaml'
            config = Config.fromfile(config_file)
            if config.model != 'SenseVoiceSmallWithTimestamp':
                logger.info('change model to SenseVoiceSmallWithTimestamp')
                config.model = 'SenseVoiceSmallWithTimestamp'
                shutil.copy(config_file , config_file.with_suffix('.bak.yaml'))
                config.dump(config_file)


        self.voice_model = AutoModel(
            model=asr_model,
            vad_model=vad_model,
            punc_model=punc_model,
            device=f"cuda:{local_rank}" if torch.cuda.is_available() else "cpu",
            disable_update=True
        )

    def _format_time(self, seconds):
        return str(datetime.timedelta(seconds=seconds))

    def recognize(self, file_path):
        result = self.voice_model.generate(
            str(file_path),
            sentence_timestamp=True)

        for sentence in result[0]['sentence_info']:
            sentence['offset_timestamp'] = [sentence['start'] / 1000, sentence['end'] / 1000]
            sentence.pop('start')
            sentence.pop('end')
            # sentence.pop('timestamp')
            start_time = self._format_time(sentence['offset_timestamp'][0])
            end_time = self._format_time(sentence['offset_timestamp'][1])
            sentence['vis'] = (start_time, end_time)

        return result[0]['sentence_info']


def init_sencevoice_model():
    global sencevoice_model
    if sencevoice_model is None:
        return SenceVoiceModel()
