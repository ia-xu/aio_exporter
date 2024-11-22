import shutil
import hashlib
from PIL import Image
from io import BytesIO
import streamlit as st
from aio_exporter.utils import html_utils
from aio_exporter.utils import sql_utils
from aio_exporter.utils import get_work_dir
from aio_exporter.server.parser import WechatParser
from aio_exporter.server.parser import SenseVoiceSimpleParser
import pandas as pd
from pathlib import Path
import tempfile
import requests
import os

parser = {
    'wechat': WechatParser(),
    'bilibili' : SenseVoiceSimpleParser()
}


def extract_image_links(md_text):
    image_links = []
    # 获取一个 markdown 文档当中的所有的 ![img](url) 当中的 url
    import re
    pattern = r'!\[img\]\((http.*?)\)'
    matches = re.findall(pattern, md_text)
    for match in matches:
        if len(match) == 1:
            image_links.append(match)
        else:
            image_links.append(match.split(' ')[0])

    return image_links

def download():

    cls = ['wechat' , 'bilibili']

    tabs = st.tabs(cls)

    for source in cls:

        index = cls.index(source)
        with tabs[index]:
            session = sql_utils.init_sql_session(source)
            # 获取所有的存储的情况
            data = sql_utils.get_storage(session)
            data = pd.DataFrame(data)

            status = data.groupby('status').count().loc[:,'id'].reset_index()
            st.write('## 下载任务情况')
            st.write(' - 所有的 url 并不会一次性加入到下载队列当中,会逐渐加入')
            st.data_editor(status)

            st.write('## 已下载数据')
            ids = data[data.status == '下载成功'].id.to_list()
            filter_df = sql_utils.gather_article_with_storage(session ,ids)
            filter_df.loc[:,'storage_path_'] = filter_df.loc[:,'storage_path'].map(lambda x: Path(x).parent.name + '/' + Path(x).name)

            filter_df_ = filter_df.loc[:,['author','title','storage_path_']]
            # st.data_editor(filter_df_)

            # 随机展示
            # Add a slider to select the number of articles to display
            num_articles_to_display = st.slider('Select the number of articles to display', min_value=1, max_value=len(filter_df_), value=50, step=1)

            # Select a random subset of articles based on the slider value
            selected_articles = filter_df_.sample(n=num_articles_to_display, random_state=42)

            # Display the selected articles
            st.data_editor(selected_articles)
            st.write('## 查看转换为 markdown 格式的结果')

            # 简单展示
            show_im = st.checkbox('展示图片/展示转换后的 md 文件', True, key=f'{source}-checkbox')

            text_input = st.text_input('筛选文章标题', '', key=f'{source}-text-input')

            if text_input:
                filtered_titles = filter_df[filter_df.title.str.contains(text_input, case=False)].title.tolist()
            else:
                filtered_titles = filter_df.title.tolist()
            select_article = st.selectbox('挑选文章', filtered_titles, key=f'{source}-selectbox')
            file_path = filter_df[filter_df.title == select_article]

            url = file_path['url'].values[0]
            storage_path = file_path['storage_path'].values[0]

            st.write(f'- 原文链接: {url}')
            st.write(f'- 存储路径: {storage_path}')
            st.divider()

            with st.spinner('准备展示转换结果'):

                md_text = parser[source].parse(storage_path)

                if not show_im:

                    st.markdown(f'```\n{md_text}\n```\n')

                    return

                with parser[source].localize_images(md_text) as (local_md_text , _ , _ ):
                    md_text = html_utils.markdown_insert_images(local_md_text)
                    st.markdown(md_text, unsafe_allow_html=True)

            session.close()
download()