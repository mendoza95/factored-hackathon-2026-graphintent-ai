from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CountryEnum(str, Enum):
    MEXICO = "Mexico"
    COLOMBIA = "Colombia"
    ARGENTINA = "Argentina"


class TransactionStatus(str, Enum):
    APPROVED = "Approved"
    DECLINED = "Declined"
    PENDING = "Pending"
    REVERSED = "Reversed"


class DisputeStatus(str, Enum):
    OPEN = "Open"
    IN_PROCESS = "In Process"
    ESCALATED = "Escalated"
    RESOLVED = "Resolved"
    REJECTED = "Rejected"


# --- Transaction Model ---
class TransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str = Field(..., description="Unique transaction ID")
    transaction_date: datetime
    product_id: str
    customer_id: str
    transaction_type: str
    amount: Decimal
    currency: str = Field(..., max_length=3)
    amount_usd: Optional[Decimal] = None
    merchant_name: Optional[str] = None
    merchant_category: Optional[str] = None
    transaction_country: CountryEnum
    transaction_status: TransactionStatus
    is_fraud: bool = False
    fraud_score: Optional[Decimal] = None


# --- Dispute Payload (Internal State) ---
class DisputeCreate(BaseModel):
    customer_id: str
    affected_product_id: str
    transaction_id: str
    claimed_amount: Decimal
    currency: str
    reason: str = Field(
        ...,
        description="Reason provided by user in Spanish (e.g., "
        "'Unrecognized transaction')",
    )
    detected_country: CountryEnum
    detected_accent: Optional[str] = None


# --- Complaint Record (Matches 'complaints' table) ---
class ComplaintSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    complaint_id: str
    creation_date: datetime
    customer_id: str
    case_type: str = "Claim"
    category: str = "Transaction Dispute"
    affected_product_id: Optional[str] = None
    claimed_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    priority: str = "Medium"
    status: DisputeStatus = DisputeStatus.OPEN
    assigned_agent_id: Optional[str] = None
    resolution: Optional[str] = None
    sla_breached: bool = False
