# app/backend/services/task_handlers.py
import asyncio
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Awaitable, Callable, Dict

from app.backend.db.deps import get_db
from app.backend.schemas.chat import ChatRequest
from app.backend.schemas.dispute import ComplaintSchema

# Variable global para definir la ventana de búsqueda en días
DEFAULT_DAYS_BACK = 30

# Contract para los handlers
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
    await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )

    customer = await asyncio.to_thread(db.get_customer, customer_id)
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
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )

    # Búsqueda utilizando la variable global DEFAULT_DAYS_BACK
    tx_list = (
        await asyncio.to_thread(
            db.get_customer_transactions, customer_id, days_back=DEFAULT_DAYS_BACK
        )
        or []
    )
    context["recent_transactions"] = tx_list

    claimed_amount = entities.get("claimed_amount")
    currency = entities.get("currency", "USD")
    user_text = request.message.lower()

    is_duplicate_intent = "duplicado" in user_text or "doble" in user_text
    context["is_duplicate_intent"] = is_duplicate_intent
    context["transactions_found"] = []
    context["has_duplicate_match"] = False

    if not claimed_amount:
        context["missing_info"] = "amount_and_currency"
        return context

    formatted_txs = []
    for tx in tx_list:
        amt = float(tx.amount) if tx.amount is not None else 0.0
        amt_usd = float(tx.amount_usd) if tx.amount_usd is not None else amt
        curr = tx.currency or "USD"
        merchant = tx.merchant_name or "Comercio Desconocido"
        ts = (
            tx.transaction_date.strftime("%Y-%m-%d %H:%M:%S")
            if tx.transaction_date
            else ""
        )

        raw_status = str(tx.transaction_status or "Approved")
        status = "disputed" if raw_status in ["Reversed", "disputed"] else "posted"

        formatted_txs.append(
            {
                "id": tx.transaction_id,
                "merchant": merchant,
                "amount": amt,
                "currency": curr,
                "amount_usd": amt_usd,
                "timestamp": ts,
                "status": status,
                "already_disputed": status == "disputed",
            }
        )

    if is_duplicate_intent:
        duplicates = [
            tx
            for tx in formatted_txs
            if abs(tx["amount"] - float(claimed_amount)) < 0.01
            and tx["currency"] == currency
        ]
        if len(duplicates) >= 2:
            context["has_duplicate_match"] = True
            context["transactions_found"] = duplicates
        else:
            context["transactions_found"] = duplicates
    else:
        similar_txs = [
            tx
            for tx in formatted_txs
            if abs(tx["amount"] - float(claimed_amount))
            <= (float(claimed_amount) * 0.10)
        ]
        context["transactions_found"] = similar_txs

    return context


@register_handler("evaluate_fraud_score")
async def handle_evaluate_fraud_score(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    transactions = context.get("recent_transactions", [])
    claimed_amount = entities.get("claimed_amount", 0.0)

    if transactions and claimed_amount:
        amounts = [
            float(tx.amount) if hasattr(tx, "amount") and tx.amount is not None else 0.0
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
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )

    if entities.get("claimed_amount"):
        complaint_id = f"COMP_{uuid.uuid4().hex[:8].upper()}"
        new_complaint = ComplaintSchema(
            complaint_id=complaint_id,
            creation_date=datetime.now(),
            customer_id=customer_id,
            claimed_amount=Decimal(str(entities["claimed_amount"])),
            currency=entities.get("currency", "USD"),
            status="Open",
        )
        await asyncio.to_thread(db.create_complaint, new_complaint)
        context["dispute_id"] = complaint_id

    return context


@register_handler("fetch_customer_info")
async def handle_fetch_customer_info(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )
    customer = await asyncio.to_thread(db.get_customer, customer_id)
    context["customer_info"] = customer or {}
    return context


@register_handler("fetch_customer_products")
async def handle_fetch_customer_products(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )
    products = await asyncio.to_thread(db.get_customer_products, customer_id)
    context["products"] = products or []
    return context


@register_handler("fetch_recent_transactions")
async def handle_fetch_recent_transactions_inquiry(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )
    # Búsqueda utilizando la variable global DEFAULT_DAYS_BACK
    tx_list = await asyncio.to_thread(
        db.get_customer_transactions, customer_id, days_back=DEFAULT_DAYS_BACK
    )
    context["recent_transactions"] = tx_list if tx_list is not None else []
    return context


@register_handler("fetch_active_complaints")
async def handle_fetch_active_complaints(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    # await asyncio.sleep(0.05)
    db = get_db()
    customer_id = (
        context.get("customer_id")
        or getattr(request, "customer_id", None)
        or "CUST_12345"
    )
    # Búsqueda utilizando la variable global DEFAULT_DAYS_BACK
    complaints = await asyncio.to_thread(
        db.get_active_complaints, customer_id, days_back=DEFAULT_DAYS_BACK
    )
    context["active_complaints"] = complaints or []
    return context


@register_handler("fetch_exchange_rates")
async def handle_fetch_exchange_rates(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    # await asyncio.sleep(0.05)
    db = get_db()
    rate = await asyncio.to_thread(db.get_exchange_rate, "MXN", "USD")
    context["exchange_rate_usd"] = rate
    return context


@register_handler("consolidate_financial_summary")
async def handle_consolidate_financial_summary(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    products = context.get("products", [])
    rate_usd = context.get("exchange_rate_usd", 1.0)

    # Usa 'current_balance' con guion bajo correspondiente al esquema
    total_balance_local = 0.0
    for p in products:
        if isinstance(p, dict):
            val = p.get("current_balance") or p.get("balance") or 0.0
        else:
            val = getattr(p, "current_balance", 0.0)
        total_balance_local += float(val)

    total_balance_usd = total_balance_local * float(rate_usd)

    context["account_summary"] = {
        "customer": context.get("customer_info"),
        "total_balance_local": total_balance_local,
        "total_balance_usd": total_balance_usd,
        "products_count": len(products),
        "recent_tx_count": len(context.get("recent_transactions", [])),
        "open_complaints_count": len(context.get("active_complaints", [])),
    }
    return context


@register_handler("generate_summary_report")
async def handle_generate_summary_report(
    context: Dict[str, Any], request: ChatRequest, entities: Dict[str, Any]
) -> Dict[str, Any]:
    context["summary_ready"] = True
    return context
