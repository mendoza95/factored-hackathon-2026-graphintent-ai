import pytest
from httpx import AsyncClient

from app.backend.core.security import create_access_token
from app.backend.schemas.chat import IntentEnum


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_chat_high_confidence_dispute_flow(client: AsyncClient):
    """Test high-confidence dispute message triggering fast-path graph execution."""
    token = create_access_token(data={"sub": "CUST_12345"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "session_id": "SESS_HIGH_CONF_1",
        "message": "No reconozco un cargo de $150 USD en mi tarjeta de crédito.",
        "language": "es",
        "user_accent": "mexican",
    }

    response = await client.post("/api/v1/chat", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    # assert data["intent_detected"] == IntentEnum.DISPUTE_INITIATE
    assert "response_message" in data
    assert data["optimization_metrics"]["graph_nodes_count"] > 0


@pytest.mark.asyncio
async def test_chat_low_confidence_fallback_flow(client: AsyncClient):
    """Test low-confidence greeting message triggering LLM fallback path."""
    token = create_access_token(data={"sub": "CUST_12345"})
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "session_id": "SESS_LOW_CONF_1",
        "message": "Hola buenas tardes",
        "language": "es",
        "user_accent": "mexican",
    }

    response = await client.post("/api/v1/chat", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "response_message" in data
    assert data["intent_detected"] != IntentEnum.DISPUTE_INITIATE.value
