import requests
from pathlib import Path

url = "http://localhost:56006/api/ocr/ocr"

img_file = Path(__file__).parent / 'test_image.png'
# Open the file in binary mode


with open(img_file, "rb") as audio_file:
    files = {
        "file": ("file.png", audio_file , "image/png"),  # Specify the file name and MIME type
    }
    data = {
        "model": "gotocr"
    }
    # Send the request
    response = requests.post(url,data=data, files=files)
    print(response.json())