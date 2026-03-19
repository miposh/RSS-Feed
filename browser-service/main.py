"""
Botasaurus Browser Service - HTTP API for centralized browser scraping.
"""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from botasaurus.browser import Driver, browser

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
MAX_CONCURRENT = int(os.getenv("MAX_CONCURRENT", "5"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "45"))


class FetchRequest(BaseModel):
    url: HttpUrl
    timeout: Optional[int] = REQUEST_TIMEOUT
    wait_for_selector: Optional[str] = None


class FetchResponse(BaseModel):
    success: bool
    html: Optional[str] = None
    error: Optional[str] = None
    url: str


# Semaphore for concurrency control
semaphore: asyncio.Semaphore


@browser(
    reuse_driver=True,
    cache=False,
    block_images=True,
    max_retry=2,
    close_on_crash=True,
    output=None,
    create_error_logs=False,
    headless=True,
    wait_for_complete_page_load=False,
    add_arguments=[
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-plugins",
        "--renderer-process-limit=2",
        "--memory-pressure-off",
    ],
)
def fetch_html_sync(driver: Driver, url: str, timeout: int = 45) -> str:
    """Fetch HTML using Botasaurus browser with anti-detection."""
    try:
        driver.google_get(url, timeout=timeout)
    except TimeoutError:
        logger.warning(f"Timeout loading {url}, returning partial content")
        html = driver.page_html
        if html and len(html) > 100:
            return html
        raise
    return driver.page_html


async def fetch_html_async(url: str, timeout: int = 45) -> str:
    """Async wrapper for the sync browser function."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch_html_sync, url, timeout)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    global semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    logger.info(f"Browser service started (max_concurrent={MAX_CONCURRENT})")
    yield
    logger.info("Browser service shutting down")


app = FastAPI(
    title="Botasaurus Browser Service",
    description="Centralized browser service with anti-detection",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/fetch", response_model=FetchResponse)
async def fetch_page(request: FetchRequest):
    """Fetch HTML content from URL using browser."""
    url = str(request.url)

    async with semaphore:
        try:
            logger.info(f"Fetching: {url}")
            html = await fetch_html_async(url, request.timeout)

            if not html:
                return FetchResponse(
                    success=False,
                    url=url,
                    error="Empty response"
                )

            logger.info(f"Fetched {len(html)} bytes from {url}")
            return FetchResponse(
                success=True,
                html=html,
                url=url
            )

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return FetchResponse(
                success=False,
                url=url,
                error=str(e)
            )


@app.get("/fetch")
async def fetch_page_get(
    url: HttpUrl = Query(..., description="URL to fetch"),
    timeout: int = Query(REQUEST_TIMEOUT, description="Timeout in seconds")
):
    """GET endpoint for simple fetching."""
    return await fetch_page(FetchRequest(url=url, timeout=timeout))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
