# EchoDoc

## 🚀 Introduction
EchoDoc is an **AI-powered document processing and job management dashboard** designed for developers and LLMOps professionals. It enables users to create **RAG (Retrieval-Augmented Generation) models**, **Fine-Tuned models**, and **RAFT (Retrieval-Augmented Fine-Tuning) models** with ease. Whether you are handling **fine-tuning jobs**, **managing document processing workflows**, or **interacting with AI models**, EchoDoc provides a streamlined experience with an intuitive API and real-time UI updates. **A model can be deployed instantly after uploading the relevant files, allowing for seamless integration and rapid iteration.**

## Features

### 📌 User Interface (UI)
- **🚀 Job Management**
  - View job details, including status, completion time, and file count.
  - Monitor fine-tuning progress and execute fine-tuning as needed.
  - Open job logs in a modal for debugging.

- **💂 File Upload System**
  - Upload multiple files under a specified job name.
  - Receive real-time status updates during the upload process.
  - Error messages for missing fields or failed uploads.

- **💬 Chat Interface**
  - Chat with AI models after job completion.
  - Supports different modes: **RAG**, **RAFT**, and **Fine-Tuned**.
  - Uses `marked.js` for Markdown rendering.

- **⚡ Real-Time UI Updates**
  - Job cards dynamically update based on API responses.
  - Displays spinners and status indicators for better UX.
  - Error messages are provided for API failures.

## 📊 Evaluation Metrics
EchoDoc includes a **robust evaluation framework** for assessing fine-tuned and retrieval-augmented models. The evaluation process includes:

- **Relevancy:** Measures how well the response aligns with the query.
- **Faithfulness:** Checks for hallucinations or inaccurate claims.
- **Completeness:** Ensures all necessary details are covered.
- **Clarity:** Evaluates how well-structured and understandable the response is.
- **Correctness:** Assesses factual accuracy.
- **Oracle Agreement:** Compares the response with a ground-truth reference.

This framework helps ensure high-quality AI outputs for **RAG, RAFT, and fine-tuned models**.

## 🔗 API Endpoints
The FastAPI backend provides the following RESTful API endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat/job/{jobId}` | POST | Sends user messages to AI models and retrieves responses |
| `/api/evaluate/job/{jobId}` | POST | Evaluates a fine-tuned model for a job |
| `/api/finetune/job` | POST | Initiates fine-tuning for a job |
| `/api/finetune/job-with-model` | POST | Fine-tunes a job using a specific model |
| `/api/finetune/status/{jobId}` | GET | Fetches the fine-tuning status of a job |
| `/api/logs/{jobId}` | GET | Retrieves logs for a given job |
| `/api/jobs` | GET | Fetches a list of document processing jobs |
| `/api/upload` | POST | Handles file uploads |

### Standardized API Response Format
All API responses follow the `APIResponse` model:
```python
class APIResponse(BaseModel):
    data: Optional[Any] = None
    errorMessage: Optional[str] = ""
    success: bool = True
    errors: List[str] = []
```
#### Sample JSON Response:
```json
{
  "data": { "jobId": 123, "status": "completed" },
  "errorMessage": "",
  "success": true,
  "errors": []
}
```

### 📃 Viewing API Documentation (Swagger UI)
FastAPI automatically generates interactive API documentation:
- Open **Swagger UI**:
  ```
  http://localhost:8000/docs
  ```
- Open **ReDoc**:
  ```
  http://localhost:8000/redoc
  ```

## 🤝 Setup Instructions

### **Prerequisites**
- Install [Python 3.x](https://www.python.org/downloads/)
- Ensure `pip` is installed
- Create an `.env` file with the following credentials:
  ```sh
  DATABASE_URL=mssql+pyodbc://<username>:<password>@<servername>.database.windows.net:1433/<dbname>>?driver=ODBC+Driver+17+for+SQL+Server&Encrypt=yes
  AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=<account_name>;AccountKey=<account_key>;EndpointSuffix=core.windows.net
  OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  DEFAULT_CHAT_MODEL=gpt-4o
  DEFAULT_EMBEDDING_MODEL=text-embedding-ada-002
  DEFAULT_FINETUNE_MODEL=gpt-4o-2024-08-06
  LOCAL_STORAGE_FOLDER=local_storage
  FAISS_SUBFOLDER=faiss
  ```

### **Running the Application**
To quickly start the application, use the provided scripts:

1. **Clone the repository**
   ```sh
   git clone https://github.com/aghimir3/EchoDoc.git
   cd EchoDoc
   ```
2. **Run the setup script**:
   
   **Windows:**
   ```sh
   run.bat
   ```
   
   **Mac/Linux:**
   ```sh
   chmod +x run.sh && ./run.sh
   ```
   Once you see **"Application startup complete"**, the server is running successfully.

### **Running with Docker**
You can run EchoDoc using Docker and `docker-compose`.

1. **Ensure Docker and Docker Compose are installed**
2. **Start the application using**:
   ```sh
   docker-compose up --build
   ```
3. **Access the application at**:
   ```sh
   http://localhost:8000
   ```

### **Performing a Hard Reset**
If you need a full environment reset or if you are running it for the first time:

**Windows:**
```sh
hard-reset.bat
```

**Mac/Linux:**
```sh
chmod +x hard-reset.sh && ./hard-reset.sh
```

## 🚀 Usage

### **Accessing the Dashboard**
Once the server is running, open:
```
http://localhost:8000
```

### **Working with Jobs**
1. **Uploading Files**
   - Navigate to the `Upload` tab.
   - Enter a `Job Name`.
   - Select and upload files.
   - Receive confirmation upon successful upload.

2. **Managing Jobs**
   - Switch to the `Jobs` tab.
   - View job details including status and fine-tune status.
   - Click `Run Finetune` to start fine-tuning.
   - View job logs for details.

3. **Chat with AI Models**
   - Click `Chat` on a completed job.
   - Select a chat mode (**RAG, RAFT, or Fine-Tuned**).
   - Enter a message and receive AI-generated responses.

## 🧪 Running Unit Tests
To run unit tests, use `pytest`:
```sh
pytest tests/test_api.py
```

### ⚠️ Important Note
Before running tests, ensure that your **database connection strings** and other environment variables are set for your **testing environment** to prevent unintended modifications to production or development databases.


## 🤝 Contribution Guidelines
We welcome contributions! Follow these steps:
1. **Fork** the repository.
2. **Create a new feature branch**: `git checkout -b feature-name`
3. **Commit changes**: `git commit -m "Your commit message"`
4. **Push to your branch**: `git push origin feature-name`
5. **Submit a pull request (PR)** for review.

---
**Maintainer:** [Abhigya Ghimire](https://github.com/aghimir3/)

**Project Repository:** [EchoDoc](https://github.com/aghimir3/EchoDoc)
