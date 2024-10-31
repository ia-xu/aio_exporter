

from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
from aio_exporter.server.scrawler import WechatScrawler



class ScrawlerController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/scrawler"

    @classmethod
    def class_name(cls) -> str:
        return "scrawler"


    @get("/get_new_wechat")
    async def update_wechat_articles(self):
        scrawler = WechatScrawler()
        new_articles = scrawler.walk()
        scrawler.close()
        return new_articles

    @get('/count_new_wechat')
    async def count_wechat_articles(self):
        scrawler = WechatScrawler()
        counts = scrawler.count()
        scrawler.close()
        return counts



