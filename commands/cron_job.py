import requests

# 定时启动当前脚本, gather wechat url and download article

response = requests.get(
    'http://127.0.0.1:31006/api/scrawler/count_new_wechat'
)

response = requests.get(
    'http://127.0.0.1:31006/api/scrawler/get_new_wechat'
)
