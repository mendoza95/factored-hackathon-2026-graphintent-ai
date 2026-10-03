# tests/conftest.py
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.backend.core.security import create_access_token
from app.backend.main import app


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
def auth_headers():
    """Shared fixture for generating Authorization headers across test files."""
    token = create_access_token(data={"sub": "CUST_12345"})
    return {"Authorization": f"Bearer {token}"}
