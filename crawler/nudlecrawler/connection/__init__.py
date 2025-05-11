import os
import httpx
import logging
from typing import List
from nudlecrawler.connection.types import Proxy, ProxyChecks

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self, proxy_pool: List[Proxy]):
        """Initialize the connection manager with a proxy pool."""
        # @param: Proxy connection variables
        self.rotation_idx: int = 0
        self.current_proxy_idx: int = 0
        self.proxy_pool: List[Proxy] = proxy_pool
        self.timeout: int = int(os.getenv("TIMEOUT", 10))

        # @param: Non-argument variables
        self.custom_user_agent = None
        self.proxy_checks = [
            ProxyChecks.ALIVE,
            ProxyChecks.WORKING,
            ProxyChecks.CLOUDFLARE,
            ProxyChecks.GENERAL
        ]

    # @context: Utility
    def set_user_agent(self, user_agent: str) -> None:
        """Set the user agent for the connection."""
        if user_agent is not None and not isinstance(user_agent, str):
            raise ValueError("User agent must be a string or None")

        self.custom_user_agent = user_agent
        logger.debug(
            f"User agent set to: {user_agent if user_agent else 'default'}")
    
    def set_proxy_checks(self, checks: List[ProxyChecks]) -> None:
        """Set the proxy checks to perform."""
        if not isinstance(checks, list):
            raise ValueError("Proxy checks must be a list")

        self.proxy_checks = checks
        logger.debug(f"Proxy checks set to: {checks}")

    # @context: Public
    async def post(self, url: str, payload: dict) -> httpx.Response:
        """Make a POST request to the given URL with the given payload."""
        pass
    
    async def get(self, url: str) -> httpx.Response:
        """Make a GET request to the given URL."""
        pass
    
    # @context: Private
    def _get_headers(self) -> dict:
        pass
    
    async def _get_proxy(self) -> Proxy | Exception:
        pass
    
    async def _check_proxy(self, proxy: Proxy) -> bool:
        pass