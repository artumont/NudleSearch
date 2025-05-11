class ProxyException(Exception):
    """Exception raised when no working proxies are available."""
    pass


class BridgeException(Exception):
    """Exception raised when the bridge connection fails."""
    pass
