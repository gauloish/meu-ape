"""Incremental CSV persistence with checkpointing and deduplication by listing ID.

Tracks seen listing IDs and flushes in-memory buffers to disk incrementally
to support resilient resumption of interrupted scraping tasks.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Set

import pandas as pd

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_PATH = Path("data/raw/zap_dataset.csv")


class CheckpointStore:
    """Buffer and store for managing incremental CSV output with ID deduplication.

    Attributes:
        output_path: Target CSV file path.
        buffer_size: Number of buffered records required before triggering automatic flush.
        seen_ids: Set of listing IDs already processed or present in the output file.
    """

    def __init__(
        self,
        output_path: Path = DEFAULT_OUTPUT_PATH,
        buffer_size: int = 50,
    ) -> None:
        """Initialize the CheckpointStore and load previously stored listing IDs.

        Args:
            output_path: Destination path for CSV output.
            buffer_size: Minimum buffer length before flushing to disk.
        """
        self.output_path = output_path
        self.buffer_size = buffer_size
        self._buffer: List[Dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self.seen_ids: Set[str] = set()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_existing_ids()

    def is_new(self, listing_id: str) -> bool:
        """Check if a listing ID has not yet been processed.

        Args:
            listing_id: Listing unique identifier string.

        Returns:
            True if the ID is unseen, False otherwise.
        """
        return listing_id not in self.seen_ids

    def register(self, listing_id: str, record: Dict[str, Any]) -> None:
        """Mark a listing ID as seen and append its record to the buffer.

        Args:
            listing_id: Listing unique identifier string.
            record: Dictionary of parsed listing fields.
        """
        self.seen_ids.add(listing_id)
        self._buffer.append(record)

    def add_many(self, records: List[Dict[str, Any]]) -> int:
        """Filter out seen listings and append new records to the internal buffer.

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
            listing_id = str(record.get("id", ""))
            if listing_id and self.is_new(listing_id):
                self.register(listing_id, record)
                new_count += 1
        return new_count

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

    def flush_sync(self) -> None:
        """Synchronously write buffered records to disk."""
        self._write_to_disk()

    def _load_existing_ids(self) -> None:
        """Load unique listing IDs from existing CSV file if present."""
        if not self.output_path.exists():
            return
        try:
            df = pd.read_csv(self.output_path, low_memory=False, usecols=["id"])
            self.seen_ids = set(df["id"].dropna().astype(str).tolist())
            logger.info("Resuming extraction: loaded %d existing listing IDs.", len(self.seen_ids))
        except Exception as exc:
            logger.warning("Could not load existing checkpoint file: %s", exc)

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
