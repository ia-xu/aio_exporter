from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from aio_exporter.server.scrawler import BilibiliScrawler
import traceback
from loguru import logger
from aio_exporter.cli.domain import Cookies
from aio_exporter.utils import get_work_dir
import json

work_dir = get_work_dir()

class BilibiliController(Controller):

    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/bilibili"

    @classmethod
    def class_name(cls) -> str:
        return "bilibili"

    @post("/login")
    async def login(self , data:  Cookies):
        login = data.dict()
        cookie_dir = work_dir / 'cookies' / 'bilibili'
        with open(cookie_dir / 'cookies.json' , 'w' , encoding='utf-8') as f:
            json.dump(login , f , ensure_ascii=False , indent=4)

        with BilibiliScrawler() as scrawler:
            status = scrawler.login_status()
        return status

    @get("/get_new_video")
    async def update_wechat_articles(self):
        # scrawler = WechatScrawler()
        with BilibiliScrawler() as scrawler:
            new_articles = scrawler.walk()
        return new_articles

    @get('/count_new_video')
    async def count_wechat_articles(self):
        # scrawler = WechatScrawler()
        with BilibiliScrawler() as scrawler:
            counts = scrawler.count()
        return counts

