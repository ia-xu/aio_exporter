import requests
from PIL import Image
import tempfile

def asr(mp3_file , model , url , api_key = None):

    # Open the file in binary mode
    with open(mp3_file, "rb") as audio_file:
        files = {
            "file": ("file.mp3", audio_file, "audio/mpeg"),  # Specify the file name and MIME type
        }
        data = {
            "model": model
        }
        headers = {}
        if api_key is not None:
            headers = {
                "Authorization": f"Bearer {api_key}",
            }
        # Send the request
        response = requests.post(url, headers=headers, data=data, files=files)
        return response.json()

def ocr(img_file , model ,  url ):
    # 如果是 pil image,存成临时文件
    temp_f = None
    if isinstance(img_file , Image.Image):
        temp_f =  tempfile.NamedTemporaryFile(suffix='.png')
        img_file.save(temp_f.name)
        img_file = temp_f.name

    with open(img_file, "rb") as audio_file:
        files = {
            "file": ("file.png", audio_file, "image/png"),  # Specify the file name and MIME type
        }
        data = {
            "model": model
        }
        # Send the request
        response = requests.post(url, data=data, files=files)

        out = response.json()

    if temp_f is not None:
        temp_f.close()
    return out