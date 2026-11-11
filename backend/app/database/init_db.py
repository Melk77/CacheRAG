from app.database.base import Base
from app.database.connections import postgres_engine
import app.models


def create_tables() -> None:
    Base.metadata.create_all(bind=postgres_engine)


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
    print("Tables:", list(Base.metadata.tables.keys()))
