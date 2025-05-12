import httpx
import logging
from enum import Enum
from typing import Callable, Dict, List, Optional, Type, Union
from pydantic import BaseModel, field_validator, Field
from nudlecrawler.connection.proxy.checks import BaseProxyCheck, AliveCheck, CloudflareCheck, GeneralCheck

logger = logging.getLogger(__name__)


class ProxyType(Enum):
    """Proxy connection types model.

    Attributes:
        NONE: No proxy connection (direct)
        SIMPLE: Basic proxy connection
        ROTATING: Auto-rotating proxy connection
        BRIDGE: Connection routed through a proxy bridge service
    """
    NONE = 0
    SIMPLE = 1
    ROTATING = 2
    BRIDGE = 3


class UseCases(Enum):
    """Use cases for the proxy connection.

    Attributes:
        DEFAULT: Standard proxy usage for general websites
        CLOUDFLARE: Proxy specifically configured for Cloudflare-protected sites
    """
    DEFAULT = 0
    CLOUDFLARE = 1


class ProxyChecks(Enum):
    """Proxy checks to perform.

    Attributes:
        ALIVE: Basic connectivity check
        CLOUDFLARE: Check compatibility with Cloudflare sites
        GENERAL: Check general website accessibility
    """
    ALIVE = 0
    CLOUDFLARE = 1
    GENERAL = 2


class RotationConfig(BaseModel):
    """Configuration for proxy rotation.

    Attributes:
        enabled (bool): Whether rotation is enabled
        interval (Optional[int]): Number of requests before rotation
    """
    enabled: bool = Field(default=False)
    interval: Optional[int] = Field(default=None, gt=0)


class Proxy(BaseModel):
    """Proxy connection model.

    Attributes:
        url (str): The proxy URL in format protocol://host:port or protocol://user:pass@host:port
        type (ProxyType): Type of proxy connection
        usage (List[UseCases]): Intended use cases for this proxy
        rotation (RotationConfig): Proxy rotation settings
    """
    url: str
    type: ProxyType
    usage: List[UseCases] = Field(default_factory=list)
    rotation: RotationConfig = Field(default_factory=RotationConfig)
    perform_checks: Callable = None

    _check_map: Dict[ProxyChecks, Type[BaseProxyCheck]] = {
        ProxyChecks.ALIVE: AliveCheck,
        ProxyChecks.CLOUDFLARE: CloudflareCheck,
        ProxyChecks.GENERAL: GeneralCheck
    }

    @field_validator('url')
    def validate_url(cls, v):
        """Validate proxy URL format."""
        if not v:
            raise ValueError("Proxy URL cannot be empty")

        parts = v.split('://')
        if len(parts) != 2:
            raise ValueError(
                "Proxy URL must include protocol (e.g., http://, https://)")

        host_part = parts[1].split('@')[-1]
        if ':' not in host_part:
            raise ValueError("Proxy URL must include port number")

        return v

    @field_validator('usage')
    def validate_usage(cls, v):
        """Validate proxy usage configuration."""
        if not v:
            return [UseCases.DEFAULT]
        return v

    async def perform_checks(self, checks: List[ProxyChecks]) -> bool:
        """Perform the specified checks on this proxy in parallel.

        Args:
            checks (List[ProxyChecks]): List of checks to perform

        Returns:
            bool: True if all checks pass, False otherwise
        """
        if not checks or self.type == ProxyType.NONE:
            return True

        check_instances = []
        for check_type in checks:
            checker_class = self._check_map.get(check_type)
            if checker_class:
                check_instances.append(checker_class())

        if not check_instances:
            return True

        async with httpx.AsyncClient(
            proxy=self.url,
            verify=True,  # @param: Enable SSL verification
            timeout=30.0  # @param: Set a reasonable timeout
        ) as client:
            try:
                return await BaseProxyCheck.run_checks(client, check_instances)
            except Exception as e:
                logger.error(
                    f"Error performing checks for proxy {self.url}: {str(e)}")
                return False
