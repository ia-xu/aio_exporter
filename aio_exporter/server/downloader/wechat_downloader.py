import os
import shutil
import asyncio

import requests
from functools import partial
from aio_exporter.server.downloader.base_downloader import BaseDownloader
from aio_exporter.utils.utils import get_work_dir
from aio_exporter.utils import load_driver

from loguru import logger
from tqdm import tqdm
from aio_exporter.utils import sql_utils
from aio_exporter.utils import html_utils
import markdownify
import readability
from bs4 import BeautifulSoup
import hashlib

work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)
wechat_dir = database / 'wechat'
wechat_dir.mkdir(exist_ok=True)

class WechatDownloader(BaseDownloader):

    def __init__(self):
        super().__init__('wechat')
        self.batch_size = 5
        # 单次最多更新的数量
        self.max_assign_count = self.config.max_assign_count
        self.max_download_size = self.config.max_download_size

        # 用于加载一些需要javascript渲染的网页


    def assign_path_for_new_articles(self):
        # 检查更新的id,为这些id分配存储的路径
        # 检查已经下载的 wechat 的 id
        # 判断这些 id 哪些出现在 download 里
        ids = self.gather_no_download_ids()
        logger.info(f'found {len(ids)} wechat articles to insert')
        articles = self.gather_articles(ids)
        locations = []
        count = 0
        for _ , article in tqdm(articles.iterrows()):
            if article.url == 'https://none':
                continue
            count += 1
            if count > self.max_assign_count:
                return locations
            # 分配存储路径,添加到库,将 状态变化为 '尚未开始'
            file_path = self.insert_and_assign_path(article)
            locations .append(
                {
                    'account' : article.author,
                    'title' : article.title ,
                    'location' : str(file_path)
                }
            )
        return locations

    def insert_and_assign_path(self,article):
        # 根据 article 的信息，为article 生成存储的路径
        # 将 article 的信息插入到 download 表中
        # 将 article 的状态更新为 '尚未开始'


        account_dir = wechat_dir / article.author
        account_dir.mkdir(exist_ok=True)
        title = self.clean_title(article.title)

        file_path = account_dir /  f'{article.id}_{title}.html'
        # 检查filepath 是否已经存在
        idx = 0
        while self.check_file_path_exists(file_path):
            # 更新位置
            file_path = account_dir / f'{article.id}_{idx}_{title}.html'
            idx += 1
        logger.info(f'为账号{article.author} 文章分配路径到 {file_path.name}.html')
        self.insert_assigned_path(
            article.id ,
            file_path ,
            '尚未开始' ,
            'file',
            0
        )
        return file_path



    async def post_process_html(self, url , result, new_article = True):
        # 如果 new article == False , 表明现在处理的都是一些用 requests 处理失败的文章
        try:
            if result.status_code != 200:
                logger.info(result.content)
                return None

            # 判断是否被删除
            soup = BeautifulSoup(result.content , 'html.parser')

            maybe_delete =  soup.find(class_= 'weui-msg__text-area')
            if maybe_delete:
                maybe_delete = maybe_delete.text
                if '已被发布者删除' in maybe_delete:
                    return '已删除'
                if '此内容因违规无法查看' in maybe_delete:
                    return '已删除'
                if '经审核涉嫌侵权' in maybe_delete:
                    return '已删除'


            text = ""
            for p in soup.find_all('p'):
                text += p.text

            if '该页面不存在' in text:
                return '不存在'

            if not text and soup.find_all(class_ = 'share_content_page'):
                # 可能是一个需要动态加载的网页内容
                logger.info('use chrome driver to render js webpage')
                driver = load_driver(headless=True)
                driver.get(url)
                html = driver.page_source
                soup = BeautifulSoup(html , 'html.parser')

                text = ""
                for p in soup.find_all('p'):
                    text += p.text
                # 及时关闭
                driver.close()

            if '环境异常' in text or '去验证' in text:
                return None
            article_content = soup.find('div', id='js_content')
            if not article_content:
                return ""

            plan_text = ""
            p_tags = article_content.find_all('p')
            for p_tag in p_tags:
                plan_text += p_tag.get_text() + "\n"
            plan_text = html_utils.clean_html(plan_text)
            if not plan_text:

                # 有一些只发图但是无文字内容的url
                toutu = soup.find(class_ = 'page_top_area')
                if toutu:
                    extra = article_content.find(class_='rich_media_meta_area_extra')
                    extra.extract()
                    left = html_utils.clean_html(markdownify.markdownify(str(article_content)))
                    if not left:
                        return '无文字内容'
                else:
                    clean_content = html_utils.clean_html(markdownify.markdownify(str(article_content)))
                    if clean_content == '![]()':
                        return '无文字内容'

                # 考虑可能是一个微信的想法
                share_notice = article_content.find(class_ = 'share_notice')
                if share_notice:
                    text = html_utils.clean_html(share_notice.text)
                    if text:
                        # 说明是一个微信想法
                        return str(soup)

                # 找 section
                plan_text = ""
                p_tags = article_content.find_all(['p','section'])
                for p_tag in p_tags:
                    plan_text += p_tag.get_text() + "\n"
                plan_text = html_utils.clean_html(plan_text)
                if plan_text:
                    return str(soup)

                return None
            return str(soup)

            # # 删除一些不需要的内容
            # # code 的行数展示
            # code_snippets = article_content.find_all(class_ = 'code-snippet__line-index code-snippet__js')
            # for snippet in code_snippets:
            #     snippet.extract()
            # # <br>换行符
            # for p in article_content.find_all('p'):
            #     if p.find('br') and len(p.contents) == 1:
            #         # 占位符,可以省略
            #         p.extract()
            #
            #
            # # 对图片进行解析处理
            # images = []
            # # 下载图片
            # img_tags = article_content.find_all('img')
            # for idx, img_tag in enumerate(img_tags):
            #     if img_tag.get('data-src') and not img_tag.get('src'):
            #         img_tag['src'] = img_tag['data-src']
            #         # 添加 alt ，区别于超链接，让转出来的 markdown 带有这个链接
            #         img_tag['alt'] = 'img'
            #
            # markdown_text = html_utils.to_markdown(
            #     article_content , plan_text
            # )
            # markdown_text = html_utils.clean_html(markdown_text)
            # return markdown_text
        except:
            return None

    def create_new_download_task(self , new_article = True):

        status = '尚未开始'
        if not new_article:
            status = '下载失败'

        ids_need_download = self.gather_ids_with_status(status)
        article_with_file_path = self.gather_article_with_storage(ids_need_download)
        article_with_file_path = article_with_file_path.sample(frac=1).reset_index(drop=True)
        article_with_file_path = article_with_file_path.iloc[:self.max_download_size]
        for _, row in article_with_file_path.iterrows():
            self.upsert_status(row.id, '正在下载')
        return article_with_file_path['title'].tolist()


    async def download(self, new_article = True):
        # new_article:  默认只尝试下载那些还没有下载过的文章
        # 关于代理，后续使用: https://blog.csdn.net/crayonjingjing/article/details/137596882
        ids_need_download = self.gather_ids_with_status('正在下载')
        article_with_file_path = self.gather_article_with_storage(ids_need_download)

        article_with_file_path = article_with_file_path.sample(frac = 1).reset_index(drop = True)
        # 将文章卸载到指定目录
        download_count = 0
        status = []
        for i in range(0, len(article_with_file_path), self.batch_size):
            batch = article_with_file_path[i:i + self.batch_size]
            if not len(batch):
                continue
            download_count += len(batch)
            # if download_count > self.max_download_size:
            #     logger.info('超出单次下载限制!')
            #     return status
            urls = batch['url'].tolist()  # 获取当前批次的 URL
            # 每次调用 asyncio 的方法，一次性获取10篇文章的 html
            post_fn = partial(self.post_process_html , new_article = new_article)
            results = await html_utils.download_urls_async(urls ,post_fn)  # 下载 HTML
            for (_ ,row) ,result in zip(batch.iterrows(),results):
                if row.url == 'https://none':
                    self.upsert_status(row.id , '无效数据')
                    continue
                if not result:
                    # 说明下载失败
                    logger.info(f'fail {row.url}')
                    self.upsert_status(row.id , '下载失败' ,  row.download_count + 1)
                    status.append({'title':row.title ,'status':'下载失败'})
                elif result == '已删除':
                    logger.info(f'文章 {row.title} 已被删除!')
                    self.upsert_status(row.id, '已被删除', row.download_count + 1)
                    status.append({'title': row.title, 'status': '失效'})
                elif result == '不存在':
                    logger.info(f'文章 {row.title} 不存在!')
                    self.upsert_status(row.id, '不存在', row.download_count + 1)
                    status.append({'title': row.title, 'status': '失效'})
                elif result == '无文字内容':
                    self.upsert_status(row.id, '无文字内容', row.download_count + 1)
                    status.append({'title': row.title, 'status': '无文字内容'})
                else:
                    # 说明下载成功
                    with open(row.storage_path, 'w', encoding='utf-8') as f:
                        f.write(result)
                    prefix = '' if new_article else '重新'
                    logger.info( row.title + ':' + prefix + '下载成功')
                    self.upsert_status(row.id , '下载成功' , row.download_count + 1)
                    status.append({'title':row.title ,'status':'下载成功'})
        return status

    def move_data(self ,  old_prefix = '/root/projects/aio_exporter', new_prefix =  '/mnt/d/root/projects/aio_exporter'):
        # 迁移数据库时需要调用这个函数
        sql_utils.move_data(
            self.session , old_prefix , new_prefix
        )
        #
        # articles_to_update = self.session.query(sql_utils.ArticleStorage).all()
        # for article in articles_to_update:
        #     print(article.storage_path)


if __name__ == '__main__':
    wechat_downloader = WechatDownloader()
    # reset
    # sql_utils.reset_article_storage(wechat_downloader.session)
    # wechat_downloader.clean_download()
    # download
    # wechat_downloader.assign_path_for_new_articles()
    # asyncio.run(wechat_downloader.download(new_article=False))
    # wechat_downloader.move_data()



