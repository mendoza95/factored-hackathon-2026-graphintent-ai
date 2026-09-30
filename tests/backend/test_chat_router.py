import pytest
from httpx import AsyncClient
from app.backend.main import app



@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_process_chat_endpoint(client: AsyncClient):
    payload = {
        "customer_id": "CUST_12345",
        "session_id": "SESS_98765",
        "message": "No reconozco un cargo de $150 USD en mi tarjeta.",
        "language": "es",
        "user_accent": "mexican",
    }

    response = await client.post("/api/v1/chat", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "response_message" in data
    assert "intent_detected" in data
    assert "optimization_metrics" in data
    assert "chromatic_number" in data["optimization_metrics"]