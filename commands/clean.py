

# 对下载数据库进行整理
# 需要将所有的显示为已下载但是不存在下载路径的内容分配为尚未开始
# 将下载中的内容分配为尚未开始
import os
from aio_exporter.utils import sql_utils
from aio_exporter.utils.sql_utils import  *

for source in ['wechat','bilibili']:
    session = sql_utils.init_sql_session(source)
    # 遍历数据库，找到所有的下载的结果
    articles = session.query(ArticleStorage).filter(
        ArticleStorage.status.in_(['下载成功', '正在下载'])
    ).all()

    for article in articles:
        # 如果 status 为 '下载成功' 且 storage_path 不存在，将 status 变为 '尚未开始'
        if article.status == '下载成功' and not os.path.exists(article.storage_path):
            logger.warning(f"Storage path does not exist for article ID {article.id}. Changing status to '尚未开始'.")
            article.status = '尚未开始'

        # 如果 status 为 '正在下载'，将 status 变为 '尚未开始'
        elif article.status == '正在下载':
            logger.info(f"Article ID {article.id} is currently '正在下载'. Changing status to '尚未开始'.")
            article.status = '尚未开始'
            # 如果 storage_path 存在，删除文件或文件夹
            if os.path.exists(article.storage_path):
                if os.path.isfile(article.storage_path):
                    os.remove(article.storage_path)
                    logger.info(f"Deleted file at path: {article.storage_path} for article ID {article.id}.")
                elif os.path.isdir(article.storage_path):
                    # 使用 shutil.rmtree 删除非空文件夹
                    import shutil

                    shutil.rmtree(article.storage_path)
                    logger.info(f"Deleted directory at path: {article.storage_path} for article ID {article.id}.")

    session.commit()
    logger.info("All changes committed to the database.")