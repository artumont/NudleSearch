from enum import Enum
from typing import List
from pydantic import BaseModel


class ProxyType(Enum):
    """Proxy connection types model."""
    # @note: Simple proxy connection (normal proxy)
    SIMPLE = 0
    # @note: Rotating connection (auto rotating proxy)
    ROTATING = 1
    # @note: Bridge connection (routing thru a cf worker / service)
    BRIDGE = 2


class UseCases(Enum):
    """Use cases for the proxy connection."""
    # @note: Use this on normal sites
    DEFAULT = 0
    # @note: Use this on cloudflare sites
    CLOUDFLARE = 1


class ProxyChecks(Enum):
    """Proxy checks to perform."""
    # @note: Check if the proxy is alive (if it can connect)
    ALIVE = 0
    # @note: Check if the proxy is working with http (changing ip)
    WORKING = 1
    # @note: Check if the proxy is working with cloudflare sites
    CLOUDFLARE = 2
    # @note: Check if the proxy is working with general sites
    GENERAL = 3


class Proxy(BaseModel):
    """Proxy connection model."""
    # @note: Proxy connection string (ip:port add user:pass if needed)
    url: str
    # @note: Proxy type (simple, rotating, bridge)
    type: ProxyType
    # @note: Use cases for this proxy (<= 1)
    usage: List[UseCases]
    # @note: Rotate after a certain number of requests (<= 1 or false for no rotation)
    rotation: bool | int = False
