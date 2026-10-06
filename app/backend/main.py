import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.backend.api.v1.auth import router as auth_router
from app.backend.api.v1.chat import router as chat_router
from app.backend.api.v1.dispute import router as dispute_router

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
app.include_router(dispute_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}


FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "../frontend/dist")

if os.path.exists(FRONTEND_DIST):
    # Servir archivos estáticos (JS, CSS, imágenes)
    app.mount(
        "/assets",
        StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")),
        name="assets",
    )

    # Ruta raíz para entregar el index.html
    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    # Capturar cualquier otra ruta del cliente y redirigir al index.html
    @app.get("/{catchall:path}")
    async def serve_react_app(catchall: str):
        file_path = os.path.join(FRONTEND_DIST, catchall)
        if os.path.exists(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
