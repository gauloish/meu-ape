"""Incremental CSV persistence with checkpointing, execution resumption, and ID/URL deduplication.

Tracks seen listing IDs, canonical URLs, and per-partition pagination state to
support resilient resumption of interrupted scraping tasks.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from src.scraping.zap_parser import extract_id_from_url, normalize_url

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data/raw/zap_dataset.csv")


class CheckpointStore:
    """Buffer and store for managing incremental CSV output, ID/URL deduplication, and resumption.

    Attributes:
        output_path: Target CSV file path.
        state_path: JSON file path for persisting partition/page resumption state.
        buffer_size: Number of buffered records required before triggering automatic flush.
        seen_ids: Set of listing IDs already processed or present in the output file.
        seen_urls: Set of normalised listing URLs already processed or present in the output file.
    """

    def __init__(
        self,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        buffer_size: int = 50,
        state_path: Path | None = None,
    ) -> None:
        """Initialize the CheckpointStore and load previously stored IDs, URLs, and state.

        Args:
            output_path: Destination path for CSV output.
            buffer_size: Minimum buffer length before flushing to disk.
            state_path: Optional path for JSON partition state file.
        """
        self.output_path = Path(output_path)
        self.state_path = (
            Path(state_path)
            if state_path is not None
            else self.output_path.with_suffix(".state.json")
        )
        self.buffer_size = buffer_size
        self._buffer: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self.seen_ids: set[str] = set()
        self.seen_urls: set[str] = set()
        self._partition_state: dict[str, dict[str, Any]] = {}

        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_existing_ids()
        self._load_state()

    def is_new(self, listing_id: str, url: str | None = None) -> bool:
        """Check if a listing ID and optional URL have not yet been processed.

        Args:
            listing_id: Listing unique identifier string.
            url: Optional listing URL string.

        Returns:
            True if both the ID and normalised URL are unseen, False otherwise.
        """
        if listing_id and listing_id in self.seen_ids:
            return False
        norm_url = normalize_url(url)
        return not (norm_url and norm_url in self.seen_urls)

    def is_new_url(self, url: str | None) -> bool:
        """Check if a listing URL has not yet been processed.

        Args:
            url: Listing URL string.

        Returns:
            True if the normalised URL is unseen, False otherwise.
        """
        norm_url = normalize_url(url)
        if not norm_url:
            return False
        return norm_url not in self.seen_urls

    def register(self, listing_id: str, record: dict[str, Any]) -> None:
        """Mark a listing ID and URL as seen and append its record to the buffer.

        Args:
            listing_id: Listing unique identifier string.
            record: Dictionary of parsed listing fields.
        """
        if listing_id:
            self.seen_ids.add(listing_id)
        norm_url = normalize_url(record.get("url"))
        if norm_url:
            self.seen_urls.add(norm_url)
        self._buffer.append(record)

    def add_many(self, records: list[dict[str, Any]]) -> int:
        """Filter out seen listings (by ID or URL) and append new records to the buffer.

        Note:
            Callers in multi-threaded or async environments must acquire a lock
            prior to calling this method.

        Args:
            records: Collection of parsed listing records.

        Returns:
            Count of newly added records.
        """
        new_count = 0
        for record in records:
            raw_url = record.get("url")
            norm_url = normalize_url(raw_url)
            raw_id = (
                record.get("id")
                or record.get("listing_id")
                or extract_id_from_url(norm_url or raw_url)
            )
            listing_id = str(raw_id).strip() if raw_id is not None else ""

            if not listing_id and not norm_url:
                continue

            if self.is_new(listing_id, norm_url):
                if norm_url and record.get("url") != norm_url:
                    record = {**record, "url": norm_url}
                if listing_id and not record.get("id"):
                    record = {**record, "id": listing_id}
                self.register(listing_id, record)
                new_count += 1
        return new_count

    def get_resume_page(self, partition_key: str) -> int:
        """Return the page number from which a partition should resume.

        Args:
            partition_key: Unique identifier for the category/price partition.

        Returns:
            Next page integer (1 if not previously started).
        """
        entry = self._partition_state.get(partition_key)
        if not entry:
            return 1
        return int(entry.get("last_page", 0)) + 1

    def is_partition_completed(self, partition_key: str) -> bool:
        """Return True if the given partition has already completed pagination.

        Args:
            partition_key: Unique identifier for the category/price partition.

        Returns:
            True if marked completed, False otherwise.
        """
        entry = self._partition_state.get(partition_key)
        return bool(entry and entry.get("completed", False))

    def record_progress(
        self, partition_key: str, page: int, completed: bool = False
    ) -> None:
        """Record the last processed page and completion flag for a partition.

        Args:
            partition_key: Unique identifier for the category/price partition.
            page: Last processed page number.
            completed: Whether the partition reached its end condition.
        """
        self._partition_state[partition_key] = {
            "last_page": int(page),
            "completed": bool(completed),
        }

    def save_state(self) -> None:
        """Persist partition pagination state to the JSON state file."""
        if not self._partition_state:
            return
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps(self._partition_state, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not save checkpoint state file: %s", exc)

    @property
    def buffer_full(self) -> bool:
        """Return True if buffered record count meets or exceeds buffer_size."""
        return len(self._buffer) >= self.buffer_size

    @property
    def total_seen(self) -> int:
        """Return total count of unique listing IDs recorded."""
        return len(self.seen_ids)

    async def flush_async(self, force: bool = False) -> None:
        """Asynchronously write buffered records to disk.

        Args:
            force: If True, flushes buffer regardless of buffer_full status.
        """
        if not force and not self.buffer_full:
            return
        async with self._lock:
            self._write_to_disk()
            self.save_state()

    def flush_sync(self) -> None:
        """Synchronously write buffered records and state to disk."""
        self._write_to_disk()
        self.save_state()

    def _load_existing_ids(self) -> None:
        """Load unique listing IDs and normalised URLs from existing CSV file if present."""
        if not self.output_path.exists():
            return
        try:
            df = pd.read_csv(self.output_path, low_memory=False)
            if "id" in df.columns:
                self.seen_ids = set(df["id"].dropna().astype(str).tolist())
            if "url" in df.columns:
                urls = df["url"].dropna().astype(str).tolist()
                self.seen_urls = {
                    norm for u in urls if (norm := normalize_url(u)) is not None
                }
            logger.info(
                "Resuming extraction: loaded %d existing listing IDs and %d URLs.",
                len(self.seen_ids),
                len(self.seen_urls),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load existing checkpoint file: %s", exc)

    def _load_state(self) -> None:
        """Load partition progress state from JSON file if present."""
        if not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self._partition_state = data
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not load checkpoint state file: %s", exc)

    def _write_to_disk(self) -> None:
        """Append buffered records to the target CSV file and reset buffer."""
        if not self._buffer:
            return
        df_new = pd.DataFrame(self._buffer)
        file_exists = self.output_path.exists()
        df_new.to_csv(
            self.output_path,
            mode="a" if file_exists else "w",
            header=not file_exists,
            index=False,
            encoding="utf-8",
        )
        logger.info(
            "Checkpoint saved: +%d new listings (Total accumulated: %d).",
            len(self._buffer),
            self.total_seen,
        )
        self._buffer.clear()
