from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.services.jobs import JobsService
import logging

router = APIRouter(tags=["Jobs"])
logger = logging.getLogger(__name__)

@router.get("/jobs", response_model=APIResponse)
async def list_jobs(db: Session = Depends(get_db)):
    """
    List all jobs with associated metadata.

    Returns:
      - APIResponse containing a list of job details.
    """
    try:
        service = JobsService(db)
        jobs_list = service.list_jobs()
        return APIResponse(data=jobs_list, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"list_jobs error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
