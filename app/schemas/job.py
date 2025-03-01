from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import List, Optional

class JobBase(BaseModel):
    model_config = ConfigDict()
    """
    Base schema for a job, containing common fields.
    
    Attributes:
      status (str): Current status of the job.
      type (str): Type/category of the job.
    """
    status: str
    type: str

class JobCreate(JobBase):
    """
    Schema used for creating a new job.
    """
    pass

class JobResponse(JobBase):
    model_config = ConfigDict(from_attributes=True)
    """
    Response schema representing a job.
    
    Attributes:
      id (int): Unique job identifier.
      job_name (str): Name of the job.
      created_at (datetime): Job creation timestamp.
      updated_at (datetime): Last update timestamp.
      completed_at (Optional[datetime]): Completion timestamp, if available.
      error_details (Optional[str]): Error details if the job failed.
      file_count (int): Number of files associated with the job.
      document_count (int): Number of processed documents.
      user_id (Optional[int]): User identifier (if applicable).
    """
    id: int
    job_name: str
    status: str
    type: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None
    file_count: int
    document_count: int
    user_id: Optional[int] = None

class ChatRequest(BaseModel):
    model_config = ConfigDict()
    """
    Schema for a chat request.
    
    Attributes:
      message (str): The user's chat message.
      model_type (str): The type of model to be used.
      ft_model_id (Optional[int]): Fine-tuned model ID, if applicable.
      rag_index_id (Optional[int]): FAISS index ID for RAG queries.
    """
    message: str
    model_type: str
    ft_model_id: Optional[int] = None
    rag_index_id: Optional[int] = None

class FinetuneRequest(BaseModel):
    model_config = ConfigDict()
    """
    Schema for requesting fine-tuning.
    
    Attributes:
      document_ids (List[int]): List of document IDs to use for fine-tuning.
    """
    document_ids: List[int]

class JobListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """
    Schema for listing jobs.
    
    Attributes:
      id (int): Job identifier.
      job_name (str): Name of the job.
      type (str): Type/category of the job.
      status (str): Current status.
      document_ids (List[int]): List of document IDs associated with the job.
      created_at (datetime): Creation timestamp.
      updated_at (datetime): Last update timestamp.
      completed_at (Optional[datetime]): Completion timestamp.
      error_details (Optional[str]): Any error details.
      file_count (int): Number of files uploaded.
      document_count (int): Number of processed documents.
      user_id (Optional[int]): User identifier, if applicable.
      isFinetuned (bool): Whether the job has an associated fine-tuned model.
    """
    id: int
    job_name: str = ""
    type: str
    status: str
    document_ids: List[int] = []
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_details: Optional[str] = None
    file_count: int = 0
    document_count: int = 0
    user_id: Optional[int] = None
    isFinetuned: bool = False

class ErrorResponse(BaseModel):
    model_config = ConfigDict()
    """
    Schema for error responses.

    Attributes:
      status (str): Status indicator, typically "error".
      message (str): Error message.
      details (Optional[str]): Additional error details.
    """
    status: str = "error"
    message: str
    details: Optional[str] = None

class FineTuneStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """
    Schema for representing fine-tuning status.

    Attributes:
      job_id (int): Job identifier.
      openai_job_id (str): OpenAI job identifier.
      status (str): Current fine-tuning status.
      fine_tuned_model_id (Optional[str]): Model ID after successful fine-tuning.
      details (Optional[str]): Additional details.
    """
    job_id: int
    openai_job_id: str
    status: str
    fine_tuned_model_id: Optional[str] = None
    details: Optional[str] = None

class JobLog(BaseModel):
    model_config = ConfigDict()
    """
    Schema for an individual job log entry.

    Attributes:
      event_type (str): Type of the log event.
      message (Optional[str]): Log message details.
      timestamp (datetime): Timestamp when the log entry was created.
    """
    event_type: str
    message: Optional[str]
    timestamp: datetime

class JobLogResponse(BaseModel):
    model_config = ConfigDict()
    """
    Schema for job log responses.

    Attributes:
      job_id (int): The job identifier.
      logs (List[JobLog]): List of job log entries.
    """
    job_id: int
    logs: List[JobLog]
