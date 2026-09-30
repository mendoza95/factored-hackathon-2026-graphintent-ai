import pytest

from app.backend.core.graph_scheduler import GraphColoringScheduler
from app.backend.schemas.chat import ChatRequest
from app.backend.services.dispute_service import DisputeService
from app.backend.services.task_handlers import TASK_HANDLERS


@pytest.mark.asyncio
async def test_all_registered_handlers_execute_successfully():
    """Verify each registered task handler runs and mutates context correctly."""
    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_5050",
        message="Disputing $200 USD",
        user_accent="mexican",
    )
    context = {}
    entities = {"claimed_amount": 200.00, "currency": "USD"}

    # 1. Test entity extraction handler
    context = await TASK_HANDLERS["extract_entities"](context, request, entities)
    assert context["extracted_entities"] == entities

    # 2. Test customer verification handler
    context = await TASK_HANDLERS["verify_customer"](context, request, entities)
    assert "is_verified" in context

    # 3. Test transaction fetch handler
    context = await TASK_HANDLERS["fetch_transactions"](context, request, entities)
    assert "recent_transactions" in context

    # 4. Test fraud evaluation handler
    context = await TASK_HANDLERS["evaluate_fraud_score"](context, request, entities)
    assert "fraud_score" in context

    # 5. Test complaint creation handler
    context = await TASK_HANDLERS["create_complaint_record"](context, request, entities)
    assert "dispute_id" in context
    assert context["dispute_id"].startswith("COMP_")


@pytest.mark.asyncio
async def test_end_to_end_graph_batch_execution():
    """Verify DisputeService resolves graph batches and updates context concurrently."""
    service = DisputeService()
    scheduler = GraphColoringScheduler()
    request = ChatRequest(
        customer_id="CUST_12345",
        session_id="SESS_6060",
        message="Cargo no reconocido de $300 USD",
        user_accent="mexican",
    )
    entities = {"claimed_amount": 300.00, "currency": "USD"}

    # Build graph and resolve schedule
    service._build_task_graph(scheduler, "INITIATE_DISPUTE_WORKFLOW", entities)
    batch_schedule = scheduler.compute_schedule()

    # Verify graph structure before execution
    assert len(scheduler.graph.nodes) == 5
    assert len(batch_schedule) > 1

    # Run async batch execution
    final_context = await service._execute_scheduled_batches(
        batch_schedule, request, entities
    )

    # Assert expected outputs produced by batch step execution
    assert final_context["customer_id"] == "CUST_12345"
    assert "recent_transactions" in final_context
    assert "fraud_score" in final_context
    assert "dispute_id" in final_context
