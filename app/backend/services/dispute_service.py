import asyncio
from typing import Any, Optional, Tuple

from app.backend.core.graph_scheduler import GraphColoringScheduler
from app.backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    IntentEnum,
    OptimizationMetadata,
)
from app.backend.services.guardrail_service import guardrail_service
from app.backend.services.llm_service import llm_service
from app.backend.services.orchestrator import process_interaction_event
from app.backend.services.session_service import session_service
from app.backend.services.task_handlers import TASK_HANDLERS
from app.backend.utils.entity_extractor import extract_entities_regex

# Action string to IntentEnum mapping for schema backwards-compatibility
ACTION_TO_INTENT_MAP = {
    "INITIATE_DISPUTE_WORKFLOW": IntentEnum.DISPUTE_INITIATE,
    "EXECUTE_ACCOUNT_INQUIRY": IntentEnum.ACCOUNT_INQUIRY,
    "ESCALATE_TO_HUMAN": IntentEnum.HUMAN_HANDOFF,
    "COLLECT_MORE_INFO": IntentEnum.UNSUPPORTED,
}


class DisputeService:
    """Orchestrates transaction disputes using ML Hybrid Router & Graph Scheduler."""

    def __init__(self):
        pass

    async def process_chat_message(
        self, request: ChatRequest, customer_id: Optional[str] = None
    ) -> ChatResponse:
        """
        Process incoming chat, execute fast-path or LLM routing,
        and run graph task scheduler.
        """
        session_id = getattr(request, "session_id", "default_session")
        session = session_service.get_session(session_id)

        # 0. Guardrail de entrada
        sanitized_message, is_safe = guardrail_service.sanitize_input(request.message)
        if not is_safe:
            return ChatResponse(
                response_message=(
                    "Tu mensaje contiene instrucciones "
                    "no permitidas por motivos de seguridad."
                ),
                intent_detected=IntentEnum.UNSUPPORTED,
                requires_human_handoff=False,
            )
        request.message = sanitized_message

        # 1. Rutear intención y extraer entidades
        effective_customer_id = (
            customer_id or getattr(request, "customer_id", None) or "CUST_12345"
        )
        payload = {
            "full_text": request.message,
            "channel": getattr(request, "channel", "chat"),
            "customer_id": effective_customer_id,
        }

        orch_result = await process_interaction_event(
            event_payload=payload,
            user_accent=request.user_accent,
        )

        action, intent, entities = await self._extract_and_resolve_entities(
            request, session_id, session, orch_result
        )

        # 2. Construir y ejecutar grafo de tareas
        scheduler = GraphColoringScheduler()
        self._build_task_graph(scheduler, action, entities)

        batch_schedule = scheduler.compute_schedule()
        metrics = scheduler.get_optimization_metrics()

        execution_context = await self._execute_scheduled_batches(
            batch_schedule, request, entities, effective_customer_id
        )

        execution_context["is_duplicate_intent"] = (
            session.get("dispute_type") == "duplicate"
        )
        execution_context["active_dispute"] = session.get("active_dispute", False)

        # 3. Guardrails de salida y respuesta
        requires_handoff, handoff_details = self._evaluate_handoff_guardrails(
            action, execution_context, session_id
        )

        final_response_message = self._generate_response_message(
            request, session, orch_result, intent, execution_context
        )

        options = self._build_selectable_options(request, execution_context)

        # 4. Respuesta estructurada
        return self._build_chat_response(
            final_response_message=final_response_message,
            intent=intent,
            execution_context=execution_context,
            requires_handoff=requires_handoff,
            handoff_details=handoff_details,
            options=options,
            metrics=metrics,
            batch_schedule=batch_schedule,
            orch_latency=orch_result.get("latency_ms", 0),
        )

    async def _extract_and_resolve_entities(
        self, request: ChatRequest, session_id: str, session: dict, orch_result: dict
    ) -> Tuple[str, IntentEnum, dict]:
        """Resuelve acción, intención y persiste estado de disputa en la sesión."""
        action = orch_result["action"]
        intent = ACTION_TO_INTENT_MAP.get(action, IntentEnum.UNSUPPORTED)

        entities = orch_result.get("extracted_entities")
        if not entities:
            entities = await llm_service.classify_and_extract_llm(request.message)

        if not entities.get("claimed_amount"):
            regex_entities = extract_entities_regex(request.message)
            if regex_entities.get("claimed_amount"):
                entities["claimed_amount"] = regex_entities["claimed_amount"]
            if regex_entities.get("currency") and not entities.get("currency"):
                entities["currency"] = regex_entities["currency"]

        is_dispute_intent = intent == IntentEnum.DISPUTE_INITIATE or session.get(
            "active_dispute"
        )

        if is_dispute_intent:
            action = "INITIATE_DISPUTE_WORKFLOW"
            intent = IntentEnum.DISPUTE_INITIATE

            is_duplicate = (
                "duplicad" in request.message.lower()
                or "doble" in request.message.lower()
                or (
                    session.get("dispute_type") == "duplicate"
                    and not entities.get("claimed_amount")
                )
            )

            current_amount = entities.get("claimed_amount")

            if not current_amount and not (
                "duplicad" in request.message.lower()
                or "queja" in request.message.lower()
            ):
                claimed_amount = session.get("claimed_amount")
            else:
                claimed_amount = current_amount

            currency = entities.get("currency") or "USD"

            session_service.update_session(
                session_id,
                {
                    "active_dispute": True,
                    "dispute_type": "duplicate" if is_duplicate else "unrecognized",
                    "claimed_amount": claimed_amount,
                    "currency": currency,
                },
            )

            entities["claimed_amount"] = claimed_amount
            entities["currency"] = currency
            entities["is_duplicate"] = is_duplicate

        return action, intent, entities

    def _evaluate_handoff_guardrails(
        self, action: str, execution_context: dict, session_id: str
    ) -> Tuple[bool, Optional[dict]]:
        """Verifica reglas de negocio para determinar si se escala a soporte humano."""
        requires_handoff, handoff_details = guardrail_service.evaluate_guardrails(
            action, execution_context
        )

        if execution_context.get("has_duplicate_match"):
            requires_handoff = True
            handoff_details = {
                "reason": "DUPLICATE_TRANSACTION_DETECTED",
                "details": "Coincidencia exacta de monto y fecha/hora detectada",
            }

        if requires_handoff:
            session_service.clear_session(session_id)

        return requires_handoff, handoff_details

    def _generate_response_message(
        self,
        request: ChatRequest,
        session: dict,
        orch_result: dict,
        intent: IntentEnum,
        execution_context: dict,
    ) -> str:
        """Genera y valida la respuesta final enviada al usuario."""
        if (
            session.get("active_dispute")
            or not orch_result.get("response_message")
            or execution_context.get("has_duplicate_match")
        ):
            response_text = llm_service.generate_response(
                intent=intent,
                user_accent=request.user_accent,
                context=execution_context,
            )
        else:
            response_text = orch_result.get("response_message")

        return guardrail_service.validate_output(response_text)

    def _build_selectable_options(
        self, request: ChatRequest, execution_context: dict
    ) -> list:
        """
        Construye las opciones de transacciones
        seleccionables para la interfaz gráfica.
        """
        options = []
        session_id = getattr(request, "session_id", "SESS_FE_MAIN")
        active_session = session_service.get_session(session_id)

        disputed_ids = [
            str(d) for d in active_session.get("disputed_transaction_ids", [])
        ]

        if execution_context.get("transactions_found"):
            for idx, tx in enumerate(execution_context["transactions_found"]):
                tx_id = str(tx.get("id", idx + 1))

                is_disputed = (
                    tx_id in disputed_ids
                    or str(idx + 1) in disputed_ids
                    or tx.get("status") in ["disputed", "Reversed"]
                    or tx.get("already_disputed", False)
                )

                tx_copy = dict(tx)
                tx_copy["already_disputed"] = is_disputed
                if is_disputed:
                    tx_copy["status"] = "disputed"

                options.append(
                    {
                        "id": tx_id,
                        "label": f"{tx['merchant']} - {tx['amount']} {tx['currency']}",
                        "value": str(idx + 1),
                        "already_disputed": is_disputed,
                        "transaction_data": tx_copy,
                    }
                )
        return options

    def _build_chat_response(
        self,
        final_response_message: str,
        intent: IntentEnum,
        execution_context: dict,
        requires_handoff: bool,
        handoff_details: Optional[dict],
        options: list,
        metrics: dict,
        batch_schedule: dict,
        orch_latency: float,
    ) -> ChatResponse:
        """Ensambla el objeto final de respuesta HTTP."""
        return ChatResponse(
            response_message=final_response_message,
            intent_detected=intent,
            dispute_id=execution_context.get("dispute_id"),
            requires_human_handoff=requires_handoff,
            handoff_details=handoff_details,
            context_data={
                "transactions": execution_context.get("transactions_found", []),
                "selectable_options": options,
                "is_duplicate_intent": execution_context.get(
                    "is_duplicate_intent", False
                ),
                "has_duplicate_match": execution_context.get(
                    "has_duplicate_match", False
                ),
            },
            optimization_metrics=OptimizationMetadata(
                graph_nodes_count=metrics["nodes_count"],
                graph_edges_count=metrics["edges_count"],
                chromatic_number=metrics["chromatic_number"],
                execution_batches=batch_schedule,
                total_execution_time_ms=round(
                    metrics["total_execution_time_ms"] + orch_latency, 2
                ),
            ),
        )

    def _build_task_graph(
        self, scheduler: GraphColoringScheduler, action: str, entities: dict
    ) -> None:
        """Build conflict graph dynamically based on determined action."""
        scheduler.graph.clear()

        base_tasks = ["extract_entities", "verify_customer"]
        for task in base_tasks:
            scheduler.graph.add_node(task)

        scheduler.graph.add_edge("extract_entities", "verify_customer")

        if action == "INITIATE_DISPUTE_WORKFLOW":
            dispute_tasks = [
                "fetch_transactions",
                "evaluate_fraud_score",
                "create_complaint_record",
            ]
            for task in dispute_tasks:
                scheduler.graph.add_node(task)

            scheduler.graph.add_edge("verify_customer", "fetch_transactions")
            scheduler.graph.add_edge("fetch_transactions", "evaluate_fraud_score")
            scheduler.graph.add_edge("evaluate_fraud_score", "create_complaint_record")
            scheduler.graph.add_edge("verify_customer", "create_complaint_record")

        elif action == "EXECUTE_ACCOUNT_INQUIRY":
            scheduler.graph.add_node("fetch_account_balance")
            scheduler.graph.add_edge("verify_customer", "fetch_account_balance")

    async def _execute_scheduled_batches(
        self,
        batch_schedule: dict[int, list[str]],
        request: ChatRequest,
        entities: dict,
        customer_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Execute scheduled graph tasks batch by batch concurrently."""
        resolved_customer_id = (
            customer_id or getattr(request, "customer_id", None) or "CUST_12345"
        )

        context: dict[str, Any] = {
            "customer_id": resolved_customer_id,
            "entities": entities or {},
        }

        for batch_id in sorted(batch_schedule.keys()):
            node_names = batch_schedule[batch_id]

            tasks = []
            for name in node_names:
                handler = TASK_HANDLERS.get(name)
                if handler:
                    tasks.append(handler(context, request, entities))

            if tasks:
                await asyncio.gather(*tasks)

        return context


# Global service instance
dispute_service = DisputeService()
