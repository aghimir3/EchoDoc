from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers import upload, finetune, chat, evaluate, jobs, job_logs
from app.db import create_tables
from sqlalchemy.exc import SQLAlchemyError
from openai import OpenAIError
import logging
from fastapi.staticfiles import StaticFiles
import contextlib

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application")
    create_tables()
    yield
    logger.info("Shutting down application")

app = FastAPI(title="EchoDoc API", lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "An unexpected error occurred",
            "details": str(exc)
        }
    )

@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "message": "Database error occurred",
            "details": str(exc)
        }
    )

@app.exception_handler(OpenAIError)
async def openai_exception_handler(request: Request, exc: OpenAIError):
    logger.error(f"OpenAI error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=503,
        content={
            "status": "error",
            "message": "OpenAI service error",
            "details": str(exc)
        }
    )

app.include_router(upload.router, prefix="/api")
app.include_router(finetune.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(job_logs.router, prefix="/api")

app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
