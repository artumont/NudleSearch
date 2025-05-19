from typing import Dict


class Response:
    """A class representing a response from an HTTP request.

    Attributes:
        status_code: The HTTP status code of the response.
        headers (dict): The HTTP headers returned in the response.
        content (bin): The raw binary content of the response.
        text (str, optional): The decoded text content of the response.
        html (str, optional): The HTML content of the response.
        json (dict, optional): JSON decoded data if the response contains JSON. Defaults to None.
    """

    def __init__(self, status_code, headers: Dict[str, str], content: bytes, text: str = "", html: str = "", json: dict = {}):
        self.status_code: int = status_code
        self.headers: Dict[str, str] = headers
        self.content: bytes = content
        self.text: str = text
        self.html: str = html
        self.json: dict = json

    def __repr__(self):
        return f"<Response status_code={self.status_code} headers={self.headers} content={self.content} text={self.text} html={self.html} json={self.json}>"

    def __str__(self):
        return f"Response(status_code={self.status_code}, headers={self.headers}, content={self.content}, text={self.text}, html={self.html}, json={self.json})"


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
        ```
        config = RequestConfig(
            timeout=60,
            verify_ssl=False,
            follow_redirects=True,
            max_redirects=5
        )
        ```
    """

    def __init__(self, timeout: int = 30, verify_ssl: bool = True, follow_redirects: bool = True, max_redirects: int = 10):
        self.timeout: int = timeout
        self.verify_ssl: bool = verify_ssl
        self.follow_redirects: bool = follow_redirects
        self.max_redirects: int = max_redirects
