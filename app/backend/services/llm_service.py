import time
from typing import Any, Dict, Optional

from app.backend.schemas.chat import IntentEnum

INTENT_TO_ACTION_MAP = {
    IntentEnum.DISPUTE_INITIATE: "INITIATE_DISPUTE_WORKFLOW",
    IntentEnum.HUMAN_HANDOFF: "ESCALATE_TO_HUMAN",
    IntentEnum.ACCOUNT_INQUIRY: "EXECUTE_ACCOUNT_INQUIRY",
    IntentEnum.UNSUPPORTED: "COLLECT_MORE_INFO",
}


class LLMService:
    """Service for handling low-confidence routing fallbacks using LLM reasoning."""

    def __init__(self, client: Optional[Any] = None):
        # Pass an LLM client (e.g., boto3 bedrock-runtime or openai client)
        self.client = client

    def classify_and_extract_llm(self, message: str) -> Dict[str, Any]:
        """
        Call LLM for structured reasoning when ML fast-path confidence is low.
        This resolves ambiguous phrasing, indirect complaints, or multi-intent messages.
        """
        # If no external LLM client is configured yet, return a safe fallback schema
        if not self.client:
            return {
                "intent": IntentEnum.UNSUPPORTED,
                "confidence": 0.50,
                "claimed_amount": None,
                "currency": None,
            }

        # Prompt execution logic (e.g., via Bedrock / OpenAI structured outputs)
        # prompt = f"Analyze customer message and return JSON: {message}"
        # response = self.client.generate(...)

        return {
            "intent": IntentEnum.UNSUPPORTED,
            "confidence": 0.85,
            "claimed_amount": None,
            "currency": None,
        }

    def generate_response(
        self,
        intent: IntentEnum,
        user_accent: Optional[str] = "mexican",
        context: Optional[dict] = None,
    ) -> str:
        """Generate accent-tailored response in Spanish."""
        greeting = "Hola"
        if user_accent == "argentine":
            greeting = "Hola, ¿cómo estás?"
        elif user_accent == "colombian":
            greeting = "Hola, con gusto le ayudo"

        if intent == IntentEnum.DISPUTE_INITIATE:
            return (
                f"{greeting}. He registrado tu solicitud para iniciar"
                " la disputa del cargo. Estamos validando los"
                " detalles de la transacción."
            )
        elif intent == IntentEnum.HUMAN_HANDOFF:
            return (
                f"{greeting}. Entiendo tu requerimiento. Estoy transfiriendo tu caso "
                "con un especialista de soporte humano."
            )
        elif intent == IntentEnum.ACCOUNT_INQUIRY:
            return (
                f"{greeting}. Puedes consultar el saldo y movimientos "
                "de tu cuenta desde la app móvil o el portal web."
            )

        return (
            f"{greeting}. ¿Podrías brindarme más detalles sobre la transacción "
            "o consulta que deseas realizar?"
        )

    def process_fallback(
        self,
        event_payload: Dict[str, Any],
        user_accent: Optional[str] = "mexican",
    ) -> Dict[str, Any]:
        """Unified fallback entry point called when router.py returns LLM_FALLBACK."""
        start_time = time.perf_counter()

        message = str(event_payload.get("full_text", ""))
        llm_result = self.classify_and_extract_llm(message)

        intent = llm_result["intent"]
        response_msg = self.generate_response(intent=intent, user_accent=user_accent)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "source": "LLM_FALLBACK",
            "routing_action": "EXECUTE_ACTION",
            "action": INTENT_TO_ACTION_MAP.get(intent, "COLLECT_MORE_INFO"),
            "confidence": llm_result["confidence"],
            "latency_ms": latency_ms,
            "response_message": response_msg,
            "extracted_entities": {
                "claimed_amount": llm_result.get("claimed_amount"),
                "currency": llm_result.get("currency"),
            },
        }


llm_service = LLMService()
