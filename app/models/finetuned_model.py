from sqlalchemy import Column, Integer, String, ForeignKey
from app.db import Base

class FineTunedModel(Base):
    """
    Represents a model that has been fine-tuned as a result of a job.
    
    Attributes:
      id (int): Unique identifier for the fine-tuned model record.
      job_id (int): Foreign key referencing the associated job.
      openai_model_id (str): The model ID returned by OpenAI after fine-tuning.
      openai_job_id (str): The job ID provided by OpenAI for the fine-tuning process.
    """
    __tablename__ = "finetuned_models"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"))
    openai_model_id = Column(String(255))
    openai_job_id = Column(String(255), nullable=True)
