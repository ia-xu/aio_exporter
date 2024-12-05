from aio_exporter.server.downloader.base_downloader import BaseDownloader
from aio_exporter.utils import load_driver2
import requests
from contextlib import contextmanager
import readability
from bs4 import BeautifulSoup
import re
import json
import os
from loguru import logger
from datetime import datetime
from aio_exporter.utils import sql_utils
from aio_exporter.utils.utils import get_work_dir


work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)
web_dir = database / 'web'
web_dir.mkdir(exist_ok=True)

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
            return '[ERROR]不支持的网站'
        if config.get('forbid',[]):
            if any( kw in url for kw in config.forbid):
                return '[ERROR]不支持的url'
        articles = sql_utils.get_article_by_url(self.session, url)
        if articles:
            # 说明之前处理过，不重复处理
            storage_path = self.gather_article_with_storage([_.id for _ in articles]).storage_path[0]
            if os.path.exists(storage_path):
                logger.info('加载已经下载过的文档: {}'.format(Path(storage_path).name))
                with open(storage_path , 'r' , encoding='utf-8') as f:
                    return f.read()

        html = self._download(url, config)
        articles = self.insert_new_download_article(url , html , config)
        article = articles[0]
        article_download_path = self.assign_path(article)
        try:
            with open(article_download_path, 'w', encoding='utf-8') as f:
                f.write(html)
            # 这里简单一点，不考虑重试或者其他情况
            self.upsert_status(article.id, '下载成功', 1)
        except:
            self.upsert_status(article.id, '下载失败', 1)
        return html

    def insert_new_download_article(self , url , html , config):
        title = self.title(html, config)
        date = self.date(url , html, config, title)

        # 插入新的数据
        metadata = '{}'
        sql_utils.insert_if_not_exists(
            self.session, title, config.author, url, date, self.source_name, metadata
        )
        # 分配下载路径,并下载
        articles = sql_utils.get_article_by_url(self.session, url)

        return articles



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


    def assign_path(self , article ):
        # 分配下载地址
        account_dir = web_dir / article.author
        account_dir.mkdir(exist_ok=True)
        title = self.clean_title(article.title)

        file_path = account_dir / f'{article.id}_{title}.html'
        # 检查filepath 是否已经存在
        idx = 0
        while self.check_file_path_exists(file_path):
            # 更新位置
            file_path = account_dir / f'{article.id}_{idx}_{title}.html'
            idx += 1

        logger.info(f'为账号{article.author} 文章分配路径到 {file_path.name}.html')
        self.insert_assigned_path(
            article.id,
            file_path,
            '尚未开始',
            'file',
            0
        )
        return file_path

if __name__ == "__main__":
    from aio_exporter.server.parser import WebParser
    from pathlib import Path

    # lines = [
    #     'https://www.shenlanbao.com/wenda/2-112160',
    #     'https://www.cpic.com.cn/c/2020-12-01/1612748.shtml',
    #     'https://finance.china.com.cn/roll/20241203/6192714.shtml',
    #     'https://www.csai.cn/baoxian/1295371.html',
    #     'https://news.qq.com/rain/a/20220510A06BZ700',
    #     'https://www.gov.cn/xinwen/2021-02/01/content_5584251.htm',
    #     'https://xueqiu.com/4866021334/176935687',
    #     'https://post.smzdm.com/p/aklpmlm8/',
    #     'https://www.99.com.cn/ylbx/zjx/905096.htm',
    #     'https://news.vobao.com/article/1125240934764531413.shtml',
    #     'https://finance.sina.com.cn/roll/2024-11-28/doc-incxrmwq9577455.shtml',
    #     'http://www.21jingji.com/article/20220617/herald/de64511c5c7bfdfa4b1d08eca208a13d.html',
    #     'https://www.jiemian.com/article/5231215.html',
    # ]

    lines = ['https://www.jiemian.com/article/5231215.html']
    downloader = WebDownloader()
    parser = WebParser()

    for line in lines:
        line = line.strip().replace('\'','').replace(',','')
        html = downloader.download(
            line
        )
        if '[ERROR]' not in html:
            print(parser.parse(html))
