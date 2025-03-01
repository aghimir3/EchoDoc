import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException

logger = logging.getLogger(__name__)

class JobLogsService:
    """
    Service for retrieving job activity logs.
    
    Provides methods to fetch and format job logs.
    """
    def __init__(self, db: Session) -> None:
        """
        Initialize JobLogsService with a SQLAlchemy session.
        """
        self.db = db
        self.logger = logger

    def get_job_logs(self, job_id: int) -> list:
        """
        Retrieve logs for a specific job.
        
        :param job_id: The ID of the job.
        :return: List of log entries as dictionaries.
        :raises HTTPException: If no logs are found.
        """
        from app.models.job_activity_log import JobActivityLog
        logs = (
            self.db.query(JobActivityLog)
            .filter(JobActivityLog.job_id == job_id)
            .order_by(JobActivityLog.timestamp)
            .all()
        )
        if not logs:
            raise HTTPException(status_code=404, detail="No logs found for this job")
        return [
            {
                "event_type": log.event_type,
                "message": log.message,
                "timestamp": log.timestamp.isoformat(),
            }
            for log in logs
        ]
