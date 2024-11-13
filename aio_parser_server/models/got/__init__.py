import os
from PIL import Image
from .modeling_got import *
from transformers import AutoConfig ,AutoModelForCausalLM,AutoTokenizer
from .formatter import GOTFormatter
from transformers import TextStreamer
from loguru import logger
AutoConfig.register("GOT", GOTConfig)
AutoModelForCausalLM.register(GOTConfig, GOTQwenForCausalLM)
from aio_parser_server.models.utils import load_env
load_env()


class GOTModel:
    def __init__(self):
        model_path = os.getenv('GOT_MODEL_WEIGHTS')
        logger.info('start to load got 2.0...')
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype='auto',
        )
        model.cuda().eval()
        tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        logger.info('load got 2.0 done...')
        self.formatter = GOTFormatter(model , tokenizer)

    def ocr(self , image_path , model_name):

        conversation = [
            {
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": "OCR: "},
                ],
            },
        ]
        image = Image.open(image_path).convert('RGB')

        if model_name.endswith('/ocr'):
            format = 'OCR:'
        elif model_name.endswith('/ocrf'):
            format = 'OCR with format: '
        else:
            raise ValueError('model_name must end with /ocr or /ocrf')
        inputs = self.formatter.eval_format(
            [conversation],
            [[image]],
            format = format
        )
        out = self .formatter.generate(inputs)

        return out