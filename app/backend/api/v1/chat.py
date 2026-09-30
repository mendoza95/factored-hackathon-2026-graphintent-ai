from fastapi import APIRouter, Depends, status

from app.backend.core.security import get_current_user
from app.backend.schemas.chat import ChatRequest, ChatResponse
from app.backend.services.dispute_service import DisputeService

router = APIRouter(prefix="/api/v1", tags=["Chat"])


def get_dispute_service() -> DisputeService:
    return DisputeService()


@router.post("/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def process_chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
    service: DisputeService = Depends(get_dispute_service),
) -> ChatResponse:
    return await service.process_chat_message(
        request=request, customer_id=current_user["customer_id"]
    )
