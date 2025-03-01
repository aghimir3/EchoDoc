from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.services.chat import ChatService
import logging

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)

@router.post("/chat/job/{job_id}", response_model=APIResponse)
async def chat_by_job(
    job_id: int,
    message: str,
    mode: str = Query("rag", description="Chat mode: 'rag', 'raft', or 'fine_tuned_only'"),
    db: Session = Depends(get_db)
):
    """
    Generate a chat response based on a job's aggregated context.

    Parameters:
      - job_id: ID of the job.
      - message: User's query message.
      - mode: Mode for generating the response.

    Returns:
      - APIResponse containing the chat response.
    """
    try:
        service = ChatService(db)
        result = await service.chat_by_job(job_id, message, mode)
        return APIResponse(data=result, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"chat_by_job error: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
