import time
from typing import Any, Dict, Optional

from app.backend.services.llm_service import llm_service
from app.ml.router import route_intent_event


async def process_interaction_event(
    event_payload: Dict[str, Any],
    user_accent: Optional[str] = "mexican",
) -> Dict[str, Any]:
    """Single backend entry point for hybrid dispute orchestration.

    1. Attempts sub-10ms deterministic fast-path routing via ML model.
    2. Falls back to LLM service when confidence is below threshold.
    """
    total_start = time.perf_counter()

    # Step 1: Execute ML Fast-Path Router
    router_result = route_intent_event(event_payload)

    # Fast-Path Success
    if router_result.get("routing_action") == "EXECUTE_ACTION":
        total_latency = round((time.perf_counter() - total_start) * 1000, 2)
        return {
            "source": "DETERMINISTIC_FAST_PATH",
            "action": router_result["action"],
            "confidence": router_result["confidence"],
            "class_probabilities": router_result["class_probabilities"],
            "latency_ms": total_latency,
            "response_message": None,
        }

    # Step 2: Low-Confidence LLM Fallback Execution
    fallback_result = await llm_service.process_fallback(
        event_payload=event_payload, user_accent=user_accent
    )

    total_latency = round((time.perf_counter() - total_start) * 1000, 2)

    return {
        "source": "LLM_FALLBACK",
        "action": fallback_result["action"],
        "confidence": fallback_result["confidence"],
        "class_probabilities": router_result.get("class_probabilities", {}),
        "latency_ms": total_latency,
        "response_message": fallback_result.get("response_message"),
        "extracted_entities": fallback_result.get("extracted_entities"),
        "fallback_reason": router_result.get("reason"),
    }
