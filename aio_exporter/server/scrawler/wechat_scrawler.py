from pathlib import Path
from aio_exporter.utils import get_work_dir, load_driver, get_headers, load_cookies
from aio_exporter.utils.struct import WechatLogin
from aio_exporter.server.scrawler.base_scrawler import BaseScrawler
from dataclasses import dataclass
import requests
import json
from io import BytesIO
import numpy as np

import datetime
from aio_exporter.utils.errors import WechatGetBizNoError,WechatGetArticlesError
from loguru import logger
import time

@dataclass
class SearchUrls:
    search_bizno: str = "https://mp.weixin.qq.com/cgi-bin/searchbiz"
    search_article : str = "https://mp.weixin.qq.com/cgi-bin/appmsgpublish"

class WechatScrawler(BaseScrawler):
    def __init__(self):
        super().__init__("wechat",True)
        cookies = load_cookies("wechat")
        logger.info('create driver')
        login = WechatLogin(**cookies)
        self.driver.get("https://mp.weixin.qq.com")
        for cookie in login.cookies:
            self.driver.add_cookie(cookie)
        self.driver.get("https://mp.weixin.qq.com")
        self.token = login.token
        self.header = get_headers(self.driver)
        self.max_count = 400  #一次最多获取400篇文章的 url

    def search_bizno(self, name):
        # 搜索特定内容的名称
        params = {
            "action": "search_biz",
            "begin": 0,
            "count": 5,
            "query": name,
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": 1,
        }

        out = requests.get(
            SearchUrls.search_bizno, params=params, headers=get_headers(self.driver)
        )
        response = json.load(BytesIO(out.content))
        if response["base_resp"]["err_msg"] != "ok":
            raise WechatGetBizNoError(response["base_resp"]["err_msg"])
        id_list = response["list"]
        for id in id_list:
            if id["nickname"] == name:
                return id["fakeid"]
        return None


    def count_new_article(self,account, fake_id):
        publish_page = self.get_article_list(fake_id, start=0, count=1)
        publish_count = publish_page['total_count']
        # 判断是否 up 发布了新的内容
        # 检查历史数据，分析已经获取了多少内容的数据
        count_article_by_author = self.count_by_author(account)
        return publish_count - count_article_by_author

    def walk_through_article(self, account , fake_id, count = 50, max_count = 200):
        # 先进行一个小的获取,拿到 page count
        publish_page = self.get_article_list(fake_id , start=0, count=1)
        publish_count = publish_page['total_count']
        # 判断是否 up 发布了新的内容
        # 检查历史数据，分析已经获取了多少内容的数据
        count_article_by_author = self.count_by_author(account)
        article_indices = list(range(publish_count))[::-1]
        # 去除掉已经遍历的部分
        new_article_list = article_indices[count_article_by_author:]
        # 按照50个一个等间隔的划分
        intervals = []
        for i in range(0, len(new_article_list), count):
            intervals.append(new_article_list[i:i+count])

        titles = []
        current_count = 0
        for interval in intervals:
            start = interval[-1]
            count = len(interval)
            # get article list in this interval
            articles = self.get_article_list(fake_id , start, count)
            for row in articles['publish_list']:
                current_count += 1
                if current_count >= max_count:
                    logger.info(f'更新数据库,为{account}找到了{self.max_count}篇文章')
                    logger.info('一次不能太贪心,休息一下吧')
                    return
                if not row['publish_info']:
                    continue
                row = json.loads(row['publish_info'])
                meta = row['appmsgex'][0]
                title = meta['title']
                url = meta['link']
                create_time = datetime.datetime.fromtimestamp(meta['create_time'])
                self.insert_article(account, title, url, create_time)
                logger.debug(f'成功插入文章:\t{create_time}\t{title}!')
                titles.append({'author':account , 'title':title})
            rand_sleep = np.random.randint(3, 10)
            time.sleep(rand_sleep)
        logger.info(f'更新数据库,为{account}找到了{current_count}篇文章')
        return titles
    def get_article_list(self ,  fake_id , start, count):
        params = {
            "sub": "list",
            "search_field": "null",
            "query": "",
            "begin": start,
            "count": count,
            "fakeid": fake_id,
            "type": "101_1",
            "free_publish_type": "1",
            "sub_action": "list_ex",
            "token": self.token,
            "lang": "zh_CN",
            "f": "json",
            "ajax": "1",
        }
        response = requests.get(
            SearchUrls.search_article,
            params=params,
            headers=get_headers(self.driver)
        )
        response = json.load(BytesIO(response.content))
        if response['base_resp']['err_msg'] != 'ok':
            raise WechatGetArticlesError(response['base_resp']['err_msg'])
        publish_page = json.loads(response['publish_page'])
        return publish_page

    def walk(self):
        new_articles = []
        each_count = self.max_count // len(self.config.SubscriptionAccounts)
        for account in self.config.SubscriptionAccounts:
            fake_id = self.search_bizno(account)
            articles = self.walk_through_article(account , fake_id,  max_count = each_count)
            new_articles.extend(articles)
        return new_articles

    def count(self):
        # 遍历公众号，检查还有多少文章没有获取到
        new_counts = {}
        for account in self.config.SubscriptionAccounts:
            fake_id = self.search_bizno(account)
            new_article_count = self.count_new_article(account, fake_id)
            new_counts[account] = new_article_count
        return new_counts


if __name__ == "__main__":
    # 服务端,启动服务，加载 cookie, 并利用requests获取结果
    scrawler = WechatScrawler()
    scrawler.count()
