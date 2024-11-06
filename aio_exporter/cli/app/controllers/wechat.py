

from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from aio_exporter.server.scrawler import WechatScrawler
from aio_exporter.server.downloader import WechatDownloader
from aio_exporter.cli.domain import WechatCookies
import traceback
from loguru import logger
from aio_exporter.utils import get_work_dir
import json

work_dir = get_work_dir()

class WechatController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/wechat"

    @classmethod
    def class_name(cls) -> str:
        return "wechat"

    @get("/check_login")
    async def check_login(self) -> bool:
        # 利用 scrawler 做一下爬取
        try:
            # scrawler = WechatScrawler()
            with WechatScrawler() as scrawler:
                # name = '深蓝保'
                # fake_id = scrawler.search_bizno(name)
                # scrawler.count_new_article(name , fake_id)
                status = scrawler.login_status()
            return status
        except:
            import traceback
            traceback.print_exc()
            return False


    @post("/login")
    async def login(self , data:  WechatCookies):
        login = data.dict()
        cookie_dir = work_dir / 'cookies' / 'wechat'
        with open(cookie_dir / 'cookies.json' , 'w' , encoding='utf-8') as f:
            json.dump(login , f , ensure_ascii=False , indent=4)

        # 尝试 login
        # scrawler = WechatScrawler()
        with WechatScrawler() as scrawler:
            status = scrawler.login_status()
        return status


    @get("/get_new_wechat")
    async def update_wechat_articles(self):
        # scrawler = WechatScrawler()
        with WechatScrawler() as scrawler:
            new_articles = scrawler.walk()
        return new_articles

    @get('/count_new_wechat')
    async def count_wechat_articles(self):
        # scrawler = WechatScrawler()
        with WechatScrawler() as scrawler:
            counts = scrawler.count()
        return counts

    # ----------------------------
    # download
    # ----------------------------
    @get('/task_num')
    async def get_no_download_in_task_list(self) -> int:
        downloader = WechatDownloader()
        return downloader.get_no_download_in_task_list()



    @post('/assign_download_path')
    async def assign_download_path(self):
        downloader = WechatDownloader()
        return downloader.assign_path_for_new_articles()

    @post('/download')
    async def download_articles(self , new_article : bool):
        downloader = WechatDownloader()
        result = await downloader.download(new_article)
        return result