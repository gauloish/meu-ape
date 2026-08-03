"""HTTP client abstraction for the Zap Imóveis scraping pipeline.

Provides synchronous and asynchronous clients featuring browser impersonation (curl_cffi),
User-Agent rotation, and rate-limiting backoff mechanisms.
"""

import asyncio
import logging
import random
import time
from typing import Optional

try:
    from curl_cffi import requests as cffi_requests
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import requests as stdlib_requests

from src.scraping.config import DEFAULT_HEADERS, USER_AGENTS

logger = logging.getLogger(__name__)


class SyncHttpClient:
    """Thread-safe synchronous HTTP client with TLS fingerprint impersonation.

    Handles request header rotation and exponential backoff for HTTP 429 status codes.
    """

    MAX_RETRIES = 8

    def __init__(self) -> None:
        """Initialize the synchronous HTTP client session."""
        self._session = self._build_session()

    def get(self, url: str) -> str:
        """Fetch content from the target URL.

        Args:
            url: Target URL to retrieve.

        Returns:
            Raw response HTML content as string, or empty string on failure.
        """
        for attempt in range(self.MAX_RETRIES):
            if attempt > 0:
                self._session = self._build_session()

            headers = {**DEFAULT_HEADERS, "User-Agent": random.choice(USER_AGENTS)}

            try:
                use_cffi = HAS_CURL_CFFI and attempt < 3
                if use_cffi:
                    resp = self._session.get(url, headers=headers, timeout=12)
                else:
                    resp = stdlib_requests.get(url, headers=headers, timeout=12)

                if resp.status_code == 200:
                    return resp.text
                if resp.status_code == 404:
                    return ""
                if resp.status_code == 429:
                    wait = min(120.0, 15.0 * (1.5 ** attempt) + random.uniform(2.0, 5.0))
                    logger.warning("HTTP 429 for %s - waiting %.1fs (attempt %d).", url, wait, attempt + 1)
                    time.sleep(wait)
                    continue
                logger.warning("HTTP status %d for %s.", resp.status_code, url)
                return ""

            except Exception as exc:
                logger.warning("Connection error for %s (attempt %d): %s", url, attempt + 1, exc)
                time.sleep(3)

        return ""

    def _build_session(self):
        """Construct a curl_cffi session or fall back to standard requests."""
        if HAS_CURL_CFFI:
            return cffi_requests.Session(impersonate="chrome124")
        return stdlib_requests.Session()


class AsyncHttpClient:
    """Asynchronous HTTP client supporting concurrency control via Semaphore.

    Supports context manager usage to ensure session resource cleanup.
    """

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize the asynchronous HTTP client.

        Args:
            semaphore: Concurrency limiter to cap simultaneous HTTP connections.
        """
        self.semaphore = semaphore
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> "AsyncHttpClient":
        """Enter the async context manager and instantiate AsyncSession."""
        self._session = AsyncSession(impersonate="chrome124")
        return self

    async def __aexit__(self, *_) -> None:
        """Exit the async context manager and close active AsyncSession."""
        if self._session:
            await self._session.close()

    async def get(self, url: str, label: str = "") -> str:
        """Fetch content asynchronously from the target URL.

        Args:
            url: Target URL to retrieve.
            label: Contextual label used for logging partition status.

        Returns:
            Raw response HTML content as string, or empty string on failure.
        """
        attempt = 0

        async with self.semaphore:
            await asyncio.sleep(random.uniform(2.5, 4.5))

            while True:
                headers = {**DEFAULT_HEADERS, "User-Agent": random.choice(USER_AGENTS)}

                try:
                    assert self._session is not None, "AsyncHttpClient must be used as async context manager"
                    resp = await self._session.get(url, headers=headers, timeout=20)

                    if resp.status_code == 200:
                        return resp.text
                    if resp.status_code == 404:
                        return ""
                    if resp.status_code == 429:
                        attempt += 1
                        wait = min(120.0, 15.0 * (1.5 ** min(attempt - 1, 6)) + random.uniform(2.0, 5.0))
                        logger.warning("[%s] HTTP 429 (attempt #%d). Waiting %.1fs.", label, attempt, wait)
                        await asyncio.sleep(wait)
                        continue
                    await asyncio.sleep(2)

                except Exception as exc:
                    logger.warning("[%s] Connection error (%s). Retrying.", label, str(exc)[:50])
                    await asyncio.sleep(1.5)
