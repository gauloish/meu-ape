from sqlalchemy.orm import sessionmaker

from src.database.engine import engine


Session = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)
