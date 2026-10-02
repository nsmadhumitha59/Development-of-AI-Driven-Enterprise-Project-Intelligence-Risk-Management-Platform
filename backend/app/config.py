import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
CHROMA_DB_DIR = DATA_DIR / "chroma_db"
METADATA_STORE_PATH = DATA_DIR / "metadata_store.json"

# Ensure runtime directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DB_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "AI Project Intelligence & Risk Advisor"
    VERSION: str = "1.0.0 (Milestone 1)"
    
    # RAG Settings
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    
    # Paths
    UPLOAD_DIR: str = str(UPLOAD_DIR)
    CHROMA_DB_DIR: str = str(CHROMA_DB_DIR)
    METADATA_STORE_PATH: str = str(METADATA_STORE_PATH)

settings = Settings()
