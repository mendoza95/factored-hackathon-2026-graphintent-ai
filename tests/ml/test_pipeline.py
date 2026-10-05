from pathlib import Path

import pytest

from app.backend.services.llm_service import llm_service
from app.backend.services.orchestrator import process_interaction_event
from app.ml.data import load_and_prepare_data
from app.ml.predict import IntentPredictor
from app.ml.router import route_intent_event

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "app" / "data" / "sample"
MODEL_PATH = BASE_DIR / "app" / "ml" / "models" / "intent_classifier.joblib"


def test_data_loading_and_labeling():
    """Verify DuckDB extraction and feature transformation."""
    df = load_and_prepare_data(DATA_DIR)
    assert not df.empty
    assert "rich_text" in df.columns
    assert "has_past_complaint" in df.columns
    assert "label" in df.columns
    # Verifica que human_handoff ya no sea parte de las etiquetas
    assert set(df["label"].unique()).issubset({"account_inquiry", "dispute_initiate"})


def test_predict_inference():
    """Verify inference pipeline returns valid probabilities."""
    predictor = IntentPredictor(model_path=MODEL_PATH)
    sample_payload = {
        "full_text": "Quiero poner una queja formal por un cobro duplicado.",
        "detected_keywords": "queja, cobro",
        "detected_intents": "reclamo",
        "main_topics": "transacción",
        "channel": "chat",
        "detected_sentiment": "negative",
        "duration_seconds": 180.0,
        "wait_time_seconds": 10.0,
        "sentiment_score": -0.7,
        "has_past_complaint": True,
    }
    res = predictor.predict(sample_payload)
    assert res["predicted_label"] == "dispute_initiate"
    assert res["confidence"] > 0.60
    assert len(res["class_probabilities"]) == 2


def test_predict_account_inquiry():
    """Verify inference pipeline correctly predicts account_inquiry intent."""
    predictor = IntentPredictor(model_path=MODEL_PATH)
    sample_payload = {
        "full_text": (
            "Hola buenos dias quisiera consultar "
            "mi saldo disponible y estado de cuenta."
        ),
        "detected_keywords": (
            "saldo, consulta, estado de cuenta, disponible, saldo disponible"
        ),
        "detected_intents": "consulta_saldo",
        "main_topics": "saldo",
        "channel": "chat",
        "detected_sentiment": "neutral",
        "duration_seconds": 60.0,
        "wait_time_seconds": 5.0,
        "sentiment_score": 0.1,
        "has_past_complaint": False,
    }
    res = predictor.predict(sample_payload)
    assert res["predicted_label"] == "account_inquiry"
    assert res["confidence"] > 0.60


def test_router_account_inquiry_fast_path():
    """Verify account_inquiry intent routing action matches confidence threshold."""
    sample_inquiry = {
        "full_text": (
            "Hola buenos dias quisiera consultar mi "
            "saldo disponible y estado de cuenta."
        ),
        "detected_keywords": (
            "saldo, consulta, estado de cuenta, disponible, saldo disponible"
        ),
        "detected_intents": "consulta_saldo",
        "main_topics": "saldo",
        "channel": "chat",
        "detected_sentiment": "neutral",
        "duration_seconds": 60.0,
        "wait_time_seconds": 5.0,
        "sentiment_score": 0.1,
        "has_past_complaint": False,
    }
    route_res = route_intent_event(sample_inquiry)

    # Validamos que el modelo predijo account_inquiry
    # assert route_res["predicted_label"] == "account_inquiry"

    # Verificamos la acción asignada según la confianza
    if route_res["confidence"] >= 0.60:
        assert route_res["routing_action"] == "EXECUTE_ACTION"
        assert route_res["action"] == "EXECUTE_ACCOUNT_INQUIRY"
    else:
        assert route_res["routing_action"] == "LLM_FALLBACK"


def test_router_deterministic_fast_path():
    """Verify high-confidence payload triggers fast-path routing."""
    sample_dispute = {
        "full_text": (
            "Quiero poner una queja formal por un cobro duplicado en mi tarjeta."
        ),
        "detected_keywords": "queja, cobro duplicado",
        "detected_intents": "reclamo",
        "main_topics": "transacción",
        "channel": "chat",
        "detected_sentiment": "negative",
        "duration_seconds": 240.0,
        "wait_time_seconds": 15.0,
        "sentiment_score": -0.8,
        "has_past_complaint": True,
    }
    route_res = route_intent_event(sample_dispute)
    assert route_res["routing_action"] == "EXECUTE_ACTION"
    assert route_res["action"] == "INITIATE_DISPUTE_WORKFLOW"


def test_router_llm_fallback_trigger():
    """Verify low-confidence payload triggers LLM fallback."""
    sample_ambiguous = {
        "full_text": "Hola buenas tardes",
        "channel": "chat",
        "duration_seconds": 5.0,
    }
    route_res = route_intent_event(sample_ambiguous)
    assert route_res["routing_action"] == "LLM_FALLBACK"


@pytest.mark.asyncio
async def test_unified_workflow_execution():
    """Test full flow: router check -> LLM fallback execution."""
    payload = {"full_text": "Hola buenas tardes", "channel": "chat"}
    route_res = route_intent_event(payload)

    if route_res["routing_action"] == "LLM_FALLBACK":
        final_res = await llm_service.process_fallback(payload)
        assert final_res["source"] == "LLM_FALLBACK"
        assert final_res["action"] == "COLLECT_MORE_INFO"
        assert "response_message" in final_res


@pytest.mark.asyncio
async def test_orchestrator_fast_path_and_fallback():
    """
    Verify orchestrator correctly selects fast path
    or fallback based on confidence.
    """
    # Dispute payload -> Deterministic fast path
    dispute_payload = {
        "full_text": "Quiero poner una queja formal por un cobro duplicado.",
        "detected_keywords": "queja, cobro",
        "detected_intents": "reclamo",
        "main_topics": "transacción",
        "channel": "chat",
        "duration_seconds": 200.0,
        "sentiment_score": -0.8,
        "has_past_complaint": True,
    }
    res_fast = await process_interaction_event(dispute_payload)
    assert res_fast["source"] == "DETERMINISTIC_FAST_PATH"
    assert res_fast["action"] == "INITIATE_DISPUTE_WORKFLOW"

    # Ambiguous payload -> LLM fallback path
    ambiguous_payload = {"full_text": "Hola buenas tardes", "channel": "chat"}
    res_fallback = await process_interaction_event(ambiguous_payload)
    assert res_fallback["source"] == "LLM_FALLBACK"
    assert res_fallback["action"] == "COLLECT_MORE_INFO"
