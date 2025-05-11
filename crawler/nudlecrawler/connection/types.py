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
    
    def __init__(self, status_code, headers: dict, content: bytes, text: str = None, html: str = None, json: dict = None):
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.text = text
        self.html = html
        self.json = json

    def __repr__(self):
        return f"<Response status_code={self.status_code} headers={self.headers} content={self.content} text={self.text} html={self.html} json={self.json}>"
    
    def __str__(self):
        return f"Response(status_code={self.status_code}, headers={self.headers}, content={self.content}, text={self.text}, html={self.html}, json={self.json})"