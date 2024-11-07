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
    lines = md_text.splitlines()
    image_links = []
    for line in lines:
        # 检查是否以 ![img 开头
        if line.startswith("![img") and "](" in line:
            # 提取图片链接
            start = line.index("(") + 1
            end = line.index(")")
            image_links.append(line[start:end])
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
            st.data_editor(filter_df_)

            # 随机展示
            st.write('## 查看转换为 markdown 格式的结果')

            # 简单展示
            show_im = st.checkbox('展示图片/展示转换后的 md 文件', True, key = f'{source}-checkbox')

            select_article = st.selectbox('挑选文章', filter_df.title.to_list() , key = f'{source}-selectbox')


            file_path = filter_df[filter_df.title == select_article]

            url = file_path['url'].values[0]
            st.write(f'- 原文链接: {url}')
            st.divider()

            storage_path = file_path['storage_path'].values[0]



            with st.spinner('准备展示转换结果'):

                md_text = parser[source].parse(storage_path)

                if not show_im:

                    st.markdown(f'```\n{md_text}\n```\n')

                    return

                with tempfile.TemporaryDirectory() as td:
                    image_links = extract_image_links(md_text)
                    # 3. 下载图片并保存到临时文件夹
                    local_image_paths = []
                    for link in image_links:
                        response = requests.get(link)
                        if response.status_code == 200:
                            save_suffix = Image.open(BytesIO(response.content)).format

                            # 获取文件名
                            hashcode = hashlib.md5(link.encode('utf-8')).hexdigest()
                            local_path = os.path.join(td, hashcode  + f'.{save_suffix}')
                            with open(local_path, 'wb') as f:
                                f.write(response.content)
                            local_image_paths.append(local_path)
                    for original_link, local_path in zip(image_links, local_image_paths):
                        md_text = md_text.replace(original_link, local_path)

                    md_text = html_utils.markdown_insert_images(md_text)
                    st.markdown(md_text,unsafe_allow_html=True)

download()