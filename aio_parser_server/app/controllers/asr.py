from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from blacksheep import Application, Request, Response, TextContent
import tempfile
from blacksheep.contents import FormPart
from pathlib import Path

class AsrController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/asr"


    @classmethod
    def class_name(cls) -> str:
        return "asr"

    @post("/transcribe")
    async def transcribe(request: Request):
        files = await request.files()
        if not files:
            return {}
        file = files[0]
        suffix = Path(file.file_name.decode()).suffix

        data = file.data
        with tempfile.NamedTemporaryFile(suffix=suffix) as tmp_file:
            tmp_file.write(data)
            tmp_file.flush()


