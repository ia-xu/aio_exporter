from pathlib import Path
import json
import time
from pathlib import Path
# from selenium import webdriver
from loguru import logger
try:
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from seleniumwire import webdriver
except:
    logger.warning('can not use selenium in this platform')
import platform


def get_work_dir():
    return Path(__file__).parent.parent.parent

def load_driver2(headless = True):
    work_dir = get_work_dir()

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument('window-size=1920x1080')  # 设置窗口大小
    options.add_argument('--start-maximized')  # 窗口最大化
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36")
    if platform.system().lower() == 'linux':
        chrome_driver = '/root/driver/chromedriver-linux64/chromedriver'
    else:
        chrome_driver = work_dir / 'driver' / 'chromedriver.exe'
    driver = webdriver.Chrome(service=Service(executable_path=chrome_driver), options=options)
    return driver



def load_driver(headless = True):
    work_dir = get_work_dir()
    global driver
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    if platform.system().lower() == 'linux':
        chrome_driver = '/root/driver/chromedriver-linux64/chromedriver'
    else:
        chrome_driver = work_dir / 'driver' / 'chromedriver.exe'
    driver = webdriver.Chrome(service=Service(executable_path=chrome_driver), options=chrome_options)
    return driver


def wrap(url , query):
    url = url + '?'
    for k ,v in query.items():
        url = url + f"{k}={v}&"
    return url

def get_headers(driver):
    cookies = driver.get_cookies()
    cookies_str = ""
    for cookie in cookies:
        cookies_str += cookie['name'] + '=' + cookie['value'] + ';'
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36 Edg/130.0.0.0",
        "Cookie": cookies_str,
    }
    return headers

def load_cookies(cls):
    work_dir = get_work_dir()
    with open(work_dir / 'cookies' / cls / 'cookies.json', encoding='utf-8') as f:
        cookies = json.load(f)
    return cookies

