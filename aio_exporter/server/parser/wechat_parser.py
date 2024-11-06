
from bs4 import BeautifulSoup
from aio_exporter.server.parser.base_parser import BaseParser
from pathlib import Path
import markdownify
from aio_exporter.utils import html_utils
import os
import asyncio

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


    def format_img(self,content):
        img_tags = content.find_all('img')
        for idx, img_tag in enumerate(img_tags):
            if img_tag.get('data-src') and not img_tag.get('src'):
                img_tag['src'] = img_tag['data-src']
                # 添加 alt ，区别于超链接，让转出来的 markdown 带有这个链接
                img_tag['alt'] = 'img'



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
        soup =BeautifulSoup(html,'html.parser')

        toutu = soup.find(class_ = 'page_top_area')
        md_toutu = ""
        if toutu:
            # 在 markdown 的上方插入头图
            md_toutu = self.format_toutu(toutu)

        article_content = soup.find('div', id='js_content')
        self.ignore_useless(article_content)
        self.format_img(article_content)

        extra_md = ''
        extra = article_content.find(class_ = 'rich_media_meta_area_extra')
        if extra:
            extra_md = extra.text.replace(',  ,','  ')
            extra.extract()

        md_zw = markdownify.markdownify(str(article_content))
        markdown_text = html_utils.clean_html(md_toutu + md_zw + '\n' + extra_md)
        return markdown_text

if __name__ == '__main__':
    # unit test
    from aio_exporter.server.downloader import WechatDownloader
    from aio_exporter.server.downloader.wechat_downloader import wechat_dir

    wechat_downloader = WechatDownloader()
    parser = WechatParser()

    url = 'https://mp.weixin.qq.com/s/DOgJX0whawipiC_Ewq44zA'

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
