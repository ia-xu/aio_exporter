from aio_exporter.server.downloader.base_downloader import BaseDownloader
from aio_exporter.utils.utils import get_work_dir
from loguru import logger
from tqdm import tqdm
from aio_exporter.utils import sql_utils
from aio_exporter.utils import html_utils
import markdownify
import readability
from bs4 import BeautifulSoup

work_dir = get_work_dir()
database = work_dir / 'database' / 'download'
database.mkdir(exist_ok=True)
wechat_dir = database / 'wechat'
wechat_dir.mkdir(exist_ok=True)

class WechatDownloader(BaseDownloader):

    def __init__(self):
        super().__init__('wechat')
        self.batch_size = 5
        # 单次最多更新的数量
        self.max_download_size = 100

    def assign_path_for_new_articles(self):
        # 检查更新的id,为这些id分配存储的路径
        # 检查已经下载的 wechat 的 id
        # 判断这些 id 哪些出现在 download 里
        ids = self.gather_no_download_ids()
        logger.info(f'found {len(ids)} wechat articles to insert')
        articles = self.gather_articles(ids)
        for _ , article in tqdm(articles.iterrows()):
            # 分配存储路径,添加到库,将 状态变化为 '尚未开始'
            self.insert_and_assign_path(article)

    def insert_and_assign_path(self,article):
        # 根据 article 的信息，为article 生成存储的路径
        # 将 article 的信息插入到 download 表中
        # 将 article 的状态更新为 '尚未开始'
        account_dir = wechat_dir / article.author
        account_dir.mkdir(exist_ok=True)
        title = self.clean_title(article.title)
        file_path = account_dir / f'{article.id}_{title}.md'
        # 检查filepath 是否已经存在
        idx = 0
        while self.check_file_path_exists(file_path):
            # 更新位置
            file_path = account_dir / f'{article.id}_{idx}_{title}.md'
            idx += 1
        logger.info(f'为账号{article.author} 文章分配路径到 {file_path.name}')
        return self.insert_assigned_path(
            article.id , file_path , '尚未开始' , 'file')

    async def post_process_html(self, url , result):
        if result.status_code != 200:
            return ''
        soup = BeautifulSoup(result.content , 'html.parser')
        text = ""
        for p in soup.find_all('p'):
            text += p.text
        if '环境异常' in text or '去验证' in text:
            return None
        article_content = soup.find('div', id='js_content')        # 这里由于暂时不考虑解析图片，不对 image 处理
        if not article_content:
            return ""
        plan_text = ""
        p_tags = article_content.find_all('p')
        for p_tag in p_tags:
            plan_text += p_tag.get_text() + "\n"
        plan_text = html_utils.clean_html(plan_text)
        if not plan_text:
            return ''

        markdown_text = html_utils.to_markdown(
            article_content , plan_text
        )
        markdown_text = html_utils.clean_html(markdown_text)
        return markdown_text

    def download(self):
        # 关于代理，后续使用: https://blog.csdn.net/crayonjingjing/article/details/137596882
        ids_need_download = self.gather_ids_without_downloaded()
        article_with_file_path = self.gather_article_with_storage(ids_need_download)
        # 将文章卸载到指定目录
        download_count = 0
        for i in range(0, len(article_with_file_path), self.batch_size):
            batch = article_with_file_path[i:i + self.batch_size]
            download_count += len(batch)
            if download_count > self.max_download_size:
                logger.info('超出单次下载限制!')
                return
            urls = batch['url'].tolist()  # 获取当前批次的 URL
            # 每次调用 asyncio 的方法，一次性获取10篇文章的 html
            results = html_utils.download_urls(urls ,self.post_process_html)  # 下载 HTML
            for (_ ,row) ,result in zip(batch.iterrows(),results):
                if not result:
                    # 说明下载失败
                    self.upsert_status(row.id , '下载失败')
                else:
                    # 说明下载成功
                    with open(row.storage_path, 'w', encoding='utf-8') as f:
                        f.write(result)
                    self.upsert_status(row.id , '下载成功')


if __name__ == '__main__':
    wechat_downloader = WechatDownloader()
    wechat_downloader.assign_path_for_new_articles()
    wechat_downloader.download()
