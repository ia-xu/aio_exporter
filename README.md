
# ALL IN ONE DATA EXPORTER 

- 支持对指定的 up/博主 进行定时定期的搜集更新的文章
- 适合**个人**对少数up主进行**小批量的数据**的自动化获取

## 已经支持对如下数据源按照 公众号名称/up 主 进行数据下载

    - wechat
    - bilibili

## 已经支持对于如下数据源按照指定的 url 进行网页下载 

    - zhihu(支持了下载和解析,暂时不支持爬取)
    - 各种主流的新闻网站 (qq , sina , souhu , ...) ,详见 aio_exporter/config.yaml

## 支持搜索工具
    - kimichat (调用 api/search/kimisearch?question={question})
        - 利用 seleniumn 模拟 kimi 登录，向 kimi 发送问题并获取搜索到的 urls

## 项目说明

## 1. 项目的基本结构
    - 对于每一个不同的任务(wechat / bilibili / zhihu / news ...)都可以简单的认为存在三个不同的任务
        - 1. scrawler: 获取一个主体账号下面的所有的文章,获取文章的 title,url,issue_date,author等信息(仅仅是获取这些文章的信息，不做下载)
            - 这一步会将获取到的文章信息存储到 sqlite 数据库当中
        - 2. downloader: 对每一个获取到的url,下载到本地,保存成 html / video 等形式
            - 这一步需要为每一个url分配下载状态(尚未开始/下载失败/下载成功) 和分配一个本地下载路径    
            - 对分配了本地下载路径的文章进行下载
        - 3. parser : 
            - 对于已经下载好的 html / video , 调用 parser 进行解析,转化为 markdown 形式可以用于后续操作的数据
            - 这个过程可能会涉及到调用各种深度学习模型 ， 例如 视频的 asr ，文档图片的 ocr/vl大模型 解析，等等
## 2. 项目提供的两步下载模式
    - 对于文章的下载我们自然的会希望有两个步骤
        1. 对于历史文章的批量搜集和下载
        2. 对当前历史文章下载完成后,会希望通过一个定时任务的形式,定时定期的自动化更新数据库当中的文章信息
    - 本仓库因此提供了两种下载模式
        1. command/fast_download.py 
            - 用for循环粗暴的搜集所有需要的数据,逐步的下载全量数据
            - 你应该首先执行这个脚本,获取存量数据
        2. command/cron_setting
            - 启动一些定时任务,定期的下载数据
            - 存量下载完成后,使用 crontab 配置定时任务,定期为你自己下载数据
## 3. 项目提供了一下数据的使用的接口
    - 为了更方便的使用数据，项目对每一个不同的类别数据都提供了一些接口
        - 详见 aio_exporter/cli/app/controllers   
        - 例如获取账号的文章列表,获取指定文章的 markdown 格式的解析结果
## 4. 项目提供了一个描述下载情况的看版
    - 为了查看文章爬取和下载的情况,提供了一个看版展示各种信息
        - 详见 aio_exporter/webui/main.py
## 5. 项目提供了一个“搜索引擎”，用于获取一些新闻和相关的文章
    - 在构建文档库的过程中,针对每篇文章,你可能会希望搜集文章相关的问题
    - 参考 aio_exporter/server/scrawler/web_scrawler.py   
    - 借助 kimi , 你可以获取到你生成的问题的相关的各种 url 
    - 详见 api_exporter/cli/app/controllers/search.py 
## 6. 项目需要一些登录信息
    - 对于 wechat / zhihu / bilibili / kimi 信息的获取，你都需要进行selenimu 模拟登录和获取相关的cookie
    - 参考 aio_exporter/local/login 
        在你的本地电脑上打开网页并登录,这些代码会为你自动保存 cookie 


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
2. 添加硅基流动api API_KEY=sk-xxx
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