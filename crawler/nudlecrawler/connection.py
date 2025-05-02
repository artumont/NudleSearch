import logging
from typing import List
import requests
from enum import Enum

logger = logging.getLogger(__name__)


class ConnectionTypes(Enum):
    # @note: Static connection (can be no proxy or a static proxy | 1 proxy)
    STATIC: int = 1
    # @note: Rotating connection (rotating proxy | >2 proxies)
    ROTATING: int = 2
    # @note: Bridge connection (route thru a cf worker / service | 1 url)
    BRIDGE: int = 3


class ConnectionManager:
    def __init__(self, connection_type: ConnectionTypes, proxy_pool: str | List[str] | None):
        self.connection_type = connection_type
        if proxy_pool:
            if isinstance(proxy_pool, str):
                self.proxy_pool = [proxy_pool]
            else:
                self.proxy_pool = proxy_pool
                
        self.proxy_idx = 0

    # @method: Public
    async def post(self, url: str, data: dict) -> requests.Response | Exception:
        try:
            if self.connection_type == ConnectionTypes.BRIDGE:
                response = await requests.post(
                    url=self.proxy_pool[0],
                    data={
                        "url": url,
                        "data": data
                    }
                )

                if response.status == 200:
                    return response
                else:
                    logger.error("Bridge connection failed")
                    return Exception(f"Bridge connection failed with status code: {response.status}")
            else:
                response = await requests.post(
                    url=url,
                    data=data,
                    proxies={
                        "http": self.proxy_pool[0],
                        "https": self.proxy_pool[0]
                    }
                )
                
                return response
        except Exception as e:
            logger.error(f"Post request failed: {e}")
            return e

    async def get(self, url: str) -> requests.Response:
        pass
    
    # @method: Private
    def _get_proxy(self, only_ud: bool) -> str:
        if self.proxy_idx >= len(self.proxy_pool):
            self.proxy_idx = 0
            
        proxy = self.proxy_pool[self.proxy_idx]
        ud_check = self._check_proxy(proxy) if only_ud else True
        while not ud_check and only_ud:
            self.proxy_idx += 1
            if self.proxy_idx >= len(self.proxy_pool):
                self.proxy_idx = 0
            proxy = self.proxy_pool[self.proxy_idx]
            ud_check = self._check_proxy(proxy)
        else:
            self.proxy_idx += 1
            if self.proxy_idx >= len(self.proxy_pool):
                self.proxy_idx = 0
        
        return proxy
    
    def _check_proxy(self, proxy: str) -> bool:
        try:
            pass
        except Exception as e:
            logger.error(f"Proxy check failed: {e}")