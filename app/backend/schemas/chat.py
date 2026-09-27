from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class IntentEnum(str, Enum):
    DISPUTE_INITIATE = "dispute_initiate"
    DISPUTE_STATUS = "dispute_status"
    ACCOUNT_INQUIRY = "account_inquiry"
    HUMAN_HANDOFF = "human_handoff"
    UNSUPPORTED = "unsupported"


class ChatRequest(BaseModel):
    customer_id: str = Field(..., json_schema_extra={"example": "CUST_12345"})
    session_id: str = Field(..., json_schema_extra={"example": "SESS_98765"})
    message: str = Field(
        ...,
        json_schema_extra={
            "example": "No reconozco un cargo de $150 USD en mi tarjeta."
        },
    )
    language: str = Field(default="es", description="Language code")
    user_accent: Optional[str] = Field(
        default="mexican", description="Detected accent (mexican, colombian, argentine)"
    )


# Metadata capturing your CS Graph Coloring execution metrics
class OptimizationMetadata(BaseModel):
    graph_nodes_count: int
    graph_edges_count: int
    chromatic_number: int
    execution_batches: dict[int, list[str]]
    total_execution_time_ms: float


# Human Handoff Context (Requirement 3 from PDF)
class HandoffContext(BaseModel):
    is_escalated: bool = False
    reason: Optional[str] = None
    verified_facts: dict[str, Any] = Field(default_factory=dict)
    unresolved_questions: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    response_message: str
    intent_detected: IntentEnum
    dispute_id: Optional[str] = None
    requires_human_handoff: bool = False
    handoff_details: Optional[HandoffContext] = None
    optimization_metrics: OptimizationMetadata
