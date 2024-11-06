
# 创建 webui, 展示所有的已经入库的 url
import streamlit as st
from aio_exporter.utils import sql_utils
from aio_exporter.utils import get_work_dir
from mmengine import Config

config = get_work_dir() / 'aio_exporter' / 'server' / 'config.yaml'
config = Config.fromfile(config)


work_dir = get_work_dir()


def scrawl_stats():
    cls = ['wechat', 'bilibili']
    tabs = st.tabs(cls)
    for source in cls:
        index = cls.index(source)
        with tabs[index]:
            st.write(f'# {source} 统计情况')
            session = sql_utils.init_sql_session(source)
            all_data = sql_utils.get_articles_by_ids(session)
            all_data = all_data[all_data.url != 'https://none']

            if source  == 'bilibili':
                mapping = config.scrawler.bilibili.SubscriptionAccounts
                mapping = {str(v['id']) : v['name'] for v in mapping}
                all_data['author'] = all_data['author'].map(lambda x: mapping[str(x)])

            stats = all_data.groupby('author').count()['id']
            st.write('## 已获取链接情况')
            st.data_editor(stats, key = f'{source}-stats')

            st.write(f'### 获取链接总数: {len(all_data)}')

            st.write('## 链接展示')

            selection = st.selectbox('选择展示内容', ['ALL'] + list(stats.index), 0)
            if selection != 'ALL':
                df = all_data[all_data.author == selection]
            else:
                df  = all_data


            num = st.slider('选择展示的条目数量', 0, len(df) , min(len(df) , 50),key = f'{source}-slider')
            df = df.sample(num  , replace = False)

            st.data_editor(df.loc[:,['author','issue_date','title','url']], height = 400, key = f'{source}-df')


    log_files = work_dir / 'commands' / 'scrawler_cron_log.txt'
    log = ""
    if log_files.exists():
        st.write('查看日志')
        with open(log_files) as f:
            log = f.read()
    st.text_area('日志内容展示', log)

scrawl_stats()