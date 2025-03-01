from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.services.job_logs import JobLogsService
import logging

router = APIRouter(tags=["JobLogs"])
logger = logging.getLogger(__name__)

@router.get("/logs/{jobId}", response_model=APIResponse)
async def get_job_logs(jobId: int, db: Session = Depends(get_db)):
    """
    Retrieve activity logs for a specific job.

    Parameters:
      - jobId: The job ID.

    Returns:
      - APIResponse containing job logs.
    """
    try:
        service = JobLogsService(db)
        logs = service.get_job_logs(jobId)
        return APIResponse(data={"job_id": jobId, "logs": logs}, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"get_job_logs error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
