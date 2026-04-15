import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])


# ── Modèles Pydantic ─────────────────────────────────────────────────

class RAGQuery(BaseModel):
    question: str
    max_results: int = 3


class ReportRequest(BaseModel):
    session_id: str


# ── Helper ───────────────────────────────────────────────────────────

def _get_pipeline(request: Request):
    rag = getattr(request.app.state, "rag", None)
    if not rag:
        raise HTTPException(
            status_code=503,
            detail="Pipeline RAG non initialisé.",
        )
    return rag


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/query")
async def query_rag(query: RAGQuery, request: Request):
    """
    Recherche sémantique directe dans la base de connaissances FAISS.
    Utile pour le dashboard médecin ou les tests.
    """
    rag = _get_pipeline(request)

    if not rag.initialized:
        raise HTTPException(
            status_code=503,
            detail="Index FAISS non encore initialisé.",
        )

    try:
        result = await rag.query(query.question, k=query.max_results)
    except Exception as e:
        logger.error(f"Erreur RAG query : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur recherche : {e}")

    return {
        "status": "success",
        "query": query.question,
        "sources": result.get("sources", []),
        "count": len(result.get("sources", [])),
    }


@router.post("/report")
async def generate_report(req: ReportRequest, request: Request):
    """
    Génère le rapport médical structuré d'une session terminée.
    Appelé par le frontend quand needs_report=True.
    """
    rag = _get_pipeline(request)

    try:
        report = await rag.analyze_symptoms_for_report(req.session_id)
    except Exception as e:
        logger.error(f"Erreur génération rapport [{req.session_id}] : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur rapport : {e}")

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Session introuvable ou données insuffisantes.",
        )

    return {"status": "success", "session_id": req.session_id, "report": report}


@router.get("/health")
async def rag_health(request: Request):
    """État réel du pipeline RAG — pour monitoring et dashboard."""
    rag = getattr(request.app.state, "rag", None)
    if not rag:
        return {"status": "unavailable", "initialized": False}

    stats = rag.get_stats()
    return {
        "status": "ok",
        "initialized": stats.get("rag_initialized", False),
        "chunks_indexed": stats.get("rag_chunks", 0),
        "engine": stats.get("engine", "unknown"),
        "total_steps": stats.get("total_steps", 10),
    }
