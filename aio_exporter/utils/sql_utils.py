import shutil
from typing import List
from sqlalchemy import select
from sqlalchemy import func
from pathlib import Path
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from .utils import get_work_dir
from loguru import logger
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import inspect, Column, Integer
from sqlalchemy.sql import text
from sqlalchemy.exc import OperationalError


Base = declarative_base()

# 记录文章的来源信息
class Article(Base):
    __tablename__ = 'users'
    # 在数据库当中的编号
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 文章的标题
    title = Column(String)
    # author
    author = Column(String)
    # 链接
    url = Column(String)
    # 发布时间
    issue_date = Column(DateTime)
    # 入库日期
    created_at = Column(DateTime)

    # metainfo
    # 如果数据存在额外的信息,利用json.dumps保存成string存储在这里
    metainfo = Column(String)

    # 文章来源,可选项
    # 例如 bilibili, wechat , toutiao...
    source = Column(String)  # 新增字段

# 记录文章的存储路径
class ArticleStorage(Base):
    __tablename__ = 'article_storage'
    # id: 和 article 的 id 对应
    id = Column(Integer, primary_key=True)
    # 存储在本地的路径名称,可以是文件夹,可以是文件，取决于数据源的下载方式
    storage_path = Column(String)
    # status : 下载的状态(未来可以用下载中,下载失败,下载完成,尚未开始等)
    status = Column(String)
    # 存储类型(文件或者是文件夹)
    storage_type = Column(String)
    created_at = Column(DateTime)
    # 记录下载的尝试次数
    download_count = Column(Integer)


def create_database(source = ''):
    database = get_work_dir() / 'database'
    database.mkdir(exist_ok=True)
    if source:
        source = source + '_'
    db_url = f'sqlite:///{database}/{source}articles.db'
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine

def init_sql_session(source_name):
    # 为了debug方便和避免代码调试导致删库,这里加入 source name
    # 不同的数据源存放在不同的数据库，但是格式完全一致
    engine = create_database(source_name)
    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()
    return session

# ---------------------------------------
# Article
#---------------------------------------


# Query the number of articles by a specified author
def count_articles_by_author(session, author , source = None):
    query = session.query(Article).filter(Article.author == author)
    if source:
        query = query.filter(Article.source == source)
    return query.count()


def insert_article(session, title, author, url, issue_date=None,metainfo = None,source =None):
    if issue_date is None:
        issue_date = datetime.now()
    new_article = Article(
        title=title,
        author=author,
        url=url,
        issue_date=issue_date,
        created_at=datetime.now(),
        metainfo=metainfo,
        source = source
    )
    session.add(new_article)
    session.commit()


# Read the URL of a specific article by the author and title
def get_article_url(session, author, title, source=None):
    query = session.query(Article).filter(
        Article.author == author,
        Article.title == title
    )
    if source:
        query = query.filter(Article.source == source)  # 根据 source 过滤
    article = query.first()
    return article.url if article else None


def get_ids_by_author(session, author, source=None):
    query = session.query(Article.id).filter(Article.author == author)
    if source:
        query = query.filter(Article.source == source)
    return [row.id for row in query.all()]


def get_articles_by_ids(session, article_ids : List = None, to_pd = True):
    """
    Retrieve articles based on a list of article IDs and return the results as a pandas DataFrame.

    :param session: SQLAlchemy session object
    :param article_ids: List of article IDs to retrieve
    :return: pandas DataFrame containing the retrieved articles
    """
    query = session.query(Article)
    if article_ids is not None:
        query = query.filter(Article.id.in_(article_ids))
    articles = query.all()

    # Convert the list of Article objects to a list of dictionaries
    articles_dict_list = [
        {
            'id': article.id,
            'title': article.title,
            'author': article.author,
            'url': article.url,
            'issue_date': article.issue_date,
            'created_at': article.created_at,
            'metainfo': article.metainfo,
            'source': article.source
        }
        for article in articles
    ]
    if to_pd:
        # Convert the list of dictionaries to a pandas DataFrame
        articles_dict_list = pd.DataFrame(articles_dict_list)

    return articles_dict_list




# Check if an article already exists and insert if not
def insert_if_not_exists(session, title, author, url, issue_date=None , source = None , metainfo = None):
    query = session.query(Article).filter(
        Article.author == author,
        Article.title == title
    )
    if issue_date is not None:
        query = query.filter(Article.issue_date == issue_date)

    # 如果 source 不是 None，则添加 source 的判断
    if source is not None:
        query = query.filter(Article.source == source)

    existing_article = query.first()
    if not existing_article:
        insert_article(session, title, author, url, issue_date , source = source, metainfo = metainfo)
        return True
    else:
        logger.info(f'{existing_article.title} exists in database!')
        return False


def group_articles_by_source_and_account(session, source_filter):
    results = (
        session.query(
            Article.author,
            func.count(Article.id).label('article_count')
        )
        .filter(Article.source == source_filter)
        .group_by(Article.author)
        .all()
    )
    return results

# ---------------------------------------
# Article Storage
#---------------------------------------

# 查询所有不在 storage 当中的 id
def get_ids_not_in_artilce_storage(session):
    article_ids = session.query(Article.id).all()
    storage_ids = session.query(ArticleStorage.id).all()
    article_ids_set = {id for (id,) in article_ids}
    storage_ids_set = {id for (id,) in storage_ids}
    return article_ids_set - storage_ids_set


# ---------------------------------------
# Article Storage
#---------------------------------------
# 添加函数 insert_article_storage
def upsert_article_storage(session, article_id, storage_path, status='尚未开始', storage_type='file', download_count = 0):
    """
    Insert a new record into the ArticleStorage table or update an existing record if the article_id already exists.
    :param session: SQLAlchemy session object
    :param article_id: The ID of the article to associate with the storage
    :param storage_path: The path where the article is stored
    :param status: The status of the storage '尚未开始'/‘下载中’/'下载失败‘/'下载成功’
    :param storage_type: The type of storage (default is 'file') # file/folder
    """
    existing_storage = session.query(ArticleStorage).filter(ArticleStorage.id == article_id).first()

    if existing_storage:
        # Update the existing record
        existing_storage.storage_path = storage_path
        existing_storage.status = status
        existing_storage.storage_type = storage_type
        existing_storage.download_count = download_count
        # existing_storage.created_at = datetime.now()
        logger.info(f"Updated storage record for article ID {article_id}")
    else:
        # Insert a new record
        new_storage = ArticleStorage(
            id=article_id,
            storage_path=storage_path,
            status=status,
            storage_type=storage_type,
            created_at=datetime.now(),
            download_count = download_count
        )
        session.add(new_storage)
        logger.info(f"Inserted new storage record for article ID {article_id}")

    session.commit()

def upsert_article_storage_status(session, article_id, status , count = None):
    """
    更新 article id 对应的 status 为新的 status。

    :param session: SQLAlchemy session object
    :param article_id: The ID of the article to update
    :param status: The new status to set for the article storage
    """
    existing_storage = session.query(ArticleStorage).filter(ArticleStorage.id == article_id).first()

    if existing_storage:
        # Update the existing record's status
        existing_storage.status = status
        if count is not None:
            existing_storage.download_count = count
        session.commit()
        logger.info(f"Updated status for article ID {article_id} to {status}")
    else:
        logger.warning(f"No storage record found for article ID {article_id}. Status not updated.")


# 查询所有不在 storage 当中的 id
def get_ids_not_in_article_storage(session):
    article_ids = session.query(Article.id).all()
    storage_ids = session.query(ArticleStorage.id).all()
    article_ids_set = {id for (id,) in article_ids}
    storage_ids_set = {id for (id,) in storage_ids}
    return article_ids_set - storage_ids_set


def check_file_path_exists(session, file_path):
    """
    检查给定的路径是否出现在了 article storage 当中。

    :param session: SQLAlchemy session object
    :param file_path: 要检查的文件路径
    :return: 如果路径存在则返回 True，否则返回 False
    """
    existing_storage = session.query(ArticleStorage).filter(ArticleStorage.storage_path == file_path).first()
    return existing_storage is not None


def gather_ids_by_storage_status(session, status='', source=''):
    """根据存储状态收集文章ID，并可选根据来源过滤"""
    # 查询符合指定状态的存储记录
    query = select(ArticleStorage.id).filter(ArticleStorage.status == status)

    # 如果指定了来源，进一步过滤
    if source:
        # 首先获取符合状态的 ArticleStorage ID
        storage_ids = session.execute(query).scalars().all()

        # 再根据这些 ID 查询 Article 表中符合来源的记录
        if storage_ids:
            query = select(Article.id).filter(Article.id.in_(storage_ids), Article.source == source)
            ids = session.execute(query).scalars().all()
            return ids
        else:
            return []  # 如果没有符合状态的记录，返回空列表
    else:
        # 如果没有指定来源，直接返回符合状态的 ArticleStorage ID
        ids = session.execute(query).scalars().all()
        return ids


def gather_article_with_storage(session, ids):
    """根据文章 ID 收集文章及其存储信息，并返回 Pandas DataFrame"""
    if not ids:
        return pd.DataFrame()  # 如果 ID 列表为空，返回空的 DataFrame

    # 查询 Article 和 ArticleStorage 表，连接条件是 ID 匹配
    query = (
        select(Article, ArticleStorage)
        .join(ArticleStorage, Article.id == ArticleStorage.id)
        .filter(Article.id.in_(ids))
    )

    results = session.execute(query).all()

    # 将结果处理成字典列表
    data = [
        {
            **result[0].__dict__,   # Article 对象的字段
            **result[1].__dict__,   # ArticleStorage 对象的字段
        }
        for result in results
    ]

    # 创建 Pandas DataFrame
    df = pd.DataFrame(data)

    return df


def clear_article_storage(session):
    """清空 ArticleStorage 表中的所有记录"""
    session.query(ArticleStorage).delete()
    session.commit()
    print("ArticleStorage 表已清空")


def reset_article_storage(session):
    """清空 ArticleStorage 表中的所有记录，检查并添加 download_count 列"""
    # 检查 download_count 列是否存在
    inspector = inspect(session.bind)
    columns = [col['name'] for col in inspector.get_columns('article_storage')]

    if 'download_count' not in columns:
        # 如果不存在 download_count 列，则添加该列
        try:
            # 清空表中的所有记录
            session.query(ArticleStorage).delete()
            session.commit()
            print("ArticleStorage 表已清空")

            add_column = text("ALTER TABLE article_storage ADD COLUMN download_count INTEGER")
            session.execute(add_column)
            session.commit()
            print("Column 'download_count' 已添加到 'article_storage' 表.")
        except OperationalError as e:
            print(f"添加列时出错: {e}")
    else:
        print("Column 'download_count' 已存在于 'article_storage' 表中.")


def group_articles_by_status(session, source):
    results = (
        session.query(
            ArticleStorage.status,
            func.count(ArticleStorage.id).label('count')
        )
        .join(Article, Article.id == ArticleStorage.id)  # 根据需要进行连接
        .filter(Article.source == source)
        .group_by(ArticleStorage.status)
        .all()
    )
    return results

def get_storage(session):
    """
    获取 article_storage 表中的所有记录

    :param session: SQLAlchemy 会话对象
    :return: 包含所有记录的列表，每条记录为字典
    """
    articles = session.query(ArticleStorage).all()  # 查询所有记录
    result = []

    for article in articles:
        result.append({
            'id': article.id,
            'storage_path': article.storage_path,
            'status': article.status,
            'storage_type': article.storage_type,
            'created_at': article.created_at,
            'download_count': article.download_count
        })

    return result

def move_data(session , old_prefix, new_prefix):
    try:
        articles_to_update = session.query(ArticleStorage).filter(
            ArticleStorage.storage_path.startswith(old_prefix)).all()

        # 更新路径
        for article in articles_to_update:
            if new_prefix in article.storage_path:
                continue
            if article.status == '下载成功':
                new_path = article.storage_path.replace(old_prefix, new_prefix)
                if not Path(new_path).exists() and Path(article.storage_path).exists():
                    logger.info('copy path new new~')
                    shutil.copy(article.storage_path , new_path)
                    print(new_path, Path(article.storage_path).exists())

            article.storage_path = article.storage_path.replace(old_prefix, new_prefix)
            assert '/mnt/d/mnt/d' not in article.storage_path
        # 批量提交更新
        session.commit()
        print("路径更新成功")
    except Exception as e:
        session.rollback()
        print(f"更新失败: {e}")