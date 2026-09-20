"""Tests for the shared HTTP client's lifecycle and result type — no network."""
import logging

import httpx
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


def _failing_client(exc: Exception):
    """A client whose every request raises `exc`, counting the attempts."""
    client = HTTPClient()
    client._init_session()
    client.base_backoff = 0  # no real sleeping between retries
    attempts = []

    async def get(url, headers=None):
        attempts.append(url)
        raise exc

    client._session.get = get
    return client, attempts


class TestUnreachableHost:
    """Regression: every fetch failure burned the full retry budget and then
    dumped a sixty-line httpx traceback at ERROR. A feed whose host is simply
    down (expired domain, dead server) is an expected outcome, and each extra
    attempt costs a full connect timeout while holding a worker feed slot."""

    @pytest.mark.parametrize(
        "exc", [httpx.ConnectTimeout(""), httpx.ConnectError("nodename nor servname provided")]
    )
    async def test_connect_failures_stop_early(self, exc):
        client, attempts = _failing_client(exc)
        result = await client.fetch("https://dead.example/feed/")

        assert len(attempts) == client.max_unreachable_retries == 2
        assert result.ok is False and result.status == 0
        await client.close()

    async def test_read_timeout_keeps_the_full_budget(self):
        # Mid-exchange failures do succeed on retry, so they are not shortened.
        client, attempts = _failing_client(httpx.ReadTimeout("slow"))
        await client.fetch("https://slow.example/feed/")

        assert len(attempts) == client.max_retries == 3
        await client.close()

    async def test_reason_names_the_exception(self):
        # httpx raises ConnectTimeout with an empty str(), which used to render
        # as a bare "Client error: " with the cause missing entirely.
        client, _ = _failing_client(httpx.ConnectTimeout(""))
        result = await client.fetch("https://dead.example/feed/")

        assert result.error == "ConnectTimeout"
        await client.close()

    async def test_gives_up_without_a_traceback_at_warning(self, caplog):
        client, _ = _failing_client(httpx.ConnectTimeout(""))
        with caplog.at_level(logging.DEBUG, logger="app.services.fetcher.http_client"):
            await client.fetch("https://dead.example/feed/")

        assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
        giving_up = [r for r in caplog.records if "Giving up" in r.getMessage()]
        assert len(giving_up) == 1
        assert giving_up[0].exc_info is None
        await client.close()

    async def test_a_transient_blip_still_recovers(self):
        client, attempts = _failing_client(httpx.ConnectError("blip"))
        client.base_backoff = 0

        async def get(url, headers=None):
            attempts.append(url)
            if len(attempts) == 1:
                raise httpx.ConnectError("blip")
            return httpx.Response(200, content=b"<rss/>", request=httpx.Request("GET", url))

        client._session.get = get
        result = await client.fetch("https://flaky.example/feed/")

        assert len(attempts) == 2
        assert result.ok is True and result.content == b"<rss/>"
        await client.close()
