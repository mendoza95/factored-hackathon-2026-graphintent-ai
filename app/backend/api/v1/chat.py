from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.schemas.chat import ChatRequest, ChatResponse
from app.backend.services.dispute_service import DisputeService

router = APIRouter(prefix="/api/v1", tags=["Chat"])


def get_dispute_service() -> DisputeService:
    return DisputeService()


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Process customer chat message through graph execution engine",
)
async def process_chat(
    request: ChatRequest,
    service: DisputeService = Depends(get_dispute_service),
) -> ChatResponse:
    try:
        response = await service.process_chat_message(request)
        return response
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat request: {str(exc)}",
        )
