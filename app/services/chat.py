import os
import json
import faiss
import numpy as np
import logging
from fastapi import HTTPException
from sqlalchemy.orm import Session
from openai import OpenAI
from app.config import settings
from app.models.document import Document
from app.models.finetuned_model import FineTunedModel
from app.services.rag import RagService
from app.utils.blob_storage import download_from_blob_async

logger = logging.getLogger(__name__)

class ChatService:
    """
    Service for handling chat-related functionality.
    Supports different modes:
      - "rag": Use FAISS retrieval and default chat model.
      - "raft": Use FAISS retrieval and fine-tuned model.
      - "fine_tuned_only": Use the fine-tuned model directly.
    """
    def __init__(self, db: Session) -> None:
        self.db = db
        self.logger = logger
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def chat_by_job(self, job_id: int, message: str, mode: str = "rag") -> str:
        """
        Generate a chat response for a given job.
        """
        if mode == "fine_tuned_only":
            ft_model = (
                self.db.query(FineTunedModel)
                .filter(FineTunedModel.job_id == job_id)
                .order_by(FineTunedModel.id.desc())
                .first()
            )
            if not ft_model or not ft_model.openai_model_id:
                raise HTTPException(status_code=404, detail="Fine-tuned model not available for this job")
            response = self.client.chat.completions.create(
                model=ft_model.openai_model_id,
                messages=[{"role": "user", "content": message}]
            )
            return response.choices[0].message.content

        # Retrieve aggregated document context.
        agg_doc = (
            self.db.query(Document)
            .filter(Document.job_id == job_id, Document.is_aggregated == True)
            .first()
        )
        if not agg_doc or not agg_doc.chunks_blob_path:
            raise HTTPException(status_code=404, detail="Aggregated context not available for this job")

        try:
            local_chunks_path = await download_from_blob_async(agg_doc.chunks_blob_path, "artifacts")
            with open(local_chunks_path, "r", encoding="utf-8") as f:
                aggregated_chunks = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load aggregated chunks for job {job_id}: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to load aggregated context")

        if not aggregated_chunks:
            raise HTTPException(status_code=404, detail="No aggregated context available for this job")

        try:
            temp_index_path, _ = RagService.create_faiss_index(aggregated_chunks)
            index = faiss.read_index(temp_index_path)
            query_embedding = self.client.embeddings.create(
                model=settings.DEFAULT_EMBEDDING_MODEL, input=message
            ).data[0].embedding

            k = min(5, len(aggregated_chunks))
            distances, indices = index.search(np.array([query_embedding]), k=k)
            retrieved_chunks = [aggregated_chunks[i] for i in indices[0] if i < len(aggregated_chunks)]
            if not retrieved_chunks:
                raise HTTPException(status_code=404, detail="No relevant context found for your query")

            context = "\n".join(retrieved_chunks)
            prompt = (
                f"Based on the following context, answer the question:\n\n"
                f"Context:\n{context}\n\nQuestion: {message}"
            )

            # Determine the model to use.
            if mode == "raft":
                ft_model = (
                    self.db.query(FineTunedModel)
                    .filter(FineTunedModel.job_id == job_id)
                    .order_by(FineTunedModel.id.desc())
                    .first()
                )
                if not ft_model or not ft_model.openai_model_id:
                    raise HTTPException(status_code=404, detail="Fine-tuned model not available for this job")
                model_to_use = ft_model.openai_model_id
            else:
                model_to_use = settings.DEFAULT_CHAT_MODEL

            response = self.client.chat.completions.create(
                model=model_to_use,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        finally:
            if 'temp_index_path' in locals() and os.path.exists(temp_index_path):
                os.remove(temp_index_path)
