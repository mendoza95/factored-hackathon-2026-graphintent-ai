import asyncio
from typing import Any, Optional

from app.backend.core.graph_scheduler import GraphColoringScheduler
from app.backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HandoffContext,
    IntentEnum,
    OptimizationMetadata,
)
from app.backend.services.llm_service import llm_service
from app.backend.services.orchestrator import process_interaction_event
from app.backend.services.task_handlers import TASK_HANDLERS

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
        # 0. We instanciate a graph scheduler to proccess the current chat message.
        scheduler = GraphColoringScheduler()

        # 1. Run Hybrid Orchestrator (Sub-10ms Fast-Path ML or LLM Fallback)
        # In dispute_service.py
        effective_customer_id = (
            customer_id or getattr(request, "customer_id", None) or "CUST_12345"
        )
        payload = {
            "full_text": request.message,
            "channel": getattr(request, "channel", "chat"),
            "customer_id": effective_customer_id,
        }

        orch_result = process_interaction_event(
            event_payload=payload,
            user_accent=request.user_accent,
        )

        action = orch_result["action"]
        intent = ACTION_TO_INTENT_MAP.get(action, IntentEnum.UNSUPPORTED)

        # Extract entities using LLM service or fast-path regex
        entities = orch_result.get(
            "extracted_entities"
        ) or llm_service.classify_and_extract_llm(request.message)

        # 2. Build task dependency graph based on predicted operational action
        self._build_task_graph(scheduler, action, entities)

        # 3. Schedule and execute backend tasks in parallel batches
        batch_schedule = scheduler.compute_schedule()
        metrics = scheduler.get_optimization_metrics()

        execution_context = await self._execute_scheduled_batches(
            batch_schedule, request, entities
        )

        # 4. Check guardrails for human handoff
        requires_handoff, handoff_details = self._evaluate_guardrails(
            action, execution_context
        )

        # 5. Prepare final customer-facing response text
        response_text = orch_result.get("response_message")
        if not response_text:
            response_text = llm_service.generate_response(
                intent=intent,
                user_accent=request.user_accent,
                context=execution_context,
            )

        # 6. Assemble response object including hybrid router & scheduler metrics
        return ChatResponse(
            response_message=response_text,
            intent_detected=intent,
            dispute_id=execution_context.get("dispute_id"),
            requires_human_handoff=requires_handoff,
            handoff_details=handoff_details,
            optimization_metrics=OptimizationMetadata(
                graph_nodes_count=metrics["nodes_count"],
                graph_edges_count=metrics["edges_count"],
                chromatic_number=metrics["chromatic_number"],
                execution_batches=batch_schedule,
                total_execution_time_ms=metrics["total_execution_time_ms"]
                + orch_result["latency_ms"],
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
    ) -> dict[str, Any]:
        """Execute scheduled graph tasks batch by batch concurrently."""
        context: dict[str, Any] = {
            "customer_id": request.customer_id,
            "entities": entities,
        }

        # Process batches sequentially (Batch 0, then Batch 1, etc.)
        for batch_id in sorted(batch_schedule.keys()):
            node_names = batch_schedule[batch_id]

            # Gather tasks within the current batch to execute concurrently
            tasks = []
            for name in node_names:
                handler = TASK_HANDLERS.get(name)
                if handler:
                    tasks.append(handler(context, request, entities))

            if tasks:
                await asyncio.gather(*tasks)

        return context

    def _evaluate_guardrails(
        self, action: str, context: dict
    ) -> tuple[bool, HandoffContext]:
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
                reason="Claimed dispute amount exceeds automated"
                " threshold ($1,000 USD)",
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
dispute_service = DisputeService()
