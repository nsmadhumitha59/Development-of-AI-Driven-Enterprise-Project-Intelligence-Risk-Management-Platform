import os
import shutil
import tempfile
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def test_client():
    """FastAPI TestClient fixture."""
    return TestClient(app)

@pytest.fixture
def temp_data_dir():
    """Creates temporary directory for test storage."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_data_dir():
    """Returns path to sample_data directory."""
    return Path(__file__).resolve().parent.parent / "sample_data"
