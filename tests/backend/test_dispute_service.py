from unittest.mock import AsyncMock, patch

import pytest

from app.backend.schemas.chat import ChatRequest, IntentEnum
from app.backend.services.dispute_service import dispute_service


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.llm_service")
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_dispute_fallback_to_llm_when_no_entities(
    mock_orchestrator, mock_llm_service
):
    """
    Verifica que si el orquestador no extrae entidades,
    se ejecute await sobre classify_and_extract_llm correctamente.
    """
    # 1. Simular que el orquestador no entrega entidades
    mock_orchestrator.return_value = {
        "action": "COLLECT_MORE_INFO",
        "response_message": "¿Cuál es el monto de la transacción?",
        "latency_ms": 3.0,
        "extracted_entities": None,
    }

    # 2. Configurar el mock del servicio LLM como un AsyncMock explícito
    mock_llm_service.classify_and_extract_llm = AsyncMock(
        return_value={"claimed_amount": 80.00, "currency": "USD"}
    )

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_5050",
        message="Creo que me cobraron de más en la tienda.",
        user_accent="mexican",
    )

    response = await dispute_service.process_chat_message(request)

    # 3. Aserciones del flujo y verificación del call asíncrono
    mock_llm_service.classify_and_extract_llm.assert_awaited_once_with(request.message)
    assert response.intent_detected == IntentEnum.UNSUPPORTED
    assert response.requires_human_handoff is False


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.llm_service")
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_dispute_fallback_high_amount_extracted_by_llm(
    mock_orchestrator, mock_llm_service
):
    """
    Verifica que las entidades extraídas por el LLM en el fallback
    activen los guardrails de monto alto (> $1,000 USD).
    """
    mock_orchestrator.return_value = {
        "action": "INITIATE_DISPUTE_WORKFLOW",
        "response_message": "Analizando la transacción...",
        "latency_ms": 4.0,
        "extracted_entities": {},
    }

    mock_llm_service.classify_and_extract_llm = AsyncMock(
        return_value={"claimed_amount": 1500.00, "currency": "USD"}
    )

    # FIX: Asignar un string como valor de retorno para generate_response
    mock_llm_service.generate_response.return_value = (
        "Tu solicitud supera el límite permitido y requiere revisión manual."
    )

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_6060",
        message="Tengo un cobro raro de mil quinientos dólares.",
        user_accent="mexican",
    )

    response = await dispute_service.process_chat_message(request)

    assert response.requires_human_handoff is True
    assert isinstance(response.response_message, str)


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_dispute_workflow_standard_amount(mock_orchestrator):
    """
    Verify standard dispute workflow under $1,000 creates record
    without human handoff.
    """
    mock_orchestrator.return_value = {
        "action": "INITIATE_DISPUTE_WORKFLOW",
        "response_message": "He registrado tu solicitud para iniciar "
        "la disputa del cargo.",
        "latency_ms": 4.5,
        "extracted_entities": {"claimed_amount": 150.00, "currency": "USD"},
    }

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_1010",
        message="No reconozco un cargo de $150 USD en mi tarjeta.",
        user_accent="mexican",
    )

    response = await dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.DISPUTE_INITIATE
    assert response.requires_human_handoff is False
    assert response.dispute_id is not None
    assert response.dispute_id.startswith("COMP_")
    assert response.optimization_metrics.graph_nodes_count == 5


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_dispute_workflow_high_amount_guardrail(mock_orchestrator):
    """
    Verify high-value claims (> $1,000 USD) trigger
    human handoff guardrail.
    """
    mock_orchestrator.return_value = {
        "action": "INITIATE_DISPUTE_WORKFLOW",
        "response_message": "He registrado tu solicitud para "
        "iniciar la disputa del cargo.",
        "latency_ms": 5.0,
        "extracted_entities": {"claimed_amount": 2500.00, "currency": "USD"},
    }

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_2020",
        message="Quiero reportar un cargo no reconocido de $2500 USD.",
        user_accent="colombian",
    )

    response = await dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.DISPUTE_INITIATE
    assert response.requires_human_handoff is True
    assert response.handoff_details.is_escalated is True
    assert "exceeds automated threshold" in response.handoff_details.reason


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_escalate_to_human_action(mock_orchestrator):
    """Verify ESCALATE_TO_HUMAN action sets human handoff flag and details."""
    mock_orchestrator.return_value = {
        "action": "ESCALATE_TO_HUMAN",
        "response_message": "Estoy transfiriendo tu caso con un especialista.",
        "latency_ms": 3.2,
        "extracted_entities": {"claimed_amount": None, "currency": None},
    }

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_3030",
        message="Necesito hablar con un agente humano ahora mismo.",
        user_accent="argentine",
    )

    response = await dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.HUMAN_HANDOFF
    assert response.requires_human_handoff is True
    assert (
        response.handoff_details.reason
        == "User explicitly requested a human specialist"
    )


@pytest.mark.asyncio
@patch("app.backend.services.dispute_service.process_interaction_event")
async def test_execute_account_inquiry_action(mock_orchestrator):
    """
    Verify account inquiry action computes valid graph schedule
    without creating dispute records.
    """
    mock_orchestrator.return_value = {
        "action": "EXECUTE_ACCOUNT_INQUIRY",
        "response_message": "Puedes consultar tu saldo desde la app.",
        "latency_ms": 2.8,
        "extracted_entities": {"claimed_amount": None, "currency": None},
    }

    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_4040",
        message="¿Cuál es el saldo de mi tarjeta?",
        user_accent="mexican",
    )

    response = await dispute_service.process_chat_message(request)

    assert response.intent_detected == IntentEnum.ACCOUNT_INQUIRY
    assert response.requires_human_handoff is False
    assert response.dispute_id is None
    assert response.optimization_metrics.graph_nodes_count == 3
