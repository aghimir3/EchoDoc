import os
import json
import faiss
import numpy as np
import logging
from fastapi import HTTPException
from app.config import settings
from app.utils.blob_storage import download_from_blob_async
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class RagService:
    """
    Service for performing Retrieval-Augmented Generation (RAG) queries.
    
    Provides methods to create a FAISS index from text chunks and execute RAG queries.
    """
    @staticmethod
    def create_faiss_index(chunks: list) -> tuple:
        """
        Create a FAISS index from text chunks.
        
        This method generates embeddings for each chunk using the OpenAI API,
        creates a FAISS index, writes it to a file in a local folder (as specified in settings),
        and returns a tuple containing the path to the FAISS index file and a JSON string of the chunks.
        
        :param chunks: List of text chunks.
        :return: Tuple (faiss_index_path, chunks_json)
        :raises ValueError: If creation fails.
        """
        if not chunks:
            logger.warning("No chunks provided to create FAISS index")
            return None, None
        try:
            logger.debug(f"Creating embeddings for {len(chunks)} chunks")
            embeddings = [
                client.embeddings.create(model=settings.DEFAULT_EMBEDDING_MODEL, input=chunk).data[0].embedding
                for chunk in chunks
            ]
            dimension = len(embeddings[0])
            index = faiss.IndexFlatL2(dimension)
            index.add(np.array(embeddings))
            # Construct folder path using local storage settings and FAISS subfolder.
            faiss_dir = os.path.join(settings.LOCAL_STORAGE_FOLDER, settings.FAISS_SUBFOLDER)
            os.makedirs(faiss_dir, exist_ok=True)
            faiss_index_path = os.path.join(faiss_dir, f"faiss_index_{id(index)}.bin")
            logger.debug(f"Writing FAISS index to {faiss_index_path}")
            faiss.write_index(index, faiss_index_path)
            chunks_json = json.dumps(chunks)
            logger.debug(f"Created FAISS index at {faiss_index_path}")
            return faiss_index_path, chunks_json
        except Exception as e:
            logger.error(f"Failed to create FAISS index: {str(e)}", exc_info=True)
            raise ValueError(f"Failed to create FAISS index: {str(e)}")

    @staticmethod
    async def rag_query(query: str, document_id: int, model_name: str, db) -> str:
        """
        Execute a RAG query using a specific document.

        This method downloads the FAISS index and the JSON chunks from blob storage,
        loads the index, computes the query embedding, retrieves the most relevant text chunks,
        constructs a context from them, and calls the OpenAI chat API to generate an answer.
        
        :param query: The user query.
        :param document_id: The ID of the document.
        :param model_name: The model name to use for generating the response.
        :param db: The database session.
        :return: The answer from the model.
        :raises HTTPException: If required data (index or chunks) is missing or no relevant chunks are found.
        """
        from fastapi import HTTPException
        from app.models.document import Document
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document or not document.faiss_index_blob_path or not document.chunks_blob_path:
            logger.error(f"RAG index or chunks not found for document {document_id}")
            raise HTTPException(status_code=404, detail="RAG index or chunks not found for this document")

        # Download FAISS index and chunks files asynchronously.
        faiss_index_path = await download_from_blob_async(document.faiss_index_blob_path, "artifacts")
        chunks_path = await download_from_blob_async(document.chunks_blob_path, "artifacts")
        
        # Load FAISS index.
        index = faiss.read_index(faiss_index_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)

        # Compute the query embedding.
        query_embedding = client.embeddings.create(model=settings.DEFAULT_EMBEDDING_MODEL, input=query).data[0].embedding
        
        # Search for the most relevant chunks.
        distances, indices = index.search(np.array([query_embedding]), k=min(5, len(chunks)))
        retrieved_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
        if not retrieved_chunks:
            logger.warning(f"No relevant chunks found for query on document {document_id}")
            raise HTTPException(status_code=404, detail="No relevant chunks found")
        
        # Build context and construct prompt.
        context = "\n".join(retrieved_chunks)
        prompt = f"Based on the following context, answer the question:\n\nContext:\n{context}\n\nQuestion: {query}"
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @staticmethod
    async def rag_query_by_job(query: str, job_id: int, model_name: str, db) -> str:
        """
        Execute a RAG query using the aggregated document for a job.

        This method downloads the aggregated FAISS index and JSON chunks,
        loads the index, computes the query embedding, retrieves the relevant chunks,
        constructs the context, and generates an answer using the OpenAI chat API.
        
        :param query: The user query.
        :param job_id: The job ID.
        :param model_name: The model name to use for generating the response.
        :param db: The database session.
        :return: The answer from the model.
        :raises HTTPException: If aggregated data is missing or no relevant chunks are found.
        """
        from fastapi import HTTPException
        from app.models.document import Document
        document = db.query(Document).filter(
            Document.job_id == job_id,
            Document.is_aggregated == True
        ).first()
        if not document or not document.faiss_index_blob_path or not document.chunks_blob_path:
            logger.error(f"Aggregated RAG index or chunks not found for job {job_id}")
            raise HTTPException(status_code=404, detail="Aggregated RAG index or chunks not found for this job")
        
        faiss_index_path = await download_from_blob_async(document.faiss_index_blob_path, "artifacts")
        chunks_path = await download_from_blob_async(document.chunks_blob_path, "artifacts")
        
        index = faiss.read_index(faiss_index_path)
        with open(chunks_path, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        
        query_embedding = client.embeddings.create(model=settings.DEFAULT_EMBEDDING_MODEL, input=query).data[0].embedding
        distances, indices = index.search(np.array([query_embedding]), k=min(5, len(chunks)))
        retrieved_chunks = [chunks[i] for i in indices[0] if i < len(chunks)]
        if not retrieved_chunks:
            logger.warning(f"No relevant chunks found for query on job {job_id}")
            raise HTTPException(status_code=404, detail="No relevant chunks found for your query")
        
        context = "\n".join(retrieved_chunks)
        prompt = f"Based on the following context, answer the question:\n\nContext:\n{context}\n\nQuestion: {query}"
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
