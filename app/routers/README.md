# Router Endpoints Documentation

## Overview
This document provides detailed information on the API endpoints defined in the routers module of EchoDoc. The APIs handle job management, file uploads, fine-tuning, chat interactions, evaluations, and log retrieval. All endpoints return standardized responses using the `APIResponse` schema.

## General Response Format
All API responses follow this structure:

```json
{
  "data": { ... },
  "success": true,
  "errorMessage": "",
  "errors": []
}
```

- `data`: Contains the response payload.
- `success`: Boolean indicating if the request was successful.
- `errorMessage`: Message describing any errors.
- `errors`: List of error messages.

---

## Endpoints

### 1. Chat API
**POST /chat/job/{job_id}**
- **Description:** Generates a chat response based on a job's context.
- **Parameters:**
  - `job_id` (int) – Job identifier.
  - `message` (str) – User message.
  - `mode` (str) – Chat mode: `rag`, `raft`, or `fine_tuned_only` (default: `rag`).
- **Example Request:**
  ```json
  {
    "message": "Explain the document in simple terms",
    "mode": "rag"
  }
  ```
- **Example Response:**
  ```json
  {
    "data": { "response": "This document provides an overview of AI principles..." },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

### 2. Evaluation API
**POST /evaluate/job/{jobId}**
- **Description:** Evaluates fine-tuned models based on multiple metrics.
- **Parameters:**
  - `jobId` (int) – Job identifier.
- **Example Response:**
  ```json
  {
    "data": {
      "accuracy": 0.95,
      "completeness": 0.89,
      "clarity": 0.92
    },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

### 3. Fine-Tuning API
**POST /finetune/job**
- **Description:** Initiates fine-tuning in the background for a job.
- **Request Body:**
  ```json
  {
    "jobId": 123
  }
  ```
- **Example Response:**
  ```json
  {
    "data": { "job_id": 123, "status": "Queued" },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

**POST /finetune/job-with-model**
- **Description:** Starts fine-tuning with a specific model.
- **Request Body:**
  ```json
  {
    "jobId": 123,
    "model": "gpt-4"
  }
  ```

**GET /finetune/status/{jobId}**
- **Description:** Retrieves the fine-tuning status of a job.
- **Example Response:**
  ```json
  {
    "data": {
      "job_id": 123,
      "status": "Completed",
      "fine_tuned_model_id": "ft-gpt-4-xyz"
    },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

### 4. Job Logs API
**GET /logs/{jobId}**
- **Description:** Fetches job activity logs.
- **Example Response:**
  ```json
  {
    "data": {
      "job_id": 123,
      "logs": [
        { "event_type": "upload", "message": "File uploaded", "timestamp": "2024-02-28T10:00:00Z" }
      ]
    },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

### 5. Jobs API
**GET /jobs**
- **Description:** Returns a list of all jobs.
- **Example Response:**
  ```json
  {
    "data": [
      { "id": 123, "job_name": "Doc Processing", "status": "Completed" }
    ],
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

### 6. Upload API
**POST /upload**
- **Description:** Uploads files and creates a job.
- **Request Body (multipart/form-data):**
  - `job_name`: Name of the job.
  - `files[]`: Files to be uploaded.
- **Example Response:**
  ```json
  {
    "data": { "job_id": 123, "job_name": "New Upload", "file_count": 5 },
    "success": true,
    "errorMessage": "",
    "errors": []
  }
  ```

---

## Notes for Developers
- **Error Handling:** All errors return an `errorMessage` and an `errors` array.
- **Data Schema:** Response objects adhere to `pydantic` models in `app.schemas`.
- **Future Improvements:** Developers can extend authentication and add user roles to limit access.
- **Contribution:** Developers are encouraged to fork and contribute to EchoDoc.

For more details, visit the [project repository](https://github.com/aghimir3/EchoDoc).

