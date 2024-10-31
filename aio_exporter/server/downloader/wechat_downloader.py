from .base_downloader import BaseDownloader


class WechatDownloader(BaseDownloader):

    def __init__(self):
        super().__init__('wechat')

    def count_no_download(self):
        pass


if __name__ == '__main__':
    wechat_downloader = WechatDownloader()
    wechat_downloader.count_no_download()
