
import time
from dataclasses import asdict
from aio_exporter.utils import load_driver
from aio_exporter.utils.structure import KimiLogin
from aio_exporter.utils import get_work_dir
import json


def create_kimi_cookie():
    driver = load_driver(headless=False)
    driver.get('https://kimi.moonshot.cn/')
    time.sleep(20)
    cookies = driver.get_cookies()

    accesstoken = driver.execute_script("return localStorage.getItem('access_token')")
    refreshtoken = driver.execute_script("return localStorage.getItem('refresh_token')")

    return cookies , accesstoken , refreshtoken

if __name__ == '__main__':
    cookies, accesstoken , refreshtoken = create_kimi_cookie()
    login = KimiLogin(cookies , accesstoken , refreshtoken)
    login = asdict(login)

    work_dir = get_work_dir()

    cookie_dir = work_dir / 'cookies' / 'kimi'
    cookie_dir.mkdir(exist_ok=True)

    with open(cookie_dir / 'cookies.json', 'w', encoding='utf-8') as f:
        json.dump(login, f, ensure_ascii=False, indent=4)





