import os
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models.job import Job
from app.models.finetuned_model import FineTunedModel
from app.models.document import Document
from app.utils.blob_storage import download_from_blob_async, upload_to_blob_async
from openai import OpenAI
from app.config import settings
from app.services.job_logger import JobLogger

# Configure module-level logger and OpenAI client using API key from settings.
logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class FinetuneService:
    """
    Async service for handling fine-tuning operations.
    
    This service is responsible for:
    - Queuing fine-tuning jobs in the background.
    - Triggering fine-tuning jobs with a specified model.
    - Checking and updating the status of fine-tuning jobs.
    - Managing file aggregation and communication with OpenAI's fine-tuning API.
    """
    def __init__(self, db: Session) -> None:
        """
        Initialize the FinetuneService with a database session.
        
        Args:
            db (Session): SQLAlchemy session for database operations.
        """
        self.db = db
        self.logger = logger
        self.client = client

    async def queue_background_finetune(self, job_id: int) -> tuple:
        """
        Queue a fine-tuning job in the background.
        
        This method verifies the existence of an aggregated JSONL document,
        logs the job activity, updates the job status to 'finetune pending', 
        and returns the job along with the JSONL blob path.
        
        Args:
            job_id (int): The ID of the job to be queued.
            
        Returns:
            tuple: Updated job object and JSONL blob path.
            
        Raises:
            ValueError: If the aggregated JSONL artifact or job is not found.
        """
        agg_doc = (
            self.db.query(Document)
            .filter(Document.job_id == job_id, Document.is_aggregated == True)
            .first()
        )
        if not agg_doc or not agg_doc.jsonl_blob_path:
            raise ValueError(f"Aggregated JSONL artifact not found for job {job_id}")
        JobLogger.log_job_activity(self.db, job_id, "finetune_requested", "Finetune job requested")
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.status = "finetune pending"
        self.db.commit()
        JobLogger.log_job_activity(self.db, job_id, "finetune_queued", "Finetune process queued in background")
        return job, agg_doc.jsonl_blob_path

    async def finetune_job_with_model(self, job_id: int, model: str) -> Job:
        """
        Trigger a fine-tuning job using a specified model.
        
        This method logs the fine-tuning request, validates the aggregated JSONL document,
        triggers the fine-tuning process asynchronously, updates the job status to 
        'finetune in progress', and logs the queued action.
        
        Args:
            job_id (int): The ID of the job to be fine-tuned.
            model (str): The model name to be used for fine-tuning.
            
        Returns:
            Job: The updated job instance.
            
        Raises:
            ValueError: If the aggregated JSONL artifact is not found.
        """
        JobLogger.log_job_activity(self.db, job_id, "finetune_requested", f"Finetune job requested with model {model}")
        agg_doc = (
            self.db.query(Document)
            .filter(Document.job_id == job_id, Document.is_aggregated == True)
            .first()
        )
        if not agg_doc or not agg_doc.jsonl_blob_path:
            raise ValueError(f"Aggregated JSONL artifact not found for job {job_id}")
        aggregated_jsonl_blob = agg_doc.jsonl_blob_path
        await self._trigger_finetune(job_id, [aggregated_jsonl_blob], model)
        job = self.db.query(Job).filter(Job.id == job_id).first()
        job.status = "finetune in progress"
        self.db.commit()
        JobLogger.log_job_activity(self.db, job_id, "finetune_queued", f"Finetune job triggered with model {model}")
        return job

    async def check_finetune_status(self, job_id: int) -> dict:
        """
        Check the current status of a fine-tuning job and update records if needed.
        
        This method queries the job and associated fine-tuned model record,
        retrieves the current status from OpenAI, updates the job status and logs changes,
        and if successful, updates the model ID record.
        
        Args:
            job_id (int): The ID of the job to check.
            
        Returns:
            dict: A dictionary containing job ID, OpenAI job ID, current status, and fine-tuned model ID.
            
        Raises:
            HTTPException: If the job is not found.
        """
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Job not found")
        ft_model = self.db.query(FineTunedModel).filter(FineTunedModel.job_id == job_id).first()
        if not ft_model or not ft_model.openai_job_id:
            return {"job_id": job_id, "status": "not_run"}
        status_resp = self.client.fine_tuning.jobs.retrieve(ft_model.openai_job_id)
        new_status = status_resp.status
        if job.status != new_status:
            JobLogger.log_job_activity(self.db, job_id, f"finetune_{new_status}", f"Finetune job status updated to '{new_status}'")
            self.logger.info(f"Updating job status from '{job.status}' to '{new_status}'")
            job.status = new_status
            self.db.commit()
        fine_tuned_model_id = getattr(status_resp, "fine_tuned_model", None)
        if new_status == "succeeded" and (not ft_model.openai_model_id or ft_model.openai_model_id != fine_tuned_model_id):
            self.logger.info(f"Updating fine-tuned model record with model id: {fine_tuned_model_id}")
            JobLogger.log_job_activity(self.db, job_id, "finetune_succeeded", "Finetune job succeeded")
            ft_model.openai_model_id = fine_tuned_model_id
            self.db.commit()
        return {
            "job_id": job_id,
            "openai_job_id": ft_model.openai_job_id,
            "status": new_status,
            "fine_tuned_model_id": fine_tuned_model_id
        }

    async def _trigger_finetune(self, job_id: int, jsonl_blob_paths: list, model: str) -> None:
        """
        Internal method to trigger the fine-tuning process.
        
        This function:
        - Combines multiple JSONL blob files into a single file.
        - Uploads the combined file to OpenAI.
        - Initiates the fine-tuning job via OpenAI's API.
        - Logs each major step and creates a record for the fine-tuned model.
        
        Args:
            job_id (int): The ID of the job.
            jsonl_blob_paths (list): List of JSONL blob paths.
            model (str): The model name for fine-tuning.
            
        Raises:
            ValueError: If the job is not found.
            Exception: Propagates any exceptions encountered during the process.
        """
        combined_jsonl_path = os.path.join(settings.LOCAL_STORAGE_FOLDER, f"combined_{job_id}.jsonl")
        job = self.db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        try:
            os.makedirs(settings.LOCAL_STORAGE_FOLDER, exist_ok=True)
            # Combine content from each JSONL blob into a single file.
            with open(combined_jsonl_path, "w", encoding="utf-8") as combined_file:
                for blob_path in jsonl_blob_paths:
                    self.logger.debug(f"Downloading JSONL from {blob_path}")
                    local_path = await download_from_blob_async(blob_path, "artifacts")
                    with open(local_path, "r", encoding="utf-8") as f:
                        combined_file.write(f.read() + "\n")
                    os.remove(local_path)
            # Upload combined JSONL file to OpenAI.
            with open(combined_jsonl_path, "rb") as f:
                self.logger.debug(f"Uploading combined JSONL for job {job_id}")
                file_response = self.client.files.create(file=f, purpose="fine-tune")
            self.logger.info(f"Starting fine-tuning for job {job_id} with model {model}")
            fine_tune_response = self.client.fine_tuning.jobs.create(
                training_file=file_response.id,
                model=model
            )
            openai_job_id = fine_tune_response.id
            self.logger.info(f"OpenAI fine-tune job started: {openai_job_id}")
            # Record the fine-tuned model details in the database.
            fine_tuned_model = FineTunedModel(job_id=job_id, openai_job_id=openai_job_id, openai_model_id=None)
            self.db.add(fine_tuned_model)
            self.db.commit()
        except Exception as e:
            self.logger.error(f"Error triggering finetune job {job_id}: {str(e)}", exc_info=True)
            if job:
                job.status = f"failed: {str(e)}"
                self.db.commit()
            raise
        finally:
            if os.path.exists(combined_jsonl_path):
                os.remove(combined_jsonl_path)

    @staticmethod
    async def run_background_finetune(job_id: int, jsonl_blob_paths: list) -> None:
        """
        Run a background fine-tuning job without an active service instance.
        
        This static method:
        - Establishes its own database session to avoid circular dependencies.
        - Combines JSONL blob files into one file.
        - Uploads the file to OpenAI and triggers the fine-tuning process using a default model.
        - Logs the process and updates the job and model records accordingly.
        
        Args:
            job_id (int): The ID of the job.
            jsonl_blob_paths (list): List of JSONL blob paths.
            
        Raises:
            ValueError: If the job is not found.
            Exception: Propagates any exceptions encountered during processing.
        """
        from app.db import SessionLocal  # local import to avoid circular dependency
        db = SessionLocal()
        combined_jsonl_path = os.path.join(settings.LOCAL_STORAGE_FOLDER, f"combined_{job_id}.jsonl")
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            db.close()
            raise ValueError("Job not found")
        try:
            os.makedirs(settings.LOCAL_STORAGE_FOLDER, exist_ok=True)
            # Combine JSONL blobs into a single file for upload.
            with open(combined_jsonl_path, "w", encoding="utf-8") as combined_file:
                for blob_path in jsonl_blob_paths:
                    local_path = await download_from_blob_async(blob_path, "artifacts")
                    with open(local_path, "r", encoding="utf-8") as f:
                        combined_file.write(f.read() + "\n")
                    os.remove(local_path)
            # Upload combined file and start the fine-tuning process using the default model.
            with open(combined_jsonl_path, "rb") as f:
                file_response = client.files.create(file=f, purpose="fine-tune")
            fine_tune_response = client.fine_tuning.jobs.create(
                training_file=file_response.id,
                model=settings.DEFAULT_FINETUNE_MODEL
            )
            openai_job_id = fine_tune_response.id
            logger.info(f"OpenAI fine-tune job started: {openai_job_id}")
            fine_tuned_model = FineTunedModel(job_id=job_id, openai_job_id=openai_job_id, openai_model_id=None)
            db.add(fine_tuned_model)
            db.commit()
            job.status = "finetune in progress"
            db.commit()
            logger.info(f"Background finetune job {job_id} triggered successfully")
        except Exception as e:
            logger.error(f"Error in background finetune job {job_id}: {str(e)}", exc_info=True)
            if job:
                job.status = f"failed: {str(e)}"
                db.commit()
            raise
        finally:
            db.close()
            if os.path.exists(combined_jsonl_path):
                os.remove(combined_jsonl_path)
