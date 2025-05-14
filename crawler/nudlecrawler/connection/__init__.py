import os
import httpx
import logging
import asyncio
from typing import List, Optional, Dict
from urllib.parse import urlparse
from nudlecrawler.connection.exceptions import BridgeException
from nudlecrawler.connection.proxy import Proxy, ProxyChecks, ProxyType, UseCases
from nudlecrawler.connection.types import Response

logger = logging.getLogger(__name__)


class RequestConfig:
    """Configuration settings for HTTP/HTTPS requests.

    Controls the behavior of outgoing HTTP requests including timeouts,
    SSL verification, and redirect handling.

    Attributes:
        timeout (int): Maximum time in seconds to wait for server response
        verify_ssl (bool): SSL certificate verification flag
        follow_redirects (bool): Whether to automatically follow HTTP redirects
        max_redirects (int): Maximum number of redirects to follow before failing

    Example:
        config = RequestConfig(
            timeout=60,
            verify_ssl=False,
            follow_redirects=True,
            max_redirects=5
        )
    """

    def __init__(self, timeout: int = 30, verify_ssl: bool = True, follow_redirects: bool = True, max_redirects: int = 10):
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects
        self.max_redirects = max_redirects


class ConnectionManager:
    """Manages HTTP connections with advanced proxy support and rotation.

    Provides a high-level interface for making HTTP requests with features like:
    - Proxy rotation and health checking
    - Custom header management
    - Support for both direct and bridge proxy connections
    - Automatic request retries and failover
    
    Attributes:
        proxy_pool (List[Proxy]): Available proxy servers for rotation
        request_config (RequestConfig): Global request settings
        _proxy_checks (List[ProxyChecks]): Active proxy health check configurations
        _rotation_count (Dict[str, int]): Tracks proxy usage for rotation
        _current_proxy_idx (int): Index of current proxy in pool
        _custom_user_agent (Optional[str]): Custom User-Agent header if set
    """

    def __init__(self, proxy_pool: Optional[List[Proxy]] = None, request_config: Optional[RequestConfig] = None):
        """Initialize the connection manager with proxy and request settings.

        Args:
            proxy_pool: List of proxy servers to use for requests. If None, direct
                      connections will be used.
            request_config: Global request configuration settings. If None, default
                          settings will be used.

        Example:
            manager = ConnectionManager(
                proxy_pool=[Proxy(url="http://proxy:8080")],
                request_config=RequestConfig(timeout=30)
            )
        """
        self.proxy_pool: List[Proxy] = proxy_pool or []
        self.request_config = request_config or RequestConfig(
            timeout=int(os.getenv("TIMEOUT", 30))
        )

        # @params: Proxy management
        self._rotation_count: Dict[str, int] = {}
        self._current_proxy_idx: int = 0
        self._proxy_checks: List[ProxyChecks] = [
            ProxyChecks.ALIVE,
            ProxyChecks.CLOUDFLARE,
            ProxyChecks.GENERAL
        ]

        # @params: Headers
        self._custom_user_agent: Optional[str] = None
        self._default_headers = {
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "Accept": "*/*"
        }

    # @context: Setters
    def set_user_agent(self, user_agent: Optional[str]) -> None:
        """Set a custom User-Agent header.
        
        This will override the default User-Agent header.
        If None is provided, the default User-Agent will be used.
        
        Args:
            user_agent: User agent string or None to use default

        Raises:
            ValueError: If user_agent is neither string nor None
        """
        if user_agent is not None and not isinstance(user_agent, str):
            raise ValueError("User agent must be a string or None")

        self._custom_user_agent = user_agent
        logger.debug(
            f"User agent set to: {user_agent if user_agent else 'default'}")

    def set_proxy_checks(self, checks: List[ProxyChecks]) -> None:
        """Set which proxy checks to perform.

        Args:
            checks: List of proxy checks to perform

        Raises:
            ValueError: If checks is not a list
        """
        if not isinstance(checks, list):
            raise ValueError("Proxy checks must be a list")
        if not all(isinstance(check, ProxyChecks) for check in checks):
            raise ValueError("All checks must be ProxyChecks enum values")

        self._proxy_checks = checks
        logger.debug(f"Proxy checks set to: {checks}")

    # @context: Public
    async def post(self, url: str, payload: dict) -> httpx.Response:
        """Send HTTP POST request with automatic proxy handling.

        Makes a POST request to the specified URL using the configured proxy
        settings and rotation strategy. Automatically handles both direct and
        bridge proxy connections.

        Args:
            url: Target URL for the POST request
            payload: Data to send in request body (will be JSON encoded)

        Returns:
            httpx.Response: Server response with status, headers, and body

        Raises:
            BridgeException: When bridge proxy request fails
            httpx.RequestError: On network or protocol errors
            ValueError: If URL is malformed

        Example:
            response = await manager.post(
                "https://api.example.com/data",
                {"key": "value"}
            )
        """
        self._validate_url(url)
        proxy = await self._get_proxy()

        if proxy.type == ProxyType.BRIDGE:
            return await self._post_bridge(url, payload, proxy)
        else:
            return await self._post_normal(url, payload, proxy)

    async def get(self, url: str) -> httpx.Response:
        """Make a GET request with optional proxy routing.

        Args:
            url: Target URL

        Returns:
            httpx.Response: Server response with status, headers, and body

        Raises:
            BridgeException: If bridge request fails
            httpx.RequestError: For other request failures
            ValueError: If URL is malformed

        Example:
            response = await manager.get("https://api.example.com/data")
        """
        self._validate_url(url)
        proxy = await self._get_proxy()

        if proxy.type == ProxyType.BRIDGE:
            return await self._get_bridge(url, proxy)
        else:
            return await self._get_normal(url, proxy)

    # @context: Private
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with optional custom User-Agent.

        Returns:
            Dict[str, str]: HTTP headers for the request
        """
        headers = self._default_headers.copy()
        headers["User-Agent"] = (
            self._custom_user_agent or
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        return headers

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validate URL format.

        Args:
            url: URL to validate

        Raises:
            ValueError: If URL is invalid
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")

    async def _get_proxy(self) -> Proxy:
        """Get next valid proxy from pool with rotation support.

        Returns:
            Proxy: Selected proxy configuration

        Note:
            Returns NONE type proxy if no valid proxies are available
        """
        if not self.proxy_pool:
            return Proxy(url="http://0.0.0.0:0000", type=ProxyType.NONE)

        proxies_checked = 0
        while proxies_checked < len(self.proxy_pool):
            current_proxy = self.proxy_pool[self._current_proxy_idx]

            # @logic: Update rotation tracking
            self._rotation_count[current_proxy.url] = (
                self._rotation_count.get(current_proxy.url, 0) + 1
            )

            # @logic: Check rotation interval
            if (current_proxy.rotation.enabled and
                current_proxy.rotation.interval and
                    self._rotation_count[current_proxy.url] >= current_proxy.rotation.interval):
                self._current_proxy_idx = (
                    self._current_proxy_idx + 1) % len(self.proxy_pool)
                self._rotation_count[current_proxy.url] = 0

            # @logic: Verify proxy health
            if self._proxy_checks and not await current_proxy.perform_checks(self._proxy_checks):
                self._current_proxy_idx = (
                    self._current_proxy_idx + 1) % len(self.proxy_pool)
                proxies_checked += 1
                continue

            return current_proxy

        logger.warning(
            "No valid proxies available, falling back to direct connection")
        return Proxy(url="http://0.0.0.0:0000", type=ProxyType.NONE)

    def _create_bridge_response(self, response: httpx.Response) -> httpx.Response:
        """Create response object from bridge proxy response.

        Args:
            response: Raw response from bridge proxy

        Returns:
            httpx.Response: Processed response object

        Raises:
            BridgeException: If response processing fails
        """
        try:
            json_response = response.json()
            return Response(
                status_code=response.status_code,
                headers=response.headers,
                content=json_response.get('content', b''),
                text=json_response.get('text', ''),
                html=json_response.get('html', ''),
                json=json_response.get('json', '')
            )
        except Exception as e:
            raise BridgeException(
                f"Failed to process bridge response: {str(e)}")

    async def _post_normal(self, url: str, payload: dict, proxy: Proxy) -> httpx.Response:
        """Make POST request through normal proxy.

        Args:
            url: Target URL
            payload: Request payload
            proxy: Proxy configuration

        Returns:
            httpx.Response: Server response

        Raises:
            httpx.RequestError: On request failure
        """
        client_args = {
            "timeout": self.request_config.timeout,
            "verify": self.request_config.verify_ssl,
            "follow_redirects": self.request_config.follow_redirects,
            "max_redirects": self.request_config.max_redirects
        }

        if proxy.type != ProxyType.NONE:
            client_args["proxy"] = proxy.url

        async with httpx.AsyncClient(**client_args) as client:
            return await client.post(
                url=url,
                json=payload,
                headers=self._get_headers()
            )

    async def _post_bridge(self, url: str, payload: dict, proxy: Proxy) -> httpx.Response:
        """Make POST request through bridge proxy.

        Args:
            url: Target URL
            payload: Request payload
            proxy: Bridge proxy configuration

        Returns:
            httpx.Response: Processed response

        Raises:
            BridgeException: If bridge request fails
        """
        async with httpx.AsyncClient(
            timeout=self.request_config.timeout,
            verify=self.request_config.verify_ssl
        ) as client:
            response = await client.post(
                url=proxy.url+"/post",
                json={"url": url, "payload": payload},
                headers=self._get_headers()
            )

            if response.status_code != 200:
                raise BridgeException(
                    f"Bridge request failed with status {response.status_code}")

            return self._create_bridge_response(response)

    async def _get_normal(self, url: str, proxy: Proxy) -> httpx.Response:
        """Make GET request through normal proxy.

        Args:
            url: Target URL
            proxy: Proxy configuration

        Returns:
            httpx.Response: Server response

        Raises:
            httpx.RequestError: On request failure
        """
        client_args = {
            "timeout": self.request_config.timeout,
            "verify": self.request_config.verify_ssl,
            "follow_redirects": self.request_config.follow_redirects,
            "max_redirects": self.request_config.max_redirects
        }

        if proxy.type != ProxyType.NONE:
            client_args["proxy"] = proxy.url

        async with httpx.AsyncClient(**client_args) as client:
            return await client.get(
                url=url,
                headers=self._get_headers()
            )

    async def _get_bridge(self, url: str, proxy: Proxy) -> httpx.Response:
        """Make GET request through bridge proxy.

        Args:
            url: Target URL
            proxy: Bridge proxy configuration

        Returns:
            httpx.Response: Processed response

        Raises:
            BridgeException: If bridge request fails
        """
        async with httpx.AsyncClient(
            timeout=self.request_config.timeout,
            verify=self.request_config.verify_ssl
        ) as client:
            response = await client.get(
                url=proxy.url+"/get",
                params={"url": url},
                headers=self._get_headers()
            )

            if response.status_code != 200:
                raise BridgeException(
                    f"Bridge request failed with status {response.status_code}")

            return self._create_bridge_response(response)
