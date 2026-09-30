import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Dict

from app.backend.db.mock_db import db
from app.backend.schemas.chat import ChatRequest
from app.backend.schemas.dispute import ComplaintSchema

# Async TaskHandler contract
TaskHandler = Callable[
    [Dict[str, Any], ChatRequest, Dict[str, Any]], Awaitable[Dict[str, Any]]
]

TASK_HANDLERS: Dict[str, TaskHandler] = {}


def register_handler(node_name: str):
    """Decorator to register functions as graph task handlers."""

    def decorator(func: TaskHandler) -> TaskHandler:
        TASK_HANDLERS[node_name] = func
        return func

    return decorator


@register_handler("extract_entities")
async def handle_extract_entities(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    context["extracted_entities"] = entities
    return context


@register_handler("verify_customer")
async def handle_verify_customer(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    customer = await asyncio.to_thread(db.get_customer, request.customer_id)
    if customer:
        context["customer_data"] = customer
        context["is_verified"] = True
    else:
        context["is_verified"] = False
    return context


@register_handler("fetch_transactions")
async def handle_fetch_transactions(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    tx_list = await asyncio.to_thread(db.get_customer_transactions, request.customer_id)
    context["recent_transactions"] = tx_list or []
    return context


@register_handler("evaluate_fraud_score")
async def handle_evaluate_fraud_score(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    transactions = context.get("recent_transactions", [])
    claimed_amount = entities.get("claimed_amount", 0.0)

    if transactions and claimed_amount:
        # Cast amounts to float to ensure arithmetic compatibility
        amounts = [
            float(tx.amount) if hasattr(tx, "amount") else float(tx.get("amount", 0))
            for tx in transactions
        ]
        avg_amount = sum(amounts) / len(amounts) if amounts else 1.0

        if avg_amount > 0:
            fraud_score = min(1.0, round(float(claimed_amount) / (avg_amount * 2), 2))
        else:
            fraud_score = 0.5
    else:
        fraud_score = 0.15

    context["fraud_score"] = fraud_score
    context["is_high_risk"] = fraud_score > 0.75
    return context


@register_handler("create_complaint_record")
async def handle_create_complaint_record(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
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
        await asyncio.to_thread(db.create_complaint, new_complaint)
        context["dispute_id"] = complaint_id

    return context
