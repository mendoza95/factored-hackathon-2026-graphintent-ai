from app.backend.schemas.chat import IntentEnum
from app.backend.services.llm_service import llm_service


def test_classify_intent_dispute():
    """Verify dispute intent classification for common Spanish phrasing."""
    message = "No reconozco un cargo de $150 USD en mi tarjeta"
    intent = llm_service.classify_intent(message)
    assert intent == IntentEnum.DISPUTE_INITIATE


def test_classify_intent_human_handoff():
    """Verify handoff intent classification when user asks for a human agent."""
    message = "Quiero hablar con un agente humano o supervisor"
    intent = llm_service.classify_intent(message)
    assert intent == IntentEnum.HUMAN_HANDOFF


def test_classify_intent_account_inquiry():
    """Verify account balance/movements query intent."""
    message = "¿Cuál es el saldo de mi tarjeta de crédito?"
    intent = llm_service.classify_intent(message)
    assert intent == IntentEnum.ACCOUNT_INQUIRY


def test_extract_entities_amount_and_currency():
    """Verify extraction of monetary amounts and explicit currency codes."""
    message = "Tengo un cobro indebido de $2500.50 MXN en mi estado de cuenta"
    entities = llm_service.extract_entities(message)

    assert entities["claimed_amount"] == 2500.50
    assert entities["currency"] == "MXN"


def test_extract_entities_default_usd_currency():
    """
    Verify currency defaults to USD when dollar sign is present
    without explicit text currency.
    """
    message = "No hice esta compra por $150.00"
    entities = llm_service.extract_entities(message)

    assert entities["claimed_amount"] == 150.00
    assert entities["currency"] == "USD"


def test_generate_response_dialect_adaptation():
    """
    Verify response greetings adapt to regional Spanish accents
    (Mexican, Argentine, Colombian).
    """
    intent = IntentEnum.DISPUTE_INITIATE

    res_mx = llm_service.generate_response(intent, user_accent="mexican")
    res_ar = llm_service.generate_response(intent, user_accent="argentine")
    res_co = llm_service.generate_response(intent, user_accent="colombian")

    assert "Hola." in res_mx or "Hola" in res_mx
    assert "Hola, ¿cómo estás?" in res_ar
    assert "Hola, con gusto le ayudo" in res_co
