import io
import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base, engine

# Create all tables for testing (in your test database)
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# Helper function to simulate file upload
def get_test_file(filename: str, content: bytes, content_type: str):
    return (filename, io.BytesIO(content), content_type)

def test_upload_no_files():
    """
    Test uploading without providing files.
    Expect a 422 error due to missing required form field.
    """
    response = client.post("/api/upload", data={"job_name": "Test Job"})
    # Expecting 422 because 'files' is a required field in the endpoint.
    assert response.status_code == 422
    resp_data = response.json()
    # Check that the default FastAPI validation error response has a 'detail' key.
    assert "detail" in resp_data

def test_upload_with_file():
    """
    Test a successful file upload.
    Checks that a job is created with the correct job name.
    """
    file_content = b"Sample file content for testing."
    files = {"files": get_test_file("test.txt", file_content, "text/plain")}
    data = {"job_name": "Upload Test Job"}
    response = client.post("/api/upload", data=data, files=files)
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["success"]
    job_data = resp_data["data"]
    assert "id" in job_data
    assert job_data["job_name"] == "Upload Test Job"

def test_jobs_endpoint():
    """
    Test that the jobs endpoint returns a list of jobs.
    """
    response = client.get("/api/jobs")
    assert response.status_code == 200
    resp_data = response.json()
    assert resp_data["success"]
    assert isinstance(resp_data["data"], list)

def test_chat_endpoint_invalid_job():
    """
    Test that a chat request for a non-existent job returns an error.
    """
    # Use an unlikely job id
    response = client.post("/api/chat/job/999999", params={"message": "Hello", "mode": "rag"})
    resp_data = response.json()
    assert not resp_data["success"]
    # Check that the error message contains some hint of the missing context or model.
    assert "not available" in resp_data["errorMessage"].lower() or "failed" in resp_data["errorMessage"].lower()

def test_finetune_status_invalid():
    """
    Test that checking the fine-tuning status for a non-existent job returns an error response.
    """
    response = client.get("/api/finetune/status/999999")
    resp_data = response.json()
    # In our implementation, if the job is not found, we might return a status of "not_run"
    # Or if an error is raised, our global exception handler will wrap it.
    assert not resp_data["success"] or resp_data["data"] is None

def test_evaluate_invalid():
    """
    Test evaluating a fine-tuned model for a non-existent job.
    """
    response = client.post("/api/evaluate/job/999999")
    resp_data = response.json()
    
    assert not resp_data["success"]
    
    expected_messages = [
        "no fine-tuned model",
        "not found",
        "aggregated context not available"
    ]
    
    assert any(msg in resp_data["errorMessage"].lower() for msg in expected_messages), f"Unexpected error message: {resp_data['errorMessage']}"


def test_job_logs_invalid():
    """
    Test retrieving logs for a non-existent job.
    """
    response = client.get("/api/logs/999999")
    resp_data = response.json()
    assert not resp_data["success"]
    assert "no logs" in resp_data["errorMessage"].lower() or "not found" in resp_data["errorMessage"].lower()

def test_finetune_job_with_model_invalid():
    """
    Test triggering fine-tuning synchronously with a non-existent job.
    """
    payload = {"jobId": 999999, "model": "gpt-4o"}
    response = client.post("/api/finetune/job-with-model", json=payload)
    resp_data = response.json()
    assert not resp_data["success"]
    assert "not found" in resp_data["errorMessage"].lower() or "failed" in resp_data["errorMessage"].lower()
