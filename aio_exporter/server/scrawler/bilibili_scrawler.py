import copy
import json

from aio_exporter.server.scrawler.base_scrawler import BaseScrawler
import time
import random
from selenium.webdriver.common.by import By
from loguru import logger
from selenium.webdriver.common.action_chains import ActionChains

from aio_exporter.utils import get_work_dir, load_driver2, get_headers, load_cookies
from bs4 import BeautifulSoup
from aio_exporter.utils.struct import Login
from aio_exporter.utils import html_utils
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import numpy as np

# 添加了bilibili视频的scrawler
class BilibiliScrawler(BaseScrawler):
    def __init__(self):
        super().__init__("bilibili", True)
        self.max_count = self.config.max_count

        # 尝试添加 cookie, 简化流程
        # 先随便打开一个用户的主页
        # 避免第一次打开网页被要求登录
        # load cookie
        # logger.info('load cookie')
        # self.driver.get('https://space.bilibili.com/405067166')
        # logger.info('create cookie done')

    def load_cookie(self):
        cookies = load_cookies("bilibili")
        login = Login(**cookies)
        for cookie in login.cookies:
            self.driver.add_cookie(cookie)


    def login_status(self):
        self.driver.get('https://space.bilibili.com/405067166')
        # 必须先验证登录通过
        try:
            self.load_cookie()
        except:
            logger.info('登录过期!')
            return False

        time.sleep(1)
        self.driver.get('https://space.bilibili.com/405067166')
        try:
            new_updates = self.gather_video_on_page()
            if len(new_updates) > 0:
                return True
        except:
            pass
        return False




    def walk(self):
        stats = self.count()

        total_updates = sum( v for v in stats.values()) + 1e-5
        stats = { k : int(v / total_updates * self.max_count) for k ,v in stats.items()}
        articles = []
        for account in self.config.SubscriptionAccounts:
            if account['id'] not in stats:
                continue
            if stats[account['id']] < 10:
                continue
            articles += self.walk_through_article(account['name'], account['id'], max_count=stats[account['id']])
        return articles


    def wait(self):
        # 等待页面加载完成
        WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))
        # 获取页面的宽度和高度
        body = self.driver.find_element(By.TAG_NAME, 'body')
        body_width = body.size['width']
        body_height = body.size['height']

        # 计算页面中心的坐标
        center_x = body_width / 2
        center_y = body_height / 2

        # 使用ActionChains将鼠标移动到页面中心
        actions = ActionChains(self.driver)
        actions.move_to_element_with_offset(body, center_x, center_y).perform()

        # 模拟滚动
        time.sleep(2)
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def click(self, close_class):
        ele = self.driver.find_elements(
            By.CLASS_NAME, close_class
        )[0]
        action = ActionChains(self.driver)
        action.move_to_element(ele).perform()  # 执行悬停操作
        action.click(ele).perform()

    def walk_through_article(self, up_name , uid, max_count = 200):
        # 必须先验证登录通过
        try:
            self.load_cookie()
        except:
            logger.info('登录过期或其他异常,请稍后再试!')
            return []
        # 计算当前需要下载的内容数量
        logger.info(f'账号 {up_name} 最多搜集 {max_count} 个视频')
        count = self.video_num(uid)
        if count == -1:
            logger.info(f'获取 {up_name} 视频数量失败')
            return []
        count_article_by_author = self.count_by_author(uid)
        need_update_count = count - count_article_by_author

        url = f"https://space.bilibili.com/{uid}/video"
        self.driver.get(url + f'?tid=0&pn=1&keyword=&order=pubdate')
        self.wait()


        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        if '扫描二维码登录' in soup.text:
            # 找到 叉叉，给他点掉
            # 说明 ip 暂时被封住了，暂时不调用
            logger.info('登录过期,请重新登录且稍后再试')
            return []

        # 一共要获取 max_count ， 不断翻页，直到全部获取
        new_updates = self.gather_video_on_page()
        if not new_updates:
            logger.info('请稍后再试!~')
            return []
        # 获取当前浏览器能够放多少页
        num_in_on_page = len(new_updates)
        # 计算一共需要获取多少页
        updates = []
        c = np.ceil(need_update_count / num_in_on_page)
        for pn in range(int(c) , 0, -1):
            logger.info(f'正在浏览 {up_name} 的第 {pn} 页...')
            self.driver.get(url + f'?tid=0&pn={pn}&keyword=&order=pubdate')
            self.wait()

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            if '扫描二维码登录' in soup.text:
                # 说明遇到了反爬虫
                break

            time.sleep(2 + random.random() * 3)
            new_videos = self.gather_video_on_page()
            if len(new_videos) == 0 :
                logger.info('请稍后再试')
                break
            updates += new_videos
            if len(updates) > max_count:
                # 不要一次性翻页太多
                logger.info('翻页结束')
                break

        if not updates:
            return []

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
                logger.info(f'找到 {up_name} \t {len(titles)}')
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
        try:
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            current_page_update = []

            video_list = soup.find(id='submit-video-list')
            cube = video_list.find(class_='clearfix cube-list')
            for li in cube.find_all('li'):
                link = li.find('a', class_='title')
                if link is None:
                    continue
                link_url = link.get('href')
                link_title = link.get('title')
                meta = li.find(class_='meta').find('span', class_='time').text.strip()
                if link_url.startswith('//www.bilibili.com'):
                    link_url = 'https:' + link_url
                current_page_update.append(
                    {
                        'link': link_url,
                        'title': link_title,
                        'update_time': html_utils.parse_bilibili_time(meta)
                    }
                )
            return current_page_update
        except:
            return []



    def get_name_by_uid(self, uid):
        mapping = {
            data["id"]: data["name"] for data in self.config.SubscriptionAccounts
        }
        return mapping[uid]

    def video_num(self, uid):
        try:
            url = f"https://space.bilibili.com/{uid}/video"
            self.driver.get(url)
            time.sleep(3 + random.random() * 3)
            if 'upload' in self.driver.current_url :
                e = self.driver.find_element(By.CLASS_NAME , 'upload-sidenav')
                count = int(e.text.split('\n')[1])
            else:
                e = self.driver.find_element(By.CLASS_NAME, 'contribution-list-container')
                count = e.find_elements(By.CLASS_NAME, 'num')[0].text
                count = int(count)
            return count
        except:
            return -1


    def count(self):
        # 统计每一个up主目前总共发布了多少的视频
        total = 0

        stats = {}

        # 避免对某一个特定账号访问多次
        accounts = copy.deepcopy(self.config.SubscriptionAccounts)
        random.shuffle(accounts)

        for data in accounts:
            up_name = data["name"]
            uid = data["id"]
            count = self.video_num(uid)
            if count == -1:
                logger.info(f'获取 {up_name} 视频数量失败!')
                continue
            logger.info(f'找到 up {up_name} 的更新数量为 {count}')
            exists_count = self.count_by_author(uid)
            stats[uid] = count - exists_count

            total += count - exists_count
            if total > self.max_count:
                # 集中在这几个账号上进行搜集
                # 这几个账号的更新视频数量已经处理不过来了
                break

        stats_log = {self.get_name_by_uid(uid): c for uid, c in stats.items()}
        logger.info(f'需要新入库的视频数量为: {stats_log}')
        return stats


if __name__ == "__main__":
    scrawler = BilibiliScrawler()
    scrawler.walk()
