
from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from blacksheep import Application, Request, Response, TextContent
import tempfile
from blacksheep.contents import FormPart
from pathlib import Path
from loguru import logger
from aio_parser_server.models.ocr import TorchOCRModel
from aio_parser_server.models.got import GOTModel

OCR_MODELS = {
    'torchocr': None,
    'gotocr' : None
}

class OCRController(Controller):

    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/ocr"

    @classmethod
    def class_name(cls) -> str:
        return "ocr"

    @post("/ocr")
    async def transcribe(request: Request):
        data = await request.form()
        model_name = data.get("model")

        if model_name == 'torchocr':
            if OCR_MODELS['torchocr'] is None:
                model = TorchOCRModel()
                OCR_MODELS['torchocr'] = model
            else:
                model = OCR_MODELS['torchocr']

        elif 'gotocr' in model_name:
            if OCR_MODELS['gotocr'] is None:
                model = GOTModel()
                OCR_MODELS['gotocr'] = model
            else:
                model = OCR_MODELS['gotocr']
        else:
            return {}


        files = data.get('file')
        if len(files) != 1:
            return {}
        file = files[0]
        suffix = Path(file.file_name.decode()).suffix
        data = file.data
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
            tmp_file.write(data)
            tmp_file.flush()
            ocr_result = model.ocr(tmp_file.name , model_name)

        return ocr_result
