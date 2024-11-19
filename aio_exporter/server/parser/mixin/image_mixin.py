import os
import re

from aio_exporter.utils.llm import llm_query
from aio_exporter.utils.mllm import mllm_query
from contextlib import contextmanager
from .prompts import *
from functools import partial
from aio_exporter.utils import load_env
from PIL import Image
from pathlib import Path
import numpy as np
import cv2
import json5

load_env()


class ImageMixin:
    mllm_query = partial(
        mllm_query ,
        url=os.getenv('QWEN2VL_URL'),
        model=os.getenv('QWEN2VL_MODEL'),
        api_key=os.getenv('API_KEY')
    )
    @contextmanager
    def format(self, prompt_template, images=[], **kwargs):
        if not images:
            prompt_template = create_prompt_template(prompt_template)
            query = prompt_template.format(**kwargs)
            yield query
        else:
            prompt_template = create_prompt_template(prompt_template)
            query = prompt_template.format(**kwargs)
            assert "<image>" in query
            if len(re.findall("<image>", query)) != len(images):
                query = query.replace("<image>", "<image>" * len(images))


            yield query

    def split_context(self, md_text, images):
        text = md_text
        for im in images:
            pattern = rf"!\[img\]\({re.escape(im)}.*?\)"
            matches = re.search(pattern, text)
            if matches:
                text = text.replace(matches.group() , '<image>')

        pattern = r"(.*?)(<image>((\n|\s)*<image>)*)"
        matches = re.findall(pattern, text, re.DOTALL)

        result = []
        image_index = 0

        for i in range(len(matches)):
            before_text = matches[i][0].strip()  # 当前 <image> 前的文本
            image_tags = matches[i][1]
            after_text = (
                matches[i + 1][0].strip() if i + 1 < len(matches) else text.split(matches[i][1])[-1].strip()
            )  # 当前 <image> 后的文本直到下一个 <image>
            num_images = image_tags.count("<image>")
            group = (image_index , image_index + num_images)
            image_index += num_images

            # 将结果存储为字典
            result.append({
                "text": f"{before_text} {image_tags} {after_text}".strip(),
                "group": group,
            })

        return result

    def parse_jsonl(self, caption):

        caption = caption.replace('```json','').replace('```','')
        caption = json5.loads(caption)
        return caption



    def find_useful_image(self, md_text, images, image_urls):
        contexts = self.split_context(md_text , images)
        useful = []
        for context in contexts:
            s, e = context['group']
            image_group = images[s:e]
            with self.format(FIND_USEFUL_IMAGES,
                             context=context['text'] ,
                             n = len(image_group),
                             images=image_group) as query:
                caption = self.mllm_query( query , image_group)
                print(caption)
                print(image_urls[s:e])

                caption = self.parse_jsonl(caption)
                for res  in caption:
                    if '可删除' in str(res):
                        useful.append(False)
                    else:
                        useful.append(True)
        return useful

    def extract_information(self, md_text , images , image_urls , useful):
        contexts = self.split_context(md_text, images)

        for context  in contexts:
            s, e = context['group']
            image_group = images[s:e]
            with self.format(EXTRACT_RELATED_INFORMATION,
                             context=context['text'],
                             n=len(image_group),
                             images=image_group) as query:
                caption = self.mllm_query(query, image_group)
                print(caption)
                caption = self.parse_jsonl(caption)




