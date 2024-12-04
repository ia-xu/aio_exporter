from aio_exporter.server.downloader.base_downloader import BaseDownloader
from aio_exporter.utils import load_driver2
import requests
from contextlib import contextmanager
import readability
from bs4 import BeautifulSoup
import re
from datetime import datetime


class WebDownloader(BaseDownloader):
    def __init__(self):
        self.driver = None
        super().__init__("web")
        self.driver = load_driver2(headless=True)

    @contextmanager
    def request_session(self):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36"
        }

        session = requests.Session()
        session.headers.update(headers)
        yield session

    def get_url_config(self, url):
        for task in self.config.allow_websites:
            for cfg in self.config.allow_websites[task]:
                if cfg.domain in url:
                    return cfg
        return None

    def auto_title(self, html, title_cfg):
        html_doc = readability.Document(html)
        title = html_doc.title()
        for rule in title_cfg.get("replace", []):
            if rule in title:
                title = title[: title.index(rule)]
        return title

    def title(self, html, config):
        if config.get("title", {}).get("type", "auto") == "auto":
            title = self.auto_title(html, config.get("title", {}))
        elif config.title.type == 'h1':
            soup = BeautifulSoup(html, "html.parser")
            return  soup.find(name='h1').text
        else:
            raise NotImplementedError()
        return title

    def date(self, url ,html, config, title):
        if config.get("date", {}).get("type", "auto") == "auto":
            date = self.auto_date(html, config, title)
        elif config.get("date", {}).get("type") == "fix_class":
            date = self.fix_class_date(html, config, title)
        elif config.get("date", {}).get("type") == "url":
            regex = config.get("date", {}).get("regex" , r"\b20\d{2}(-|年)\d{2}(-|月)\d{2}(\b|日)")
            date_pattern = re.compile(regex)
            date =  date_pattern.search(url).group()
        else:
            raise NotImplementedError()

        # date_pattern = re.compile(r"\b20\d{2}(-|年)\d{2}(-|月)\d{2}(\b|日)")
        # date = date_pattern.search(date).group()

        if not date:
            return None
        regex = config.get('date' , {}).get('regex',r"\b20\d{2}(-|年)\d{2}(-|月)\d{2}(\b|日)")
        try:
            date = re.search(regex, date).group()
            format1 = '%Y-%m-%d'
            format2 = "%Y年%m月%d日"
            format = config.get('date', {}).get('format', format2 if '年' in date else format1)
            date_time_obj = datetime.strptime(date, format)
            return date_time_obj
        except:
            return None


    def fix_class_date(self, html, config, title):
        soup = BeautifulSoup(html, "html.parser")
        return " ".join(
            [soup.find(class_=cls).text.strip() for cls in config.date.class_]
        )

    def auto_date(self, html, config, title):
        # 从 html 当中找到 title
        soup = BeautifulSoup(html, "html.parser")
        # 查找所有包含特定文字 "title" 的标签
        specific_text = title
        tags_with_text = soup.find_all(lambda tag: specific_text in tag.text)

        # 输出找到的标签
        head = None
        for tag in tags_with_text:
            if tag.name == "h1":
                head = tag

        for order_tag in ["span", "time"]:
            date_pattern = re.compile(r"\b20\d{2}(-|年)\d{2}(-|月)\d{2}(\b|日)")
            spans = soup.find_all(order_tag)
            # 过滤出包含符合日期格式的span标签
            date_spans = [span for span in spans if date_pattern.search(span.text)]
            if len(date_spans) == 1:
                return date_spans[0].text.strip()
            index = config.get('date',{}).get('index',-1)
            if index != -1 and len(date_spans):
                return date_spans[config.date.get('index',-1)].text.strip()
        # 找到图片当中唯一的日期
        if config.get('date',{}).get('search',False):
            tags_with_text = soup.find_all(
                lambda tag: re.match(
                r"\b20\d{2}(-|年)\d{2}(-|月)\d{2}(\b|日)",
                tag.text.strip()
            ))
            if len(tags_with_text) == 1:
                return tags_with_text[0].text.strip()

        return None

    def download(self, url):
        config = self.get_url_config(url)
        if not config:
            return ''
        print('download {}'.format(url))
        if config.get('forbid',[]):
            if any( kw in url for kw in config.forbid):
                return ''
        html = self._download(url, config)
        title = self.title(html, config)
        date = self.date(url , html, config, title)

        print(title, "||", date)
        return html

    def _download(self, url, config):
        if any(cfg.domain in url for cfg in self.config.allow_websites.complex):
            return self.selenium_download(url)
        else:
            return self.requests_download(url, config)

    def selenium_download(self, url):
        self.driver.get(url)
        return self.driver.page_source

    def requests_download(self, url , config):
        with self.request_session() as session:
            response = session.get(url)
            encoding = config.get('encoding' , response.apparent_encoding)
            response.encoding = encoding
            html = response.text
            return html


if __name__ == "__main__":
    from aio_exporter.server.parser import WebParser
    from pathlib import Path

    with open(Path(__file__).parent / 'testurl') as f:
        lines = f.readlines()

    downloader = WebDownloader()
    parser = WebParser()

    # html = downloader.download('https://www.jsw.com.cn/2024/1203/1877560.shtml')
    # print(parser.parse(html))

    for line in lines:
        line = line.strip().replace('\'','').replace(',','')
        if 'zhihu' in line:
            continue
        html = downloader.download(
            line
        )
    #     if not html:
    #         print('debug' , line)
        # print(parser.parse(html))
