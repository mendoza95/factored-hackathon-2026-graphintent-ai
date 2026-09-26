import json
import re
from typing import Any, Optional
from app.backend.schemas.chat import IntentEnum


class LLMService:
    """Service for Spanish intent classification and entity extraction."""

    def __init__(self):
        # Pre-defined intent keywords for fallback deterministic parsing
        self._dispute_keywords = [
            "no reconozco",
            "no hice",
            "cargo no autorizado",
            "estafa",
            "devolucion",
            "reclamo",
            "reportar",
            "disputa",
            "cobro indebido",
            "fraude",
        ]
        self._handoff_keywords = [
            "agente",
            "humano",
            "supervisor",
            "representante",
            "queja formal",
            "hablar con alguien",
        ]

    def classify_intent(self, message: str) -> IntentEnum:
        """Classify user intent using rule-based fallback and pattern matching."""
        message_lower = message.lower()

        print(message_lower)

        for keyword in self._handoff_keywords:
            if keyword in message_lower:
                return IntentEnum.HUMAN_HANDOFF

        for keyword in self._dispute_keywords:
            print(keyword)
            if keyword in message_lower:
                return IntentEnum.DISPUTE_INITIATE

        if any(
            word in message_lower
            for word in ["saldo", "estado de cuenta", "movimientos", "tarjeta"]
        ):
            return IntentEnum.ACCOUNT_INQUIRY

        return IntentEnum.UNSUPPORTED

    def extract_entities(self, message: str) -> dict[str, Any]:
        """Extract structured entities (amount, currency, merchant) from user text."""
        entities: dict[str, Any] = {
            "claimed_amount": None,
            "currency": None,
            "merchant_hint": None,
        }

        # Match currency symbols and numbers (e.g., "$150 USD", "2500 MXN", "$50.00")
        amount_match = re.search(
            r"(\$|\b)(?P<amount>\d+(?:[\.,]\d{1,2})?)\s*(?P<currency>USD|MXN|COP|ARS)?",
            message,
            re.IGNORECASE,
        )
        if amount_match:
            try:
                raw_amount = amount_match.group("amount").replace(",", ".")
                entities["claimed_amount"] = float(raw_amount)
            except ValueError:
                pass

            curr = amount_match.group("currency")
            if curr:
                entities["currency"] = curr.upper()
            elif "$" in message:
                entities["currency"] = "USD"

        return entities

    def generate_response(
        self,
        intent: IntentEnum,
        user_accent: Optional[str] = "mexican",
        context: Optional[dict] = None,
    ) -> str:
        """Generate accent-tailored response in Spanish."""
        # Regional phrasing adjustments based on detected accent
        greeting = "Hola"
        if user_accent == "argentine":
            greeting = "Hola, ¿cómo estás?"
        elif user_accent == "colombian":
            greeting = "Hola, con gusto le ayudo"

        if intent == IntentEnum.DISPUTE_INITIATE:
            return (
                f"{greeting}. He registrado tu solicitud para iniciar la disputa del cargo. "
                "Estamos validando los detalles de la transacción con nuestro sistema de seguridad."
            )
        elif intent == IntentEnum.HUMAN_HANDOFF:
            return (
                f"{greeting}. Entiendo tu requerimiento. Estoy transfiriendo tu caso "
                "con un especialista de soporte humano para resolverlo de inmediato."
            )
        elif intent == IntentEnum.ACCOUNT_INQUIRY:
            return f"{greeting}. Puedes consultar el saldo y movimientos de tu cuenta desde la app móvil o el portal web."

        return f"{greeting}. Lo siento, no puedo procesar esa solicitud de manera automática en este momento."


# Global service instance
llm_service = LLMService()
