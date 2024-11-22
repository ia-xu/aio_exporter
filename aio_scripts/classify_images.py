


# 目标,尝试对图片进行分类

# 类别1: 完全无用的图片

# 类别2: 包含了有效信息的图片
import random
from aio_exporter.server.parser.base_parser import BaseParser
from aio_exporter.server.parser.mixin import ImageMixin

class Parser(BaseParser , ImageMixin):
    def classify(self , md_text):
        with self.localize_images(md_text) as (updated_md_text, images, image_urls):
            # 尝试利用 prompt, 对图片进行分类
            pass

if __name__ == '__main__':
    from pathlib import Path
    parser = Parser()
    md_files = list(Path('').glob('*.md'))

    random.shuffle(md_files)
    for md in md_files:
        with open(md , 'r') as f:
            md_text = f.read()

        parser.classify(md_text)



