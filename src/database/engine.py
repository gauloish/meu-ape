from pathlib import Path

from sqlalchemy import create_engine, Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class GeocodingEngine:
    def __init__(self):
        self.db_path = PROJECT_ROOT / "data" / "cache" / "geocoding.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}")

    def __call__(self) -> Engine:
        """Return the geocoding database engine

        Returns:
            Engine: Geocoding database engine
        """
        return self.engine
