
# 下载微信公众号文章成为 html 格式
import requests
from pathlib import Path
import datetime
from loguru import logger
import argparse
from urllib.parse import urljoin

def log(message):
    logger.info(message)
    log_file = Path(__file__).parent / 'download_cron_log.txt'
    with open(log_file, 'a+', encoding='utf-8') as f:
        now = datetime.datetime.now()
        f.write(f'Time: {now.strftime("%Y-%m-%d %H:%M")}\n')
        f.write(f'{message}!\n')

baseurl = 'http://localhost:31006'

def download_wechat():
    # 检查当前还有多少条尚未下载的数据，如果有，不额外新增过多的内容
    response = requests.get(
        urljoin(baseurl, '/api/wechat/task_num')
    )
    count = response.json()
    log(f'当前队列当中的未下载任务数: {count}')
    if count < 20:
        # 说明已经下载的差不多了
        # 为新找到的文章分配下载路径
        response = requests.post(urljoin(baseurl, '/api/wechat/assign_download_path'))
        len(response.json())
        log(f'创建任务: 为 {len(response.json())} 篇文章分类了下载路径')
    else:
        log('继续执行尚未完成的下载任务!')

    response = requests.get(
    urljoin(baseurl, '/api/wechat/downloading_task_num')
    )
    count = response.json()
    if count != 0:
        log(f'还有{count}个正在下载的上一个任务')
        return

    log(f'执行新的下载任务')

    # 尝试所有 download count = 0 的内容
    response = requests.post(
        urljoin(baseurl, '/api/wechat/download?new_article=true')
    )
    results = response.json()
    success = 0
    fail = 0
    delete = 0
    for result in results:
        if result['status'] == '下载成功' :
            success += 1
        elif result['status'] == '失效':
            delete += 1
        else:
            fail += 1
    log(f'一共下载了 {success + fail} 篇新文章!, 成功 {success} /失败 {fail} / 失效 {delete}')


    response = requests.get(
        urljoin(baseurl, '/api/wechat/downloading_task_num')
    )
    count = response.json()
    if count != 0:
        log(f'还有{count}个正在下载的上一个任务')
        return

    log(f'执行新的下载任务')


    # 如果存在 download count != 0 的内容,进行重试
    # response = requests.post(
    #     urljoin(baseurl, '/api/wechat/download?new_article=false')
    # )
    # results = response.json()
    # success = 0
    # fail = 0
    # for result in results:
    #     if result['status'] == '下载成功':
    #         success += 1
    #     else:
    #         fail += 1
    # log(f'一共重试下载了 {success + fail} 篇下载失败的文章!, 成功 {success} /失败 {fail}')

def download_bilibili():

    response = requests.get(
        urljoin(baseurl, '/api/bilibili/task_num')
    )

    count = response.json()
    log(f'当前队列当中的未下载任务数: {count}')
    if count < 20:
        # 说明已经下载的差不多了
        # 为新找到的文章分配下载路径
        response = requests.post(urljoin(baseurl, '/api/bilibili/assign_download_path'))
        len(response.json())
        log(f'创建任务: 为 {len(response.json())} 个视频分类了下载路径')
    else:
        log('继续执行尚未完成的下载任务!')

    response = requests.get(
        urljoin(baseurl, '/api/bilibili/downloading_task_num')
    )
    count = response.json()
    if count != 0:
        log(f'还有{count}个正在下载的上一个任务')
        return
    log(f'执行新的下载任务')

    # 尝试所有 download count = 0 的内容
    response = requests.post(
        urljoin(baseurl, '/api/bilibili/download?new_article=true')
    )
    results = response.json()
    success = 0
    fail = 0
    for result in results:
        if result['status'] == '下载成功':
            success += 1
        else:
            fail += 1
    log(f'一共下载了 {success + fail} 篇新文章!, 成功 {success} /失败 {fail}')

    response = requests.get(
        urljoin(baseurl, '/api/bilibili/downloading_task_num')
    )
    count = response.json()
    if count != 0:
        log(f'还有{count}个正在下载的上一个任务')
        return
    log(f'执行新的下载任务')

    # 如果存在 download count != 0 的内容,进行重试
    # response = requests.post(
    #     urljoin(baseurl, '/api/bilibili/download?new_article=false')
    # )
    # results = response.json()
    # success = 0
    # fail = 0
    # for result in results:
    #     if result['status'] == '下载成功':
    #         success += 1
    #     else:
    #         fail += 1
    # log(f'一共下载了 {success + fail} 篇新文章!, 成功 {success} /失败 {fail}')

if __name__ == '__main__':

    # ---------------------------------------------------
    # 添加 argparser
    # ---------------------------------------------------
    argparser = argparse.ArgumentParser(description='Scrawl WeChat and Bilibili content.')
    argparser.add_argument('--source', type=str)
    args = argparser.parse_args()

    # ---------------------------------------------------
    # wechat flow
    # ---------------------------------------------------
    if args.source == 'wechat':
        download_wechat()

    # ---------------------------------------------------
    # bilibili flow
    # ---------------------------------------------------
    if args.source == 'bilibili':
        download_bilibili()
