import os
from typing import List, Optional
from blacksheep.server.controllers import Controller, get, post
import requests
from copy import deepcopy
from aio_exporter.utils import load_env
from aio_exporter.server.scrawler import KimiChatScrawler
from urllib.parse import urljoin

load_env()


class SearXNG:
    def __init__(self, api_base, proxies=None):
        self.url = urljoin(api_base, "search")
        self.params = {
            "q": "",
            "format": "json",
        }
        self.proxies = None
        if proxies:
            self.proxies = proxies

    def search(self, key):
        params = deepcopy(self.params)
        params["q"] = key
        response = requests.post(self.url, params, proxies=self.proxies)
        result = response.json()
        print(".")
        return result


search_engine = None
if os.environ.get("SEARCHXNG"):
    search_engine = SearXNG(api_base=os.environ.get("SEARCHXNG"))

scrawler = KimiChatScrawler()

class SearchController(Controller):
    @classmethod
    def route(cls) -> Optional[str]:
        return "/api/search"

    @classmethod
    def class_name(cls) -> str:
        return "search"

    @get("/search")
    async def search(self, question: str):
        # scrawler = WechatScrawler()
        if search_engine is None:
            return {"message": "fail"}
        try:
            search = search_engine.search(question)
        except:
            return {"message": "fail"}
        search.update({"message": "success"})
        return search

    @get("/kimisearch")
    async def kimisearch(self, question: str):
        urls = scrawler.search([question])
        return {"message": "success", "results": [{"url": url} for url in urls]}
