from pydantic import BaseModel, Field
from typing import List ,Dict

class Cookies(BaseModel):
    cookies: List[Dict]