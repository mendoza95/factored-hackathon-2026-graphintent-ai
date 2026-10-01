from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.backend.api.v1.auth import router as auth_router
from app.backend.api.v1.chat import router as chat_router

app = FastAPI(
    title="Dispute Agent AI API",
    version="0.1.0",
    description="Graph Coloring Scheduler Powered AI Agent for Transaction Disputes",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(chat_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
