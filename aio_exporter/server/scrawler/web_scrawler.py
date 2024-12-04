from aio_exporter.server.scrawler.base_scrawler import BaseScrawler
from aio_exporter.utils import sql_utils , html_utils
# 基于数据库当中搜集到的文章,自动化的根据文章,向互联网搜索相关的资料
from datetime import datetime
from datetime import timedelta
import re
from aio_exporter.server.parser import WechatParser
from aio_exporter.server.scrawler import KimiChatScrawler
from aio_exporter.utils.llm import llm_query

prompt = """
以下是一段和保险相关的材料
{article}
请仔细阅读以下材料,假设你是一个保险行业的初学者,
假设你在阅读材料的过程中存在无法理解的内容,你打算从互联网搜索你所需要的知识
请给出你的的搜索问题。你应该尽可能的保证给出的提问内容涉及不同的方面，提问的内容不能有重复。
以 python 的 list 形式返回,最多返回4个搜索问题
返回格式如下: 
```python
[
    "问题1",
    ...
]
```
"""

prompt_pro = """
以下是一段和保险相关的材料
{article}
请仔细阅读以下材料,假设你是一个保险行业的资深保险代理人,
你打算从互联网进一步搜索相关的资料，以帮助你更深入的理解当前的话题。
请给出你的的搜索问题。你应该尽可能的保证给出的提问内容涉及不同的方面，提问的内容不能有重复。提问的内容必须有价值，不需要对特别基础的知识进行提问
以 python 的 list 形式返回,最多返回4个搜索问题
返回格式如下: 
```python
[
    "问题1",
    ...
]
```
"""


class WebScrawler(BaseScrawler):
    def __init__(self):
        super().__init__('web' , headless=True)
        self.search = KimiChatScrawler()

    def walk(self):
        # 从数据库当中获取已经下载的文章内容
        articles = sql_utils.get_downloaded_articles_with_storage_by_source('wechat')
        parser = WechatParser()
        last30 = datetime.now() - timedelta(days=30)
        # 获取近一个月的文章
        urls = []
        lastest_articles = articles[articles.issue_date > last30]
        for _ , article in lastest_articles.iterrows():
            # article
            article = parser.parse(article.storage_path)
            article , _  = html_utils.clean_urls(article)
            # 对这篇文章进行提问,和搜索
            questions = self.extract_questions(article)
            # 基于提取出来的问题进行 kimi

            for question in questions:
                urls += self.search.search([question])

        return urls


    def extract_questions(self, article):
        base_questions = llm_query(prompt.format(article=article))
        pro_questions = llm_query(prompt_pro.format(article=article))
        return self.tolist(base_questions) + self.tolist(pro_questions)
    def tolist(self , questions):
        try:
            questions = eval(
                re.search(
                    '```python\n(.*)```', questions, re.DOTALL).group(1)
            )
            return questions
        except:
            return []

if __name__ == '__main__':
    scrawler = WebScrawler()
    scrawler.walk()



