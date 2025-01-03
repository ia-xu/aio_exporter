import os.path

from .base_parser import BaseParser
from bs4 import BeautifulSoup
import markdownify
from aio_exporter.utils import html_utils

class ZhihuParser(BaseParser):
    def __init__(self ):
        super().__init__()

    def clean_img(self , soup):
        for p in soup.find_all(class_ = 'origin_image zh-lightbox-thumb lazy'):
            p.extract()


    def parse(self , html_file_path):
        if 'ERROR' in html_file_path:
            return html_file_path
        if os.path.exists(html_file_path):
            with open(html_file_path, encoding='utf-8') as f:
                html = f.read()
        else:
            html = html_file_path

        soup = BeautifulSoup(html,'html.parser')

        self.clean_img(soup)

        if soup.find(class_ = 'QuestionButtonGroup') and soup.find(class_ = 'QuestionAnswers-answers'):
            # 说明是知乎的提问
            answers = soup.find(class_ = 'QuestionAnswers-answers')
            answers = answers.find_all(class_ = 'List-item')
            sep = '\n--------------------\n'
            md_all = sep
            for answer in answers:
                self.format_img(answer)
                md_zw = markdownify.markdownify(str(answer))
                md_all += html_utils.clean_html(md_zw)
                md_all += sep
        elif soup.find(class_ = 'ContentItem AnswerItem'):
            md_all = ""
            content = soup.find(class_ = 'ContentItem AnswerItem')
            self.format_img(content)
            md_zw = markdownify.markdownify(str(content))
            md_all += html_utils.clean_html(md_zw)

        else:
            content = soup.find(class_='Post-Main Post-NormalMain')
            if not content:
                content = soup.find(class_ = 'RichText ztext CopyrightRichText-richText')
                if not content:
                    return ""
            self.format_img(content)
            md_zw = markdownify.markdownify(str(content))
            md_all = html_utils.clean_html(md_zw)
        return md_all
