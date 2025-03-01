from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    AZURE_STORAGE_CONNECTION_STRING: str
    OPENAI_API_KEY: str

    DEFAULT_CHAT_MODEL: str = "gpt-4o"
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-ada-002"
    DEFAULT_FINETUNE_MODEL: str = "gpt-4o-2024-08-06"

    LOCAL_STORAGE_FOLDER: str = "local_storage"
    FAISS_SUBFOLDER: str = "faiss"

    model_config = ConfigDict(env_file=".env")

settings = Settings()
