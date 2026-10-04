import time
from typing import Any, Dict, Optional

from app.backend.schemas.chat import IntentEnum
from app.backend.services.llm_fallback import LLM_client

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
        self.llm_client = LLM_client()

    async def classify_and_extract_llm(self, message: str) -> Dict[str, Any]:
        """
        Call LLM for structured reasoning when ML fast-path confidence is low.
        This resolves ambiguous phrasing,
        indirect complaints, or multi-intent messages.
        """
        # If no client is configured, return the standard unsupported intent
        if not self.llm_client:
            return {
                "intent": IntentEnum.UNSUPPORTED,
                "confidence": 0.50,
                "claimed_amount": None,
                "currency": None,
                "llm_response": "No se pudo conectar al servicio LLM.",
            }

        # Query Hugging Face LLM service
        llm_response_text = await self.llm_client.query_llm_fallback(
            user_message=message
        )

        return {
            "intent": IntentEnum.UNSUPPORTED,
            "confidence": 0.85,
            "claimed_amount": None,
            "currency": None,
            "llm_response": llm_response_text,
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

        context = context or {}

        if intent == IntentEnum.DISPUTE_INITIATE:
            entities = context.get("entities", {})
            claimed_amount = entities.get("claimed_amount")
            currency = entities.get("currency", "USD")

            is_duplicate = context.get("is_duplicate_intent", False)
            missing_info = context.get("missing_info")
            txs = context.get("transactions_found", [])
            has_duplicate_match = context.get("has_duplicate_match", False)

            # 1. CASO COBRO DUPLICADO
            if is_duplicate:
                if missing_info == "amount_and_currency" or not claimed_amount:
                    return (
                        f"{greeting}. Para verificar si existe un "
                        f"cobro duplicado en tu cuenta, "
                        "por favor indícame el **monto** y la **moneda** "
                        f"de la transacción."
                    )

                if has_duplicate_match:
                    tx_details = "\n".join(
                        f"• **{tx['merchant']}**: {tx['amount']} "
                        f"{tx['currency']} — Fecha/Hora: `{tx['timestamp']}`"
                        for tx in txs
                    )
                    return (
                        f"{greeting}. Hemos detectado los siguientes cargos "
                        f"duplicados en tu historial:\n\n{tx_details}\n\n"
                        f"Debido a la coincidencia exacta en montos y fechas, "
                        f"he transferido tu caso a un **agente humano** "
                        f"para procesar el reembolso inmediato."
                    )

                return (
                    f"{greeting}. Analizamos las transacciones por "
                    f"**{claimed_amount} {currency}** en la última semana "
                    f"y no encontramos cargos duplicados en fechas/horas contiguas. "
                    f"¿Deseas iniciar una disputa individual "
                    f"sobre alguna de tus compras?"
                )

            # 2. CASO DISPUTA ESTÁNDAR (MONTO NO RECONOCIDO)
            if claimed_amount:
                if txs:
                    return (
                        f"{greeting}. Registramos tu solicitud por "
                        f"**{claimed_amount} {currency}**. "
                        f"Encontramos las siguientes transacciones recientes "
                        f"en la última semana con montos similares:\n\n"
                        # f"{tx_list}\n\n"
                        f"Por favor, **selecciona** de la transacción sobre "
                        f"la cual deseas iniciar el reclamo."
                    )

                return (
                    f"{greeting}. Registramos tu solicitud de disputa por"
                    f" **{claimed_amount} {currency}**. "
                    f"No encontramos transacciones en la última semana por ese "
                    f"valor exacto, pero tu caso ha quedado registrado bajo revisión."
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

    async def process_fallback(
        self,
        event_payload: Dict[str, Any],
        user_accent: Optional[str] = "mexican",
    ) -> Dict[str, Any]:
        """Procesa consultas ambiguas exclusivamente para respuesta conversacional."""
        start_time = time.perf_counter()
        message = str(event_payload.get("full_text", ""))

        # 1. Obtenemos la respuesta puramente conversacional del LLM
        llm_text = await self.llm_client.query_llm_fallback(user_message=message)
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # 2. Retornamos sin activar acciones del sistema
        return {
            "source": "LLM_FALLBACK",
            "routing_action": "EXECUTE_ACTION",
            "action": "COLLECT_MORE_INFO",  # No dispara workflows en React
            "confidence": 0.50,
            "latency_ms": latency_ms,
            "response_message": llm_text,
            "extracted_entities": {},
        }


llm_service = LLMService()
