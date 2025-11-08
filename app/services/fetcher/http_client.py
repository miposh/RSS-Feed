import asyncio
import logging
import random

from urllib.parse import urlparse
from typing import Optional, Dict, Tuple
from contextlib import asynccontextmanager

import httpx

logger = logging.getLogger(__name__)


class HTTPClient:
    _instance: Optional['HTTPClient'] = None
    _lock = asyncio.Lock()
    
    def __init__(self):
        self._session: Optional[httpx.AsyncClient] = None
        self._domain_semaphores: Dict[str, asyncio.Semaphore] = {}
        self._etag_cache: Dict[str, str] = {}
        self._last_modified_cache: Dict[str, str] = {}
        
        self.max_connections = 100
        self.max_connections_per_domain = 10
        self.timeout = httpx.Timeout(
            timeout=30.0,
            connect=5.0,
            read=10.0
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
                    cls._instance = cls()
                    await cls._instance._init_session()
        return cls._instance
    
    async def _init_session(self) -> None:
        if self._session is None or self._session.is_closed:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_connections_per_domain,
            )
            
            self._session = httpx.AsyncClient(
                limits=limits,
                timeout=self.timeout,
                headers=self.default_headers,
                follow_redirects=True,
            )
            logger.info(
                "HTTP client initialized",
                extra={
                    "max_connections": self.max_connections,
                    "timeout_total": self.timeout.timeout,
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
    
    def _get_cached_headers(self, url: str) -> Dict[str, str]:
        headers = {}
        
        if url in self._etag_cache:
            headers['If-None-Match'] = self._etag_cache[url]
        
        if url in self._last_modified_cache:
            headers['If-Modified-Since'] = self._last_modified_cache[url]
        
        return headers
    
    def _update_cache(
        self,
        url: str,
        etag: Optional[str],
        last_modified: Optional[str]
    ) -> None:
        if etag:
            self._etag_cache[url] = etag
        
        if last_modified:
            self._last_modified_cache[url] = last_modified
    
    async def fetch(
        self,
        url: str,
        use_cache: bool = True,
        verify_ssl: bool = False,
    ) -> Tuple[Optional[bytes], int, Optional[str]]:
        if not self._session:
            await self._init_session()
        
        
        domain = urlparse(url).netloc
        semaphore = self._get_domain_semaphore(domain)
        
        headers = dict(self.default_headers)
        if use_cache:
            headers.update(self._get_cached_headers(url))
        
        for attempt in range(self.max_retries):
            try:
                async with semaphore:
                    response = await self._session.get(
                        url,
                        headers=headers,
                        verify=verify_ssl,
                    )
                    status = response.status_code
                    
                    if status == 304:
                        logger.debug(
                            f"Feed not modified (304): {url}",
                            extra={"url": url, "status": 304}
                        )
                        return None, 304, None
                    
                    if status == 403:
                        logger.warning(
                            f"Access forbidden (403): {url}",
                            extra={"url": url, "status": 403}
                        )
                        return None, 403, "Site blocks automated requests"
                    
                    if status != 200:
                        logger.warning(
                            f"HTTP error {status}: {url}",
                            extra={"url": url, "status": status}
                        )
                        return None, status, f"HTTP {status}"
                    
                    content = response.content
                    
                    if use_cache:
                        etag = response.headers.get('ETag')
                        last_modified = response.headers.get('Last-Modified')
                        self._update_cache(url, etag, last_modified)
                    
                    logger.info(
                        f"Fetched successfully: {url}",
                        extra={
                            "url": url,
                            "status": status,
                            "size_bytes": len(content),
                            "attempt": attempt + 1,
                        }
                    )
                    
                    return content, 200, None
            
            except asyncio.TimeoutError:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Timeout after {self.max_retries} attempts: {url}",
                        extra={"url": url, "attempts": self.max_retries}
                    )
                    return None, 0, f"Timeout after {self.max_retries} attempts"
                
                backoff = self.base_backoff * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(
                    f"Timeout on attempt {attempt + 1}/{self.max_retries}, retrying in {backoff:.2f}s: {url}",
                    extra={"url": url, "attempt": attempt + 1, "backoff": backoff}
                )
                await asyncio.sleep(backoff)
            
            except (httpx.HTTPError, httpx.TimeoutException) as e:
                if attempt == self.max_retries - 1:
                    logger.error(
                        f"Client error after {self.max_retries} attempts: {url}",
                        extra={"url": url, "error": str(e)},
                        exc_info=True
                    )
                    return None, 0, f"Client error: {e}"
                
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
                return None, 0, f"Unexpected error: {e}"
        
        return None, 0, f"Failed after {self.max_retries} attempts"


@asynccontextmanager
async def get_http_client():
    client = await HTTPClient.get_instance()
    try:
        yield client
    finally:
        pass


async def close_http_client() -> None:
    if HTTPClient._instance:
        await HTTPClient._instance.close()
        HTTPClient._instance = None
