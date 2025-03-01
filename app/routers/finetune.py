from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.schemas.job import JobResponse
from app.services.finetune import FinetuneService
from pydantic import BaseModel
import logging

router = APIRouter(tags=["Finetune"])
logger = logging.getLogger(__name__)

class FinetuneJobRequest(BaseModel):
    jobId: int

class FinetuneJobWithModelRequest(BaseModel):
    jobId: int
    model: str

@router.post("/finetune/job", response_model=APIResponse)
async def finetune_by_job(
    request: FinetuneJobRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger fine-tuning in the background for a job.

    Parameters:
      - jobId: The job ID.

    Returns:
      - APIResponse containing the job details.
    """
    try:
        service = FinetuneService(db)
        job, aggregated_jsonl_blob = await service.queue_background_finetune(request.jobId)
        job_serialized = JobResponse.model_validate(job)
        background_tasks.add_task(FinetuneService.run_background_finetune, request.jobId, [aggregated_jsonl_blob])
        return APIResponse(data=job_serialized, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"finetune_by_job error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])

@router.post("/finetune/job-with-model", response_model=APIResponse)
async def finetune_by_job_with_model(
    request: FinetuneJobWithModelRequest,
    db: Session = Depends(get_db)
):
    """
    Synchronously trigger fine-tuning for a job using a specified model.

    Parameters:
      - jobId: The job ID.
      - model: The model name.

    Returns:
      - APIResponse containing the updated job.
    """
    try:
        service = FinetuneService(db)
        job = await service.finetune_job_with_model(request.jobId, request.model)
        return APIResponse(data=job, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"finetune_by_job_with_model error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])

@router.get("/finetune/status/{jobId}", response_model=APIResponse)
async def fine_tune_status(jobId: int, db: Session = Depends(get_db)):
    """
    Retrieve the fine-tuning status for a given job.

    Parameters:
      - jobId: The job ID.

    Returns:
      - APIResponse containing status details.
    """
    try:
        service = FinetuneService(db)
        status_info = await service.check_finetune_status(jobId)
        return APIResponse(data=status_info, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"fine_tune_status error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
