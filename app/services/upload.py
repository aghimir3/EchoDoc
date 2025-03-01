import os
import logging
from datetime import datetime, timezone
from typing import List, Tuple
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.config import settings
from app.models.job import Job
from app.models.document import Document
from app.services.document_parser import DocumentParser
from app.services.rag import RagService
from app.utils.blob_storage import upload_to_blob_async, download_from_blob_async
from app.services.job_logger import JobLogger

logger = logging.getLogger(__name__)

class UploadService:
    """
    Asynchronous service for handling file uploads and processing for EchoDoc.
    
    Responsibilities:
      - Create a new processing job.
      - Process uploaded files by:
          • Uploading original files.
          • Parsing files to extract text, JSONL data, and text chunks.
          • Creating FAISS indices for document retrieval.
          • Uploading generated artifacts (JSONL, FAISS indexes, chunk data) to blob storage.
      - Create Document records for each file and an aggregated Document record.
      - Clean up temporary local files and folders once processing is complete.
    """
    def __init__(self, db: Session) -> None:
        """
        Initialize the UploadService with a database session.
        
        Args:
            db (Session): SQLAlchemy session for database operations.
        """
        self.db = db
        self.logger = logger

    async def upload_files(self, job_name: str, files: List) -> Job:
        """
        Orchestrates the complete file upload and processing workflow.
        
        Workflow:
          - Validates that files are provided.
          - Creates a new job record.
          - Determines local and blob storage folder names.
          - Processes each file: uploads, parses, and generates artifacts.
          - Creates aggregated artifacts and Document records.
          - Finalizes the job status.
        
        Args:
            job_name (str): The name for the upload job.
            files (List): List of files to process.
        
        Returns:
            Job: The updated job record after processing.
            
        Raises:
            HTTPException: If no files are provided.
        """
        if not files:
            raise HTTPException(status_code=400, detail="No files uploaded")
        
        job = self._create_job(job_name, len(files))
        # Create a unique local folder and determine the job-specific blob folder name.
        job_folder, blob_folder = self._get_folders(job, job_name)
        aggregated_jsonl, aggregated_chunks, doc_count = await self._process_files(files, job, job_folder, blob_folder)
        await self._create_aggregated_artifacts(job, blob_folder, aggregated_jsonl, aggregated_chunks)
        self._finalize_job(job, doc_count, job_folder)
        return job

    def _create_job(self, job_name: str, file_count: int) -> Job:
        """
        Creates a new Job record in the database.
        
        Args:
            job_name (str): Name assigned to the job.
            file_count (int): Number of files to be processed.
        
        Returns:
            Job: The newly created job record.
        """
        from app.models.job import Job
        job = Job(
            status="pending",
            type="process_document",
            file_count=file_count,
            job_name=job_name
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        JobLogger.log_job_activity(self.db, job.id, "job_created", f"Created job with {file_count} file(s) and name '{job_name}'")
        self.logger.info(f"Created job {job.id} for file uploads with name '{job_name}'")
        return job

    def _get_folders(self, job: Job, job_name: str) -> Tuple[str, str]:
        """
        Determines the local and blob storage folder names for the job.
        
        Args:
            job (Job): The job record.
            job_name (str): The job name.
        
        Returns:
            Tuple[str, str]: A tuple containing the local folder path and blob folder name.
        """
        folder_name = f"job-{job.id}-{job_name}"
        local_folder = os.path.join(settings.LOCAL_STORAGE_FOLDER, folder_name)
        os.makedirs(local_folder, exist_ok=True)
        return local_folder, folder_name  # Blob folder uses the same folder name

    async def _process_files(
        self, files: List, job: Job, local_folder: str, blob_folder: str
    ) -> Tuple[List[str], List[str], int]:
        """
        Processes each uploaded file by:
          - Logging file processing start.
          - Uploading the original file to blob storage.
          - Downloading the file locally for parsing.
          - Parsing the file to generate JSONL and text chunk artifacts.
          - Uploading individual artifacts to blob storage.
          - Creating Document records.
        
        Args:
            files (List): List of uploaded file objects.
            job (Job): Current job record.
            local_folder (str): Local directory for temporary storage.
            blob_folder (str): Folder name for blob storage organization.
        
        Returns:
            Tuple[List[str], List[str], int]: Aggregated JSONL strings, aggregated text chunks, and document count.
        
        Raises:
            HTTPException: If an error occurs during file processing.
        """
        aggregated_jsonl = []
        aggregated_chunks = []
        doc_count = 0

        for file in files:
            try:
                JobLogger.log_job_activity(self.db, job.id, "file_upload_started", f"Processing file: {file.filename}")
                self.logger.info(f"Processing file: {file.filename} for job {job.id}")
                # Upload original file to blob storage.
                doc_blob_path = await upload_to_blob_async(
                    file.file.read(),
                    f"{blob_folder}/{file.filename}",
                    container="documents"
                )
                self.logger.info(f"Uploaded {file.filename} to documents container at {doc_blob_path}")
                # Download file locally for processing.
                local_file_path = await download_from_blob_async(doc_blob_path, "documents")
                if not os.path.exists(local_file_path):
                    raise FileNotFoundError(f"Local file {local_file_path} not found")
                # Parse the file to generate processing artifacts.
                parser = DocumentParser()
                artifacts = await parser.process_file(local_file_path, file.content_type, job.id)
                if artifacts.get("jsonl"):
                    aggregated_jsonl.append(artifacts["jsonl"])
                if artifacts.get("chunks"):
                    aggregated_chunks.extend(artifacts["chunks"])
                # Upload per-file artifacts (JSONL, FAISS index, chunks)
                jsonl_blob, faiss_blob, chunks_blob = await self._upload_artifacts(file, job, artifacts, blob_folder)
                # Create a Document record for this file.
                self._create_document_record(job, doc_blob_path, file.content_type, jsonl_blob, faiss_blob, chunks_blob)
                doc_count += 1
            except Exception as e:
                self.db.rollback()
                JobLogger.log_job_activity(self.db, job.id, "file_processing_failed", f"Error processing {file.filename}: {str(e)}")
                self.logger.error(f"Error processing {file.filename}: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to process file {file.filename}: {str(e)}"
                )
        return aggregated_jsonl, aggregated_chunks, doc_count

    async def _upload_artifacts(
        self, file, job: Job, artifacts: dict, blob_folder: str
    ) -> Tuple[str, str, str]:
        """
        Uploads the generated artifacts for a single file to blob storage.
        
        Artifacts may include:
          - JSONL data representing processed text.
          - FAISS index binary file for vector search.
          - JSON file with chunk data for further processing.
        
        Args:
            file: The file being processed.
            job (Job): The current job record.
            artifacts (dict): Artifacts generated by the DocumentParser.
            blob_folder (str): Blob folder for storing artifacts.
        
        Returns:
            Tuple[str, str, str]: Blob paths for JSONL, FAISS index, and chunks.
        """
        jsonl_blob = None
        faiss_blob = None
        chunks_blob = None

        if artifacts.get("jsonl"):
            jsonl_blob = await upload_to_blob_async(
                artifacts["jsonl"].encode("utf-8"),
                f"{blob_folder}/jsonl/{job.id}_{file.filename}_combined.jsonl",
                container="artifacts"
            )
        if artifacts.get("chunks") and artifacts.get("chunks") != []:
            try:
                # Create FAISS index using RagService from the text chunks.
                file_faiss_path, file_chunks_json = RagService.create_faiss_index(artifacts["chunks"])
                # Read the FAISS index file content.
                with open(file_faiss_path, "rb") as f:
                    file_content = f.read()
                faiss_blob = await upload_to_blob_async(
                    file_content,
                    f"{blob_folder}/faiss/{job.id}_{file.filename}_index.bin",
                    container="artifacts"
                )
                chunks_blob = await upload_to_blob_async(
                    file_chunks_json.encode("utf-8"),
                    f"{blob_folder}/chunks/{job.id}_{file.filename}_chunks.json",
                    container="artifacts"
                )
                # Clean up local FAISS file.
                if os.path.exists(file_faiss_path):
                    os.remove(file_faiss_path)
            except Exception as e:
                self.logger.error(f"Failed to create FAISS index for file {file.filename}: {str(e)}")
        return jsonl_blob, faiss_blob, chunks_blob

    def _create_document_record(self, job: Job, doc_blob_path: str, content_type: str,
                                  jsonl_blob: str, faiss_blob: str, chunks_blob: str) -> None:
        """
        Creates a Document record in the database for an individual file.
        
        The record stores:
          - The original file's blob path.
          - The content type.
          - Blob paths for generated JSONL, FAISS index, and chunk artifacts.
          - An indicator that this record is not aggregated.
        
        Args:
            job (Job): The current job record.
            doc_blob_path (str): Blob path of the original uploaded file.
            content_type (str): MIME type of the file.
            jsonl_blob (str): Blob path of the JSONL artifact.
            faiss_blob (str): Blob path of the FAISS index artifact.
            chunks_blob (str): Blob path of the chunks artifact.
        """
        from app.models.document import Document
        document = Document(
            job_id=job.id,
            blob_path=doc_blob_path,
            file_type=content_type,
            jsonl_blob_path=jsonl_blob,
            faiss_index_blob_path=faiss_blob,
            chunks_blob_path=chunks_blob,
            is_aggregated=False
        )
        self.db.add(document)
        self.db.commit()
        JobLogger.log_job_activity(self.db, job.id, "document_created", "Document record created for file")
        self.logger.info(f"Created Document record for job {job.id}")

    async def _create_aggregated_artifacts(self, job: Job, blob_folder: str,
                                           aggregated_jsonl: List[str], aggregated_chunks: List[str]) -> None:
        """
        Creates aggregated artifacts for the entire job by combining data across files.
        
        Aggregated artifacts include:
          - A combined JSONL file.
          - A FAISS index built from combined text chunks.
          - A JSON file representing the combined chunk data.
        
        After uploading these artifacts, an aggregated Document record is created.
        
        Args:
            job (Job): The current job record.
            blob_folder (str): Blob folder for storing artifacts.
            aggregated_jsonl (List[str]): List of JSONL strings from each file.
            aggregated_chunks (List[str]): Combined list of text chunks from all files.
        """
        aggregated_jsonl_blob_path = None
        if aggregated_jsonl:
            combined_jsonl_str = "\n".join(aggregated_jsonl)
            aggregated_jsonl_blob_path = await upload_to_blob_async(
                combined_jsonl_str.encode("utf-8"),
                f"{blob_folder}/jsonl/{job.id}_combined.jsonl",
                container="artifacts"
            )
            JobLogger.log_job_activity(self.db, job.id, "aggregated_jsonl_created",
                                        f"Aggregated JSONL uploaded to {aggregated_jsonl_blob_path}")
            self.logger.info(f"Uploaded aggregated JSONL artifact for job {job.id} to {aggregated_jsonl_blob_path}")
        
        aggregated_faiss_blob_path = None
        aggregated_chunks_blob_path = None
        if aggregated_chunks:
            agg_faiss_index_path, agg_chunks_json = RagService.create_faiss_index(aggregated_chunks)
            # Read the aggregated FAISS index file.
            with open(agg_faiss_index_path, "rb") as f:
                file_content = f.read()
            aggregated_faiss_blob_path = await upload_to_blob_async(
                file_content,
                f"{blob_folder}/faiss/{job.id}_combined.bin",
                container="artifacts"
            )
            aggregated_chunks_blob_path = await upload_to_blob_async(
                agg_chunks_json.encode("utf-8"),
                f"{blob_folder}/chunks/{job.id}_combined.json",
                container="artifacts"
            )
            JobLogger.log_job_activity(self.db, job.id, "aggregated_faiss_created",
                                        f"Aggregated FAISS uploaded to {aggregated_faiss_blob_path}")
            JobLogger.log_job_activity(self.db, job.id, "aggregated_chunks_created",
                                        f"Aggregated chunks uploaded to {aggregated_chunks_blob_path}")
            self.logger.info(f"Uploaded aggregated FAISS index for job {job.id} to {aggregated_faiss_blob_path}")
            self.logger.info(f"Uploaded aggregated chunks for job {job.id} to {aggregated_chunks_blob_path}")
            if os.path.exists(agg_faiss_index_path):
                os.remove(agg_faiss_index_path)
        
        # Create a Document record for the aggregated artifacts.
        aggregated_document = Document(
            job_id=job.id,
            blob_path="",
            file_type="aggregated",
            jsonl_blob_path=aggregated_jsonl_blob_path,
            faiss_index_blob_path=aggregated_faiss_blob_path,
            chunks_blob_path=aggregated_chunks_blob_path,
            is_aggregated=True
        )
        self.db.add(aggregated_document)
        self.db.commit()
        JobLogger.log_job_activity(self.db, job.id, "aggregated_document_created", "Aggregated Document record created")

    def _finalize_job(self, job: Job, doc_count: int, job_folder: str) -> None:
        """
        Finalizes the job by:
          - Updating document count, status, and completion timestamp.
          - Logging job completion.
          - Cleaning up local temporary files and folders.
        
        Args:
            job (Job): The current job record.
            doc_count (int): Number of successfully processed documents.
            job_folder (str): Local folder where job files were stored.
        """
        job.document_count = doc_count
        job.status = "completed"
        job.completed_at = datetime.now(timezone.utc)
        self.db.commit()
        JobLogger.log_job_activity(self.db, job.id, "job_completed",
                                    f"Completed processing with {doc_count} document(s)")
        self.logger.info(f"Completed job {job.id} with aggregated artifacts from {doc_count} file(s)")
        try:
            if not os.listdir(job_folder):
                os.rmdir(job_folder)
                self.logger.info(f"Removed empty job folder: {job_folder}")
        except Exception as e:
            self.logger.error(f"Error removing job folder {job_folder}: {str(e)}", exc_info=True)
