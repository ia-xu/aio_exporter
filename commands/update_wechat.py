


# 调用远端服务器的 update wechat 接口
import requests

# 获取更新
response = requests.get(
    'http://127.0.0.1:31006/api/scrawler/count_new_wechat'
)
response

# download url
# response = requests.get(
#     'http://127.0.0.1:31006/api/scrawler/get_new_wechat'
# )