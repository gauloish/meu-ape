from pathlib import Path

from sqlalchemy import create_engine, Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class GeoencodingEngine:
    def __init__(self):
        self.db_path = PROJECT_ROOT / "data" / "cache" / "geoencoding.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path}")

    def __call__(self) -> Engine:
        return self.engine
