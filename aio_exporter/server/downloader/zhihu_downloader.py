from aio_exporter.utils import load_driver2
from aio_exporter.utils import load_cookies
import readability
import markdownify
import html_text
from pathlib import  Path
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from contextlib import contextmanager

class ZhihuDownloader:
    def __init__(self):
        self.driver = None

    def load_driver(self):
        self.driver = load_driver2(headless=False)
        self.driver.get('https://www.zhihu.com')
        cookies = load_cookies('zhihu')
        for cookie in cookies['cookies']:
            self.driver.add_cookie(cookie)
        # 随便打开一个结果
        self.driver.get('https://www.zhihu.com/people/emiya-98')
        for cookie in self.driver.get_cookies():
            if cookie['name'] ==  '__zse_ck':
                cookie['value']  = cookies['zse_ck']
                self.driver.add_cookie(cookie)

    @contextmanager
    def session(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
        }

        session = requests.Session()
        cookies = load_cookies('zhihu')
        for cookie in cookies['cookies']:
            session.cookies.set(cookie['name'], cookie['value'])
        session.cookies.set('__zse_ck', cookies['zse_ck'])
        session.headers.update(headers)
        yield session


    def _download(self , url):
        with self.session() as session:
            response = session.get(url)
            response.encoding = response.apparent_encoding
            html = response.text
            if '{"appName":"zse_ck","trackJSRuntimeError":true}' in html:
                return '[ERROR]zse_ck过期!请联系我更新zse_ck'
            return html

    def fallback_download(self, url):
        if self.driver is None:
            self.load_driver()
        self.driver.get(url)
        return self.driver.page_source

if __name__ == '__main__':

    pass







