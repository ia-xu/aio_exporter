from aio_exporter.utils import sql_utils , html_utils
import pandas as pd
from aio_exporter.server.downloader import BiliBiliDownloader
from aio_exporter.server.downloader import WechatDownloader
from aio_exporter.server.scrawler import WechatScrawler
import random
from pathlib import Path
import shutil
from functools import partial
import asyncio
from tqdm import tqdm
from loguru import logger
import time
from aio_exporter.utils import load_driver


downloader = BiliBiliDownloader()
wechat_downloader = WechatDownloader()
# 对于存量的历史文章，不需要通过 crontab 的方式定时触发，可以一次性批量的下载
async def download_bilibili():

    # downloader.max_assign_count = 1000
    # 一次性放进去
    # downloader.assign_path_for_new_video()
    source = 'bilibili'
    session = sql_utils.init_sql_session(source)
    data = sql_utils.get_storage(session)
    data = pd.DataFrame(data)
    status = data.groupby('status').count().loc[:, 'id'].reset_index()
    ids = data[data.status == '尚未开始'].id.to_list()

    articles = downloader.gather_article_with_storage(ids)
    articles = articles.sample(frac=1, replace=False)
    # 用 for 循环依次下载
    for _ , row in tqdm(articles.iterrows()):
        url2f = [(row.url,row.storage_path)]
        if '383587023' in str(url2f[0][1]):
            # 这个人转载了太多的公开课，先不管他
            continue

        print('正在下载' , url2f)
        results = await downloader.adownload_videos(url2f)
        result = results[0]

        if result == '下载失败':
            logger.info(f'fail {row.title}')
            downloader.upsert_status(row.id, '下载失败', row.download_count + 1)
        elif result == '下载成功':
            logger.info(f'success {row.title}')
            downloader.upsert_status(row.id, '下载成功', row.download_count + 1)
        await asyncio.sleep(2)


def gather_article():
    logger.info('start to gather wechat article')
    scrawler = WechatScrawler()
    status = scrawler.login_status()


    # 然后开始下载数据
    # 我们每一次尽量集中的下载一个公众号下面的文章
    account = random.choice(scrawler.config['SubscriptionAccounts'])
    # account = random.choice(['保险一哥','蓝鲸insurance','蓝鲸课堂','关哥说险','明亚保险经纪'])
    fake_id = scrawler.search_bizno(account)
    articles = scrawler.walk_through_article(account, fake_id, max_count=500)
    return articles



async def download_wechat():
    # 放行
    wechat_downloader.max_assign_count = 10000
    wechat_downloader.assign_path_for_new_articles()

    source = 'wechat'
    session = sql_utils.init_sql_session(source)
    data = sql_utils.get_storage(session)
    data = pd.DataFrame(data)
    status = data.groupby('status').count().loc[:, 'id'].reset_index()
    ids = data[data.status == '尚未开始'].id.to_list()

    if len(ids) < 20:
        gather_article()
        # 重新下载
        result = await download_wechat()
        return result

    articles = wechat_downloader.gather_article_with_storage(ids)
    articles = articles.sample(frac=1, replace=False)
    # 从历史下载当中拷贝,先大批量解决一次问题
    for _, row in tqdm(articles.iterrows()):
        tgt_path = Path(row['storage_path'])
        prev_path = row['storage_path'].replace(
            '/mnt/d/root/projects/aio_exporter/database/download/wechat',
            '/mnt/d/root/projects/aio_exporter/database/wechat.bak/wechat'
        )

        name = '_'.join(tgt_path.name.split('_')[1:])
        account_dir = Path('/mnt/d/root/projects/aio_exporter/database/wechat.bak/wechat') / tgt_path.parent.name
        prev_download = list(account_dir.glob('*{}'.format(name)))
        if len(prev_download) == 1:
            logger.info('find prev download file: {}'.format(prev_download[0].name))
            shutil.copy(
                prev_download[0], tgt_path
            )
            wechat_downloader.upsert_status(row.id, '下载成功', row.download_count + 1)

    # 然后对没有下载过的文章进行下载
    # 重新获取
    data = sql_utils.get_storage(session)
    data = pd.DataFrame(data)
    status = data.groupby('status').count().loc[:, 'id'].reset_index()
    ids = data[data.status == '尚未开始'].id.to_list()

    articles = wechat_downloader.gather_article_with_storage(ids)
    articles = articles.sample(frac=1, replace=False)

    driver = load_driver(headless=True)
    post_fn = partial(wechat_downloader.post_process_html,
                      new_article=False,
                      driver=driver
                      )
    for _ , row in articles.iterrows():

        if row.url == 'https://none':
            wechat_downloader.upsert_status(row.id, '无效数据')
            continue


        urls = [row.url]
        results = await html_utils.download_urls_async(urls, post_fn)  #
        result = results[0]

        if not result:
            # 说明下载失败
            logger.info(f'fail {row.url}')
            wechat_downloader.upsert_status(row.id, '下载失败', row.download_count + 1)
        elif result == '已删除':
            logger.info(f'文章 {row.title} 已被删除!')
            wechat_downloader.upsert_status(row.id, '已被删除', row.download_count + 1)
        elif result == '不存在':
            logger.info(f'文章 {row.title} 不存在!')
            wechat_downloader.upsert_status(row.id, '不存在', row.download_count + 1)
        elif result == '无文字内容':
            wechat_downloader.upsert_status(row.id, '无文字内容', row.download_count + 1)
        else:
            # 说明下载成功
            with open(row.storage_path, 'w', encoding='utf-8') as f:
                f.write(result)
            prefix = '' if False else '重新'
            logger.info(row.title + ':' + prefix + '下载成功')
            wechat_downloader.upsert_status(row.id, '下载成功', row.download_count + 1)

if __name__ == '__main__':
    # while True:
    #     gather_article()
    #     time.sleep(60)

    # asyncio.run(download_bilibili())
    asyncio.run(download_wechat())



