from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from blacksheep.server.controllers import Controller, get, post
from typing import List, Optional
from blacksheep import Application, Request, Response, TextContent
from aio_parser_server.models.utils import load_env
import os
load_env()

class LocalEmbeddings(HuggingFaceBgeEmbeddings):
    def __init__(self, model_name):
        model_kwargs = {'device': 'cuda'}
        super().__init__(model_name = model_name , model_kwargs = model_kwargs)

embedding_model = None
if os.getenv('EMBEDDING_MODEL_PATH'):
    embedding_model = LocalEmbeddings(os.getenv('EMBEDDING_MODEL_PATH'))




# 调用 BGEM3 对输入数据进行 embedding
class TransformerEmbedding(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/embedding"

    @classmethod
    def class_name(cls) -> str:
        return "embedding"

    @post("/embeddings")
    async def embeddings(request: Request):
        payload = await request.json()
        assert payload['model'] == 'BAAI/bge-m3'
        embeddings = embedding_model.embed_documents(payload['input'])
        embeddings = [ {'embedding':embed , 'index':idx} for  idx , embed in enumerate(embeddings)]
        return {
            'data': embeddings ,
            'model' : payload['model']
        }
