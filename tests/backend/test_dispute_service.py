from app.backend.schemas.chat import ChatRequest, IntentEnum
from app.backend.services.dispute_service import dispute_service


def test_dispute_orchestration_low_amount():
    """Verify standard dispute processing under $1,000 without human handoff."""
    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_1010",
        message="No reconozco un cargo de $150 USD en mi tarjeta.",
        user_accent="mexican",
    )

    response = dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.DISPUTE_INITIATE
    assert response.dispute_id is not None
    assert response.requires_human_handoff is False
    assert response.optimization_metrics.graph_nodes_count > 0
    assert response.optimization_metrics.chromatic_number > 0


def test_dispute_orchestration_guardrail_escalation():
    """Verify high dollar claim (> $1,000 USD) triggers human handoff guardrail."""
    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_2020",
        message="Quiero reportar un cargo no reconocido de $2500 USD.",
        user_accent="colombian",
    )

    response = dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.DISPUTE_INITIATE
    assert response.requires_human_handoff is True
    assert response.handoff_details is not None
    assert response.handoff_details.is_escalated is True
    assert "exceeds automated approval threshold" in response.handoff_details.reason


def test_human_handoff_explicit_request():
    """Verify explicit human agent request triggers handoff flag directly."""
    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_3030",
        message="Necesito hablar con un agente humano ahora mismo.",
        user_accent="argentine",
    )

    response = dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.HUMAN_HANDOFF
    assert response.requires_human_handoff is True
    assert response.handoff_details.is_escalated is True
