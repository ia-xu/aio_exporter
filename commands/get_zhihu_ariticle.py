
import requests


urls = [
    'https://www.zhihu.com/tardis/bd/art/506750046',
    'https://zhuanlan.zhihu.com/p/370173032',
    'https://www.zhihu.com/question/20745287',
]
for url in urls:
    answer = requests.get(
        'https://aio.vip.cpolar.top/api/zhihu/simple_parse?url=' + url
        # 'http://localhost:31006/api/zhihu/simple_parse?url=' + url
    )
    print(url)
    print(answer.json()['content'])


