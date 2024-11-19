import os

from dotenv import load_dotenv
from langchain_community.chat_models import ChatOpenAI

from aio_exporter.utils import get_work_dir
from typing import List

work_dir = get_work_dir()
load_dotenv(work_dir / '.env')

def llm_query(query ,  history  = []  ):
    llm = ChatOpenAI(
        model_name =  os.getenv('LLM_MODEL_NAME') ,
        openai_api_base = os.getenv('LLM_URL') ,
        openai_api_key = os.getenv('API_KEY')
    )
    return llm.invoke(query).content


if __name__ == '__main__':

    o = llm_query(
        '你好',
    )
    print(o)

