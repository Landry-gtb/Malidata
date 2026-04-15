import uuid
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Modèles Pydantic ────────────────────────────────────────────────

class StartSessionResponse(BaseModel):
    session_id: str
    response: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    response: str
    session_id: str
    step: int = 0
    total: int = 10
    completed: bool = False
    needs_report: bool = False


# ── Helpers ─────────────────────────────────────────────────────────

def _get_pipeline(request: Request):
    """Récupère le pipeline RAG depuis app.state — lève 503 si absent."""
    rag = getattr(request.app.state, "rag", None)
    if not rag:
        raise HTTPException(
            status_code=503,
            detail="Pipeline RAG non initialisé. Réessayez dans quelques secondes.",
        )
    return rag


# ── Endpoints ───────────────────────────────────────────────────────

@router.post("/start", response_model=StartSessionResponse)
async def start_session(request: Request):
    """
    Crée une nouvelle session et retourne le message d'accueil.
    Le session_id généré ici doit être conservé par le frontend
    et transmis dans chaque appel /message.
    """
    rag = _get_pipeline(request)
    session_id = str(uuid.uuid4())

    try:
        result = await rag.generate_response(
            session_id=session_id,
            query="__INIT__",
        )
    except Exception as e:
        logger.error(f"Erreur démarrage session {session_id} : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur démarrage session : {e}")

    return StartSessionResponse(
        session_id=session_id,
        response=result["answer"],
    )


@router.post("/message", response_model=ChatResponse)
async def send_message(request: Request, req: ChatRequest):
    """
    Transmet un message au pipeline et retourne la réponse.
    Le pipeline gère entièrement l'état, l'extraction et la progression.
    """
    if not req.session_id or not req.message.strip():
        raise HTTPException(
            status_code=422,
            detail="session_id et message sont obligatoires.",
        )

    rag = _get_pipeline(request)

    try:
        result = await rag.generate_response(
            session_id=req.session_id,
            query=req.message,
        )
    except Exception as e:
        logger.error(f"Erreur message [{req.session_id}] : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur traitement message : {e}")

    return ChatResponse(
        response=result["answer"],
        session_id=req.session_id,
        step=result.get("step", 0),
        total=result.get("total", 10),
        completed=result.get("completed", False),
        needs_report=result.get("needs_report", False),
    )


@router.get("/history/{session_id}")
async def get_history(session_id: str, request: Request):
    """
    Retourne l'historique et les données collectées d'une session.
    Utilise le SessionManager du pipeline (source de vérité unique).
    """
    rag = _get_pipeline(request)

    try:
        state = rag.session_manager.get(session_id)
    except Exception as e:
        logger.error(f"Erreur lecture session {session_id} : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur lecture historique : {e}")

    return {
        "session_id": session_id,
        "step": state.get("step", 0),
        "completed": state.get("completed", False),
        "collected_data": state.get("collected_data", {}),
        "history": state.get("memory", []),
    }


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, request: Request):
    """Supprime une session Redis (RGPD / fin de consultation)."""
    rag = _get_pipeline(request)
    try:
        rag.session_manager.delete(session_id)
    except Exception as e:
        logger.error(f"Erreur suppression session {session_id} : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur suppression session : {e}")
    return {"status": "deleted", "session_id": session_id}
