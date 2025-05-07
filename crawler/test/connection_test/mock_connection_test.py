import os
import socket
import threading
import time
import flask
import httpx
import pytest
from werkzeug.serving import make_server
from unittest.mock import AsyncMock, MagicMock, patch, call
from nudlecrawler.connection import ConnectionManager, ProxyTypes, BridgeException, ProxyException


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

    @app.route('/bridge/post', methods=['POST'])
    def bridge_route():
        if not flask.request.is_json:
            return flask.jsonify({
                "status": "error",
                "message": "Content-Type must be application/json"
            }), 415

        json_data = flask.request.get_json(force=True)
        if json_data is None:
            return flask.jsonify({
                "status": "error",
                "message": "No JSON data received"
            }), 400

        return flask.jsonify({
            "status": "success",
            "relayed_data": "Mocked data from live bridge",
            # @note: This is the data used in the test (not sent back in actual requests)
            "requested_url": json_data.get("url"),
            "payload": json_data.get("payload"),
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
async def test_post_disabled_success(mock_async_client_cls, mock_response, mock_async_client):
    """Test successful POST request with DISABLED proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok"}))

    manager = ConnectionManager(
        proxy_type=ProxyTypes.DISABLED, proxy_pool=None)
    url = "http://test.com"
    data = {"key": "value"}

    response = await manager.post(url, data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_async_client.post.assert_called_once_with(
        url=url,
        headers=manager._get_headers(),
        timeout=manager.timeout,
        json=data
    )


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_disabled_failure(mock_async_client_cls, mock_response, mock_async_client):
    """Test failed POST request (non-200) with DISABLED proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(
        return_value=mock_response(status_code=404))

    manager = ConnectionManager(
        proxy_type=ProxyTypes.DISABLED, proxy_pool=None)
    url = "http://test.com/notfound"
    data = {"key": "value"}

    with pytest.raises(BridgeException) as excinfo:
        await manager.post(url, data)
    assert "Proxyless connection failed with status code: 404" in str(
        excinfo.value)


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_static_success(mock_async_client_cls, mock_check_proxy, mock_response, mock_async_client):
    """Test successful POST request with STATIC proxy type."""
    mock_check_proxy.return_value = True
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok_static"}))

    proxy = "http://user:pass@staticproxy.com:8080"
    manager = ConnectionManager(proxy_type=ProxyTypes.STATIC, proxy_pool=proxy)
    url = "http://test.com/post_static"
    data = {"key_static": "value_static"}

    response = await manager.post(url, data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok_static"}
    expected_proxies = {"http://": proxy, "https://": proxy}

    mock_async_client_cls.assert_called_once_with(proxies=expected_proxies)

    mock_async_client.post.assert_called_once_with(
        url=url,
        headers=manager._get_headers(),
        timeout=manager.timeout,
        json=data
    )

    mock_check_proxy.assert_called_once_with(proxy)


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_static_failure(mock_async_client_cls, mock_check_proxy, mock_response, mock_async_client):
    """Test failed POST request (non-200) with STATIC proxy type."""
    mock_check_proxy.return_value = True
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(
        return_value=mock_response(status_code=500))

    proxy = "http://staticproxy.com:8080"
    manager = ConnectionManager(proxy_type=ProxyTypes.STATIC, proxy_pool=proxy)
    url = "http://test.com/servererror"
    data = {"key": "value"}

    with pytest.raises(BridgeException) as excinfo:
        await manager.post(url, data)
    assert "Static/Rotating connection failed with status code: 500" in str(
        excinfo.value)
    mock_check_proxy.assert_called_once_with(proxy)


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_rotating_success(mock_async_client_cls, mock_check_proxy, mock_response, mock_async_client):
    """Test successful POST request with ROTATING proxy type."""
    mock_check_proxy.return_value = True
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"status": "ok_rotating"}))

    proxies = ["http://proxy1.com:8080", "http://proxy2.com:8080"]
    manager = ConnectionManager(
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies, rotate_after=1)
    url = "http://test.com/post_rotating"
    data = {"key_rotating": "value_rotating"}

    response = await manager.post(url, data)

    assert response.status_code == 200
    assert response.json() == {"status": "ok_rotating"}

    mock_check_proxy.assert_called_once_with(proxies[0])

    expected_proxies = {"http://": proxies[0], "https://": proxies[0]}
    mock_async_client_cls.assert_called_once_with(proxies=expected_proxies)

    mock_async_client.post.assert_called_once_with(
        url=url,
        headers=manager._get_headers(),
        timeout=manager.timeout,
        json=data
    )
    assert manager.proxy_idx == 1


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_rotating_skips_bad_proxy(mock_async_client_cls, mock_check_proxy, mock_response, mock_async_client):
    """Test ROTATING proxy skips a bad proxy and uses the next one."""
    mock_check_proxy.side_effect = [False, True]
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(
        return_value=mock_response(status_code=200))

    proxies = ["http://badproxy.com:8080", "http://goodproxy.com:8080"]
    manager = ConnectionManager(
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies, rotate_after=1)
    url = "http://test.com/post_rotating_skip"
    data = {"key": "value"}

    await manager.post(url, data)

    assert mock_check_proxy.call_count == 2
    mock_check_proxy.assert_has_calls([call(proxies[0]), call(proxies[1])])

    expected_proxies = {"http://": proxies[1], "https://": proxies[1]}
    mock_async_client_cls.assert_called_once_with(proxies=expected_proxies)

    mock_async_client.post.assert_called_once_with(
        url=url,
        headers=manager._get_headers(),
        timeout=manager.timeout,
        json=data
    )
    assert manager.proxy_idx == 0


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
async def test_post_rotating_no_working_proxies(mock_check_proxy):
    """Test ROTATING proxy raises ProxyException when no proxies work."""
    mock_check_proxy.return_value = False

    proxies = ["http://badproxy1.com:8080", "http://badproxy2.com:8080"]
    manager = ConnectionManager(
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies, rotate_after=1)
    url = "http://test.com/post_rotating_fail"
    data = {"key": "value"}

    with pytest.raises(ProxyException) as excinfo:
        await manager.post(url, data)
    assert "No working proxies available" in str(excinfo.value)

    assert mock_check_proxy.call_count == 2
    mock_check_proxy.assert_has_calls([call(proxies[0]), call(proxies[1])])


@pytest.mark.asyncio
async def test_post_bridge_success(live_bridge_server):
    """Test successful POST request with BRIDGE proxy type."""
    target_url_to_proxy = "http://example.com/some/path"
    payload_for_target_url = {"key": "value", "action": "submit"}

    manager = ConnectionManager(
        proxy_type=ProxyTypes.BRIDGE,
        proxy_pool=live_bridge_server + "/bridge"
    )

    response = await manager.post(target_url_to_proxy, payload_for_target_url)

    assert response is not None, "Response object should not be None"
    assert response.status_code == 200, \
        f"Bridge post request failed. Status: {response.status_code}. Response text: {await response.text()}"

    try:
        response_data = response.json()
    except Exception as e:
        pytest.fail(f"Failed to parse response JSON: {e}. Response text: {await response.text()}")

    assert response_data.get(
        "status") == "success", "Bridge operation status was not 'success'"
    assert response_data.get(
        "requested_url") == target_url_to_proxy, "Proxied URL mismatch in response"
    assert response_data.get(
        "payload") == payload_for_target_url, "Proxied payload mismatch in response"
    assert response_data.get(
        "relayed_data") == "Mocked data from live bridge", "Relayed data content mismatch"


@pytest.mark.asyncio
async def test_post_bridge_failure(live_bridge_server):
    """Test failed POST request (non-200) with BRIDGE proxy type."""
    target_url = "http://example.com/some/path"
    payload = {"key": "value", "action": "submit"}

    manager = ConnectionManager(
        proxy_type=ProxyTypes.BRIDGE,
        proxy_pool=live_bridge_server + "/invalid_bridge"
    )

    with pytest.raises(BridgeException) as excinfo:
        await manager.post(target_url, payload)
    assert "Bridge connection failed with status code: 404" in str(
        excinfo.value)
