

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
from aio_exporter.utils.struct import Login
work_dir = get_work_dir()

def create_bili_cookie():
    driver = load_driver(headless=False)
    driver.get('https://space.bilibili.com/33775467')
    time.sleep(20)
    cookies = driver.get_cookies()
    return cookies
    #
    #
    # driver2 = load_driver(False)
    # driver2.get('https://space.bilibili.com/33775467')
    # for cookie in cookies:
    #     driver2.add_cookie(cookie)

if __name__ == '__main__':
    cookies = create_bili_cookie()
    login = Login(cookies)
    login = asdict(login)

    cookie_dir = work_dir  / 'cookies' / 'bilibili'
    cookie_dir.mkdir(exist_ok=True)

    with open(cookie_dir / 'cookies.json' , 'w' , encoding='utf-8') as f:
        json.dump(login , f , ensure_ascii=False , indent=4)


    # post 到远端
    url = 'http://a4807e0.r20.cpolar.top'
    status = requests.post(
        urljoin(url , 'api/bilibili/login') ,
        json = login
    )
    # 检查远端状态是否更新
    print(status.content)