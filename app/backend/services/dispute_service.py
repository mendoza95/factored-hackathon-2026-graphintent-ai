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


class DisputeService:
    """Orchestrates transaction disputes using the Graph Coloring Scheduler."""

    def __init__(self):
        self.scheduler = GraphColoringScheduler()

    def process_chat_message(self, request: ChatRequest) -> ChatResponse:
        """
        Process incoming user chat and execute necessary tasks
        via Graph Scheduler.
        """
        # 1. Classify intent and extract entities using LLM Service
        intent = llm_service.classify_intent(request.message)
        entities = llm_service.extract_entities(request.message)

        # 2. Build task dependency graph based on intent
        self._build_task_graph(intent, request, entities)

        # 3. Schedule and execute tasks in optimal parallel batches
        batch_schedule = self.scheduler.compute_schedule()
        metrics = self.scheduler.get_optimization_metrics()

        # Execute scheduled work
        execution_context = self._execute_scheduled_batches(
            batch_schedule, request, entities
        )

        # 4. Check guardrails for human handoff
        requires_handoff, handoff_details = self._evaluate_guardrails(
            intent, execution_context
        )

        # 5. Generate response text
        response_text = llm_service.generate_response(
            intent=intent,
            user_accent=request.user_accent,
            context=execution_context,
        )

        # 6. Assemble response object
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
                total_execution_time_ms=metrics["total_execution_time_ms"],
            ),
        )

    def _build_task_graph(
        self, intent: IntentEnum, request: ChatRequest, entities: dict
    ) -> None:
        """
        Build the conflict graph directly on the scheduler's
        NetworkX graph object.
        """

        # 1. Reset the graph for a new request
        self.scheduler.graph.clear()

        # 2. Add base nodes
        base_tasks = ["extract_entities", "verify_customer"]
        for task in base_tasks:
            self.scheduler.graph.add_node(task)

        # Base dependency edge (cannot execute in parallel)
        self.scheduler.graph.add_edge("extract_entities", "verify_customer")

        # 3. Add intent-specific nodes and conflict edges
        if intent == IntentEnum.DISPUTE_INITIATE:
            dispute_tasks = [
                "fetch_transactions",
                "evaluate_fraud_score",
                "create_complaint_record",
            ]
            for task in dispute_tasks:
                self.scheduler.graph.add_node(task)

            # Sequential dependency edges
            self.scheduler.graph.add_edge("verify_customer", "fetch_transactions")
            self.scheduler.graph.add_edge("fetch_transactions", "evaluate_fraud_score")
            self.scheduler.graph.add_edge(
                "evaluate_fraud_score", "create_complaint_record"
            )

            # Resource write-lock conflict edge
            self.scheduler.graph.add_edge("verify_customer", "create_complaint_record")

        elif intent == IntentEnum.ACCOUNT_INQUIRY:
            self.scheduler.graph.add_node("fetch_account_balance")
            self.scheduler.graph.add_edge("verify_customer", "fetch_account_balance")

    def _execute_scheduled_batches(
        self,
        batch_schedule: dict[str, list[str]],
        request: ChatRequest,
        entities: dict,
    ) -> dict[str, Any]:
        """Execute task batches step by step."""
        context: dict[str, Any] = {
            "customer_id": request.customer_id,
            "entities": entities,
        }

        # Simulated batch execution based on database state
        customer = db.get_customer(request.customer_id)
        if customer:
            context["customer_data"] = customer

        tx_list = db.get_customer_transactions(request.customer_id)
        if tx_list:
            context["recent_transactions"] = tx_list

        if entities.get("claimed_amount"):
            # Create a complaint record if initiating dispute
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
        self, intent: IntentEnum, context: dict
    ) -> tuple[bool, HandoffContext]:
        """Evaluate business rules to trigger human escalation when necessary."""
        if intent == IntentEnum.HUMAN_HANDOFF:
            return True, HandoffContext(
                is_escalated=True,
                reason="User explicitly requested a human specialist",
                verified_facts={"customer_id": context.get("customer_id")},
                unresolved_questions=["What specific issue requires agent assistance?"],
            )

        # Guardrail: High dollar amount disputes require human supervisor
        claimed_amt = context.get("entities", {}).get("claimed_amount")
        if claimed_amt and claimed_amt > 1000.0:
            return True, HandoffContext(
                is_escalated=True,
                reason="Claimed dispute amount exceeds automated approval "
                "threshold ($1,000 USD)",
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
