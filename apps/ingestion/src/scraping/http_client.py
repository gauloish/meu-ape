"""HTTP client abstraction for the Zap Imóveis scraping pipeline.

Provides synchronous and asynchronous HTTP clients with standard headers,
rate-limiting backoff mechanisms, and diagnostic tracking of HTTP 403/429
access blocks without anti-bot or TLS fingerprint evasion.
"""

import asyncio
import logging
import random
import time
from typing import Self

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
    """Thread-safe synchronous HTTP client with retry and block diagnostics.

    Handles exponential backoff for HTTP 429 status codes and records
    transport-layer HTTP 403/429 blocks.
    """

    MAX_RETRIES = 3

    def __init__(self) -> None:
        """Initialize the synchronous HTTP client session."""
        self.last_status_code: int | None = None
        self.blocked_count: int = 0
        self.rate_limited_count: int = 0
        self._session = self._build_session()

    @property
    def is_blocked(self) -> bool:
        """Return True if the last HTTP response was blocked (403 or 429)."""
        return self.last_status_code in (403, 429)

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

                self.last_status_code = resp.status_code

                if resp.status_code == 200:
                    return resp.text
                if resp.status_code in (404, 410):
                    return ""
                if resp.status_code == 429:
                    self.rate_limited_count += 1
                    wait = min(
                        45.0, 8.0 * (1.5 ** (attempt - 1)) + random.uniform(1.0, 3.0)
                    )
                    logger.warning(
                        "[HTTP Transport Block] HTTP 429 Rate Limit for %s - waiting %.1fs (attempt %d/%d).",
                        url,
                        wait,
                        attempt,
                        self.MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue

                if resp.status_code == 403:
                    self.blocked_count += 1
                    logger.warning(
                        "[HTTP Transport Block] HTTP 403 Forbidden (WAF/Edge) for %s (attempt %d/%d).",
                        url,
                        attempt,
                        self.MAX_RETRIES,
                    )
                    time.sleep(random.uniform(2.0, 4.0))
                    continue

                logger.warning(
                    "HTTP status %d for %s (attempt %d/%d).",
                    resp.status_code,
                    url,
                    attempt,
                    self.MAX_RETRIES,
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(2.0)
                else:
                    return ""

            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Connection error for %s (attempt %d/%d): %s",
                    url,
                    attempt,
                    self.MAX_RETRIES,
                    exc,
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(2.0)
                else:
                    return ""

        return ""

    def _build_session(self):
        """Construct a standard HTTP session without fingerprint spoofing."""
        if HAS_CURL_CFFI:
            return cffi_requests.Session(headers=DEFAULT_HEADERS)
        session = stdlib_requests.Session()
        session.headers.update(DEFAULT_HEADERS)
        return session


class AsyncHttpClient:
    """Asynchronous HTTP client supporting concurrency control via Semaphore.

    Uses standard HTTP sessions without anti-bot or TLS fingerprint spoofing
    and tracks transport-layer HTTP 403/429 responses.
    """

    MAX_RETRIES = 3

    def __init__(self, semaphore: asyncio.Semaphore) -> None:
        """Initialize the asynchronous HTTP client.

        Args:
            semaphore: Concurrency limiter to cap simultaneous HTTP connections.
        """
        self.semaphore = semaphore
        self._session: AsyncSession | None = None
        self._lock = asyncio.Lock()
        self._warmed = False
        self.last_status_code: int | None = None
        self.blocked_count: int = 0
        self.rate_limited_count: int = 0

    @property
    def is_blocked(self) -> bool:
        """Return True if the last HTTP response was blocked (403 or 429)."""
        return self.last_status_code in (403, 429)

    async def __aenter__(self) -> Self:
        """Enter the async context manager and instantiate AsyncSession."""
        self._session = AsyncSession(headers=DEFAULT_HEADERS)
        await self._warmup_session()
        return self

    async def __aexit__(self, *_) -> None:
        """Exit the async context manager and close active AsyncSession."""
        if self._session:
            try:
                await self._session.close()
            except Exception:  # noqa: BLE001, S110
                pass

    async def _warmup_session(self) -> None:
        """Perform an initial connectivity check against BASE_URL."""
        if not self._session:
            return
        try:
            resp = await self._session.get(
                BASE_URL, headers=DEFAULT_HEADERS, timeout=15
            )
            self.last_status_code = resp.status_code
            if resp.status_code == 200:
                self._warmed = True
                logger.debug(
                    "Session connectivity verified with %d cookies.",
                    len(self._session.cookies),
                )
            elif resp.status_code in (403, 429):
                self.blocked_count += int(resp.status_code == 403)
                self.rate_limited_count += int(resp.status_code == 429)
                logger.warning(
                    "[HTTP Transport Block] Initial request to %s blocked with HTTP %d.",
                    BASE_URL,
                    resp.status_code,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Session connectivity check failed: %s", exc)

    async def _reset_session(self) -> None:
        """Close existing session and recreate a fresh AsyncSession."""
        async with self._lock:
            if self._session:
                try:
                    await self._session.close()
                except Exception:  # noqa: BLE001, S110
                    pass
            self._session = AsyncSession(headers=DEFAULT_HEADERS)
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
                try:
                    assert self._session is not None, (
                        "AsyncHttpClient must be used as async context manager"
                    )
                    resp = await self._session.get(
                        url, headers=DEFAULT_HEADERS, timeout=15
                    )
                    self.last_status_code = resp.status_code

                    if resp.status_code == 200:
                        return resp.text
                    if resp.status_code in (404, 410):
                        return ""
                    if resp.status_code == 429:
                        self.rate_limited_count += 1
                        wait = min(
                            30.0,
                            5.0 * (1.5 ** (attempt - 1)) + random.uniform(1.0, 2.0),
                        )
                        logger.warning(
                            "[%s] [HTTP Transport Block] HTTP 429 Rate Limit (attempt #%d/%d). Waiting %.1fs.",
                            label,
                            attempt,
                            self.MAX_RETRIES,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        continue
                    if resp.status_code == 403:
                        self.blocked_count += 1
                        logger.warning(
                            "[%s] [HTTP Transport Block] HTTP 403 Forbidden (attempt #%d/%d). Resetting session.",
                            label,
                            attempt,
                            self.MAX_RETRIES,
                        )
                        await self._reset_session()
                        await asyncio.sleep(random.uniform(2.5, 4.0))
                        continue

                    logger.warning(
                        "[%s] HTTP status %d for %s (attempt #%d/%d).",
                        label,
                        resp.status_code,
                        url,
                        attempt,
                        self.MAX_RETRIES,
                    )
                    if attempt < self.MAX_RETRIES:
                        await asyncio.sleep(1.5)
                    else:
                        return ""

                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "[%s] Connection error (attempt #%d/%d): %s",
                        label,
                        attempt,
                        self.MAX_RETRIES,
                        str(exc)[:60],
                    )
                    if attempt < self.MAX_RETRIES:
                        await self._reset_session()
                        await asyncio.sleep(1.5)
                    else:
                        return ""

            return ""
