from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def create_tables():
    """
    Create all database tables.
    Imports models so that they are registered with the metadata and then creates tables.
    """
    from app.models import job, job_activity_log  # Adjust as needed
    Base.metadata.create_all(bind=engine)
