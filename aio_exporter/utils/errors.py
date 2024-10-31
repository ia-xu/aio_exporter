

# 定义一个自定义异常
class WechatGetBizNoError(Exception):
    def __init__(self, message="An error occurred"):
        self.message = message
        super().__init__(self.message)

class WechatGetArticlesError(Exception):
    def __init__(self , message = "an error occurred"):
        self.message = message
        super().__init__(self.message)
