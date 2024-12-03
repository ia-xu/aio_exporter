from aio_exporter.server.downloader import ZhihuDownloader
from aio_exporter.server.parser import ZhihuParser
from blacksheep.server.controllers import Controller, get, post
from typing import List, Optional ,Dict
import numpy as np
from aio_exporter.utils import sql_utils

session = sql_utils.init_sql_session('zhihu')

class ZhihuController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/zhihu"

    @classmethod
    def class_name(cls) -> str:
        return "zhihu"

    @get('/check_status')
    async def check_status(self):
        downloader = ZhihuDownloader()
        return {'status': downloader.check_status()}



    @get("/simple_parse")
    async def simple_parse(self, url: str) -> Dict[str, str]:
        downloader = ZhihuDownloader()
        parser = ZhihuParser()
        html = downloader.download_with_record(url)
        # 随机等待，避免过快
        import time
        time.sleep(np.random.rand() * 2  + 1)

        title = ''
        article = sql_utils.get_article_by_url(session , url)
        if article:
            title = article[0].title
        return {'content' : parser.parse(html) , 'title' : title}




