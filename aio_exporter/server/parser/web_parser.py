from .base_parser import BaseParser
import markdownify
import readability
import html_text
class WebParser(BaseParser):
    def __init__(self):
        super().__init__()

    def parse(self , file):
        doc_text = file
        html_doc = readability.Document(doc_text)
        content = html_text.extract_text(html_doc.summary(html_partial=True))
        return content
