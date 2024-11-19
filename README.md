
# ALL IN ONE DATA EXPORTER 

- 支持对指定的 up/博主 进行定时定期的搜集更新的文章
- 适合**个人**对少数up主进行**小批量的数据**的自动化获取

## 已经支持如下数据源

    - wechat
    - bilibili

## 使用方式

### On Linux Server

1. install 
    1. pip3 install -r requirements.txt
    2. download chrome driver and edit aio_exporter/utils/utils.py
       - substitute the path of chrome driver in the file

2. change config file
   - edit aio_exporter/server/config.py 
   - customise subscription accounts

3. start server
    
    - PYTHONPATH=`pwd` python3 aio_exporter/cli/main.py

4. update your cookies
    
    - for wechat / bilibili scrawling or downloading , you must upload your cookies to server 
    - in your local computer (which can use selenium to open a web browser)
    - using PYTHONPATH=`pwd` python3 aio_exporter/local/login/xxx_login.py
    - this scripts will let you login to the website and record your cookies , then send to your server 


5. set crontab task

   - edit commands/cron_setting , and copy these lines to 'crontab -e'
   - these will create four task for getting url and downling html / video 
   
6. use webui to view stats of download 

    - using PYTHONPATH=`pwd` streamlit run webui/main.py
    - you will see the dashboard about scrawling stats and download stats 


## Webui 展示信息

资料的获取和下载一共分为两个部分

1. 获取所有博主的帖子/视频的 url
2. 对这些 url 内容进行下载

- 提供了两个 webui 页面

    - 页面1 负责展示 url 的获取情况
      -  ![img](/doc/page1.png)
    
    - 页面2 负责提供当前下载情况的展示以及下载结果的展示
      -  ![img](/doc/page2.png)
        
[注意]
视频结果展示会调用公网的asr服务,如需使用:
1. 在本仓库下建立 .env 文件
2. 添加硅基流动api SILICON_TOKEN=sk-xxx
3. 你也可以自行更换为自己的服务


# 目录结构说明

## aio_exporter

    ## cli
        - 提供各种后端爬虫服务的接口,包括获取更新的url,下载等功能

    ## server
        - scrawler
            - 获取所有希望爬取的网页的 url
        - downloader
            - 对各种网页,进行下载
    ## local
            - 负责各种源的 cookie 的重新生成和推送到远端服务器

## aio_parser_server 
    
    - 负责将 torchocr 能力 / whisper 能力 / got ocr 2.0 的能力包装成服务   
    - 这样可以在一个 GPU 服务器上运行这些服务,然后如果 爬虫服务的 parser 需要使用相关的能力，可以通过接口调用的方式调用这些能力 
    - 通过 PYTHONPATH=`pwd` python3 aio_parser_server/main.py 启动

## commands:
        - 执行定时任务的脚本



# installation tips 

## linux chrome driver download 
    - https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.91/linux64/chromedriver-linux64.zip
    - https://googlechromelabs.github.io/chrome-for-testing/

## pip source 
    - https://pypi.tuna.tsinghua.edu.cn/simple

## yutto
    pip3 install 
    - pip install --pre yutto -i https://pypi.tuna.tsinghua.edu.cn/simple
    ffmpeg
    - apt install ffmpeg
    or 
    - wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-<version>-static.tar.xz
    - tar -xvJf ffmpeg-release-<version>-static.tar.xz
    - cd ffmpeg-<version>-static/
    - sudo cp ffmpeg /usr/local/bin/
    - sudo cp ffprobe /usr/local/bin/
    - sudo chmod +x /usr/local/bin/ffmpeg
    - sudo chmod +x /usr/local/bin/ffprobe

## 参考项目
    1. https://github.com/jooooock/wechat-article-exporter
    2. https://github.com/yutto-dev/yutto

## 公有云大模型服务
    1. https://cloud.siliconflow.cn