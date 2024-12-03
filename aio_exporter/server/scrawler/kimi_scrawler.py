



import json

from loguru import logger
from selenium.webdriver.support.wait import WebDriverWait

from aio_exporter.utils import load_driver2
from aio_exporter.utils import load_cookies
from aio_exporter.utils.structure import Login,KimiLogin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from time import sleep
import time
from selenium.webdriver.common.action_chains import ActionChains

class KimiChatScrawler:
    def __init__(self):
        self.url = "https://kimi.moonshot.cn/"
        logger.info('start to load kimi webpage ...')
        self.open_window()
        retry = 0
        while (retry <= 2):
            try:
                self.locate_query()
                break
            except:
                time.sleep(5)
                retry += 1
        logger.info('load kimi webpage done...')

    def open_window(self):
        self.driver = load_driver2(headless=True)
        self.driver.get(self.url)
        login = self.load_cookie()
        self.driver.execute_script("localStorage.setItem('access_token', '{}')".format(login.accesstoken))
        self.driver.execute_script("localStorage.setItem('refresh_token', '{}')".format(login.refreshtoken))
        self.driver.get(self.url)


    def load_cookie(self):
        cookies = load_cookies("kimi")
        login = KimiLogin(**cookies)
        for cookie in login.cookies:
            self.driver.add_cookie(cookie)
        return login


    def scroll(self):
        xpath = '//*[@id="msh-chat-pagecontainer"]/div/div/div/div[1]/div[4]/div/div[1]/div[2]/div/button/span[1]/svg'
        ele = self.driver.find_elements(
            By.XPATH, xpath
        )[0]
        action = ActionChains(self.driver)
        action.move_to_element(ele).perform()  # 执行悬停操作
        action.click(ele).perform()

    def click(self,xpath):
        self.driver.find_elements(
            By.XPATH, xpath
        )[0].click()

    def locate_query(self):

        div_element = self.driver.find_element(By.XPATH, "//div[contains(text(), '使用 Kimi 探索版')]")
        actions = ActionChains(self.driver)
        # 将鼠标移动到元素上并点击
        actions.move_to_element(div_element).click().perform()


    def send_query(self, query):
        xpath = '//*[@id="msh-chateditor"]/p'
        text_label = self.driver.find_elements(
            By.XPATH,
            xpath
        )[0]
        # 在搜索框中输入内容
        text_label.send_keys(f'请联网搜索问题:“{query}”并回答，你的回答应当在50字以内')
        time.sleep(5)
        # enter
        text_label.send_keys(Keys.ENTER)
        time.sleep(5)
        try:
            text_label.send_keys(Keys.ENTER)
        except:
            # 可能目前没有办法点击
            time.sleep(5)
            pass

    def gather(self):
        xpath = '//*[@id="msh-chat-pagecontainer"]/div/div/div/div[2]/div/div[3]/div[2]'
        search_res = self.driver.find_elements(
            By.XPATH,
            xpath
        )[0]
        links = search_res.find_elements(By.XPATH , ".//a[@href]")
        urls = []
        # 遍历所有找到的<a>标签
        for link in links:
            # 获取每个<a>标签的URL
            url = link.get_attribute('href')
            urls.append(url)
        return urls

    def new_chat(self):
        xpath = '//*[@id="root"]/div/div[1]/div[1]/div/div[1]/div/div[3]/div'
        self.click(xpath)

    def search(self, queries):

        try:
            self.new_chat()
            time.sleep(5)
            logger.info('start new chat success...')
        except:
            print('error')

        gathered_url = []
        for question in queries:

            logger.info('send query : {} , please wait...'.format(question))

            self.send_query(question)
            time.sleep(10)
            try:
                self.scroll()
            except:
                # 可能输出不够长
                pass

            fail = False
            urls = []
            try:
                urls = self.gather()
                logger.info('gather urls done...')
                if gathered_url and urls[0] == gathered_url[-1][0]:
                    fail = True
            except:
                fail = True

            if len(urls) == 0:
                fail = True
            if fail:
                urls = []
            gathered_url.append(urls)
        return sum(gathered_url , [])

    def close(self):
        self.driver.close()

if __name__ == '__main__':
    kimi = KimiChatScrawler()
    references = kimi.ask(['猫癫痫吃什么药','我的猫吃苯巴比妥没有用，请问还应该吃什么药'])
    print(references)
