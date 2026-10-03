from app.backend.schemas.chat import IntentEnum
from app.backend.services.llm_service import llm_service


def test_classify_and_extract_llm_default():
    """
    Verify default stub returns UNSUPPORTED intent and
    safe fallback confidence without client.
    """
    message = "No reconozco un cargo de $150 USD en mi tarjeta"
    result = llm_service.classify_and_extract_llm(message)

    assert result["intent"] == IntentEnum.UNSUPPORTED
    assert result["confidence"] == 0.50
    assert result["claimed_amount"] is None
    assert result["currency"] is None


def test_generate_response_dialect_adaptation():
    """Verify response greetings adapt to regional Spanish accents."""
    intent = IntentEnum.DISPUTE_INITIATE

    res_mx = llm_service.generate_response(intent, user_accent="mexican")
    res_ar = llm_service.generate_response(intent, user_accent="argentine")
    res_co = llm_service.generate_response(intent, user_accent="colombian")

    assert "Hola" in res_mx
    assert "Hola, ¿cómo estás?" in res_ar
    assert "Hola, con gusto le ayudo" in res_co


def test_process_fallback_execution():
    """
    Verify process_fallback processes payload and
    returns expected response schema.
    """
    event_payload = {
        "full_text": "Tengo una consulta sobre un movimiento",
        "channel": "chat",
    }

    res = llm_service.process_fallback(event_payload, user_accent="colombian")

    assert res["source"] == "LLM_FALLBACK"
    assert res["routing_action"] == "EXECUTE_ACTION"
    assert res["action"] == "COLLECT_MORE_INFO"
    assert res["confidence"] == 0.50
    assert "latency_ms" in res
    assert res["response_message"] is not None
    assert res["extracted_entities"]["claimed_amount"] is None
