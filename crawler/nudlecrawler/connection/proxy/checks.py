import httpx
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, List
from urllib.parse import urlparse


class BaseProxyCheck(ABC):
    """Base class for all proxy checks.

    Attributes:
        url (str): The URL to check against
        expected_content (Optional[str]): Content that should be present in the response
        timeout (int): Timeout in seconds for the check
    """

    def __init__(self, url: str, expected_content: Optional[str] = None, timeout: int = 10):
        self._validate_url(url)
        self.url = url
        self.expected_content = expected_content
        self.timeout = timeout

    @staticmethod
    def _validate_url(url: str) -> None:
        """Validate the URL format.

        Args:
            url (str): URL to validate

        Raises:
            ValueError: If URL is invalid
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                raise ValueError("Invalid URL format")
        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")

    @abstractmethod
    async def check(self, client: httpx.AsyncClient) -> bool:
        """Execute the check using the provided client.

        Args:
            client (httpx.AsyncClient): HTTP client to use for the check

        Returns:
            bool: True if check passes, False otherwise
        """
        pass

    @classmethod
    async def run_checks(cls, client: httpx.AsyncClient, checks: List['BaseProxyCheck']) -> bool:
        """Run multiple checks in parallel.

        Args:
            client (httpx.AsyncClient): HTTP client to use for checks
            checks (List[BaseProxyCheck]): List of checks to perform

        Returns:
            bool: True if all checks pass, False otherwise
        """
        results = await asyncio.gather(*[check.check(client) for check in checks],
                                       return_exceptions=True)
        return all(isinstance(r, bool) and r for r in results)


class AliveCheck(BaseProxyCheck):
    """Check if proxy is responsive by verifying IP address endpoint access."""

    def __init__(self):
        super().__init__(
            url="http://httpbin.org/ip",
            expected_content="origin"
        )

    async def check(self, client: httpx.AsyncClient) -> bool:
        try:
            response = await client.get(self.url)
            return response.status_code == 200 and self.expected_content in response.text
        except Exception:
            return False


class CloudflareCheck(BaseProxyCheck):
    """Check if proxy works with Cloudflare protected sites by testing access to a known CF site."""

    def __init__(self):
        super().__init__(
            url="https://nowsecure.nl",
            expected_content="<title>nowsecure.nl</title>"
        )

    async def check(self, client: httpx.AsyncClient) -> bool:
        try:
            response = await client.get(self.url)
            return self.expected_content in response.text
        except Exception:
            return False


class GeneralCheck(BaseProxyCheck):
    """Check if proxy works with general websites by testing access to Wikipedia."""

    def __init__(self):
        super().__init__(
            url="https://wikipedia.org",
            expected_content="<title>Wikipedia</title>"
        )

    async def check(self, client: httpx.AsyncClient) -> bool:
        try:
            response = await client.get(self.url, timeout=self.timeout)
            return response.status_code == 200 and self.expected_content in response.text
        except Exception as e:
            return False
