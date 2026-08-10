"""Tests for the shared HTTP client's lifecycle and result type — no network."""
import pytest

from app.services.fetcher.http_client import (
    FetchResult,
    HTTPClient,
    close_http_client,
    get_http_client,
)


@pytest.fixture(autouse=True)
async def _reset_singleton():
    yield
    await close_http_client()


class TestFetchResult:
    def test_ok_requires_200_and_a_body(self):
        assert FetchResult(b"data", 200).ok is True
        assert FetchResult(None, 200).ok is False
        assert FetchResult(b"data", 500).ok is False

    def test_not_modified_detects_304(self):
        assert FetchResult(None, 304).not_modified is True
        assert FetchResult(b"x", 200).not_modified is False

    def test_is_immutable(self):
        with pytest.raises(Exception):
            FetchResult(b"x", 200).status = 500


class TestSingleton:
    async def test_get_instance_is_shared(self):
        assert await get_http_client() is await get_http_client()

    async def test_close_http_client_clears_the_instance(self):
        await get_http_client()
        await close_http_client()
        assert HTTPClient._instance is None


class TestSessionLifecycle:
    async def test_close_resets_session_so_it_can_be_rebuilt(self):
        # Regression: close() left a closed client in place, so every later
        # fetch raised "Cannot send a request, as the client has been closed".
        client = HTTPClient()
        client._init_session()
        assert client._session is not None

        await client.close()
        assert client._session is None

        client._init_session()
        assert client._session is not None and not client._session.is_closed
        await client.close()

    async def test_close_on_a_never_opened_client_is_safe(self):
        await HTTPClient().close()


class TestDomainSemaphores:
    def test_same_domain_reuses_one_semaphore(self):
        client = HTTPClient()
        assert client._get_domain_semaphore("a.com") is client._get_domain_semaphore("a.com")

    def test_different_domains_get_different_semaphores(self):
        client = HTTPClient()
        assert client._get_domain_semaphore("a.com") is not client._get_domain_semaphore("b.com")
