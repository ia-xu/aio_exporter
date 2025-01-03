from pathlib import Path
from aio_exporter.utils import get_work_dir, load_driver , load_driver2, get_headers , load_cookies
from aio_exporter.utils import sql_utils
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

from mmengine import Config

class BaseScrawler:
    def __init__(self, source_name,headless=True):
        # source name : 数据源名称, 详见 sql_utils::Article::source
        self.source_name = source_name
        self.driver = load_driver2(headless=headless) # 非debug的情况可以采用静默模式
        # self.driver = load_driver(headless = headless)
        config_file = get_work_dir() / 'aio_exporter' / 'server' / 'config.yaml'
        self.config = Config.fromfile(config_file).scrawler[self.source_name]
        # 在 workdir 下面创建一个 database,并初始化 database下的数据库
        database = get_work_dir() / 'database'
        database.mkdir(exist_ok=True)
        self.session = sql_utils.init_sql_session(self.source_name)

    def init_sql_session(self):
        # 创建一个 database
        engine = sql_utils.create_database()
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        return session

    def get_prev_articles(self , author):
        ids = sql_utils.get_ids_by_author(self.session , author)
        articles = sql_utils.get_articles_by_ids(self.session , ids)
        return articles

    def count_by_author(self, author):
        return sql_utils.count_articles_by_author(
            self.session ,
            author,
            source = self.source_name
        )

    def insert_article(self, author, title, url, create_time , metainfo = None):
        return sql_utils.insert_if_not_exists(
            self.session,
            title ,
            author,
            url ,
            create_time,
            source = self.source_name,
            metainfo = metainfo
        )

    def close(self):
        self.driver.close()
        self.session.close()
        return

    def __enter__(self):
        # Return the instance itself so it can be used in the `with` block
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Close the driver when exiting the context
        self.close()