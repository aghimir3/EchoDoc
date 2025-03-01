import os
import logging
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob.aio import BlobServiceClient
from app.config import settings

logger = logging.getLogger(__name__)

# Create a global async client instance.
blob_service_client_async = (
    BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
    if settings.AZURE_STORAGE_CONNECTION_STRING else None
)

async def _ensure_container_exists_async(container: str):
    """Ensure the specified container exists in Azure Blob Storage asynchronously."""
    if not container:
        logger.error("Container name is empty")
        raise ValueError("Container name cannot be empty")
    if blob_service_client_async:
        container_client = blob_service_client_async.get_container_client(container)
        try:
            await container_client.get_container_properties()
            logger.debug(f"Container {container} already exists")
        except ResourceNotFoundError:
            await container_client.create_container()
            logger.info(f"Created container: {container}")
        except Exception as e:
            logger.error(f"Failed to ensure container {container} exists: {str(e)}", exc_info=True)
            raise

async def upload_to_blob_async(data, blob_name: str, container: str = "artifacts") -> str:
    """
    Asynchronously upload data to Azure Blob Storage or, if no connection string is provided, to local storage.
    
    :param data: The data to be uploaded (string or file-like object).
    :param blob_name: The target blob name.
    :param container: The container name (default "artifacts").
    :return: The blob path (e.g., "artifacts/blob_name") or local file path.
    """
    try:
        if not blob_name:
            logger.error("Blob name is empty")
            raise ValueError("Blob name cannot be empty")
        if not container:
            logger.error("Container name is empty")
            raise ValueError("Container name cannot be empty")
        if not data:
            logger.error("Data is empty or None")
            raise ValueError("Data cannot be empty or None")

        logger.debug(f"Uploading to {container}/{blob_name} with data type: {type(data)}")

        if blob_service_client_async:
            await _ensure_container_exists_async(container)
            blob_client = blob_service_client_async.get_blob_client(container=container, blob=blob_name)
            # Upload based on type.
            if isinstance(data, str):
                await blob_client.upload_blob(data, overwrite=True)
            elif hasattr(data, "read"):
                if hasattr(data, "seek"):
                    data.seek(0)
                # Read entire content as bytes.
                content = data.read()
                await blob_client.upload_blob(content, overwrite=True)
            else:
                await blob_client.upload_blob(data, overwrite=True)
            logger.debug(f"Uploaded to Azure: {container}/{blob_name}")
            return f"{container}/{blob_name}"
        else:
            # Fallback to local storage if no connection string is provided.
            local_path = os.path.join(settings.LOCAL_STORAGE_FOLDER, blob_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            if isinstance(data, str):
                with open(local_path, "w", encoding="utf-8") as f:
                    f.write(data)
            elif hasattr(data, "read"):
                if hasattr(data, "seek"):
                    data.seek(0)
                with open(local_path, "wb") as f:
                    f.write(data.read())
            else:
                with open(local_path, "wb") as f:
                    f.write(data)
            logger.debug(f"Saved to local storage: {local_path}")
            return local_path
    except Exception as e:
        logger.error(f"Failed to upload to blob {blob_name} in container {container}: {str(e)}", exc_info=True)
        raise

async def download_from_blob_async(blob_path: str, container: str = "artifacts") -> str:
    """
    Asynchronously download a blob from Azure Blob Storage or local storage.
    
    :param blob_path: The blob path.
    :param container: The container name (default "artifacts").
    :return: Local file path where the blob is saved.
    """
    try:
        if not blob_path:
            logger.error("Blob path is empty")
            raise ValueError("Blob path cannot be empty")
        if not container:
            logger.error("Container name is empty")
            raise ValueError("Container name cannot be empty")

        # Remove container prefix if present.
        blob_name = blob_path
        if blob_path.startswith(f"{container}/"):
            blob_name = blob_path[len(f"{container}/"):]
        logger.debug(f"Downloading blob: {blob_name} from container: {container}")

        if not blob_name:
            logger.error(f"Blob name extracted from {blob_path} is empty")
            raise ValueError("Blob name cannot be empty after extraction")

        if blob_service_client_async:
            blob_client = blob_service_client_async.get_blob_client(container=container, blob=blob_name)
            local_file_path = os.path.join(settings.LOCAL_STORAGE_FOLDER, os.path.basename(blob_name))
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            stream = await blob_client.download_blob()
            data = await stream.readall()
            with open(local_file_path, "wb") as f:
                f.write(data)
            logger.debug(f"Downloaded from Azure to: {local_file_path}")
            return local_file_path
        else:
            # Fallback: return local file if it exists.
            local_path = blob_path
            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")
            logger.debug(f"Downloaded from local storage: {local_path}")
            return local_path
    except Exception as e:
        logger.error(f"Failed to download blob {blob_path} from container {container}: {str(e)}", exc_info=True)
        raise
