"""Bulk CSV loader for populating PostgreSQL listings table efficiently."""

import argparse
import logging
from pathlib import Path
import time
import pandas as pd

from src.database import Base, Session, engine, ListingRepository

logger = logging.getLogger(__name__)


def load_csv_to_db(csv_file: Path, chunk_size: int = 2000) -> None:
    """Load records from CSV into database in chunks.

    Args:
        csv_file: Path to CSV dataset file.
        chunk_size: Number of records to process per batch.
    """
    path = Path(csv_file)
    if not path.exists():
        logger.error("File not found: %s", path)
        return

    logger.info("Ensuring database tables exist...")
    Base.metadata.create_all(engine)

    logger.info("Reading CSV in chunks of %d from %s...", chunk_size, path)
    
    total_processed = 0
    total_inserted = 0
    start_time = time.time()
    
    for chunk_df in pd.read_csv(path, chunksize=chunk_size, low_memory=False):
        # Convert NaN values to None for SQL null compatibility
        clean_df = chunk_df.where(pd.notnull(chunk_df), None)
        records = clean_df.to_dict(orient="records")
        
        with Session() as session:
            repo = ListingRepository(session)
            inserted = repo.add_many(records)
            total_inserted += inserted
            total_processed += len(records)
            
        elapsed = time.time() - start_time
        logger.info(
            "Processed %d records | Inserted %d new | Elapsed: %.1fs",
            total_processed,
            total_inserted,
            elapsed,
        )

    logger.info(
        "Bulk load complete! Total processed: %d | Total inserted: %d | Time: %.1fs",
        total_processed,
        total_inserted,
        time.time() - start_time,
    )


def main() -> None:
    """CLI entry point for bulk CSV loading."""
    parser = argparse.ArgumentParser(description="Bulk load CSV dataset to database.")
    parser.add_argument(
        "--input",
        default="data/processed/zap_dataset_deduplicated.csv",
        help="CSV input path",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=2000,
        help="Batch size per transaction",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    load_csv_to_db(Path(args.input), chunk_size=args.chunk_size)


if __name__ == "__main__":
    main()
