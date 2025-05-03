import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch, call
from nudlecrawler.connection import ConnectionManager, ProxyTypes, BridgeException, ProxyException
import os


os.environ.setdefault("TIMEOUT", "5")


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
        data=data
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
        data=data
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
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies)
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
        data=data
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
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies)
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
        data=data
    )
    assert manager.proxy_idx == 0


@pytest.mark.asyncio
@patch('nudlecrawler.connection.ConnectionManager._check_proxy', new_callable=AsyncMock)
async def test_post_rotating_no_working_proxies(mock_check_proxy):
    """Test ROTATING proxy raises ProxyException when no proxies work."""
    mock_check_proxy.return_value = False

    proxies = ["http://badproxy1.com:8080", "http://badproxy2.com:8080"]
    manager = ConnectionManager(
        proxy_type=ProxyTypes.ROTATING, proxy_pool=proxies)
    url = "http://test.com/post_rotating_fail"
    data = {"key": "value"}

    with pytest.raises(ProxyException) as excinfo:
        await manager.post(url, data)
    assert "No working proxies available" in str(excinfo.value)

    assert mock_check_proxy.call_count == 2
    mock_check_proxy.assert_has_calls([call(proxies[0]), call(proxies[1])])


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_bridge_success(mock_async_client_cls, mock_response, mock_async_client):
    """Test successful POST request with BRIDGE proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(return_value=mock_response(
        status_code=200, json_data={"bridge_status": "ok"}))

    bridge_url = "http://mybridge.com/fetch"
    manager = ConnectionManager(
        proxy_type=ProxyTypes.BRIDGE, proxy_pool=bridge_url)
    target_url = "http://target.com/data"
    data = {"target_key": "target_value"}

    response = await manager.post(target_url, data)

    assert response.status_code == 200
    assert response.json() == {"bridge_status": "ok"}

    mock_async_client.post.assert_called_once_with(
        url=bridge_url,
        headers=manager._get_headers(),
        timeout=manager.timeout,
        data={
            "url": target_url,
            "data": data
        }
    )


@pytest.mark.asyncio
@patch('nudlecrawler.connection.httpx.AsyncClient')
async def test_post_bridge_failure(mock_async_client_cls, mock_response, mock_async_client):
    """Test failed POST request (non-200) with BRIDGE proxy type."""
    mock_async_client_cls.return_value = mock_async_client
    mock_async_client.post = AsyncMock(
        return_value=mock_response(status_code=503))

    bridge_url = "http://mybridge.com/fetch"
    manager = ConnectionManager(
        proxy_type=ProxyTypes.BRIDGE, proxy_pool=bridge_url)
    target_url = "http://target.com/data"
    data = {"target_key": "target_value"}

    with pytest.raises(BridgeException) as excinfo:
        await manager.post(target_url, data)
    assert "Bridge connection failed with status code: 503" in str(
        excinfo.value)
