import requests
from urllib.parse import urljoin
import pandas as pd


url = 'http://localhost:31006'
status = requests.get(
    urljoin(url , 'api/wechat/article_list?author=蓝鲸课堂') ,
)
# 检查远端状态是否更新
print(status.json())

data = pd.DataFrame(status.json()['response'])
title = data['title'].sample(1).iloc[0]

md = requests.get(
    urljoin(url , f'api/wechat/article_md?title={title}')
)
print(md.text)
