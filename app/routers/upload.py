from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.services.upload import UploadService
from app.schemas.job import JobResponse
import logging

router = APIRouter(tags=["Upload"])
logger = logging.getLogger(__name__)

@router.post("/upload", response_model=APIResponse)
async def upload_files(
    job_name: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Process uploaded files and create a job record.

    Parameters:
      - job_name: Name of the job.
      - files: List of files to be processed.

    Returns:
      - APIResponse containing the created job details.
    """
    try:
        service = UploadService(db)
        job = await service.upload_files(job_name, files)        
        job_serialized = JobResponse.model_validate(job)
        return APIResponse(data=job_serialized, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"upload_files error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
