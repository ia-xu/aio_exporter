from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from aio_exporter.server.scrawler import BilibiliScrawler
from aio_exporter.server.downloader import BiliBiliDownloader
from concurrent.futures import ThreadPoolExecutor
import traceback
from loguru import logger
from aio_exporter.cli.domain import Cookies
from aio_exporter.utils import get_work_dir
import json
import asyncio

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

    # ----------------------------
    # download
    # ----------------------------
    @get('/task_num')
    async def get_no_download_in_task_list(self) -> int:
        downloader = BiliBiliDownloader()
        return downloader.get_no_download_in_task_list()



    @post('/assign_download_path')
    async def assign_download_path(self):
        downloader = BiliBiliDownloader()
        return downloader.assign_path_for_new_video()

    @post('/download')
    async def download_articles(self , new_article : bool):
        downloader = BiliBiliDownloader()
        new_task = downloader.create_new_download_task(new_article)
        # async def download_task():
        #     await downloader.download()
        # asyncio.create_task(download_task())
        await downloader.download()
        return new_task