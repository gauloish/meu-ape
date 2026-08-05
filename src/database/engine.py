from pathlib import Path

from sqlalchemy import create_engine, Engine

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_database_path(project_root: Path) -> Path:
    """Get database base path for geocoding cache

    Args:
        project_root (Path): Path of the project root

    Returns:
        Path: Path of the database for geocoding cache
    """
    db_path = PROJECT_ROOT / "data" / "cache" / "geocoding.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return db_path


db_path = get_database_path(PROJECT_ROOT)
engine = create_engine(f"sqlite:///{db_path}")
