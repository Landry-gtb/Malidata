import os
import logging
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Dossier de stockage des PDFs 
BASE_DIR  = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ── Modèles Pydantic ─────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
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


def _safe_filename(filename: str) -> Path:
    """
    Valide que filename est un nom de fichier simple (pas un chemin).
    Lève HTTPException 400 si une tentative de path traversal est détectée.

    Ex. valide   : rapport_malaria_abc123_20250101_120000.pdf
    Ex. invalide : ../../.env  ou  /etc/passwd
    """
    # Extrait uniquement le dernier composant
    safe = Path(filename).name

    # Refuse les noms qui ont été modifiés 
    if safe != filename:
        logger.warning(f"Tentative de path traversal bloquée : '{filename}'")
        raise HTTPException(status_code=400, detail="Nom de fichier invalide.")

    # N'autorise que les PDFs générés par Malidata
    if not safe.endswith(".pdf") or not safe.startswith("rapport_malaria_"):
        raise HTTPException(status_code=400, detail="Fichier non autorisé.")

    return REPORTS_DIR / safe


# ── Endpoints ────────────────────────────────────────────────────────

@router.post("/generate")
async def generate_report(request: Request, req: GenerateReportRequest):
    """
    Génère un rapport PDF pour une session terminée.
    Appelé par le frontend quand il reçoit needs_report=True.

    Flux :
      1. Récupère les données collectées via SessionManager (Redis v2)
      2. Génère l'analyse structurée via analyze_symptoms_for_report(session_id)
      3. Produit le PDF via generate_medical_report_pdf()
      4. Retourne l'URL de téléchargement
    """
    rag = _get_pipeline(request)

    # ── 1. Lecture session via SessionManager ──
    try:
        state = rag.session_manager.get(req.session_id)
    except Exception as e:
        logger.error(f"Erreur lecture session [{req.session_id}] : {e}")
        raise HTTPException(status_code=500, detail="Erreur accès session Redis.")

    if not state or not any(v for v in state.get("collected_data", {}).values()):
        raise HTTPException(
            status_code=404,
            detail="Session introuvable ou données insuffisantes pour le rapport.",
        )

    if not state.get("completed"):
        raise HTTPException(
            status_code=400,
            detail="Le questionnaire n'est pas encore terminé.",
        )

    # ── 2. Analyse médicale structurée ──────────────────────────────
    try:
        analysis = await rag.analyze_symptoms_for_report(req.session_id)
    except Exception as e:
        logger.error(f"Erreur analyse [{req.session_id}] : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analyse : {e}")

    # ── 3. Génération PDF ────────────────────────────────────────────
    try:
        from utils.pdf_utils import generate_medical_report_pdf

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"rapport_malaria_{req.session_id[:8]}_{timestamp}.pdf"
        filepath  = REPORTS_DIR / filename

        generate_medical_report_pdf(
            filepath=str(filepath),
            user_info=state["collected_data"],
            responses=state.get("memory", []),
            analysis=analysis,
            session_id=req.session_id,
        )
    except Exception as e:
        logger.error(f"Erreur PDF [{req.session_id}] : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur génération PDF : {e}")

    logger.info(f"✅ Rapport généré : {filename}")

    return {
        "status": "success",
        "filename": filename,
        "download_url": f"/api/reports/download/{filename}",
        "message": "Rapport généré avec succès.",
    }


@router.get("/download/{filename}")
def download_report(filename: str):
    """
    Télécharge un rapport PDF.
    Validation stricte du nom de fichier.
    """
    filepath = _safe_filename(filename)

    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Rapport non trouvé.")

    return FileResponse(
        str(filepath),
        media_type="application/pdf",
        filename=filename,
    )


@router.get("/list")
def list_reports():
    """Liste tous les rapports PDF disponibles (dashboard médecin)."""
    try:
        files = [
            {
                "filename": f.name,
                "created": datetime.fromtimestamp(f.stat().st_ctime).isoformat(),
                "size_kb": round(f.stat().st_size / 1024, 1),
                "download_url": f"/api/reports/download/{f.name}",
            }
            for f in REPORTS_DIR.glob("rapport_malaria_*.pdf")
        ]
        return {
            "reports": sorted(files, key=lambda x: x["created"], reverse=True),
            "count": len(files),
        }
    except Exception as e:
        logger.error(f"Erreur listing rapports : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur listing : {e}")
