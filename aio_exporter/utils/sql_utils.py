

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from .utils import get_work_dir
from loguru import logger
from datetime import datetime

Base = declarative_base()


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


def create_database():
    database = get_work_dir() / 'database'
    database.mkdir(exist_ok=True)
    db_url = f'sqlite:///{database}/articles.db'
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)
    return engine

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
        source = None
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
