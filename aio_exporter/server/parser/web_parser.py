import os.path

from .base_parser import BaseParser
import markdownify
import readability
import html_text
import pylcs
import numpy as np
from bs4 import BeautifulSoup


class WebParser(BaseParser):
    def __init__(self):
        super().__init__()

    def find_common_se(self, html_doc , md_zw):

        res = pylcs.lcs_sequence_idx(html_doc, md_zw)
        res = [_ for _ in res if _ != -1]
        start = min([_ for _ in res if _ != -1])
        end = max([_ for _ in res if _ != -1])

        res2 = np.array(pylcs.lcs_sequence_idx(md_zw , html_doc))
        start2 = (res2 != -1).nonzero()[0][0]
        end2 = (res2 != -1).nonzero()[0][1]
        start = min(start , start2)
        end = max(end , end2)
        return start , end


        return start , end


    def parse(self , file):
        if os.path.exists(file):
            with open(file) as f:
                doc_text = f.read()
        else:
            doc_text = file

        # content = html_text.extract_text(html_doc.summary(html_partial=True))

        html_doc = readability.Document(doc_text)
        soup = BeautifulSoup(html_doc.summary(), 'html.parser')
        self.format_img(soup)
        md_zw = markdownify.markdownify(str(soup))

        # 找到正文的部分
        return md_zw
