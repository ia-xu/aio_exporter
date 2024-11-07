
import json
import time
from pathlib import Path
# from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from dataclasses import asdict
import requests
import json
from urllib.parse import urljoin
from PIL import Image
from io import BytesIO
# import cv2
# import numpy as np
from aio_exporter.utils import get_work_dir
from seleniumwire import webdriver
from aio_exporter.utils import load_driver
from aio_exporter.utils.struct import WechatLogin
work_dir = get_work_dir()





def create_wechat_cookie():
    driver = load_driver(headless=False)
    # login and export cookie
    driver.get('https://mp.weixin.qq.com')
    # 15s 内登录
    time.sleep(15)

    get_list = driver.requests
    token = None
    for request in get_list:
        if request.url == 'https://mp.weixin.qq.com/cgi-bin/bizlogin?action=login':
            try:
                response = json.loads(request.response.body.decode())
                redirect_url = response['redirect_url']
                token = redirect_url.split('token=')[1]
            except:
                pass
    cookies = driver.get_cookies()
    # 将获取到的  cookies 和 token 进行返回
    return cookies , token

if __name__ == '__main__':
    # 第一步,比较简单,直接将获取到的 cookie 和 token 保存到本地
    cookies , token = create_wechat_cookie()
    login = WechatLogin(cookies , token)
    login = asdict(login)

    # cookie_dir = work_dir  / 'cookies' / 'wechat'
    # cookie_dir.mkdir(exist_ok=True)
    #
    # with open(cookie_dir / 'cookies.json' , 'w' , encoding='utf-8') as f:
    #     json.dump(login , f , ensure_ascii=False , indent=4)

    # post 到远端
    url = 'http://a4807e0.r20.cpolar.top'
    status = requests.post(
        urljoin(url , 'api/wechat/login') ,
        json = login
    )
    # 检查远端状态是否更新
    print(status.content)





