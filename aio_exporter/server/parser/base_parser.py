import re
import requests
from PIL import Image
from  io import BytesIO
import os
import hashlib
import concurrent.futures
from contextlib import contextmanager
import tempfile


class BaseParser:
    def __init__(self):
        pass

    def format_img(self,content):
        img_tags = content.find_all('img')
        for idx, img_tag in enumerate(img_tags):
            # wechat 的情况
            if img_tag.get('data-src') and not img_tag.get('src'):
                img_tag['src'] = img_tag['data-src']
                # 添加 alt ，区别于超链接，让转出来的 markdown 带有这个链接
                img_tag['alt'] = 'img'
            # zhihu 的情况
            if img_tag.get('src') and 'zhimg' in img_tag.get('src'):
                img_tag['alt'] = 'img'
            if img_tag.get('src') and not img_tag.get('alt'):
                img_tag['alt'] = 'img'

    def extract_images(self, md_text):
        # 从 md text 当中解析所有的 img url
        image_links = []
        # 获取一个 markdown 文档当中的所有的 ![img](url) 当中的 url

        pattern = r'!\[img\]\((http.*?)\)'
        matches = re.findall(pattern, md_text)
        for match in matches:
            if len(match) == 1:
                image_links.append(match)
            else:
                image_links.append(match.split(' ')[0])

        return image_links

    def download(self, image_links, dir):
        local_image_paths = []

        def download_image(link):
            response = requests.get(link)
            save_suffix = Image.open(BytesIO(response.content)).format

            # 获取文件名
            hashcode = hashlib.md5(link.encode('utf-8')).hexdigest()
            local_path = os.path.join(dir, hashcode + f'.{save_suffix}')
            with open(local_path, 'wb') as f:
                f.write(response.content)
            return local_path

        with concurrent.futures.ThreadPoolExecutor() as executor:
            local_image_paths = list(executor.map(download_image, image_links))
        return local_image_paths

    @contextmanager
    def localize_images(self, md_text):
        """
        Context manager to replace image URLs in a Markdown file with local paths.

        Args:
            md_text (str): The Markdown text containing image URLs.

        Yields:
            str: The updated Markdown text with local paths.
        """
        with tempfile.TemporaryDirectory() as td:
            try:
                image_links = self.extract_images(md_text)
                local_image_paths = self.download(image_links, td)
                updated_md_text = md_text
                for original_link, local_path in zip(image_links, local_image_paths):
                    updated_md_text = updated_md_text.replace(original_link, local_path)
                yield updated_md_text , local_image_paths, image_links
            finally:
                pass  # Cleanup of temporary directory is handled by TemporaryDirectory
