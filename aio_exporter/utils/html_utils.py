import random

import requests
import asyncio
import readability
import html_text
import markdownify
import pylcs
import re

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
    valid_md_text = markdown_text[start:end]
    return valid_md_text

def clean_html(text):
    text = text.strip().replace(u'\u3000', u' ').replace(u'\xa0', u' ')
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text


async def download_url(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
    }
    # 简单地进行 url 请求
    rand = random.randint(1,3)
    await asyncio.sleep(rand)
    page_content = requests.get(url , headers = headers)
    return page_content



def download_urls(urls , post_process_fn):
    async def main():
        tasks = [download_url(url) for url in urls]
        results = await asyncio.gather(*tasks)

        post_process_tasks = [post_process_fn(url , content) for url , content in zip(urls , results)]
        post_process_results = await asyncio.gather(*post_process_tasks)
        return post_process_results

    return asyncio.run(main())