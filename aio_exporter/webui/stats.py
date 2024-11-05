
# 创建 webui, 展示所有的已经入库的 url
import streamlit as st
from aio_exporter.utils import sql_utils
from aio_exporter.utils import get_work_dir

work_dir = get_work_dir()


def main():
    session = sql_utils.init_sql_session('wechat')
    all_data = sql_utils.get_articles_by_ids(session)
    all_data = all_data[all_data.url != 'https://none']
    stats = all_data.groupby('author').count()['id']
    st.write('## 已获取链接情况')
    st.data_editor(stats)

    st.write(f'### 获取链接总数: {len(all_data)}')

    st.write('## 链接展示')
    selection = st.selectbox('选择展示内容', ['ALL'] + list(stats.index), 0)
    if selection != 'ALL':
        df = all_data[all_data.author == selection]
    else:
        df  = all_data

    st.data_editor(df.loc[:,['author','issue_date','title','url']], height = 400)


    log_files = work_dir / 'commands' / 'scrawler_cron_log.txt'
    if log_files.exists():
        st.write('查看日志')
        with open(log_files) as f:
            log = f.read()
    st.text_area('日志内容展示', log)

main()