
# ALL IN ONE DATA EXPORTER 
    - wechat
    - [TODO] bilibili

## aio_exporter

    ## cli
        - 提供爬虫服务的各种接口,包括获取更新的url,下载等功能


    ## server
        - scrawler
            - 获取所有希望爬取的网页的 url
        - downloader
            - 对各种网页,进行下载

## commands:
    - 执行定时任务的脚本

## local
    - 负责各种工具的 cookie的重新生成和推送到远端服务器


## linux chrome driver download 
    - https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.91/linux64/chromedriver-linux64.zip
    - https://googlechromelabs.github.io/chrome-for-testing/

## pip source 
    - https://pypi.tuna.tsinghua.edu.cn/simple

## yutto
    pip3 install 
    - pip install --pre yutto -i https://pypi.tuna.tsinghua.edu.cn/simple
    ffmpeg
    - wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-arm64-static.tar.xz
    - tar -xvJf ffmpeg-release-arm64-static.tar.xz
    - cd ffmpeg-<version>-static/
    - sudo cp ffmpeg /usr/local/bin/
    - sudo cp ffprobe /usr/local/bin/
    - sudo chmod +x /usr/local/bin/ffmpeg
    - sudo chmod +x /usr/local/bin/ffprobe