"""
Configuration settings for AI Project Intelligence & Risk Advisor (Milestone 1).
"""
import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # App Information
    APP_NAME: str = "AI Project Intelligence & Risk Advisor"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server configuration
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOADS_DIR: Path = BASE_DIR / "data" / "uploads"
    PROCESSED_DIR: Path = BASE_DIR / "data" / "processed"
    VECTOR_DB_DIR: Path = BASE_DIR / "data" / "vectorstore"
    DOCUMENTS_REGISTRY_FILE: Path = BASE_DIR / "data" / "documents_registry.json"
    
    # Supported File Formats & Limits
    ALLOWED_EXTENSIONS: set = {".pdf", ".docx", ".csv", ".txt"}
    MAX_FILE_SIZE_MB: int = 50
    
    # RAG & Chunking Parameters
    CHUNK_SIZE: int = 500  # Target characters per chunk
    CHUNK_OVERLAP: int = 100  # Character overlap between adjacent chunks
    MIN_CHUNK_LENGTH: int = 30  # Filter out noise / empty chunks
    
    # Embedding Configuration
    # Using a fast, high quality sentence-transformers model
    EMBEDDING_MODEL_NAME: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384
    EMBEDDING_DEVICE: str = "cpu"  # 'cpu', 'cuda', etc.
    EMBEDDING_BATCH_SIZE: int = 32
    
    # Vector Database Configuration
    VECTOR_COLLECTION_NAME: str = "project_intelligence_docs"
    DISTANCE_METRIC: str = "cosine"  # 'cosine', 'l2', 'ip'
    
    # Retrieval Settings
    DEFAULT_TOP_K: int = 5
    SCORE_THRESHOLD: float = 0.0  # Minimum similarity score
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Global settings singleton
settings = Settings()

# Ensure directories exist
for path in [settings.DATA_DIR, settings.UPLOADS_DIR, settings.PROCESSED_DIR, settings.VECTOR_DB_DIR]:
    path.mkdir(parents=True, exist_ok=True)
