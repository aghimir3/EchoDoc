import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class JobsService:
    """
    Service for handling job-related operations.
    
    Provides methods to list and manage job records.
    """
    def __init__(self, db: Session) -> None:
        """
        Initialize JobsService with a SQLAlchemy session.
        """
        self.db = db
        self.logger = logger

    def list_jobs(self) -> list:
        """
        Retrieve a list of all jobs with associated metadata.
        
        :return: A list of dictionaries representing jobs.
        """
        from app.models.job import Job
        from app.models.document import Document
        from app.models.finetuned_model import FineTunedModel

        jobs = self.db.query(Job).all()
        job_list = []
        for job in jobs:
            documents = self.db.query(Document).filter(
                Document.job_id == job.id,
                Document.is_aggregated == False
            ).all()
            document_ids = [doc.id for doc in documents]
            ft_model = self.db.query(FineTunedModel).filter(FineTunedModel.job_id == job.id).first()
            isFinetuned = bool(ft_model and ft_model.openai_model_id)
            job_list.append({
                "id": job.id,
                "job_name": job.job_name,
                "type": job.type,
                "status": job.status,
                "document_ids": document_ids,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "completed_at": job.completed_at,
                "error_details": job.error_details,
                "file_count": job.file_count,
                "document_count": job.document_count,
                "user_id": job.user_id,
                "isFinetuned": isFinetuned
            })
        return job_list
