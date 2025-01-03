import random
from pathlib import Path
from aio_exporter.utils import get_work_dir, load_driver, get_headers, load_cookies
from aio_exporter.utils.structure import WechatLogin
from aio_exporter.server.scrawler.base_scrawler import BaseScrawler
from dataclasses import dataclass
import requests
import json
import random
import string

from aio_exporter.utils import sql_utils
from io import BytesIO
import numpy as np

import datetime
from aio_exporter.utils.errors import WechatGetBizNoError,WechatGetArticlesError
from loguru import logger
import time

@dataclass
class SearchUrls:
    scan_qrcode: str = 'https://mp.weixin.qq.com/cgi-bin/scanloginqrcode'
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
        self.max_count = self.config.max_count  #一次最多获取400篇文章的 url
        self.num_for_once = self.config.num_for_once # 最大只能设置成20!!
        assert self.num_for_once <= 20


    def login_status(self):
        # # 检查是否能够成功登录
        # self.driver.get("https://mp.weixin.qq.com")
        # params = {
        #     "action": "ask",
        #     "token" : self.token,
        #     "lang": 'zh_CN',
        #     "f": "json",
        #     "ajax": 1,
        # }
        # out = requests.get(
        #     SearchUrls.scan_qrcode, params=params, headers=get_headers(self.driver)
        # )

        # 先用一个简单的方法替代一下
        try:
            self.search_bizno('蓝鲸课堂')
        except:
            return False

        return True


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
        publish_count = self.find_last(account , fake_id)
        # 判断是否 up 发布了新的内容
        # 检查历史数据，分析已经获取了多少内容的数据
        count_article_by_author = self.count_by_author(account)
        new_article_num = publish_count - count_article_by_author
        logger.info(f'数据库需要更新 {account} 的文章数量为 : {new_article_num}')
        return new_article_num

    def find_last(self, account , fake_id):
        # 先进行一个小的获取,拿到 page count
        publish_page = self.get_article_list(fake_id , start=0, count=1)
        publish_count = publish_page['total_count']

        # 这个拿到的数量可能不是特别准，尝试进行一次获取
        start = max(0,publish_count - 20)
        total_num = -1
        while start != 0 or total_num < 0:
            # 尝试获取文章数量
            articles = self.get_article_list(fake_id, start, 20)
            time.sleep(random.random() * 2)

            article_num = len(articles['publish_list'])
            if not articles['publish_list']:
                start = max(0 , start - 20)
            else:
                total_num = start + article_num
                break

        logger.info(f'确认! {account} 文章数量总数为 {total_num}')
        return total_num

    def get_new_article_list(self, account, publish_count):
        mask = np.zeros(publish_count)
        articles = self.get_prev_articles(account)
        if 'metainfo' in articles.columns:
            for queryinfo in articles['metainfo'].unique():
                queryinfo = json.loads(queryinfo)
                diff = publish_count - queryinfo['publish_count']
                start = queryinfo['start']
                rid = queryinfo['rid']
                mask[diff + start + rid] = 1
        last = -1
        for  index in range(len(mask)):
            if mask[index] == 0:
                last = index
                continue
            break
        # 老的文章放在前面
        return list(range(last + 1 ))[::-1]




    def walk_through_article(self, account , fake_id, max_count = 200):
        # 获取当前文章数
        publish_count = self.find_last(account , fake_id)

        time.sleep(random.random() * 3)

        # 判断是否 up 发布了新的内容
        # 检查历史数据，分析已经获取了多少内容的数据
        new_article_list = self.get_new_article_list(account , publish_count)

        # 按照50个一个等间隔的划分
        count = self.num_for_once
        intervals = []
        for i in range(0, len(new_article_list), count):
            intervals.append(new_article_list[i:i+count])


        titles = []
        current_count = 0
        failure = 0
        for interval in intervals:
            start = interval[-1]
            count = len(interval)
            # get article list in this interval
            articles = self.get_article_list(fake_id , start, count)
            # 把这些文章倒过来,越老的文章越先被加入到库当中
            for rid , row in enumerate(articles['publish_list'][::-1]):
                rid = len(articles['publish_list']) - 1 - rid
                current_count += 1
                if current_count >= max_count:
                    logger.info(f'更新数据库,为{account}找到了{current_count}篇文章')
                    logger.info('一次不能太贪心,休息一下吧')
                    return titles

                query_info = json.dumps({'start' : start , 'count' : count , 'rid' : rid, 'publish_count' :  publish_count } , ensure_ascii=False)

                if not row['publish_info']:
                    failure += 1
                    # 为了避免数据库问题,插入一个假的内容
                    title = ''.join(random.choices(string.ascii_lowercase + string.ascii_uppercase + string.digits, k=13))
                    url = 'https://none'
                    self.insert_article(account , title , url , datetime.datetime.now() , metainfo=query_info)
                    continue
                row = json.loads(row['publish_info'])
                appmsgex = row['appmsgex']
                for mid , meta in enumerate(appmsgex):
                    # 每天可能会更新很多的文章，需要遍历当前所有的文章列表
                    title = meta['title']
                    url = meta['link']
                    create_time = datetime.datetime.fromtimestamp(meta['create_time'])
                    status = self.insert_article(account, title, url, create_time , metainfo = query_info)
                    if status:
                        logger.debug(f'成功插入当天第{mid+1}篇文章:\t{create_time}\t{title}!')
                        titles.append({'author':account , 'title':title})
                    else:
                        logger.info('why?')
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
        # 首先统计每一个部分所需要更新的数量
        stats = self.count()
        # 根据 stats 进行权重分配
        total_updates = sum( v for v in stats.values())
        stats = { k : int(v / total_updates * self.max_count) for k ,v in stats.items()}

        logger.info(f'current search stats: {stats}')
        new_articles = []
        each_count = self.max_count // len(self.config.SubscriptionAccounts)
        for account in self.config.SubscriptionAccounts:
            if stats[account] <= 10:
                # 要更新的文章数量不多，不过多的占用查询资源
                logger.info(f'Skip {account} for article num {stats[account]} not too many')
                continue
            try:
                fake_id = self.search_bizno(account)
            except:
                print('account error !! {}'.format(account))
                continue
            articles = self.walk_through_article(account , fake_id,  max_count = stats[account])
            new_articles.extend(articles)
            if len(new_articles) >= self.max_count:
                break
        return new_articles

    def count(self):
        # 遍历公众号，检查还有多少文章没有获取到
        new_counts = {}
        for account in self.config.SubscriptionAccounts:
            fake_id = self.search_bizno(account)
            new_article_count = self.count_new_article(account, fake_id)
            new_counts[account] = new_article_count
            sleep = random.randint(1,5)
            time.sleep(sleep)
        return new_counts


if __name__ == "__main__":
    # 服务端,启动服务，加载 cookie, 并利用requests获取结果
    scrawler = WechatScrawler()
    # scrawler.walk()
    # scrawler.login_status()
    # scrawler.walk()
    # print(scrawler.count())
    fake_id = scrawler.search_bizno('深蓝保')
    articles = scrawler.walk_through_article('深蓝保', fake_id, max_count=500)
    # articles = scrawler.get_article_list(fake_id , 0 , 20)