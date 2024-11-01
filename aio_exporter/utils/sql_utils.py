
from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from .utils import get_work_dir
from loguru import logger
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

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



def get_articles_by_ids(session, article_ids):
    """
    Retrieve articles based on a list of article IDs and return the results as a pandas DataFrame.

    :param session: SQLAlchemy session object
    :param article_ids: List of article IDs to retrieve
    :return: pandas DataFrame containing the retrieved articles
    """
    query = session.query(Article).filter(Article.id.in_(article_ids))
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

    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(articles_dict_list)

    return df




# Check if an article already exists and insert if not
def insert_if_not_exists(session, title, author, url, issue_date=None , source = None):
    query = session.query(Article).filter(
        Article.author == author,
        Article.title == title
    )

    # 如果 source 不是 None，则添加 source 的判断
    if source is not None:
        query = query.filter(Article.source == source)

    existing_article = query.first()
    if not existing_article:
        insert_article(session, title, author, url, issue_date , source = source)
    else:
        logger.info('{existing_article.title} exists in database!')

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
def upsert_article_storage(session, article_id, storage_path, status='尚未开始', storage_type='file'):
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
        # existing_storage.created_at = datetime.now()
        logger.info(f"Updated storage record for article ID {article_id}")
    else:
        # Insert a new record
        new_storage = ArticleStorage(
            id=article_id,
            storage_path=storage_path,
            status=status,
            storage_type=storage_type,
            created_at=datetime.now()
        )
        session.add(new_storage)
        logger.info(f"Inserted new storage record for article ID {article_id}")

    session.commit()

def upsert_article_storage_status(session, article_id, status):
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

