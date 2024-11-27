import time

from aio_exporter.utils import load_driver2
from aio_exporter.utils import get_work_dir
from aio_exporter.utils.structure import ZhihuLogin
import json
from dataclasses import asdict

def create_zhihu_cookie():
    driver = load_driver2(headless=False)
    driver.get('https://www.zhihu.com')
    time.sleep(15)
    get_list = driver.requests
    cookies = driver.get_cookies()
    return cookies

work_dir = get_work_dir()

cookies = create_zhihu_cookie()


zse_code = input('输入你的zse码，参考https://forum-zh.obsidian.md/t/topic/36833/3 \n')
login = ZhihuLogin(cookies = cookies, zse_ck=zse_code)
login = asdict(login)

cookie_dir = work_dir  / 'cookies' / 'zhihu'
cookie_dir.mkdir(exist_ok=True)

with open(cookie_dir / 'cookies.json' , 'w' , encoding='utf-8') as f:
    json.dump(login , f , ensure_ascii=False , indent=4)
