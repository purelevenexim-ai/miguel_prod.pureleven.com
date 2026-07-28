from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,           # max persistent connections
    max_overflow=5,         # max extra connections under load
    pool_timeout=10,        # raise after 10s if no connection available
    pool_recycle=1800,      # recycle connections every 30 min
    pool_pre_ping=True,     # test connection health before using
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()          # commit if handler succeeded without error
    except Exception:
        db.rollback()        # rollback on any unhandled exception
        raise
    finally:
        db.close()           # always release connection back to pool

