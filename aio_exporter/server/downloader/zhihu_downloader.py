import json

from aio_exporter.utils import load_driver2
from aio_exporter.utils import load_cookies
import readability
import markdownify
import html_text
import os
from datetime import datetime
import re
from pathlib import  Path
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from contextlib import contextmanager
from aio_exporter.utils import sql_utils , html_utils
from aio_exporter.server.downloader.base_downloader import BaseDownloader
from aio_exporter.utils.utils import get_work_dir
from loguru import logger

work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)
zhihu_dir = database / 'zhihu'
zhihu_dir.mkdir(exist_ok=True)


class ZhihuDownloader(BaseDownloader):
    def __init__(self):
        self.driver = None
        super().__init__('zhihu')

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
    def request_session(self):
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

    def find_author(self,url ,soup):
        if 'question' in url:
            author = 'question'
        elif 'zhuanlan' in url:
            author = soup.find(class_='AuthorInfo').text
        elif 'tardis' in url:
            author = 'seller'
        else:
            raise NotImplementedError()
        return author

    def find_issue_date(self , url , soup):
        if 'zhuanlan' in url or 'tardis' in url:
            issue_date = soup.find(class_ = 'ContentItem-time').text
            # 从中提取出来 20xx-xx-xx 的日期
            date_str = re.search('\d{4}-\d{2}-\d{2}' , issue_date).group()
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj
        elif 'question' in url:
            issue_date = None
        else:
            raise NotImplementedError()
        return issue_date

    def find_metainfo(self, url , soup):
        meta = {}
        if 'question' in url :
            meta['question'] = soup.find(class_ = 'QuestionHeader-title').text
            # 给出当前所有列举的回答
            meta['author'] = []
            for author in soup.find_all(class_ = 'UserLink AuthorInfo-name'):
                meta['author'].append(html_utils.clean_html(author.text))
            meta['issue_date'] = []
            for issue_date in soup.find_all(class_ = 'ContentItem-time'):
                meta['issue_date'].append(html_utils.clean_html(issue_date.text))

        return json.dumps(meta , ensure_ascii=False )


    def check_status(self):
        # 找一篇历史文章重新下载
        test_url = 'https://zhuanlan.zhihu.com/p/260085891'
        # 检查下载结果是否包含正确内容
        html = self._download(test_url)
        valid_texts = [
            '所以需要看重综合意外，挑选出较实用的那一款，尤其是常年出差的工作党，更需要看关于交通出行方面的综合保障。',
            '所以今天学姐打算和大家好好聊聊意外险，本文篇幅较长，心急的朋友可以看看学姐之前写过的浓缩版的科普文哦',
            '因此，我们在挑选意外的时候需要根据年龄段的不同，来选择保障内容侧重点不同的意外险。像小孩子和老年人磕磕绊绊很常见，这个年龄的人群就需要着重看意外医疗的保障是否充足。',
            '亚太超人把猝死也纳入保障范围内，还算是跟得上意外险的潮流，适合工作强度很大的朋友，比如那些经常熬夜、作息不规律的上班一族。'
        ]
        return all([ text in html for text in valid_texts])

    def download_with_record(self , url):
        # 对网页进行下载，并主动添加到数据库当中
        # 这里的逻辑和正常下载逻辑不同，这里是首先主动的解析url,然后将 url 添加到 article 库当中
        # 然后分配下载地址，并完成后续操作

        # 首先检查 是否存在 url 对应的内容
        articles = sql_utils.get_article_by_url(self.session , url)
        if articles:
            # 说明之前处理过，不重复处理
            storage_path = self.gather_article_with_storage([_.id for _ in articles]).storage_path[0]
            if os.path.exists(storage_path):
                logger.info('加载已经下载过的文档: {}'.format(Path(storage_path).name))
                with open(storage_path , 'r' , encoding='utf-8') as f:
                    return f.read()


        html = self._download(url)
        if '[ERROR]' in html:
            return html

        articles = self.insert_new_download_article(url , html)
        article = articles[0]
        article_download_path = self.assign_path(article )
        try:

            with open(article_download_path , 'w' , encoding='utf-8') as f:
                f.write(html)
            # 这里简单一点，不考虑重试或者其他情况
            self.upsert_status(article.id , '下载成功' , 1)
        except:
            self.upsert_status(article.id, '下载失败', 1)
        return html




    def assign_path(self , article ):
        # 分配下载地址
        account_dir = zhihu_dir / article.author
        account_dir.mkdir(exist_ok=True)
        title = self.clean_title(article.title)
        if article.author == 'question':
            act_author = '__'.join(json.loads(article.metainfo)['author'])
            title = act_author + '_' + title

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




    def insert_new_download_article(self, url , html):
        soup = BeautifulSoup(html, 'lxml')
        title = soup.find('title').text
        author = self.find_author(url , soup)
        issue_date = self.find_issue_date(url , soup)
        metadata = self.find_metainfo(url , soup)

        # 插入新的数据
        sql_utils.insert_if_not_exists(
            self.session , title , author , url , issue_date , self.source_name ,metadata
        )
        # 分配下载路径,并下载
        articles = sql_utils.get_article_by_url(self.session, url)
        return articles



    def _download(self , url):
        with self.request_session() as session:
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
    from aio_exporter.server.parser import ZhihuParser
    # html = ZhihuDownloader().download_with_record(
    #     # 'https://www.zhihu.com/question/20745287'
    #     # 'https://www.zhihu.com/tardis/bd/art/506750046'
    #     'https://www.zhihu.com/question/38632401/answer/1060250796'
    # )
    # parse = ZhihuParser().parse(html)

    zhihudownloader = ZhihuDownloader()
    zhihudownloader.check_status()







