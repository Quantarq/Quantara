"""
This module contains the database configuration and session management.

Reads PostgreSQL connection parameters from environment variables and
exposes the SQLAlchemy engine, session factory, and declarative base
for use throughout the web application.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

load_dotenv(override=False)

DB_USER = os.environ.get("DB_USER", "")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_SERVER = os.environ.get("DB_HOST", "")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "")

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()



# Create a shared DBConnector instance
from web_app.db.crud.base import DBConnector
db_connector = DBConnector(engine=engine)


def get_database() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session and ensures cleanup.

    :yield: SQLAlchemy Session instance
    :raises: None (always closes the session in the finally block)
    """
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
