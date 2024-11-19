import os
import re
import base64
import io
from pathlib import Path

def encode_pil_image(image_path):
    if isinstance(image_path, (str, Path )):
        byte_data = open(image_path ,'rb').read()
    else:
        byte_io = io.BytesIO()
        image_path.convert('RGB').save(byte_io, format='JPEG')
        byte_data = byte_io.getvalue()
    base64_image = base64.b64encode(byte_data).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_image}"

# 提供将多模态数据包装成 openai 格式进行调用
def convert(query, images):
    converted_value = []
    im_count = 0
    if '<image>' in query:
        # Split the value by the image placeholder
        parts = re.split(r'(<image>)', query)
        for part in parts:
            if not part:
                continue
            elif part == '<image>':
                # Handle the image placeholder
                converted_value.append({"type": "image_url", "image_url": {
                    'url': encode_pil_image(images[im_count])
                }})
                im_count += 1
            else:
                # Handle the text parts
                if part:  # Ignore empty strings
                    converted_value.append({"type": "text", "text": part})
    else:
        converted_value.append({"type": "text", "text": query})
    return converted_value

def mllm_query(query , images , url , model = 'default-lora' , api_key = None):
    from openai import OpenAI
    client = OpenAI(
        api_key= api_key,  # 'EMPTY',
        base_url=url,
    )
    query = convert(query, images)
    chat_response = client.chat.completions.create(
        model= model, messages=[
            {'role': 'user', 'content': query}
        ], stream=False,
        temperature = 0.01
    )
    return chat_response.choices[0].message.content

