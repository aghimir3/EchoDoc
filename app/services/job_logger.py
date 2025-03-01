import logging
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

class JobLogger:
    """
    Service for logging job activity.
    
    Provides a method to record job events in the database.
    """
    @staticmethod
    def log_job_activity(db: Session, job_id: int, event_type: str, message: str = None) -> None:
        """
        Log an activity for a given job.
        
        :param db: SQLAlchemy session.
        :param job_id: The job's ID.
        :param event_type: The type of event (e.g., "upload_started").
        :param message: Optional message detailing the event.
        """
        try:
            from app.models.job_activity_log import JobActivityLog
            log_entry = JobActivityLog(job_id=job_id, event_type=event_type, message=message)
            db.add(log_entry)
            db.commit()
            logger.info(f"Logged activity for job {job_id}: {event_type} - {message}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to log activity for job {job_id}: {str(e)}")
