from typing import List
import requests
from enum import Enum


class ConnectionTypes(Enum):
    STATIC: int = 1 # @note: Static connection (can be no proxy or a static proxy | 1 proxy)
    ROTATING: int = 2 # @note: Rotating connection (rotating proxy | >2 proxies)
    BRIDGE : int = 3 # @note: Bridge connection (route thru a cf worker / service | 1 url)

class ConnectionManager:
    def __init__(self, connection_type: ConnectionTypes, proxy_pool: str | List[str] | None):
        self.connection_type = connection_type
        if proxy_pool:
            if isinstance(proxy_pool, str):
                self.proxy_pool = [proxy_pool]
            else:
                self.proxy_pool = proxy_pool
    
    # @method: Public            
    def post(self, url: str, data: dict, cf_bypass: bool) -> requests.Response:
        pass
    
    def get(self, url: str, cf_bypass: bool) -> requests.Response:
        pass