import json

from aio_exporter.server.scrawler.base_scrawler import BaseScrawler
import time
import random
from selenium.webdriver.common.by import By
from loguru import logger
from bs4 import BeautifulSoup
from aio_exporter.utils import html_utils
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import numpy as np

# 添加了bilibili视频的scrawler
class BilibiliScrawler(BaseScrawler):
    def __init__(self):
        super().__init__("bilibili", False)
        self.max_count = self.config.max_count

    def walk(self):
        stats = self.count()
        stats_log = { self.get_name_by_uid(uid): c for uid , c in stats.items()}
        logger.info(f'找到 up 更新视频数量为 : {stats_log}')

        total_updates = sum( v for v in stats.values())
        stats = { k : int(v / total_updates * self.max_count) for k ,v in stats.items()}
        for account in self.config.SubscriptionAccounts:
            if stats[account['id']] < 10:
                continue

            articles = self.walk_through_article(account['name'], account['id'], max_count=stats[account['id']])


    def walk_through_article(self, up_name , uid, max_count = 200):
        # 计算当前需要下载的内容数量
        count = self.video_num(uid)
        count_article_by_author = self.count_by_author(up_name)
        need_update_count = count - count_article_by_author

        url = f"https://space.bilibili.com/{uid}/video"
        self.driver.get(url)

        # 一共要获取 max_count ， 不断翻页，直到全部获取
        new_updates = self.gather_video_on_page()
        # 获取当前浏览器能够放多少页
        num_in_on_page = len(new_updates)
        # 计算一共需要获取多少页
        updates = []
        c = np.ceil(need_update_count / num_in_on_page)
        for pn in range(int(c) , 0, -1):
            self.driver.get(url + f'?tid=0&pn={pn}&keyword=&order=pubdate')
            time.sleep(2 + random.random() * 3)
            updates += self.gather_video_on_page()
        valid_updates = []
        hash_ = set()
        for u in updates:
            if u['title'] not in hash_:
                hash_.add(u['title'])
                valid_updates.append(u)
        # 从后往前,越老越先插入
        valid_updates = sorted(valid_updates , key= lambda x: x['update_time'])

        titles = []
        for video_info in valid_updates:
            if len(titles) >= max_count:
                logger.info(f'已经为账号 {up_name} 找到 {len(titles)} 个视频')
                return titles
            meta_info = {
                'up_name' : up_name
            }
            meta_info = json.dumps(meta_info , ensure_ascii=False , indent=2)
            status = self.insert_article(
                uid,
                video_info['title'],
                video_info['link'],
                video_info['update_time'],
                metainfo=meta_info
            )
            if status:
                logger.info(f'为账号 {up_name} 找到视频: {video_info["title"]}')
                titles.append({'author': up_name, 'title': video_info['title']})

        return titles


    def gather_video_on_page(self):
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        current_page_update = []
        for li in soup.find(id='submit-video-list').find(class_='clearfix cube-list').find_all('li'):
            link = li.find('a', class_='title')
            if link is None:
                continue
            link_url = link.get('href')
            link_title = link.get('title')
            meta = li.find(class_='meta').find('span', class_='time').text.strip()
            current_page_update.append(
                {
                    'link': link_url,
                    'title': link_title,
                    'update_time': html_utils.parse_bilibili_time(meta)
                }
            )
        return current_page_update




    def get_name_by_uid(self, uid):
        mapping = {
            data["id"]: data["name"] for data in self.config.SubscriptionAccounts
        }
        return mapping[uid]

    def video_num(self, uid):
        url = f"https://space.bilibili.com/{uid}/video"
        self.driver.get(url)
        time.sleep(random.random() * 3)
        e = self.driver.find_element(By.CLASS_NAME, 'contribution-list-container')
        count = e.find_elements(By.CLASS_NAME, 'num')[0].text
        count = int(count)
        return count


    def count(self):
        # 统计每一个up主目前总共发布了多少的视频
        stats = {}
        for data in self.config.SubscriptionAccounts:
            up_name = data["name"]
            uid = data["id"]
            count = self.video_num(uid)
            exists_count = self.count_by_author(uid)
            stats[uid] = count - exists_count
        return stats


if __name__ == "__main__":
    scrawler = BilibiliScrawler()
    scrawler.walk()
