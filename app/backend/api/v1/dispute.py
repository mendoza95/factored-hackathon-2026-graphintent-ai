import random
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from app.backend.core.security import get_current_user
from app.backend.db.base import BaseDatabase
from app.backend.db.deps import get_db
from app.backend.schemas.dispute import DisputeRequest, DisputeResponse, Transaction
from app.backend.services.session_service import session_service  # <--- Importante

router = APIRouter(prefix="/api/v1", tags=["disputes"])


@router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    current_user: dict = Depends(get_current_user), db: BaseDatabase = Depends(get_db)
):
    """Fetch recent posted transactions from mock database."""
    return db.get_frontend_transactions()


@router.post("/disputes", response_model=DisputeResponse)
async def submit_dispute(
    payload: DisputeRequest,
    current_user: dict = Depends(get_current_user),
    db: BaseDatabase = Depends(get_db),
):
    """Submit a dispute claim for a specific transaction."""
    tx = db.get_transaction(payload.transaction_id)
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # 1. Actualiza la base de datos en memoria
    db.update_transaction_status(payload.transaction_id, "Reversed")
    ref_id = f"DISP-{random.randint(100000, 999999)}"

    # 2. Actualiza la sesión del chat
    session_id = getattr(payload, "session_id", None) or "SESS_FE_MAIN"
    session_service.add_disputed_transaction(session_id, str(payload.transaction_id))

    return DisputeResponse(
        reference_id=ref_id,
        transaction_id=payload.transaction_id,
        status="under_review",
        message=f"Dispute claim successfully recorded under reference {ref_id}.",
    )
