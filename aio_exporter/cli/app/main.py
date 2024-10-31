

import asyncio
from blacksheep import Application
from blacksheep.messages import Request, Response
from rodi import Container

# 创建服务容器
services = Container()

app = Application(
    services=services, show_error_details=True
)

@app.router.get("/")
async def home(request: Request):
    return {'message':'Hello, World!'}

