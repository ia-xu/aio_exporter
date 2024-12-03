

import streamlit as st
from aio_exporter.server.parser import BaseParser
from aio_exporter.utils import html_utils

parser = BaseParser()

st.set_page_config(layout="wide")

def view():
    cols = st.columns((3,5))
    with cols[0]:
        st.write('## 输入 md')
        with st.container(border=True):
            md_text = st.text_area('input' , height=400)
    with cols[1]:
        st.write('## 预览结果')
        with st.spinner('转换中'):
            with st.container(border=True):
                with parser.localize_images(md_text) as (local_md_text, _, _):
                    md_text = html_utils.markdown_insert_images(local_md_text)
                    st.markdown(md_text, unsafe_allow_html=True)


view()