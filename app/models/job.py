from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.db import Base

class Job(Base):
    """
    Represents a processing job, which groups one or more document uploads and processing activities.
    
    Attributes:
      id (int): Unique identifier for the job.
      job_name (str): Name assigned to the job.
      status (str): Current status of the job (e.g., "pending", "completed", "failed").
      type (str): Type of the job (e.g., "process_document").
      created_at (datetime): Timestamp when the job was created.
      updated_at (datetime): Timestamp when the job was last updated.
      completed_at (datetime): Timestamp when the job was completed (if applicable).
      error_details (str): Detailed error message in case of failure.
      file_count (int): Number of files uploaded for this job.
      document_count (int): Number of documents processed.
      user_id (int): Optional user identifier if the system supports multiple users.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_name = Column(String(255), nullable=False)
    status = Column(String(255), index=True)
    type = Column(String(255), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_details = Column(Text, nullable=True)
    file_count = Column(Integer, default=0)
    document_count = Column(Integer, default=0)
    user_id = Column(Integer, nullable=True)
