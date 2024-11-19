import tempfile
from pathlib import Path
from aio_exporter.server.downloader.base_downloader import BaseDownloader
from loguru import logger
from aio_exporter.utils import sql_utils
from aio_exporter.utils import html_utils
from tqdm import tqdm
from aio_exporter.utils.utils import get_work_dir
import asyncio
import subprocess

from aio_exporter.utils import load_cookies

work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)
bilibili_dir = database / 'bilibili'
bilibili_dir.mkdir(exist_ok=True)


class BiliBiliDownloader(BaseDownloader):
    def __init__(self):
        super().__init__('bilibili')
        self.max_assign_count = self.config.max_assign_count
        self.max_download_size = self.config.max_download_size
        # 允许同时存在 4 个正在被下载的数据
        self.batch_size = self.config.batch_size

        # 获取 yutto 所需要的 cookie
        self.env_name = 'scrawl'
        cookies = load_cookies("bilibili")
        self.sessdata = None
        for cookie in cookies['cookies']:
            if 'SESSDATA' in cookie['name']:
                self.sessdata = cookie['value']


    def assign_path_for_new_video(self):
        # 对于up新更新的视频，加入到下载队列当中
        ids = self.gather_no_download_ids()
        logger.info(f'found {len(ids)} bilibili video to insert')

        # 获取到这些视频的相关信息
        articles = self.gather_articles(ids)

        locations = []
        count = 0
        for _ , article in tqdm(articles.iterrows()):

            count += 1
            if count > self.max_assign_count:
                return locations

            file_path = self.insert_and_assign_path(article)
            locations.append(
                {
                    'account': article.author,
                    'title': article.title,
                    'location': str(file_path)
                }
            )
        return locations

    def insert_and_assign_path(self, article):
        account_dir = bilibili_dir / article.author
        account_dir.mkdir(exist_ok=True)
        title = self.clean_title(article.title)

        # 目前下载到一个指定文件夹
        file_path = account_dir / f'{article.id}_{title}'
        # 检查filepath 是否已经存在
        idx = 0
        while self.check_file_path_exists(file_path):
            # 更新位置
            file_path = account_dir / f'{article.id}_{idx}_{title}'
            idx += 1

        logger.info(f'为账号{article.author} 文章分配路径到 {file_path.name}')
        self.insert_assigned_path(
            article.id,
            file_path,
            '尚未开始',
            'folder',
            0
        )
        return file_path

    def create_new_download_task(self , new_article = True):
        # 抽取一部分任务，将这些任务的状态更新为正在下载
        status = '尚未开始'
        if not new_article:
            status = '下载失败'
        ids_need_download = self.gather_ids_with_status(status)
        # 获取文件的下载路径
        if not ids_need_download:
            return []
        article_with_file_path = self.gather_article_with_storage(ids_need_download)
        article_with_file_path = article_with_file_path.sample(frac=1).reset_index(drop=True)
        article_with_file_path = article_with_file_path.iloc[:self.max_download_size]
        for _ , row in article_with_file_path.iterrows():
            self.upsert_status(row.id , '正在下载')
        return article_with_file_path['title'].tolist()

    async def download(self):
        ids_need_download = self.gather_ids_with_status('正在下载')
        logger.info(f'找到需要下载的视频数量: {len(ids_need_download)}')
        # 获取文件的下载路径
        article_with_file_path = self.gather_article_with_storage(ids_need_download)
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
            u2f = []
            for _ , row in batch.iterrows():
                u2f.append((row.url , row.storage_path))

            results = await self.adownload_videos(u2f)  # 下载 HTML
            for (_, row), result in zip(batch.iterrows(), results):
                if result == '下载失败':
                    logger.info(f'fail {row.title}')
                    self.upsert_status(row.id, '下载失败', row.download_count + 1)
                    status.append({'title': row.title, 'status': '下载失败'})
                elif result == '下载成功':
                    logger.info(f'success {row.title}')
                    self.upsert_status(row.id, '下载成功', row.download_count + 1)
                    status.append({'title': row.title, 'status': '下载成功'})
        return status

    async def adownload_videos(self, u2f):
        tasks = [self.adownload_video(url , path) for url, path in u2f]
        results = await asyncio.gather(*tasks)
        return results

    async def adownload_video(self, url, path):
        # 叫醒 cmd, 帮我下载视频
        # (video 720p 30fps hevc > avc / audio 128kbps aac)
        path = Path(path)

        if not path.parent.exists():
            # up 主的文件夹
            path.parent.mkdir()

        if not path.exists():
            path.mkdir()

        if path.exists() and len([file for file in path.glob('*.mp4')]) > 0 :
            return '下载成功'

        conda_path = '/root/miniconda3/bin/conda'
        command = f"{conda_path} run -n {self.env_name} yutto -b {url} -d {path} -q 64 -aq 30232 --download-vcodec-priority hevc,avc,av1 -c '{self.sessdata}' " + "-tp '{title}/{id}-{name}'"
        try:
            subprocess.run(command, shell=True, check=True)
            return '下载成功'
        except:
            # import traceback
            # traceback.print_exc()
            # import ipdb;ipdb.set_trace()
            return '下载失败'


if __name__ == '__main__':
    bilibili_downloader = BiliBiliDownloader()
    bilibili_downloader.clean_download()
    bilibili_downloader.assign_path_for_new_video()
    # bilibili_downloader.create_new_download_task()
    # asyncio.run(bilibili_downloader.download())
    # /root/miniconda3/bin/conda run -n scrawl yutto https://www.bilibili.com/video/BV1zkUPY6ErH/ -d ./td -q 64 -aq 30232 --download-vcodec-priority hevc,avc,av1 -c '59b8f149%2C1747458990%2C110a3%2Ab1CjCgwkrIk9Bh5JpGdjFuXyC0JE8ILNOyfsNHSTCVGiaLNo5d86Awi1K1fLLPEIP8mmQSVlROMHprandZdGtmZ1JDLUZVWVhfZWlCUExOMkVlRGhacHZLeU9XVnF5ZFVkY0xzenpVMFExY3pjRlkxRkNXaE9lbkRNWGtGTW9OMkZiZmIzUlh6V1ZBIIEC'