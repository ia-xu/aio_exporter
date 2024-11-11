import requests

url = "http://localhost:56006/api/asr/transcribe"

mp3_file = 'd:\\test_audio.mp3'
# Open the file in binary mode
token = 'aaa'


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
    print(response.json())