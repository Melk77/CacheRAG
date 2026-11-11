from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.database.connections import postgres_engine


SessionLocal = sessionmaker(
    bind=postgres_engine,
    autoflush=False,
    autocommit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
