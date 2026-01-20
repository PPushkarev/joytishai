
from dotenv import load_dotenv
import sys
import httpx
import pytest
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app

import pytest
from unittest.mock import MagicMock, patch
from app.services.vector_store import VectorStoreManager


load_dotenv()
# FiXTUTE FOR LOCAL REAL SERVER TESTING
@pytest.fixture
async def network_client():
    async with httpx.AsyncClient(timeout=60.0) as client:
        yield client

    await asyncio.sleep(0.1)


# FiXTUTE FOR LOCAL CODE TESTING
@pytest.fixture
async def local_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

# 1. FIX for Windows ( RuntimeError: Event loop is closed)
@pytest.fixture(scope="session")
def event_loop():

    if sys.platform == 'win32':
        loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
    else:
        loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# FiXTUTE FOR RAG TESTING TO USING MOCK AI BASE
@pytest.fixture
def mock_embeddings():
    """Mock OpenAI Embeddings to avoid API calls."""
    with patch("app.services.vector_store.OpenAIEmbeddings") as mocked:
        yield mocked.return_value

# FiXTUTE FOR TESTING RAG BASE WITH MOCK DB
@pytest.fixture
def vsm(mock_embeddings):
    """Initialize VectorStoreManager with mocked embeddings."""
    # We patch os.makedirs to prevent creating real folders during tests
    with patch("os.makedirs"):
        manager = VectorStoreManager()
        return manager