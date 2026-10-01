import time
from pathlib import Path
from typing import Any, Dict

from app.ml.predict import IntentPredictor

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "ml" / "models" / "intent_classifier.joblib"

# Initialize predictor globally for fast cold-starts
predictor = IntentPredictor(model_path=MODEL_PATH)

CONFIDENCE_THRESHOLD = 0.65

# Operational action mapping
INTENT_TO_ACTION = {
    "dispute_initiate": "INITIATE_DISPUTE_WORKFLOW",
    "human_handoff": "ESCALATE_TO_HUMAN",
    "account_inquiry": "EXECUTE_ACCOUNT_INQUIRY",
}


def route_intent_event(event_payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Route interaction event using deterministic
    fast-path or flag for LLM fallback.
    """
    start_time = time.perf_counter()

    prediction = predictor.predict(event_payload)
    predicted_intent = prediction["predicted_intent"]
    confidence = prediction["confidence"]
    latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

    # Low-confidence fallback path
    if confidence < CONFIDENCE_THRESHOLD:
        return {
            "source": "DETERMINISTIC_FAST_PATH",
            "routing_action": "LLM_FALLBACK",
            "action": "COLLECT_MORE_INFO",
            "confidence": round(confidence, 4),
            "latency_ms": latency_ms,
            "reason": f"Low confidence ({confidence:.2f} < {CONFIDENCE_THRESHOLD})",
            "class_probabilities": prediction["class_probabilities"],
        }

    # High-confidence deterministic fast-path
    operational_action = INTENT_TO_ACTION.get(predicted_intent, "COLLECT_MORE_INFO")

    return {
        "source": "DETERMINISTIC_FAST_PATH",
        "routing_action": "EXECUTE_ACTION",
        "action": operational_action,
        "confidence": round(confidence, 4),
        "latency_ms": latency_ms,
        "class_probabilities": prediction["class_probabilities"],
    }


if __name__ == "__main__":
    # Test High-Confidence Dispute Case
    dispute_sample = {
        "full_text": "No reconozco un cargo de $150 USD en mi tarjeta ",
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

    # Test Low-Confidence Generic Case
    greeting_sample = {
        "full_text": "Hola buenas tardes",
        "channel": "chat",
        "duration_seconds": 5.0,
    }

    print("=== HIGH-CONFIDENCE PAYLOAD ===")
    print(route_intent_event(dispute_sample))

    print("\n=== LOW-CONFIDENCE PAYLOAD ===")
    print(route_intent_event(greeting_sample))
