from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from .engine import GeoencodingEngine


class GeoencodingSession:
    def __init__(self, engine: GeoencodingEngine):
        self.session = sessionmaker(
            bind=engine(),
            autoflush=False,
            autocommit=False,
        )

    def __call__(self):
        return self.session()