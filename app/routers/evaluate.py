from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.schemas.response import APIResponse
from app.services.evaluation import EvaluationService
import logging

router = APIRouter(tags=["Evaluate"])
logger = logging.getLogger(__name__)

@router.post("/evaluate/job/{jobId}", response_model=APIResponse)
async def evaluate_job(jobId: int, db: Session = Depends(get_db)):
    """
    Evaluate the performance of the RAG and fine-tuned models for a given job.

    This endpoint uses a robust evaluation framework that:
      - Uses an extended list of evaluation questions (including distractors, ground truth, and oracle answers).
      - Evaluates multiple metrics (relevancy, faithfulness, completeness, clarity, correctness, and oracle agreement).
      - Runs multiple trials per question to average out LLM variability.

    The returned data is structured for easy consumption and graphing in the UI.

    Parameters:
      - jobId: The identifier of the job to be evaluated.

    Returns:
      - APIResponse containing detailed evaluation metrics.
    """
    try:
        evaluation_service = EvaluationService(db)
        result = await evaluation_service.evaluate_model(jobId)
        return APIResponse(data=result, success=True, errorMessage="", errors=[])
    except Exception as e:
        logger.error(f"Evaluation error for job {jobId}: {str(e)}", exc_info=True)
        return APIResponse(data=None, success=False, errorMessage=str(e), errors=[str(e)])
