
# ALL IN ONE DATA EXPORTER 
    - wechat
    - [TODO] bilibili


## cli
    - 负责利用 selenimn 扫码登录,创建cookie
    - 利用 server 端提供的 post 服务,将 cookie 和其他各种信息推送到 服务端

## server
    - 1. 接受 client 端推送的 cookie 和 其他信息
    - 2. 利用 cookie 和 其他信息, 通过定时任务调用各种接口获取数据
    
    - scrawler
        - 获取所有希望爬取的网页的 url
    - downloader
        - 对各种网页,进行下载


## local
    - 负责各种工具的 cookie的重新生成 


## linux chrome driver download 
    - https://storage.googleapis.com/chrome-for-testing-public/130.0.6723.91/linux64/chromedriver-linux64.zip
    - https://googlechromelabs.github.io/chrome-for-testing/

## pip source 
    - https://pypi.tuna.tsinghua.edu.cn/simple