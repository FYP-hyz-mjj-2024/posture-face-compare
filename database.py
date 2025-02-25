import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load database url from local env
load_dotenv()
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create SessionsLocals
SessionLocal = sessionmaker(autocommit=False,
                            autoflush=False,
                            bind=engine)

# Base class of all ORM classes
Base = declarative_base()


def get_db():
    """
    Get database session.
    :return: database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
