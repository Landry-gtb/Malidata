import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

from routers import chat, rag
from database import init_db
from rag_pipeline import RAGPipeline

# ── Lifespan ────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisation au démarrage, nettoyage à l'arrêt."""
    logger.info("🚀 Démarrage du backend Malidata...")

    # 1. Base de données
    try:
        await init_db()
        logger.info("✅ Base de données initialisée.")
    except Exception as e:
        logger.warning(f"⚠️  Erreur DB (non bloquante) : {e}")

    # 2. Pipeline RAG
    try:
        pipeline = RAGPipeline()
        await pipeline.initialize()
        app.state.rag = pipeline
        logger.info("✅ Pipeline RAG initialisé.")
    except Exception as e:
        logger.error(f"❌ Erreur RAG (bloquante) : {e}")
        raise

    # 3. Vérification clé API — GROQ
    if not os.getenv("GROQ_API_KEY"):
        logger.warning("⚠️  GROQ_API_KEY manquante — le LLM sera indisponible.")

    # 4. Vérification Redis
    try:
        import redis as redis_sync
        r = redis_sync.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
        )
        r.ping()
        logger.info("✅ Redis accessible.")
    except Exception as e:
        logger.warning(f"⚠️  Redis inaccessible : {e}")

    yield

    logger.info("🛑 Arrêt du backend Malidata.")


# ── Application ─────────────────────────────────────────────────────

app = FastAPI(
    title="Malidata Chatbot",
    description=(
        "Système de pré-consultation médicale pour la malaria. "
        "⚠️ Ne remplace pas un diagnostic professionnel."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# CORS
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
    "http://localhost:3000",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(rag.router,  prefix="/api",      tags=["rag"])

from routers import reports
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])


# ── Endpoints de base ────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "Malidata Backend",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check — état réel du pipeline et des dépendances."""
    pipeline = getattr(app.state, "rag", None)
    rag_stats = pipeline.get_stats() if pipeline else {}

    return {
        "status": "healthy",
        "rag_initialized": rag_stats.get("rag_initialized", False),
        "rag_chunks": rag_stats.get("rag_chunks", 0),
        "llm_engine": rag_stats.get("engine", "N/A"),
        "groq_api_key_set": bool(os.getenv("GROQ_API_KEY")),
        "total_steps": rag_stats.get("total_steps", 10),
    }
