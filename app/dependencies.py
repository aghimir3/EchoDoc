from sqlalchemy.orm import Session
from app.db import SessionLocal

def get_db():
    """
    Dependency function that provides a database session.

    Yields a SQLAlchemy SessionLocal instance and ensures that the session
    is closed after the request is completed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
