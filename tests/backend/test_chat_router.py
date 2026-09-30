import pytest
from httpx import AsyncClient

from app.backend.core.security import create_access_token


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_process_chat_endpoint(client: AsyncClient):
    # Generate mock JWT token for testing the route
    token = create_access_token(data={"sub": "CUST_12345"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "session_id": "SESS_TEST_123",
        "message": "No reconozco un cargo de $150 USD en mi tarjeta.",
        "language": "es",
    }

    response = await client.post("/api/v1/chat", json=payload, headers=headers)
    assert response.status_code == 200
