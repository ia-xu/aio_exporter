from aio_exporter.utils import sql_utils

import re
from mmengine import Config
from aio_exporter.utils import get_work_dir
import shutil

work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)

class BaseDownloader:
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = sql_utils.init_sql_session(self.source_name)
        config_file = get_work_dir() / 'aio_exporter' / 'server' / 'config.yaml'
        self.config = Config.fromfile(config_file).downloader[self.source_name]



    def gather_no_download_ids(self):
        return sql_utils.get_ids_not_in_article_storage(self.session)

    def gather_articles(self, ids):
        return sql_utils.get_articles_by_ids(
            self.session , ids
        )

    def insert_assigned_path(self,id,file_path,status, file_type,download_count):
        file_path = str(file_path)
        sql_utils.upsert_article_storage(
            self.session,
            id,
            file_path,
            status,
            file_type,
            download_count
        )

    def upsert_status(self , id , status , count = None):
        sql_utils.upsert_article_storage_status(self.session , id , status, count)


    def clean_title(self , title):
        cleaned_title = re.sub(r'[<>:"/\\|?*]', '__', title)
        # 最多保存60个字,避免超长文件
        if len(cleaned_title) > 50:
            cleaned_title = cleaned_title[:20] + '...' + cleaned_title[-20:]
        cleaned_title = cleaned_title.replace(' ','')
        return cleaned_title

    def check_file_path_exists(self, file_path):
        file_path = str(file_path)
        return sql_utils.check_file_path_exists(self.session , file_path)

    def gather_ids_with_status(self , status = '尚未开始'):
        # 返回所有尚未下载的内容
        return sql_utils.gather_ids_by_storage_status(
            self.session ,
            status,
            source=self.source_name
        )

    def gather_article_with_storage(self , ids):
        return sql_utils.gather_article_with_storage(
            self.session,
            ids
        )

    def clean_download(self, ):
        # 用于调试结果,清理所有已经下载的内容
        sql_utils.clear_article_storage(self.session)
        download_dir = work_dir / 'database' / 'download'
        shutil.rmtree(download_dir)
        download_dir.mkdir(exist_ok=True)
        source_dir = database / self.source_name
        source_dir.mkdir(exist_ok=True)