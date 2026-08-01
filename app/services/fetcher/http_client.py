import asyncio
import logging
import random

from dataclasses import dataclass
from urllib.parse import urlparse
from typing import Optional, Dict

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    """Outcome of a single HTTP fetch."""

    content: Optional[bytes]
    status: int
    error: Optional[str] = None
    etag: Optional[str] = None
    last_modified: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.status == 200 and self.content is not None

    @property
    def not_modified(self) -> bool:
        return self.status == 304


class HTTPClient:
    _instance: Optional['HTTPClient'] = None
    _lock = asyncio.Lock()

    def __init__(self, verify_ssl: bool = False):
        self._session: Optional[httpx.AsyncClient] = None
        self._domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._verify_ssl = verify_ssl

        self.max_connections = 100
        self.max_connections_per_domain = 10
        self.timeout = httpx.Timeout(
            60.0,  # default timeout
            connect=10.0,
            read=30.0
        )
        self.max_retries = 3
        self.base_backoff = 1.0

        self.default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'application/rss+xml, application/xml, text/xml, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }

    @classmethod
    async def get_instance(cls) -> 'HTTPClient':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    instance = cls()
                    instance._init_session()
                    cls._instance = instance
        return cls._instance

    def _init_session(self) -> None:
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_connections_per_domain,
        )

        self._session = httpx.AsyncClient(
            limits=limits,
            timeout=self.timeout,
            headers=self.default_headers,
            follow_redirects=True,
            verify=self._verify_ssl,
        )
        logger.info(
            "HTTP client initialized",
            extra={
                "max_connections": self.max_connections,
                "verify_ssl": self._verify_ssl,
            }
        )

    async def close(self) -> None:
        if self._session and not self._session.is_closed:
            await self._session.aclose()
            logger.info("HTTP client closed")

    def _get_domain_semaphore(self, domain: str) -> asyncio.Semaphore:
        if domain not in self._domain_semaphores:
            self._domain_semaphores[domain] = asyncio.Semaphore(
                self.max_connections_per_domain
            )
        return self._domain_semaphores[domain]

    async def fetch(
        self,
        url: str,
        etag: Optional[str] = None,
        last_modified: Optional[str] = None,
    ) -> FetchResult:
        """Fetch a URL, optionally as a conditional request.

        Args:
            url: Target URL
            etag: Previously seen ``ETag``, sent as ``If-None-Match``
            last_modified: Previously seen ``Last-Modified``, sent as ``If-Modified-Since``

        Returns:
            A :class:`FetchResult`; ``status == 304`` means the content is unchanged.
        """
        if self._session is None:
            self._init_session()

        domain = urlparse(url).netloc
        semaphore = self._get_domain_semaphore(domain)

        headers = {}
        if etag:
            headers['If-None-Match'] = etag
        if last_modified:
            headers['If-Modified-Since'] = last_modified

        for attempt in range(self.max_retries):
            try:
                async with semaphore:
                    response = await self._session.get(url, headers=headers)
                    status = response.status_code

                    if status == 304:
                        logger.debug(
                            f"Feed not modified (304): {url}",
                            extra={"url": url, "status": 304}
                        )
                        return FetchResult(None, 304)

                    if status == 403:
                        logger.warning(
                            f"Access forbidden (403): {url}",
                            extra={"url": url, "status": 403}
                        )
                        return FetchResult(None, 403, "Site blocks automated requests")

                    if status != 200:
                        logger.warning(
                            f"HTTP error {status}: {url}",
                            extra={"url": url, "status": status}
                        )
                        return FetchResult(None, status, f"HTTP {status}")

                    content = response.content

                    logger.info(
                        f"Fetched successfully: {url}",
                        extra={
                            "url": url,
                            "status": status,
                            "size_bytes": len(content),
                            "attempt": attempt + 1,
                        }
                    )

                    return FetchResult(
                        content=content,
                        status=200,
                        etag=response.headers.get('ETag'),
                        last_modified=response.headers.get('Last-Modified'),
                    )

            except (httpx.HTTPError, httpx.TimeoutException, asyncio.TimeoutError) as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Client error after {self.max_retries} attempts: {url}",
                        extra={"url": url, "error": str(e)},
                        exc_info=True
                    )
                    return FetchResult(None, 0, f"Client error: {e}")

                backoff = self.base_backoff * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Client error on attempt {attempt + 1}/{self.max_retries}, retrying in {backoff:.2f}s: {url}",
                    extra={"url": url, "attempt": attempt + 1, "backoff": backoff, "error": str(e)}
                )
                await asyncio.sleep(backoff)

            except Exception as e:
                logger.error(
                    f"Unexpected error fetching {url}: {e}",
                    extra={"url": url, "error": str(e)},
                    exc_info=True
                )
                return FetchResult(None, 0, f"Unexpected error: {e}")

        return FetchResult(None, 0, f"Failed after {self.max_retries} attempts")


async def get_http_client() -> HTTPClient:
    """Return the shared HTTP client, creating it on first use."""
    return await HTTPClient.get_instance()


async def close_http_client() -> None:
    if HTTPClient._instance:
        await HTTPClient._instance.close()
        HTTPClient._instance = None
