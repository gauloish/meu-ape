"""HTTP client abstraction for the Zap Imóveis scraping pipeline.

Provides synchronous and asynchronous clients featuring browser impersonation (curl_cffi),
initial session warming (cookie acquisition), and rate-limiting backoff mechanisms.
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

from src.scraping.config import BASE_URL, DEFAULT_HEADERS

logger = logging.getLogger(__name__)


class SyncHttpClient:
    """Thread-safe synchronous HTTP client with TLS fingerprint impersonation.

    Handles automatic exponential backoff for HTTP 429 status codes.
    """

    MAX_RETRIES = 3

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
        for attempt in range(1, self.MAX_RETRIES + 1):
            if attempt > 1:
                self._session = self._build_session()

            try:
                if HAS_CURL_CFFI:
                    resp = self._session.get(url, timeout=12)
                else:
                    resp = stdlib_requests.get(url, headers=DEFAULT_HEADERS, timeout=12)

                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in (404, 410):
                    return ""
                if resp.status_code == 429:
                    wait = min(45.0, 8.0 * (1.5 ** (attempt - 1)) + random.uniform(1.0, 3.0))
                    logger.warning("HTTP 429 for %s - waiting %.1fs (attempt %d/%d).", url, wait, attempt, self.MAX_RETRIES)
                    time.sleep(wait)
                    continue

                if resp.status_code == 403:
                    logger.warning("HTTP 403 Forbidden for %s (attempt %d/%d) - resetting session.", url, attempt, self.MAX_RETRIES)
                    time.sleep(random.uniform(2.0, 4.0))
                    continue

                logger.warning("HTTP status %d for %s (attempt %d/%d).", resp.status_code, url, attempt, self.MAX_RETRIES)
                if attempt < self.MAX_RETRIES:
                    time.sleep(2.0)
                else:
                    return ""

            except Exception as exc:
                logger.warning("Connection error for %s (attempt %d/%d): %s", url, attempt, self.MAX_RETRIES, exc)
                if attempt < self.MAX_RETRIES:
                    time.sleep(2.0)
                else:
                    return ""

        return ""

    def _build_session(self):
        """Construct a curl_cffi session or fall back to standard requests."""
        if HAS_CURL_CFFI:
            return cffi_requests.Session(impersonate="chrome124")
        return stdlib_requests.Session()


class AsyncHttpClient:
    """Asynchronous HTTP client supporting concurrency control via Semaphore.

    Uses native Chrome 124 browser impersonation via curl_cffi with session warming
    (obtaining valid Cloudflare/navigation cookies on homepage first).
    """

    MAX_RETRIES = 3

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize the asynchronous HTTP client.

        Args:
            semaphore: Concurrency limiter to cap simultaneous HTTP connections.
        """
        self.semaphore = semaphore
        self._session: Optional[AsyncSession] = None
        self._lock = asyncio.Lock()
        self._warmed = False

    async def __aenter__(self) -> "AsyncHttpClient":
        """Enter the async context manager, instantiate AsyncSession and warm cookies."""
        self._session = AsyncSession(impersonate="chrome124")
        await self._warmup_session()
        return self

    async def __aexit__(self, *_) -> None:
        """Exit the async context manager and close active AsyncSession."""
        if self._session:
            try:
                await self._session.close()
            except Exception:
                pass

    async def _warmup_session(self) -> None:
        """Visit homepage to acquire initial navigation cookies and pass Cloudflare checks."""
        if not self._session:
            return
        try:
            headers = {"Referer": "https://www.google.com/"}
            resp = await self._session.get(BASE_URL, headers=headers, timeout=15)
            if resp.status_code == 200:
                self._warmed = True
                logger.debug("Session warmed up successfully with %d cookies.", len(self._session.cookies))
        except Exception as exc:
            logger.warning("Session warmup failed: %s", exc)

    async def _reset_session(self) -> None:
        """Close existing session and recreate a fresh warmed AsyncSession."""
        async with self._lock:
            if self._session:
                try:
                    await self._session.close()
                except Exception:
                    pass
            self._session = AsyncSession(impersonate="chrome124")
            await self._warmup_session()

    async def get(self, url: str, label: str = "") -> str:
        """Fetch content asynchronously from the target URL.

        Args:
            url: Target URL to retrieve.
            label: Contextual label used for logging partition status.

        Returns:
            Raw response HTML content as string, or empty string on failure.
        """
        async with self.semaphore:
            await asyncio.sleep(random.uniform(1.2, 2.8))

            for attempt in range(1, self.MAX_RETRIES + 1):
                headers = {"Referer": f"{BASE_URL}/"}

                try:
                    assert self._session is not None, "AsyncHttpClient must be used as async context manager"
                    resp = await self._session.get(url, headers=headers, timeout=15)

                    if resp.status_code == 200:
                        return resp.text
                    if resp.status_code in (404, 410):
                        return ""
                    if resp.status_code == 429:
                        wait = min(30.0, 5.0 * (1.5 ** (attempt - 1)) + random.uniform(1.0, 2.0))
                        logger.warning("[%s] HTTP 429 Rate Limit (attempt #%d/%d). Waiting %.1fs.", label, attempt, self.MAX_RETRIES, wait)
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code == 403:
                        logger.warning("[%s] HTTP 403 Forbidden (attempt #%d/%d). Resetting session with warmup.", label, attempt, self.MAX_RETRIES)
                        await self._reset_session()
                        await asyncio.sleep(random.uniform(2.5, 4.0))
                        continue

                    logger.warning("[%s] HTTP status %d for %s (attempt #%d/%d).", label, resp.status_code, url, attempt, self.MAX_RETRIES)
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(1.5)
                    else:
                        return ""

                except Exception as exc:
                    logger.warning("[%s] Connection error (attempt #%d/%d): %s", label, attempt, self.MAX_RETRIES, str(exc)[:60])
                    if attempt < self.MAX_RETRIES:
                        await self._reset_session()
                        await asyncio.sleep(1.5)
                    else:
                        return ""

            return ""
