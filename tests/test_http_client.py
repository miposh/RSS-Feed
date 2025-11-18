"""
Tests for HTTP client functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from app.services.fetcher.http_client import HTTPClient


@pytest.fixture
async def http_client():
    """Create HTTP client instance for testing."""
    client = HTTPClient()
    await client._init_session(verify_ssl=False)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_http_client_initialization():
    """Test HTTP client initialization."""
    client = HTTPClient()
    await client._init_session(verify_ssl=False)
    
    assert client._session is not None
    assert not client._session.is_closed
    assert client._current_verify_ssl is False
    
    await client.close()


@pytest.mark.asyncio
async def test_http_client_verify_ssl_change():
    """Test that client recreates session when verify_ssl changes."""
    client = HTTPClient()
    
    # Initialize with verify_ssl=False
    await client._init_session(verify_ssl=False)
    assert client._current_verify_ssl is False
    session1 = client._session
    
    # Change to verify_ssl=True
    await client._init_session(verify_ssl=True)
    assert client._current_verify_ssl is True
    session2 = client._session
    
    # Should be different session objects
    assert session1 is not session2
    assert session1.is_closed
    
    await client.close()


@pytest.mark.asyncio
async def test_http_client_singleton():
    """Test that HTTPClient uses singleton pattern."""
    client1 = await HTTPClient.get_instance()
    client2 = await HTTPClient.get_instance()
    
    assert client1 is client2
    
    await client1.close()
    HTTPClient._instance = None


@pytest.mark.asyncio
async def test_cache_headers():
    """Test cache header generation."""
    client = HTTPClient()
    
    # Set cache values
    test_url = "https://example.com/feed.xml"
    client._etag_cache[test_url] = "test-etag"
    client._last_modified_cache[test_url] = "Mon, 11 Nov 2024 12:00:00 GMT"
    
    headers = client._get_cached_headers(test_url)
    
    assert headers['If-None-Match'] == "test-etag"
    assert headers['If-Modified-Since'] == "Mon, 11 Nov 2024 12:00:00 GMT"


@pytest.mark.asyncio
async def test_update_cache():
    """Test cache update."""
    client = HTTPClient()
    test_url = "https://example.com/feed.xml"
    
    client._update_cache(
        test_url,
        etag="new-etag",
        last_modified="Tue, 12 Nov 2024 12:00:00 GMT"
    )
    
    assert client._etag_cache[test_url] == "new-etag"
    assert client._last_modified_cache[test_url] == "Tue, 12 Nov 2024 12:00:00 GMT"


@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_fetch_success(mock_get):
    """Test successful fetch."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"Test RSS content"
    mock_response.headers = {
        'ETag': 'test-etag',
        'Last-Modified': 'Mon, 11 Nov 2024 12:00:00 GMT'
    }
    mock_get.return_value = mock_response
    
    client = HTTPClient()
    await client._init_session(verify_ssl=False)
    
    content, status, error = await client.fetch(
        "https://example.com/feed.xml",
        use_cache=True
    )
    
    assert status == 200
    assert content == b"Test RSS content"
    assert error is None
    
    await client.close()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_fetch_not_modified(mock_get):
    """Test 304 Not Modified response."""
    mock_response = MagicMock()
    mock_response.status_code = 304
    mock_get.return_value = mock_response
    
    client = HTTPClient()
    await client._init_session(verify_ssl=False)
    
    content, status, error = await client.fetch(
        "https://example.com/feed.xml",
        use_cache=True
    )
    
    assert status == 304
    assert content is None
    assert error is None
    
    await client.close()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_fetch_forbidden(mock_get):
    """Test 403 Forbidden response."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_get.return_value = mock_response
    
    client = HTTPClient()
    await client._init_session(verify_ssl=False)
    
    content, status, error = await client.fetch(
        "https://example.com/feed.xml"
    )
    
    assert status == 403
    assert content is None
    assert "blocks automated requests" in error
    
    await client.close()


@pytest.mark.asyncio
@patch('httpx.AsyncClient.get')
async def test_fetch_timeout_retry(mock_get):
    """Test timeout with retry logic."""
    # First two attempts timeout, third succeeds
    mock_get.side_effect = [
        httpx.TimeoutException("Timeout"),
        httpx.TimeoutException("Timeout"),
        MagicMock(status_code=200, content=b"Success")
    ]
    
    client = HTTPClient()
    client.base_backoff = 0.01  # Speed up test
    await client._init_session(verify_ssl=False)
    
    content, status, error = await client.fetch(
        "https://example.com/feed.xml"
    )
    
    assert status == 200
    assert content == b"Success"
    assert error is None
    assert mock_get.call_count == 3
    
    await client.close()


@pytest.mark.asyncio
async def test_domain_semaphore():
    """Test domain-based rate limiting."""
    client = HTTPClient()
    
    semaphore1 = client._get_domain_semaphore("example.com")
    semaphore2 = client._get_domain_semaphore("example.com")
    semaphore3 = client._get_domain_semaphore("other.com")
    
    # Same domain should return same semaphore
    assert semaphore1 is semaphore2
    
    # Different domain should return different semaphore
    assert semaphore1 is not semaphore3
