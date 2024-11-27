
from bs4 import BeautifulSoup
from aio_exporter.server.parser.base_parser import BaseParser
from pathlib import Path
import markdownify
from aio_exporter.utils import html_utils
import os
import asyncio
from aio_exporter.utils.dl_models import asr
from aio_exporter.utils.mllm import mllm_query
from aio_exporter.utils.llm import llm_query
from aio_exporter.server.parser.mixin import ImageMixin
import tempfile



class WechatParser(BaseParser):
    def __init__(self):
        super().__init__()

    def ignore_useless(self,article_content):

        code_snippets = article_content.find_all(class_ = 'code-snippet__line-index code-snippet__js')
        for snippet in code_snippets:
            snippet.extract()
        # <br>换行符
        for p in article_content.find_all('p'):
            if p.find('br') and len(p.contents) == 1:
                # 占位符,可以省略
                p.extract()






    def format_toutu(self, toutu):
        img_tags = toutu.find_all('img')
        images = []
        for image in img_tags:
            if image['src']:
                images.append(
                    f'![img]({image["src"]})'
                )
        return '## 头图 \n{}\n\n## 正文\n\n'.format('\n\n'.join(images))


    def parse(self, html_file_path):
        with open(html_file_path, encoding='utf-8') as f:
            html = f.read()
        soup = BeautifulSoup(html,'html.parser')

        toutu = soup.find(class_ = 'page_top_area')
        md_toutu = ""
        if toutu:
            # 在 markdown 的上方插入头图
            md_toutu = self.format_toutu(toutu)

        if soup.find(class_ = 'share_notice'):
            # 说明这是一个想法
            md_text = markdownify.markdownify(str(soup.find(class_ = 'share_notice')))
            md_text = html_utils.clean_html(md_text)
        else:
            article_content = soup.find('div', id='js_content')
            self.ignore_useless(article_content)
            self.format_img(article_content)
            extra_md = ''
            extra = article_content.find(class_ = 'rich_media_meta_area_extra')
            if extra:
                extra_md = extra.text.replace(',  ,','  ')
                extra.extract()
            md_zw = markdownify.markdownify(str(article_content))
            md_zw = html_utils.clean_html(md_zw)
            md_text = md_zw + '\n' + extra_md

        markdown_text = html_utils.clean_html(md_toutu + md_text)
        return markdown_text


class MLLMWechatParser(WechatParser , ImageMixin):
    def parse(self, html_file_path):
        md_text = super().parse(html_file_path)
        with self.localize_images(md_text) as (updated_md_text , images, image_urls):
            useful = self.find_useful_image(updated_md_text , images ,image_urls)
            info = self.extract_information(updated_md_text , images , image_urls , useful)


def test_download_withparse():
    from aio_exporter.server.downloader import WechatDownloader
    from aio_exporter.server.downloader.wechat_downloader import wechat_dir

    wechat_downloader = WechatDownloader()
    parser = WechatParser()

    url = 'https://mp.weixin.qq.com/s?__biz=MzAwNDQ4OTYzMw==&mid=2649544077&idx=1&sn=6c1a7a11be4e2466ac02bc1097b66289&chksm=83335d43b444d4550cd5e20027c81378ecd62ec65ddf431316551a2cfb28289f1f9d0e7d224b#rd'

    async def unitest(url):
        result = await html_utils.download_url(url)
        result = await wechat_downloader.post_process_html(url, result)
        debug_file = wechat_dir / 'debug.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(result)
        parser.parse(debug_file)
        os.remove(debug_file)
        return result

    asyncio.run(unitest(url))

def test_parse():
    parser = MLLMWechatParser()
    # html = '/mnt/d/root/projects/aio_exporter/database/download/wechat/蓝鲸insurance/16528_无力还款、两度延期，中煤财险销售子公司临资本金托管压力.html'
    # html = '/mnt/d/root/projects/aio_exporter/database/download/wechat/中国太平洋保险/17914_国际气象节丨风里雪里，我们在你身边.html'
    # html = '/mnt/d/root/projects/aio_exporter/database/download/wechat/沐熙花园/107_3%下架猝不及防.html'
    html = '/mnt/d/root/projects/aio_exporter/database/download/wechat/中国保险行业协会/14979_【媒体走基层】为百姓生活装上保险“安全阀”——浙江宁波创新保险服务助力经济社会发展.html'

    parser.parse(html)


if __name__ == '__main__':
    # unit test
    test_parse()

