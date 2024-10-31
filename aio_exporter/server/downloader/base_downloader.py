from aio_exporter.utils import sql_utils
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import sessionmaker

class BaseDownloader:
    def __init__(self, source_name):
        self.source_name = source_name
        self.session = self.init_sql_session()

    def init_sql_session(self):
        engine = sql_utils.create_database()
        Session = scoped_session(sessionmaker(bind=engine))
        session = Session()
        return session

