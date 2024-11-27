from dataclasses import dataclass
from typing import List,Dict

@dataclass
class Login:
    cookies : List[Dict] = None

@dataclass
class WechatLogin(Login):
    token: int = None

@dataclass
class ZhihuLogin(Login):
    zse_ck: str = None