import os
import socket
import threading
import time
import flask
import httpx
import pytest
from werkzeug.serving import make_server
from unittest.mock import AsyncMock, MagicMock, patch
from nudlecrawler.connection import ConnectionManager, RequestConfig
from nudlecrawler.connection.exceptions import BridgeException
from nudlecrawler.connection.proxy import Proxy, ProxyType, UseCases, RotationConfig

os.environ.setdefault("TIMEOUT", "5")


class LiveServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1'):
        super().__init__()
        self.daemon = True  # @note: Allow main program to exit even if this thread is running
        self.app = app
        self.host = host
        # @note: Bind to port 0 to let the OS choose a free port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((self.host, 0))
            self.port = s.getsockname()[1]

        self.server = make_server(
            self.host, self.port, self.app, threaded=True)
        self.ctx = self.app.app_context()
        self.url = f"http://{self.host}:{self.port}"

    def run(self):
        self.ctx.push()
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()
        self.join(timeout=5)


@pytest.fixture(scope="module")
def bridge_flask_app():
    """Fixture to create the Flask app instance for the bridge proxy."""
    app = flask.Flask(__name__)
    app.testing = True

    @app.route('/bridge/get', methods=['GET'])
    def bridge_route():
        return flask.jsonify({
            "content": "Mocked data from live bridge",
            "text": "Mocked text from live bridge",
            "html": "Mocked HTML from live bridge",
        })

    return app


@pytest.fixture(scope="module")
def live_bridge_server(bridge_flask_app):
    """Fixture to start the Flask app on a live server and yield its base URL."""
    server_thread = LiveServerThread(bridge_flask_app)
    server_thread.start()
    time.sleep(0.1)
    yield server_thread.url
    server_thread.shutdown()


@pytest.fixture
def mock_response():
    """Fixture to create a mock httpx.Response."""
    def _mock_response(status_code=200, json_data=None, text_data="", headers=None):
        response = MagicMock(spec=httpx.Response)
        response.status_code = status_code
        response.headers = headers or {}
        response.json = MagicMock(return_value=json_data or {})
        response.text = text_data

        if status_code >= 400:
            response.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError(
                f"{status_code} Client Error",
                request=MagicMock(),
                response=response
            ))
        else:
            response.raise_for_status = MagicMock()
        return response
    return _mock_response


@pytest.fixture
def mock_async_client():
    """Fixture to mock httpx.AsyncClient."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    return mock_client


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_disabled_success(mock_async_client_cls, mock_response, mock_async_client):
    """Test successful GET request with no proxy."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok"}))

    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=None, request_config=config)
    url = "http://test.com"

    response = await manager.get(url)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"} # type: ignore
    mock_async_client.get.assert_called_once_with(
        url=url,
        headers=manager._get_headers()
    )


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_disabled_failure(mock_async_client_cls, mock_response, mock_async_client):
    """Test failed GET request (non-200) with no proxy."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(
        return_value=mock_response(status_code=404))

    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=None, request_config=config)
    url = "http://test.com/notfound"

    response = await manager.get(url)
    assert response.status_code == 404


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_static_success(mock_async_client_cls, mock_response, mock_async_client):
    """Test successful GET request with SIMPLE proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok_static"}))

    proxy = Proxy(
        url="http://user:pass@staticproxy.com:8080",
        type=ProxyType.SIMPLE,
        usage=[UseCases.DEFAULT]
    )
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=[proxy], request_config=config)
    manager.set_proxy_checks([])

    url = "http://test.com/get_static"

    response = await manager.get(url)

    assert response.status_code == 200
    assert response.json() == {"status": "ok_static"} # type: ignore


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_static_failure(mock_async_client_cls, mock_response, mock_async_client):
    """Test failed GET request (non-200) with SIMPLE proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(return_value=mock_response(
        status_code=500))

    proxy = Proxy(
        url="http://staticproxy.com:8080",
        type=ProxyType.SIMPLE,
        usage=[UseCases.DEFAULT]
    )
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=[proxy], request_config=config)
    manager.set_proxy_checks([])

    url = "http://test.com/servererror"

    response = await manager.get(url)

    assert response.status_code == 500


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_rotating_success(mock_async_client_cls, mock_response, mock_async_client):
    """Test successful GET request with ROTATING proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok_rotating"}))

    proxies = [
        Proxy(
            url="http://proxy1.com:8080",
            type=ProxyType.ROTATING,
            usage=[UseCases.DEFAULT],
            rotation=RotationConfig(enabled=True, interval=1)
        ),
        Proxy(
            url="http://proxy2.com:8080",
            type=ProxyType.ROTATING,
            usage=[UseCases.DEFAULT],
            rotation=RotationConfig(enabled=True, interval=1)
        )
    ]
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=proxies, request_config=config)
    manager.set_proxy_checks([])

    url = "http://test.com/get_rotating"

    assert manager._current_proxy_idx == 0
    response = await manager.get(url)

    assert response.status_code == 200
    assert response.json() == {"status": "ok_rotating"} # type: ignore

    assert manager._current_proxy_idx == 1
    assert manager._rotation_count[proxies[0].url] == 0


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_rotating_skips_bad_proxy(mock_async_client_cls, mock_response, mock_async_client):
    """Test ROTATING proxy skips a bad proxy and uses the next one."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(
        return_value=mock_response(status_code=200))

    proxies = [
        Proxy(
            url="http://badproxy.com:8080",
            type=ProxyType.ROTATING,
            usage=[UseCases.DEFAULT],
            rotation=RotationConfig(enabled=True, interval=1)
        ),
        Proxy(
            url="http://goodproxy.com:8080",
            type=ProxyType.ROTATING,
            usage=[UseCases.DEFAULT],
            rotation=RotationConfig(enabled=True, interval=1)
        )
    ]
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=proxies, request_config=config)
    manager.set_proxy_checks([])

    async def mock_perform_checks(*args, **kwargs):
        return proxies[0].url != "http://badproxy.com:8080"

    for proxy in proxies:
        proxy.perform_checks = AsyncMock(side_effect=mock_perform_checks)

    url = "http://test.com/get_rotating_skip"

    response = await manager.get(url)
    assert response.status_code == 200
    assert manager._current_proxy_idx == 1


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_get_rotating_no_working_proxies(mock_async_client_cls, mock_response, mock_async_client):
    """Test ROTATING proxy returns NONE type when no proxies work."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.get = AsyncMock(
        return_value=mock_response(status_code=200))

    proxies = [
        Proxy(
            url="http://badproxy1.com:8080",
            type=ProxyType.ROTATING,
            usage=[UseCases.DEFAULT],
            rotation=RotationConfig(enabled=True, interval=1)
        )
    ]
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=proxies, request_config=config)

    for proxy in proxies:
        proxy.perform_checks = AsyncMock(return_value=False)

    url = "http://test.com/get_rotating_fail"

    response = await manager.get(url)
    assert response.status_code == 200

    for proxy in proxies:
        proxy.perform_checks.assert_called_once() # type: ignore


@pytest.mark.asyncio
async def test_get_bridge_success(live_bridge_server):
    """Test successful GET request with BRIDGE proxy type."""
    target_url_to_proxy = "http://example.com/some/path"

    proxy = Proxy(
        url=live_bridge_server + "/bridge",
        type=ProxyType.BRIDGE,
        usage=[UseCases.DEFAULT]
    )
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=[proxy], request_config=config)
    manager.set_proxy_checks([])

    response = await manager.get(target_url_to_proxy)

    assert response.status_code == 200
    assert response.content == "Mocked data from live bridge"
    assert response.text == "Mocked text from live bridge"
    assert response.html == "Mocked HTML from live bridge" # type: ignore


@pytest.mark.asyncio
async def test_get_bridge_failure(live_bridge_server):
    """Test failed GET request (non-200) with BRIDGE proxy type."""
    target_url = "http://example.com/some/path"

    proxy = Proxy(
        url=live_bridge_server + "/invalid_bridge",
        type=ProxyType.BRIDGE,
        usage=[UseCases.DEFAULT]
    )
    config = RequestConfig(timeout=5)
    manager = ConnectionManager(proxy_pool=[proxy], request_config=config)
    manager.set_proxy_checks([])

    with pytest.raises(BridgeException) as excinfo:
        await manager.get(target_url)
    assert "Bridge request failed with status" in str(excinfo.value)
