

# 对第7步制作的标签利用 streamlit 进行修正
import streamlit as st
from pathlib import Path
import json
import pandas as pd
from PIL import Image
import numpy as np
st.set_page_config(page_title='本地标注', page_icon="🧊", layout="wide")


def create_gt(current_dir, csv_filename):
    labels = []
    for jsonfile in current_dir.glob('*.json'):
        with open(jsonfile) as f:
            data = json.load(f)
        ann = data['shapes'][0]['label'].split('∫')
        labels.append(
            {
                'org':  ann[0],
                'rectified' : ann[1],
                'equal' :  '相等' if ann[0] == ann[1] else '不相等',
                'status' : '未确认',
                'source' : str(jsonfile)
            }
        )
    pd.DataFrame(labels).to_csv(csv_filename , index= False)
    return
def main():
    root_dir = Path('E:\\company\\data\\ocr-asr\\ann')
    subdir = list(root_dir.glob('*'))
    subdir = [_ for _ in subdir if _.is_dir()]
    current_dir = st.sidebar.selectbox(
        '选择任务',
        subdir , 0
    )
    # 搜集所有的标注的结果,保存到一个 csv 当中
    csv_filename = root_dir / (current_dir.name + '.csv')
    if not csv_filename.exists():
        create_gt(current_dir , csv_filename)

    data = pd.read_csv(csv_filename)

    # data = st.data_editor(data)
    allowed_status = ['未确认', '已确认' , '待检查']

    data['equal'] = data.apply(lambda x: '相等' if x['org'] == x['rectified'] else '不相等', axis=1)

    # random shuffle
    # Define the custom order for sorting
    custom_order = ['已确认', '待检查', '未确认']
    # Sort the data based on the custom order
    data['status_order'] = data['status'].apply(lambda x: custom_order.index(x) if x in custom_order else 3)
    data = data.sort_values(by='status_order').drop(columns=['status_order']).reset_index(drop=True)
    data = st.data_editor(
        data,
        column_config={
            'status': st.column_config.SelectboxColumn(
                options=allowed_status
            )
        },
    )

    # 从上述数据当中遍历所有的待确认
    need_check_files = data[data['status'] == '待检查']
    need_check_files2 = data[data['status'] == '未确认'].iloc[:1,:]
    need_check_files = pd.concat([need_check_files , need_check_files2])
    for _ , row in need_check_files.iterrows():
        with open(row['source']) as f:
            source = json.load(f)
        # 获取到 labelme 当中的图像路径
        image_path = source['imagePath']
        image = Image.open( current_dir / image_path)
        st.image(image)


    confirm = st.button('保存更新结果')
    if confirm:
        data['equal'] = data.apply(lambda x: '相等' if x['org'] == x['rectified'] else '不相等', axis=1)
        data.to_csv(csv_filename, index= False)
        st.rerun()
        st.success('更新完成')
        return

    st.warning('请随时保存结果')
    return








main()
