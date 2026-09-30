import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    payload = {"document_type": "CC", "document_number": "1098765432"}
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    payload = {"document_type": "CC", "document_number": "0000000000"}
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_chat_flow(client: AsyncClient):
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"document_type": "CC", "document_number": "1098765432"},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"

    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    chat_payload = {
        "session_id": "SESS_TEST_123",
        "message": "No reconozco un cargo de $150 USD en mi tarjeta.",
        "language": "es",
    }

    response = await client.post("/api/v1/chat", json=chat_payload, headers=headers)
    assert response.status_code == 200
