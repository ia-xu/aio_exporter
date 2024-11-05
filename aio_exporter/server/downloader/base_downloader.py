from aio_exporter.utils import sql_utils

import re
from mmengine import Config
from aio_exporter.utils import get_work_dir

class BaseDownloader:
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = sql_utils.init_sql_session(self.source_name)
        config_file = get_work_dir() / 'aio_exporter' / 'server' / 'config.yaml'
        self.config = Config.fromfile(config_file).scrawler[self.source_name]




    def gather_no_download_ids(self):
        return sql_utils.get_ids_not_in_article_storage(self.session)

    def gather_articles(self, ids):
        return sql_utils.get_articles_by_ids(
            self.session , ids
        )

    def insert_assigned_path(self,id,file_path,status, file_type):
        file_path = str(file_path)
        sql_utils.upsert_article_storage(
            self.session,
            id,
            file_path,
            status,
            file_type
        )

    def upsert_status(self , id , status):
        sql_utils.upsert_article_storage_status(self.session , id , status)


    def clean_title(self , title):
        cleaned_title = re.sub(r'[<>:"/\\|?*]', '__', title)
        # 最多保存60个字,避免超长文件
        if len(cleaned_title) > 50:
            cleaned_title = cleaned_title[:20] + '...' + cleaned_title[-20:]
        cleaned_title = cleaned_title
        return cleaned_title

    def check_file_path_exists(self, file_path):
        file_path = str(file_path)
        return sql_utils.check_file_path_exists(self.session , file_path)

    def gather_ids_without_downloaded(self):
        # 返回所有尚未下载的内容
        return sql_utils.gather_ids_by_storage_status(
            self.session ,
            '尚未开始',
            source=self.source_name
        )

    def gather_article_with_storage(self , ids):
        return sql_utils.gather_article_with_storage(
            self.session,
            ids
        )
