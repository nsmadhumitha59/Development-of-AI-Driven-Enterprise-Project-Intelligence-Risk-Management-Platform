"""
FastAPI Application Entrypoint for AI Project Intelligence & Risk Advisor.
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from configs.settings import settings
from .routes import router as api_router
from .agent_routes import router as agent_router
from .m3_routes import router as m3_router

STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
INDEX_HTML = Path(__file__).resolve().parent.parent / "web" / "index.html"


def create_app() -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI Project Intelligence & Risk Advisor (Milestones 1, 2, and 3)\n\n"
            "Features:\n"
            "- Multi-format document ingestion (PDF, DOCX, CSV, TXT)\n"
            "- Content normalization and metadata tracking\n"
            "- Dense vector embeddings via SentenceTransformers & ChromaDB vector store\n"
            "- Milestone 2 Multi-Agent Intelligence (Scope, Risk Forecasting, Blockers & Actions)\n"
            "- Milestone 3 Documentation Generation (User Stories, Risk Register, Action Items)\n"
            "- Milestone 3 Project Health Scoring (Scope Clarity, Timeline Risk, Blocker Severity)\n"
            "- Milestone 3 Conversational Project Intelligence Assistant (RAG Chatbot)"
        ),
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API routers
    app.include_router(api_router)
    app.include_router(agent_router)
    app.include_router(m3_router)

    # Mount Static Files for UI if they exist
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        if INDEX_HTML.exists():
            return FileResponse(str(INDEX_HTML))
        return {
            "message": "AI Project Intelligence & Risk Advisor API",
            "docs": "/docs",
            "health": "/api/v1/health"
        }

    return app


app = create_app()
