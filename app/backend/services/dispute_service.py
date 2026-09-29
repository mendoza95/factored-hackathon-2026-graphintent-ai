import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.backend.core.graph_scheduler import GraphColoringScheduler
from app.backend.db.mock_db import db
from app.backend.schemas.chat import (
    ChatRequest,
    ChatResponse,
    HandoffContext,
    IntentEnum,
    OptimizationMetadata,
)
from app.backend.schemas.dispute import ComplaintSchema
from app.backend.services.llm_service import llm_service
from app.backend.services.orchestrator import process_interaction_event

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
        self.scheduler = GraphColoringScheduler()

    def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process incoming chat, execute fast-path or LLM routing,
        and run graph task scheduler.
        """

        # 1. Run Hybrid Orchestrator (Sub-10ms Fast-Path ML or LLM Fallback)
        payload = {
            "full_text": request.message,
            "channel": getattr(request, "channel", "chat"),
            "customer_id": request.customer_id,
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
        self._build_task_graph(action, entities)

        # 3. Schedule and execute backend tasks in parallel batches
        batch_schedule = self.scheduler.compute_schedule()
        metrics = self.scheduler.get_optimization_metrics()

        execution_context = self._execute_scheduled_batches(
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

    def _build_task_graph(self, action: str, entities: dict) -> None:
        """Build conflict graph dynamically based on determined action."""
        self.scheduler.graph.clear()

        base_tasks = ["extract_entities", "verify_customer"]
        for task in base_tasks:
            self.scheduler.graph.add_node(task)

        self.scheduler.graph.add_edge("extract_entities", "verify_customer")

        if action == "INITIATE_DISPUTE_WORKFLOW":
            dispute_tasks = [
                "fetch_transactions",
                "evaluate_fraud_score",
                "create_complaint_record",
            ]
            for task in dispute_tasks:
                self.scheduler.graph.add_node(task)

            self.scheduler.graph.add_edge("verify_customer", "fetch_transactions")
            self.scheduler.graph.add_edge("fetch_transactions", "evaluate_fraud_score")
            self.scheduler.graph.add_edge(
                "evaluate_fraud_score", "create_complaint_record"
            )
            self.scheduler.graph.add_edge("verify_customer", "create_complaint_record")

        elif action == "EXECUTE_ACCOUNT_INQUIRY":
            self.scheduler.graph.add_node("fetch_account_balance")
            self.scheduler.graph.add_edge("verify_customer", "fetch_account_balance")

    def _execute_scheduled_batches(
        self,
        batch_schedule: dict[int, list[str]],
        request: ChatRequest,
        entities: dict,
    ) -> dict[str, Any]:
        """Execute scheduled tasks step by step."""
        context: dict[str, Any] = {
            "customer_id": request.customer_id,
            "entities": entities,
        }

        customer = db.get_customer(request.customer_id)
        if customer:
            context["customer_data"] = customer

        tx_list = db.get_customer_transactions(request.customer_id)
        if tx_list:
            context["recent_transactions"] = tx_list

        if entities.get("claimed_amount"):
            complaint_id = f"COMP_{uuid.uuid4().hex[:8].upper()}"
            new_complaint = ComplaintSchema(
                complaint_id=complaint_id,
                creation_date=datetime.now(),
                customer_id=request.customer_id,
                claimed_amount=Decimal(str(entities["claimed_amount"])),
                currency=entities.get("currency", "USD"),
                status="Open",
            )
            db.create_complaint(new_complaint)
            context["dispute_id"] = complaint_id

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
