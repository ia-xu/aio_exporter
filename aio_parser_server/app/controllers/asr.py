from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from blacksheep import Application, Request, Response, TextContent
import tempfile
from blacksheep.contents import FormPart
from pathlib import Path
from loguru import logger
from aio_parser_server.models.asr.sencevoicesmall import sencevoice_model , init_sencevoice_model
from aio_parser_server.models.asr.whisper import whisper_model , init_whisper_model



ASR_Models = {
    'SenseVoiceSmall': whisper_model,
    'Whisper-Large': whisper_model
}

class AsrController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/asr"


    @classmethod
    def class_name(cls) -> str:
        return "asr"

    @post("/transcribe")
    async def transcribe(request: Request):
        data = await request.form()
        model_name = data.get("model")


        if 'SenseVoiceSmall' in model_name:
            model = ASR_Models['SenseVoiceSmall']
            if model is None:
                logger.info('start to load model...')
                model = init_sencevoice_model()
                ASR_Models['SenseVoiceSmall'] = model
                logger.info('load model done...')
        elif 'Whisper-Large' in model_name:
            model = ASR_Models['Whisper-Large']
            if model is None:
                logger.info('start to load model...')
                model = init_whisper_model()
                ASR_Models['Whisper-Large'] = model
                logger.info('load model done...')
        else:
            raise ValueError(f"Unsupported model: {model_name}")


        files = data.get('file')
        if len(files) != 1:
            return {}
        file = files[0]
        suffix = Path(file.file_name.decode()).suffix

        data = file.data
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
            tmp_file.write(data)
            tmp_file.flush()
            asr_result = model.recognize(tmp_file.name)

        return asr_result



