from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.db import Base

class JobActivityLog(Base):
    """
    Represents an activity log entry for a job.
    
    Attributes:
      id (int): Unique identifier for the log entry.
      job_id (int): Foreign key referencing the associated job.
      event_type (str): A short code or description of the event (e.g., "upload_started").
      message (str): Detailed message about the event.
      timestamp (datetime): Time when the event occurred.
    """
    __tablename__ = "job_activity_log"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    event_type = Column(String(100))
    message = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
