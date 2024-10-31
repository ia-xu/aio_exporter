from pathlib import Path
import json
import time
from pathlib import Path
# from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from seleniumwire import webdriver



def get_work_dir():
    return Path(__file__).parent.parent.parent


def load_driver(headless = True):
    work_dir = get_work_dir()
    global driver
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

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


