

from .plug.blip_process import BlipImageEvalProcessor
from transformers import AutoProcessor,AutoConfig
from .conversation import conv_templates,SeparatorStyle
from .constants import *
import torch
from .utils import KeywordsStoppingCriteria
from transformers import TextStreamer

class GOTFormatter:
    def __init__(self , model ,  tokenizer):
        self.model = model
        self.image_processor = BlipImageEvalProcessor(image_size=1024)
        self.image_processor_high = BlipImageEvalProcessor(image_size=1024)
        self.tokenizer = tokenizer
        self.use_im_start_end = True
        self.image_token_len = 256

    def eval_format(self , conversations , images_list , format):


        for conversation , images , in zip(conversations , images_list):
            # 目前只考虑 bs = 1 ， 先跑通
            # 这里就简单处理一下

            # qs = 'OCR with format: '
            qs = DEFAULT_IM_START_TOKEN + DEFAULT_IMAGE_PATCH_TOKEN * self.image_token_len + DEFAULT_IM_END_TOKEN + '\n' + format

            conv = conv_templates['mpt'].copy()
            conv.append_message(conv.roles[0], qs)
            conv.append_message(conv.roles[1], None)

            prompt = conv.get_prompt()
            inputs = self.tokenizer([prompt])

            image = torch.stack([ self.image_processor(image)  for image in images ])
            image1 = torch.stack([self.image_processor_high(image) for image in images])
            input_ids = torch.as_tensor(inputs.input_ids)
            return {
                'input_ids' : input_ids.cuda() ,
                'images' : [(image.half().cuda() , image1.half().cuda())]
            }

    def generate(self, inputs):
        streamer = TextStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        conv = conv_templates['mpt'].copy()
        stop_str = conv.sep if conv.sep_style != SeparatorStyle.TWO else conv.sep2
        keywords = [stop_str]
        stopping_criteria = KeywordsStoppingCriteria(keywords, self.tokenizer, inputs['input_ids'])

        with torch.autocast("cuda", dtype=torch.bfloat16):
            output_ids = self.model.generate(
                **inputs,
                do_sample=False,
                num_beams=1,
                no_repeat_ngram_size=20,
                streamer=streamer,
                max_new_tokens=4096,
                stopping_criteria=[stopping_criteria]
            )
            out = self.tokenizer.decode(output_ids[0])
            out = out[out.index('assistant') +len('assistant'):]
            out = out.replace('<|im_end|>', '')
            return out