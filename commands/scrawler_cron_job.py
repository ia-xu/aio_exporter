import requests
import os
import sys
from pathlib import Path
import datetime
import json
import shutil
from aio_exporter.utils import get_work_dir



def log(message):
    log_file = Path(__file__).parent / 'scrawler_cron_log.txt'
    with open(log_file, 'a+', encoding='utf-8') as f:
        now = datetime.datetime.now()
        f.write(f'Time: {now.strftime("%Y-%m-%d %H:%M")}\n')
        f.write(f'{message}!\n')

if __name__ == '__main__':
    # 检查登录 cookie 是否过期

    log_status = requests.get(
        'http://127.0.0.1:31006/api/wechat/check_login'
    )
    if not log_status.json():
        log('登陆失败')
        sys.exit(0)

    log('登录成功,开始检查更新数量!')


    response = requests.get(
        'http://127.0.0.1:31006/api/wechat/count_new_wechat'
    )
    stat = json.dumps(response.json(), indent=2, ensure_ascii=False)
    log(stat)
    if not any((v > 20 for k, v in response.json().items())):
        # 不需要频繁更新所有的内容
        log('更新文章不多!')
        sys.exit(0)
    log('开始下载')
    # 获取文章
    response = requests.get(
        'http://127.0.0.1:31006/api/wechat/get_new_wechat'
    )
    log('下载完成')

    db_file = get_work_dir() / 'database' / 'wechat_articles.db'
    bak_file = get_work_dir() / 'database' / 'wechat_articles.db.bak'
    shutil.copy(db_file , bak_file)
    log('备份完成')