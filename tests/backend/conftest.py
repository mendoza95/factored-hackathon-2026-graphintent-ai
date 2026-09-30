# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.backend.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
