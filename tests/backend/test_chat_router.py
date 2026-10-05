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
        "message": (
            "Quiero poner una queja formal por un reclamo de cobro duplicado "
            "y no reconozco un cargo no autorizado "
            "de $150 USD en mi tarjeta de crédito."
        ),
        "detected_keywords": "queja, reclamo, cobro duplicado, cargo no autorizado",
        "detected_intents": "dispute_initiate",
        "main_topics": "transacción",
        "channel": "chat",
        "detected_sentiment": "negative",
        "duration_seconds": 200.0,
        "sentiment_score": -0.8,
        "has_past_complaint": True,
        "language": "es",
        "user_accent": "mexican",
    }

    response = await client.post("/api/v1/chat", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()

    # Al pasar los campos requeridos, el predictor superará el 0.65 de confianza
    assert data["intent_detected"] == "dispute_initiate"


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
    assert data["intent_detected"] != IntentEnum.DISPUTE_INITIATE
