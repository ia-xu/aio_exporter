import random
import time
import os
import base64
from pathlib import Path

import requests
import asyncio
import readability
import html_text
import markdownify
import pylcs
import re
from loguru import logger

def to_plain_text(article_content ):
    html_doc = readability.Document(str(article_content))
    # 对于 wechat , html text 能够提取到其中的合理的文本片段
    content = html_text.extract_text(html_doc.summary(html_partial=True))
    return content

def to_markdown(article_content, plan_text):
    markdown_text = markdownify.markdownify(str(article_content))
    res = pylcs.lcs_sequence_idx(plan_text, markdown_text)
    res = [_ for _ in res if _ != -1]

    start = min([_ for _ in res if _ != -1])
    end = max([_ for _ in res if _ != -1])
    valid_md_text = markdown_text[start:end + 1 ]
    return valid_md_text


def clean_html(text):
    text = text.strip().replace(u'\u3000', u' ').replace(u'\xa0', u' ')
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace('﻿','')

    # 删掉不重要的行
    lines = text.splitlines()
    # 过滤掉只有空格和逗号的行
    cleaned_lines = [line for line in lines if not (all(c in " ,\t" for c in line) and ',' in line) ]
    # 合并回一个文本字符串
    text =  "\n".join(cleaned_lines)

    text = text.replace('\u202e','').replace('\u202c','')
    return text


async def download_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
    }
    # 简单地进行 url 请求
    rand = random.randint(1,3)
    time.sleep(3)
    try:
        page_content = requests.get(url , headers = headers)
    except:
        logger.info(f'time out for {url}')
        return None

    return page_content




async def download_urls_async(urls , post_process_fn):
    tasks = [download_url(url) for url in urls]
    results = await asyncio.gather(*tasks)
    if post_process_fn is None:
        return results
    post_process_tasks = [post_process_fn(url , content) for url , content in zip(urls , results)]
    post_process_results = await asyncio.gather(*post_process_tasks)
    return post_process_results


# 一些 markdown 可视化的辅助函数

def markdown_images(markdown):
    # example image markdown:
    # ![Test image](images/test.png "Alternate text")
    images = re.findall(r'(!\[(?P<image_title>[^\]]+)\]\((?P<image_path>[^\)"\s]+)\s*([^\)]*)\))', markdown)
    return images


def img_to_bytes(img_path):
    img_bytes = Path(img_path).read_bytes()
    encoded = base64.b64encode(img_bytes).decode()
    return encoded


def img_to_html(img_path, img_alt):
    img_format = img_path.split(".")[-1]
    img_html = f'<img src="data:image/{img_format.lower()};base64,{img_to_bytes(img_path)}" alt="{img_alt}" style="max-width: 100%;">'

    return img_html


def markdown_insert_images(markdown):
    images = markdown_images(markdown)

    for image in images:
        image_markdown = image[0]
        image_alt = image[1]
        image_path = image[2]
        if os.path.exists(image_path):
            markdown = markdown.replace(image_markdown, img_to_html(image_path, image_alt))
    return markdown


def parse_bilibili_time(time_str):
    import datetime

    # 正则表达式匹配不同的时间格式
    patterns = [
        (r'(\d+)分钟前', lambda x: datetime.datetime.now() - datetime.timedelta(minutes=int(x))),
        (r'(\d+)小时前', lambda x: datetime.datetime.now() - datetime.timedelta(hours=int(x))),
        (r'昨天', lambda: datetime.datetime.now() - datetime.timedelta(days=1)),
        (
        r'^(\d+)-(\d+)$', lambda x, y: datetime.datetime.strptime(f"{datetime.datetime.now().year}-{x}-{y}", "%Y-%m-%d")),
        (r'(\d{4})-(\d{1,2})-(\d{1,2})', lambda x, y, z: datetime.datetime.strptime(f"{x}-{y}-{z}", "%Y-%m-%d"))
    ]

    for pattern, func in patterns:
        match = re.match(pattern, time_str)
        if match:
            dt = func(*match.groups())
            if dt.date() < datetime.datetime.now().date():
                dt = dt.replace(hour=0, minute=0, second=0)
            return dt

    return time_str  # 如果没有匹配的模式，返回None
