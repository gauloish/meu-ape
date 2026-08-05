from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from .engine import GeocodingEngine


class GeocodingSession:
    def __init__(self, engine: GeocodingEngine):
        self.session = sessionmaker(
            bind=engine(),
            autoflush=False,
            autocommit=False,
        )

    def __call__(self):
        return self.session()