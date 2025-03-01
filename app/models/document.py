from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from app.db import Base

class Document(Base):
    """
    Represents a document that is either uploaded or processed as part of a job.
    
    Attributes:
      id (int): Unique identifier for the document.
      job_id (int): Foreign key referencing the associated job.
      blob_path (str): Path to the original file in blob storage.
      file_type (str): MIME type of the document.
      jsonl_blob_path (str): Path to the generated JSONL artifact (if any).
      faiss_index_blob_path (str): Path to the generated FAISS index artifact (if any).
      chunks_blob_path (str): Path to the text chunks artifact (if any).
      is_aggregated (bool): Indicates whether this document represents aggregated data.
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    blob_path = Column(String(255))
    file_type = Column(String(255))
    jsonl_blob_path = Column(String(255), nullable=True)
    faiss_index_blob_path = Column(String(255), nullable=True)
    chunks_blob_path = Column(String(255), nullable=True)
    is_aggregated = Column(Boolean, default=False)
