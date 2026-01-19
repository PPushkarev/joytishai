import pytest
import httpx
import os
from dotenv import load_dotenv
import asyncio
import pytest
import sys
import httpx


load_dotenv()

@pytest.fixture(scope="session")
async def api_client():

    """Make Http client fixture."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client



# 1. FIX для Windows ( RuntimeError: Event loop is closed)
@pytest.fixture(scope="session")
def event_loop():

    if sys.platform == 'win32':
        loop = asyncio.WindowsSelectorEventLoopPolicy().new_event_loop()
    else:
        loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()