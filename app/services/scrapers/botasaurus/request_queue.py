"""
FIFO request queue for rate-limited web scraping.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_DELAY: float = 2.0


@dataclass(slots=True)
class QueuedRequest:
    """A request waiting in the queue."""
    
    url: str
    future: asyncio.Future[Any]
    added_at: float = field(default_factory=time.time)


class RequestQueue:
    """
    FIFO queue for rate-limited request processing.
    
    Thread-safe singleton that processes requests sequentially with
    configurable delays between them.
    """
    
    __slots__ = (
        "_delay_seconds",
        "_queue",
        "_last_request_time",
        "_worker_task",
        "_fetch_func",
        "_running",
        "_pending_count",
    )
    
    _instance: RequestQueue | None = None
    _lock: asyncio.Lock = asyncio.Lock()
    
    def __init__(self, delay_seconds: float = DEFAULT_REQUEST_DELAY) -> None:
        self._delay_seconds = delay_seconds
        self._queue: asyncio.Queue[QueuedRequest] = asyncio.Queue()
        self._last_request_time: float = 0.0
        self._worker_task: asyncio.Task[None] | None = None
        self._fetch_func: Callable[[str], Any] | None = None
        self._running = False
        self._pending_count = 0
    
    @classmethod
    async def get_instance(
        cls,
        delay_seconds: float = DEFAULT_REQUEST_DELAY,
    ) -> RequestQueue:
        """Get or create singleton instance."""
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(delay_seconds)
            return cls._instance
    
    @classmethod
    async def reset_instance(cls) -> None:
        """Reset singleton instance (useful for testing)."""
        async with cls._lock:
            if cls._instance is not None:
                await cls._instance.stop()
                cls._instance = None
    
    @property
    def fetch_func(self) -> Callable[[str], Any] | None:
        """Current fetch function."""
        return self._fetch_func
    
    @fetch_func.setter
    def fetch_func(self, func: Callable[[str], Any]) -> None:
        """Set the function used to fetch URLs."""
        self._fetch_func = func
    
    @property
    def delay_seconds(self) -> float:
        """Current delay between requests."""
        return self._delay_seconds
    
    @delay_seconds.setter
    def delay_seconds(self, value: float) -> None:
        """Update the delay between requests."""
        self._delay_seconds = max(0.0, value)
        logger.info("Request delay set to %.1fs", self._delay_seconds)
    
    @property
    def pending_count(self) -> int:
        """Number of requests waiting in queue."""
        return self._pending_count
    
    @property
    def is_running(self) -> bool:
        """Whether the queue worker is running."""
        return self._running
    
    async def start(self) -> None:
        """Start the queue worker if not already running."""
        if self._running:
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(
            self._worker(),
            name="request_queue_worker",
        )
        logger.info("Request queue worker started")
    
    async def stop(self) -> None:
        """Stop the queue worker gracefully."""
        if not self._running:
            return
            
        self._running = False
        
        if self._worker_task is not None:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None
        
        logger.info("Request queue worker stopped")
    
    async def enqueue(self, url: str) -> Any:
        """
        Add a URL to the queue and wait for the result.
        
        Raises:
            RuntimeError: If fetch function not set
        """
        if not self._running:
            await self.start()
        
        if self._fetch_func is None:
            raise RuntimeError("Fetch function not set")
        
        future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
        request = QueuedRequest(url=url, future=future)
        
        self._pending_count += 1
        await self._queue.put(request)
        
        logger.info("FIFO: Enqueued request #%d for %s", self._pending_count, url)
        
        try:
            return await future
        finally:
            self._pending_count -= 1
    
    async def _worker(self) -> None:
        """Process requests from the queue with rate limiting."""
        logger.debug("Queue worker loop started")
        
        while self._running:
            try:
                request = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0,
                )
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            
            await self._process_request(request)
        
        logger.debug("Queue worker loop ended")
    
    async def _process_request(self, request: QueuedRequest) -> None:
        """Process a single request with rate limiting."""
        try:
            await self._apply_rate_limit()
            
            wait_time = time.time() - request.added_at
            logger.info(
                "FIFO: Processing request for %s (waited %.2fs in queue)",
                request.url,
                wait_time,
            )
            
            self._last_request_time = time.time()
            
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                self._fetch_func,
                request.url,
            )
            
            request.future.set_result(result)
            
        except Exception as e:
            logger.error("Error processing request for %s: %s", request.url, e)
            if not request.future.done():
                request.future.set_exception(e)
        finally:
            self._queue.task_done()
    
    async def _apply_rate_limit(self) -> None:
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self._last_request_time
        delay_needed = self._delay_seconds - elapsed
        
        if delay_needed > 0:
            logger.debug("Rate limiting: waiting %.2fs", delay_needed)
            await asyncio.sleep(delay_needed)
