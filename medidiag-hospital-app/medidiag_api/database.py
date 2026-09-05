import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Defaults to a local SQLite file for local dev. Set DATABASE_URL (e.g. to a
# Railway/Postgres connection string) in production -- Railway's filesystem
# is ephemeral, so SQLite there would lose all data on every redeploy.
SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./medidiag.db")
if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    # Railway/Heroku-style URLs use the "postgres://" scheme, which SQLAlchemy
    # 1.4+ no longer accepts -- it requires "postgresql://".
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
