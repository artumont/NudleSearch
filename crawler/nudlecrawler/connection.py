import os
import logging
import httpx
from enum import Enum
from typing import List
from .exceptions import BridgeException, ProxyException

logger = logging.getLogger(__name__)


class ProxyTypes(Enum):
    # @note: Static connection (1 proxy)
    STATIC: int = 1
    # @note: Rotating connection (rotating proxy | >2 proxies)
    ROTATING: int = 2
    # @note: Bridge connection (route thru a cf worker / service | 1 url)
    BRIDGE: int = 3
    # @note: Disabled connection (no proxy)
    DISABLED: int = 4


class ConnectionManager:
    def __init__(self, proxy_type: ProxyTypes, proxy_pool: str | List[str] | None):
        self.proxy_idx = 0
        self.timeout = int(os.environ.get("TIMEOUT", 10))
        self.proxy_type = proxy_type
        if proxy_pool:
            if isinstance(proxy_pool, str):
                self.proxy_pool = [proxy_pool]
            else:
                self.proxy_pool = proxy_pool

    # @context: Public
    async def post(self, url: str, data: dict) -> httpx.Response | Exception:
        try:
            # @note: This will be fetching via a fetcher API instead of fetching thru a proxy
            if self.proxy_type == ProxyTypes.BRIDGE:
                try:
                    return await self._post_bridge(url, data)
                except Exception as e:
                    logger.error(f"Bridge post request failed: {e}")
                    raise
            # @note: This will be fetching via a proxy/client_ip instead of fetching thru a fetcher API
            elif self.proxy_type in [ProxyTypes.STATIC, ProxyTypes.ROTATING]:
                try:
                    return await self._post_static_rotating(url, data)
                except Exception as e:
                    logger.error(f"Static/Rotating post request failed: {e}")
                    raise
            # @note: This will be fetching without a proxy
            else:
                try:
                    return await self._post_disabled(url, data)
                except Exception as e:
                    logger.error(f"Proxyless post request failed: {e}")
                    raise
        except Exception as e:
            logger.error(f"Post request failed: {e}")
            raise

    async def get(self, url: str) -> httpx.Response | Exception:
        pass

    # @context: Private
    async def _post_bridge(self, url: str, data: dict) -> httpx.Response | Exception:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=self.proxy_pool[0],
                headers=self._get_headers(),
                timeout=self.timeout,
                data={
                    "url": url,
                    "data": data
                }
            )

        if response.status_code != 200:
            logger.error("Bridge connection failed")
            raise BridgeException(
                f"Bridge connection failed with status code: {response.status_code}")

        return response

    async def _post_static_rotating(self, url: str, data: dict) -> httpx.Response | Exception:
        proxy = await self._get_proxy()
        async with httpx.AsyncClient(proxies=proxy) as client:
            response = await client.post(
                url=url,
                headers=self._get_headers(),
                timeout=self.timeout,
                data=data
            )

        if response.status_code != 200:
            logger.error(
                f"Static/Rotating connection failed with status code: {response.status_code}")
            raise BridgeException(
                f"Static/Rotating connection failed with status code: {response.status_code}")

        return response

    async def _post_disabled(self, url: str, data: dict) -> httpx.Response | Exception:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url=url,
                headers=self._get_headers(),
                timeout=self.timeout,
                data=data
            )

        if response.status_code != 200:
            logger.error(
                f"Proxyless connection failed with status code: {response.status_code}")
            raise BridgeException(
                f"Proxyless connection failed with status code: {response.status_code}")

        return response

    async def _get_proxy(self) -> str | Exception:
        start_idx = self.proxy_idx
        while True:
            proxy = self.proxy_pool[self.proxy_idx]
            self.proxy_idx = (self.proxy_idx + 1) % len(self.proxy_pool)
            proxy_check = await self._check_proxy(proxy)
            if self.proxy_idx == start_idx and not proxy_check:
                raise ProxyException("No working proxies available")
            if proxy_check:
                return {
                    "http://": proxy,
                    "https://": proxy,
                }

    def _get_headers(self) -> dict:
        # @todo: Make this dynamic based on the request type or something else (GET/POST) maybe even rotating user agents
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        }

    async def _check_proxy(self, proxy: str) -> bool:
        try:
            proxy_parts = proxy.split('@')
            headers = self._get_headers()
            proxies = {
                "http://": proxy,
                "https://": proxy,
            }

            async with httpx.AsyncClient(proxies=proxies, timeout=self.timeout, headers=headers) as client:
                # @logic: Test 1 - Basic proxy check
                try:
                    ip_response = await client.get("https://httpbin.org/ip")
                    ip_response.raise_for_status()

                    data = ip_response.json()
                    proxy_ip_part = proxy_parts[-1] if '@' in proxy else proxy
                    proxy_ip = proxy_ip_part.split(':')[0]

                    if not data or "origin" not in data or data["origin"] != proxy_ip:
                        logger.warning(
                            f"Proxy IP verification failed for {proxy}. Expected {proxy_ip}, got {data.get('origin')}")
                        return False
                    logger.debug(f"Proxy basic check passed for {proxy}")

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"Basic proxy check failed for {proxy}: Status {e.response.status_code}")
                    return False
                except Exception as e:
                    logger.warning(
                        f"Basic proxy check failed for {proxy}: {e}")
                    return False

                # @logic: Test 2 - Cloudflare protected site
                try:
                    cf_response = await client.get("https://nowsecure.nl")
                    cf_response.raise_for_status()
                    if "cf-ray" not in cf_response.headers:
                        logger.warning(
                            f"Cloudflare check failed for {proxy}: 'cf-ray' header missing.")
                    logger.debug(f"Proxy Cloudflare check passed for {proxy}")

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"Cloudflare check failed for {proxy}: Status {e.response.status_code}")
                    return False
                except Exception as e:
                    logger.warning(f"Cloudflare check failed for {proxy}: {e}")
                    return False

                # @logic: Test 3 - General site accessibility (optional, can be slow)
                try:
                    google_response = await client.get("https://www.google.com")
                    google_response.raise_for_status()
                    logger.debug(
                        f"Proxy general accessibility check passed for {proxy}")

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"General accessibility check failed for {proxy}: Status {e.response.status_code}")
                    return False
                except Exception as e:
                    logger.warning(
                        f"General accessibility check failed for {proxy}: {e}")
                    return False

            logger.info(f"Proxy check successful for {proxy}")
            return True

        except Exception as e:
            logger.error(f"Proxy check failed unexpectedly for {proxy}: {e}")
            return False
