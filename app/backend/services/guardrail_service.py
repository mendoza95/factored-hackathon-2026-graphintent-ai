import re
from typing import Any, Tuple

from app.backend.schemas.chat import HandoffContext


class GuardrailService:
    # Patrón básico para detectar números de tarjeta (13 a 19 dígitos)
    CARD_PATTERN = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    # Patrones para inyección de prompts comunes
    INJECTION_PATTERNS = [
        r"ignore previous instructions",
        r"ignora las instrucciones anteriores",
        r"system prompt",
        r"actua como",
        r"act as",
    ]

    def sanitize_input(self, text: str) -> Tuple[str, bool]:
        """
        Enmascara tarjetas de crédito y detecta intentos de prompt injection.
        Retorna (texto_sanitizado, es_seguro).
        """
        text_lower = text.lower()
        for pattern in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower):
                return "Solicitud no procesable por motivos de seguridad.", False

        sanitized_text = self.CARD_PATTERN.sub("[TARJETA_ENMASCARADA]", text)
        return sanitized_text, True

    def validate_output(self, llm_response: str) -> str:
        """
        Garantiza que el LLM no prometa devoluciones o
        decisiones financieras definitivas.
        """
        forbidden_phrases = [
            "te garantizo el reembolso",
            "hemos aprobado tu devolución",
            "te devolveremos el dinero inmediatamente",
        ]

        response_lower = llm_response.lower()
        for phrase in forbidden_phrases:
            if phrase in response_lower:
                return (
                    "He registrado tu consulta. Un especialista revisará tu caso "
                    "para validar la procedencia de cualquier reembolso."
                )
        return llm_response

    def evaluate_guardrails(
        self, action: str, context: dict[str, Any]
    ) -> Tuple[bool, HandoffContext]:
        """Evaluate business guardrails for human handoff."""
        if action == "ESCALATE_TO_HUMAN":
            return True, HandoffContext(
                is_escalated=True,
                reason="User explicitly requested a human specialist",
                verified_facts={"customer_id": context.get("customer_id")},
                unresolved_questions=["What specific issue requires agent assistance?"],
            )

        claimed_amt = context.get("entities", {}).get("claimed_amount")
        if claimed_amt and claimed_amt > 1000.0:
            return True, HandoffContext(
                is_escalated=True,
                reason=(
                    "Claimed dispute amount exceeds automated threshold ($1,000 USD)"
                ),
                verified_facts={
                    "customer_id": context.get("customer_id"),
                    "claimed_amount": claimed_amt,
                },
                unresolved_questions=[
                    "Manual supervisor approval needed for high-value claim"
                ],
            )

        return False, HandoffContext(is_escalated=False)


# Global service instance
guardrail_service = GuardrailService()
