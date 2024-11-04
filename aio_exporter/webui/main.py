
from urllib.parse import urljoin
import streamlit as st
import requests
import pandas as pd
from aio_exporter.utils import sql_utils

server_url = 'http://127.0.0.1:31006/'
check_login = 'api/wechat/check_login'
count_new_articles = 'api/wechat/count_new_wechat'
get_new_articles = 'api/wechat/get_new_wechat'
assign_download_path = 'api/wechat/assign_download_path'
download = 'api/wechat/download'

session = sql_utils.init_sql_session('wechat')

def stats2df(result, key , pk = 'account'):
    rows = []
    if isinstance(result , dict):
        result = list(result.items())
    for account, num in result:
        rows.append(
            {pk: account, key: num},
        )
    return pd.DataFrame(rows)


# st , set wide
st.set_page_config(layout="wide")

def main():
    st.title('View Status')

    st.write('## Database Status')

    # 这里偷个懒,数据库操作不通过 api, 直接获取结果
    with st.spinner('检查当前已经发现的文章数'):
        status = sql_utils.group_articles_by_source_and_account(
            session , 'wechat'
        )
        st.data_editor(stats2df(status ,'文章数量'))


    with st.spinner('检查当前已经下载的文章数'):
        status = sql_utils.group_articles_by_status(
            session , 'wechat'
        )
        st.data_editor(stats2df(status, '文章数量', pk = '下载情况'))

    st.write('## Wechat Status')
    view_status = True
    with st.spinner('检查微信 cookie 是否可用...'):
        if 'scrawler-status' not in st.session_state:
            response = requests.get(urljoin(server_url,check_login))
            status = response.text
            st.session_state['scrawler-status'] = response.text
        else:
            status = st.session_state['scrawler-status']
        try:
            if status == 'true':
                st.write('### cookie 可用,请谨慎的爬取资料!')
            else:
                view_status = False
                st.write('### cookie 可用,请谨慎的爬取资料!')
        except:
            view_status = False
            import traceback
            err = traceback.format_exc()
            st.write(err)
    if not view_status:
        return
    st.write('## Check Article Updates')
    st.write('- article 数据库记录了每一个文章和对应的url')
    st.write('- 该步骤检查有多少更新文章不在数据库当中')
    if st.button('查询关注公众号新更新文章...'):
        with st.spinner('查询关注公众号新更新文章...'):
            if 'update-status' not in st.session_state:
                response = requests.get(urljoin(server_url, count_new_articles))
                st.session_state['update-status'] = stats2df(response.json() , key = '不在库当中的文章数量')
            table = st.session_state['update-status']
            st.data_editor(table)

    if st.button('获取更新文章的url'):
        with st.spinner('解析文章url,添加到 article 数据库当中...'):
            response = requests.get(urljoin(server_url, get_new_articles))
            rows = response.json()
            st.write('### 一共找到了 {} 篇新文章'.format(len(rows)))
            st.data_editor(pd.DataFrame(rows) , height=400)


    if st.button('对新文章分配下载路径'):
        with st.spinner('开始分配下载路径'):
            response = requests.get(urljoin(server_url , assign_download_path))
            rows = response.json()
            if len(rows):
                st.write('### 一共分配了 {} 个路径'.format(len(rows)))
                st.data_editor(pd.DataFrame(rows), height=400)

    if st.button('下载文章'):
        with st.spinner('开始下载文章'):
            response = requests.get(urljoin(server_url, download))
            rows = response.json()
            st.write('### 一共分配了 {} 个路径'.format(len(rows)))
            if len(rows):
                st.data_editor(pd.DataFrame(rows), height=400)

    if st.button('刷新'):
        st.rerun()

main()
