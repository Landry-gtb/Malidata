"""
RAGPipeline v2.1 — Production
═══════════════════════════════════════════════════════════════════
Corrections appliquées vs v1 :
  #1  DEMO_STATE global      → SessionManager Redis (session_id)
  #2  validate_input (bool)  → _extract_entity (valeur réelle, LLM JSON-mode)
  #3  Prompts verbeux        → PERSONA fixe + max_tokens=300
  #4  RAG systématique       → RAG conditionnel (étapes 3 et 9 uniquement)
  #5  Mélange tu/vous        → PERSONA impose le vouvoiement
  #6  temperature=0.5        → 0.0 extraction / 0.1 réponse
  #7  4 étapes seulement     → 10 étapes (3 identification + 7 médicales)
  #8  Angle mort questions   → _detect_intent + _handle_user_question
        Si l'utilisateur pose une question ou exprime une incompréhension,
        le LLM répond et re-pose la même question (step inchangé).

Breaking changes pour les routes FastAPI :
  - generate_response(query, ...) → generate_response(session_id, query)
  - analyze_symptoms_for_report(user_info, responses) → analyze_symptoms_for_report(session_id)
  - Appel d'init : envoyer query="__INIT__" pour démarrer une session
═══════════════════════════════════════════════════════════════════
"""

import os
import json
import logging
import requests
import redis
from pathlib import Path
from typing import Optional, Dict, List, Any, Tuple

from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, PyPDFLoader
from dotenv import load_dotenv
from fastapi.concurrency import run_in_threadpool
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()


# ═══════════════════════════════════════════════════════════════════
# SECTION 1 — CONFIGURATION MÉTIER
# Modifier uniquement cette section pour ajuster le questionnaire.
# ═══════════════════════════════════════════════════════════════════

STEPS: List[Dict] = [
    # ── Phase identification (étapes 0-2) ──────────────────────────
    {
        "id": 0,
        "field": "nom",
        "phase": "identification",
        "question": (
            "Bonjour, je suis Malidata, votre assistant de pré-consultation. "
            "Pour commencer, quel est votre prénom ?"
        ),
        "followup": "Je n'ai pas saisi votre prénom. Pourriez-vous me l'indiquer ?",
        "use_rag": False,
    },
    {
        "id": 1,
        "field": "age",
        "phase": "identification",
        "question": "Quel est votre âge ?",
        "followup": "Pourriez-vous m'indiquer votre âge en chiffres ?",
        "use_rag": False,
    },
    {
        "id": 2,
        "field": "sexe",
        "phase": "identification",
        "question": "Êtes-vous un homme ou une femme ?",
        "followup": "Pourriez-vous préciser votre sexe : homme ou femme ?",
        "use_rag": False,
    },
    # ── Phase médicale (étapes 3-9) ────────────────────────────────
    {
        "id": 3,
        "field": "symptomes_principaux",
        "phase": "medical",
        "question": "Quels symptômes vous ont amené(e) à consulter aujourd'hui ? Décrivez-les librement.",
        "followup": "Pourriez-vous décrire vos symptômes principaux en quelques mots ?",
        "use_rag": True,   # RAG activé ici pour enrichir le contexte
    },
    {
        "id": 4,
        "field": "fievre",
        "phase": "medical",
        "question": "Avez-vous de la fièvre ? Si oui, quelle est votre température ?",
        "followup": "Avez-vous mesuré votre température ? Pouvez-vous m'en donner la valeur approximative ?",
        "use_rag": False,
    },
    {
        "id": 5,
        "field": "duree_symptomes",
        "phase": "medical",
        "question": "Depuis combien de temps ressentez-vous ces symptômes ?",
        "followup": "Depuis combien de jours ou de semaines êtes-vous souffrant(e) ?",
        "use_rag": False,
    },
    {
        "id": 6,
        "field": "antecedents_malaria",
        "phase": "medical",
        "question": "Avez-vous déjà eu la malaria auparavant ? Si oui, quand ?",
        "followup": "Avez-vous des antécédents de malaria ou de paludisme ?",
        "use_rag": False,
    },
    {
        "id": 7,
        "field": "medicaments_en_cours",
        "phase": "medical",
        "question": "Prenez-vous actuellement des médicaments ? Si oui, lesquels ?",
        "followup": "Pouvez-vous préciser les médicaments que vous prenez en ce moment ?",
        "use_rag": False,
    },
    {
        "id": 8,
        "field": "zone_geographique",
        "phase": "medical",
        "question": (
            "Avez-vous voyagé récemment dans une zone à risque paludéen "
            "(forêt, zone rurale, pays endémique) ?"
        ),
        "followup": (
            "Avez-vous séjourné dans une zone forestière, rurale "
            "ou un pays endémique ces dernières semaines ?"
        ),
        "use_rag": False,
    },
    {
        "id": 9,
        "field": "autres_symptomes",
        "phase": "medical",
        "question": (
            "Avez-vous d'autres symptômes : nausées, vomissements, "
            "maux de tête ou frissons ?"
        ),
        "followup": "Y a-t-il d'autres symptômes que vous souhaitez signaler ?",
        "use_rag": True,   # RAG activé ici pour compléter le tableau clinique
    },
]

TOTAL_STEPS: int = len(STEPS)  # 10
SESSION_TTL: int = 3600        # 1 heure

# Persona injectée dans CHAQUE appel LLM — garantit le vouvoiement et la concision
PERSONA: str = (
    "Tu es Malidata, un assistant de pré-consultation médicale pour la malaria. "
    "Règles STRICTES et NON NÉGOCIABLES : "
    "1. Utilise TOUJOURS le vouvoiement (vous, votre, vos). JAMAIS le tutoiement. "
    "2. Tes réponses font MAXIMUM 2 phrases. "
    "3. Tu ne fournis AUCUNE explication médicale non sollicitée. "
    "4. Tu poses UNE SEULE question à la fois. "
    "5. Tu ne demandes JAMAIS d'email, téléphone ou coordonnées personnelles. "
    "6. Tu ne répètes JAMAIS une question à laquelle il a déjà répondu. "
)

# Prompts d'extraction LLM — JSON strict, temperature=0.0
# Uniquement pour les champs structurés. Les champs libres n'utilisent pas le LLM.
EXTRACTION_PROMPTS: Dict[str, str] = {
    "nom": (
        "Extrait le prénom ou nom propre dans ce message. "
        "Réponds UNIQUEMENT en JSON valide : {\"value\": \"Alice\"} ou {\"value\": null}. "
        "Règle : min 2 caractères alphabétiques, pas un mot banal "
        "(bonjour, ok, oui, non, salut, test, hello, allô, bien, merci)."
    ),
    "age": (
        "Extrait l'âge (nombre entier d'années) dans ce message. "
        "Réponds UNIQUEMENT en JSON valide : {\"value\": 28} ou {\"value\": null}. "
        "L'âge doit être un entier entre 1 et 120. "
        "Accepte : '28 ans', 'j\\'ai 28', 'vingt-huit ans' → 28."
    ),
    "sexe": (
        "Extrait le sexe biologique dans ce message. "
        "Réponds UNIQUEMENT en JSON valide : "
        "{\"value\": \"Homme\"}, {\"value\": \"Femme\"}, ou {\"value\": null}. "
        "Mappings acceptés : "
        "homme / masculin / garçon / m / male → \"Homme\". "
        "femme / féminin / fille / f / female → \"Femme\"."
    ),
}


# ═══════════════════════════════════════════════════════════════════
# SECTION 2 — GESTION DE SESSION REDIS
# ═══════════════════════════════════════════════════════════════════

def _empty_session() -> Dict:
    """Retourne une session vierge avec tous les champs à None."""
    return {
        "step": 0,
        "completed": False,
        "collected_data": {step["field"]: None for step in STEPS},
        "memory": [],   # [{role: "user"|"assistant", content: "..."}]
    }


class SessionManager:
    """
    Gère la persistance de l'état conversationnel dans Redis.
    Chaque session est isolée par session_id — multi-utilisateurs natif.
    """

    def __init__(self) -> None:
        self._redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            decode_responses=True,
        )

    def _key(self, session_id: str) -> str:
        return f"malidata:session:{session_id}"

    def get(self, session_id: str) -> Dict:
        raw = self._redis.get(self._key(session_id))
        if raw is None:
            return _empty_session()
        return json.loads(raw)

    def save(self, session_id: str, state: Dict) -> None:
        self._redis.setex(
            self._key(session_id),
            SESSION_TTL,
            json.dumps(state, ensure_ascii=False),
        )

    def reset(self, session_id: str) -> Dict:
        """Remet la session à zéro et retourne l'état initial."""
        state = _empty_session()
        self.save(session_id, state)
        return state

    def delete(self, session_id: str) -> None:
        self._redis.delete(self._key(session_id))


# ═══════════════════════════════════════════════════════════════════
# SECTION 3 — PIPELINE RAG
# ═══════════════════════════════════════════════════════════════════

class RAGPipeline:
    """
    Orchestrateur principal de Malidata.
    Responsabilités :
      - Initialisation et gestion de l'index FAISS
      - Extraction d'entités via LLM JSON-mode
      - State machine conversationnelle (10 étapes)
      - Persistance de session via Redis
      - Génération de rapports médicaux structurés
    """

    def __init__(
        self,
        vector_store_path: Optional[str] = None,
        data_path: Optional[str] = None,
    ) -> None:
        self.vector_store_path = vector_store_path or os.getenv(
            "VECTOR_STORE_PATH", "/app/storage/faiss_index.idx"
        )
        self.data_path = data_path or str(Path(__file__).parent / "data")
        self.initialized = False
        self.faiss_index = None
        self.document_chunks: List[str] = []
        self.chunk_metadata: List[Dict] = []
        self.embedding_model = None
        self.api_key = os.getenv("GROQ_API_KEY")
        self.session_manager = SessionManager()

        try:
            logger.info("Chargement du modèle d'embedding...")
            self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("✅ Embedding prêt.")
        except Exception as e:
            logger.error(f"❌ Erreur embedding : {e}")
            raise

    # ── Initialisation FAISS ────────────────────────────────────────

    async def initialize(self) -> None:
        if self.initialized:
            return
        try:
            index_path = Path(self.vector_store_path)
            if index_path.exists():
                await run_in_threadpool(self._load_index)
                logger.info("✅ Index FAISS chargé depuis le disque.")
            else:
                logger.info("Construction de l'index FAISS...")
                await run_in_threadpool(self._build_index)
                logger.info("✅ Index FAISS construit.")
            self.initialized = True
        except Exception as e:
            logger.error(f"❌ Erreur init RAG : {e}")

    def _build_index(self) -> None:
        import faiss

        path = Path(self.data_path)
        path.mkdir(parents=True, exist_ok=True)

        loader = DirectoryLoader(str(path), glob="**/*.pdf", loader_cls=PyPDFLoader)
        docs = loader.load()

        if not docs:
            logger.warning("⚠️  Aucun PDF trouvé — index vide créé.")
            self._create_empty_index()
            return

        splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = splitter.split_documents(docs)
        texts = [c.page_content for c in chunks]

        emb = self.embedding_model.encode(
            texts, convert_to_numpy=True, show_progress_bar=False
        )
        self.faiss_index = faiss.IndexFlatL2(emb.shape[1])
        self.faiss_index.add(emb.astype(np.float32))
        self.document_chunks = texts
        self.chunk_metadata = [
            {
                "source": c.metadata.get("source"),
                "page": c.metadata.get("page"),
            }
            for c in chunks
        ]
        self._save_index()

    def _create_empty_index(self) -> None:
        import faiss

        self.faiss_index = faiss.IndexFlatL2(384)
        self._save_index()

    def _save_index(self) -> None:
        import faiss

        p = Path(self.vector_store_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.faiss_index, str(p))
        with open(f"{p}.meta", "w", encoding="utf-8") as f:
            json.dump(
                {"chunks": self.document_chunks, "meta": self.chunk_metadata},
                f,
                ensure_ascii=False,
            )

    def _load_index(self) -> None:
        import faiss

        self.faiss_index = faiss.read_index(self.vector_store_path)
        with open(f"{self.vector_store_path}.meta", "r", encoding="utf-8") as f:
            d = json.load(f)
            self.document_chunks = d.get("chunks", [])
            self.chunk_metadata = d.get("meta", [])

    # ── Recherche RAG ───────────────────────────────────────────────

    async def query(self, q: str, k: int = 3) -> Dict:
        """Recherche sémantique dans l'index FAISS. Retourne les k sources les plus proches."""
        if not self.initialized or not self.document_chunks:
            return {"sources": []}
        try:
            emb = await run_in_threadpool(
                self.embedding_model.encode, [q], convert_to_numpy=True
            )
            D, I = await run_in_threadpool(
                self.faiss_index.search,
                emb.astype(np.float32),
                min(k, len(self.document_chunks)),
            )
            return {
                "sources": [
                    {
                        "content": self.document_chunks[idx],
                        "metadata": self.chunk_metadata[idx],
                    }
                    for idx in I[0]
                    if idx != -1
                ]
            }
        except Exception as e:
            logger.error(f"Erreur RAG query : {e}")
            return {"sources": []}

    # ── Appel LLM ───────────────────────────────────────────────────

    async def _call_llm_chat(
        self,
        messages: List[Dict],
        json_mode: bool = False,
        temperature: float = 0.1,
    ) -> str:
        """
        Appel à l'API Groq.
        max_tokens=300 : contraint volontairement pour éviter la verbosité.
        """
        if not self.api_key:
            logger.error("GROQ_API_KEY manquante.")
            return "Service indisponible."

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 300,  # Intentionnellement bas — empêche les réponses essay
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            resp = await run_in_threadpool(
                lambda: requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=15,
                )
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.error("Timeout Groq API.")
            return "Délai de réponse dépassé. Veuillez réessayer."
        except Exception as e:
            logger.error(f"Erreur LLM : {e}")
            return "Erreur de connexion au service IA."

    # ── Extraction d'entités ─────────────────────────────────────────

    async def _extract_entity(
        self, field: str, user_input: str
    ) -> Tuple[bool, Any]:
        """
        Extrait une valeur structurée depuis une réponse en langage naturel.

        Retourne (succès: bool, valeur: Any).

        Pour les champs structurés (nom, âge, sexe) : appel LLM JSON-mode,
        temperature=0.0 pour une extraction déterministe.

        Pour les champs libres (symptômes, médicaments, etc.) : accepte
        tout texte d'au moins 3 caractères — pas besoin du LLM.
        """
        # Champs libres — validation légère uniquement
        if field not in EXTRACTION_PROMPTS:
            value = user_input.strip()
            if len(value) >= 3:
                return True, value
            return False, None

        # Champs structurés — extraction LLM JSON-mode
        messages = [
            {"role": "system", "content": EXTRACTION_PROMPTS[field]},
            {"role": "user", "content": user_input},
        ]
        try:
            raw = await self._call_llm_chat(
                messages, json_mode=True, temperature=0.0
            )
            data = json.loads(raw)
            value = data.get("value")
            if value is None:
                return False, None
            return True, value
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Extraction '{field}' échouée sur '{user_input}' : {e}")
            return False, None

    # ── Détection d'intention ────────────────────────────────────────

    async def _detect_intent(self, query: str, current_field: str) -> str:
        """
        Classifie le message de l'utilisateur en deux catégories :
          - "question"  : l'utilisateur pose une question ou exprime
                          une incompréhension (ex: "Pourquoi avez-vous
                          besoin de mon âge ?", "Je ne comprends pas")
          - "response"  : l'utilisateur répond à la question posée

        Retourne "question" ou "response".
        Utilise le LLM JSON-mode à temperature=0.0 pour une
        classification déterministe.
        """
        system = (
            "Tu es un classificateur d'intention. "
            "Analyse le message et détermine s'il est une QUESTION/INCOMPRÉHENSION "
            "ou une RÉPONSE à une question médicale. "
            "Réponds UNIQUEMENT en JSON valide : "
            "{\"intent\": \"question\"} ou {\"intent\": \"response\"}. "
            "Exemples de QUESTION : "
            "'Pourquoi avez-vous besoin de ça ?', "
            "'Je ne comprends pas', "
            "'C\\'est quoi un antécédent ?', "
            "'À quoi ça sert ?', "
            "'Qu\\'est-ce que vous voulez dire ?'. "
            "Exemples de RÉPONSE : "
            "'Jean', '38 ans', 'Femme', 'J\\'ai de la fièvre', "
            "'Oui', 'Non', 'Paracétamol', 'Depuis 3 jours'."
        )
        try:
            raw = await self._call_llm_chat(
                [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": query},
                ],
                json_mode=True,
                temperature=0.0,
            )
            data = json.loads(raw)
            intent = data.get("intent", "response")
            return intent if intent in ("question", "response") else "response"
        except Exception as e:
            logger.warning(f"Détection intention échouée : {e} — fallback 'response'")
            return "response"

    async def _handle_user_question(
        self,
        query: str,
        current_idx: int,
        state: Dict,
        session_id: str,
    ) -> Dict:
        """
        Gère le cas où l'utilisateur pose une question ou exprime
        une incompréhension au lieu de répondre.

        Comportement :
          1. Le LLM répond à la question en restant dans le contexte
             médical malaria (avec RAG si disponible).
          2. Re-pose EXACTEMENT la question courante pour ne pas
             perdre le fil du questionnaire.
          3. NE fait PAS avancer le step — on reste sur la même étape.
        """
        step_cfg   = STEPS[current_idx]
        current_q  = step_cfg["question"]

        # Enrichissement RAG si l'index est disponible
        rag_context = ""
        if self.initialized and self.document_chunks:
            rag_result = await self.query(query, k=2)
            sources = rag_result.get("sources", [])
            if sources:
                rag_context = "\n\nContexte médical disponible :\n" + "\n".join(
                    s["content"][:300] for s in sources
                )

        system = (
            f"{PERSONA}\n"
            "L'utilisateur a posé une question ou exprimé une incompréhension "
            "au lieu de répondre à la question du questionnaire. "
            "Fais les deux choses suivantes dans cet ordre : "
            "1. Réponds brièvement à sa question en 1-2 phrases maximum "
            "   (utilise le contexte médical si pertinent, reste factuel). "
            "2. Re-pose EXACTEMENT cette question sans la modifier : "
            f"   '{current_q}'"
            f"{rag_context}"
        )

        # Inclure l'historique récent pour que le LLM ait le contexte
        recent_memory = state.get("memory", [])[-4:]  # 4 derniers messages max

        messages = (
            [{"role": "system", "content": system}]
            + recent_memory
            + [{"role": "user", "content": query}]
        )

        answer = await self._call_llm_chat(messages, temperature=0.1)

        # Sauvegarder l'échange sans faire avancer le step
        state["memory"].append({"role": "user",      "content": query})
        state["memory"].append({"role": "assistant", "content": answer})
        self.session_manager.save(session_id, state)

        logger.info(
            f"[{session_id}] Question utilisateur détectée à l'étape "
            f"{current_idx} — step inchangé."
        )

        return {
            "answer":    answer,
            "step":      current_idx,  # step inchangé — même étape
            "total":     TOTAL_STEPS,
            "completed": False,
        }

    # ═══════════════════════════════════════════════════════════════
    # SECTION 4 — ORCHESTRATEUR PRINCIPAL
    # ═══════════════════════════════════════════════════════════════

    async def generate_response(
        self, session_id: str, query: str
    ) -> Dict:
        """
        Point d'entrée unique du pipeline conversationnel.

        Paramètres
        ----------
        session_id : str
            Identifiant unique de la session (fourni par le frontend).
        query : str
            Message de l'utilisateur, ou "__INIT__" pour démarrer une session.

        Retourne
        --------
        Dict avec les clés :
            answer       : str   — réponse à afficher
            step         : int   — étape courante (0..TOTAL_STEPS)
            total        : int   — nombre total d'étapes
            completed    : bool  — questionnaire terminé
            needs_report : bool  — présent et True si rapport à générer
            sources      : list  — sources RAG (optionnel)
            collected_data : dict — données collectées (présent si completed=True)
        """

        # ── CAS 1 : Initialisation de session ──────────────────────
        if query.strip() == "__INIT__":
            state = self.session_manager.reset(session_id)
            logger.info(f"Session {session_id} initialisée.")
            return {
                "answer": STEPS[0]["question"],
                "step": 0,
                "total": TOTAL_STEPS,
                "completed": False,
            }

        # ── CAS 2 : Chargement de session existante ─────────────────
        state = self.session_manager.get(session_id)

        # Session déjà terminée
        if state.get("completed"):
            return {
                "answer": "Votre dossier a déjà été soumis. Merci.",
                "completed": True,
            }

        current_idx: int = state["step"]

        # Dépassement d'index (sécurité)
        if current_idx >= TOTAL_STEPS:
            state["completed"] = True
            self.session_manager.save(session_id, state)
            return {
                "answer": "Merci. Votre dossier est complet.",
                "completed": True,
                "needs_report": True,
            }

        step_cfg = STEPS[current_idx]
        field: str = step_cfg["field"]

        # ── CAS 3a : Détection d'intention ─────────────────────────
        # AVANT d'extraire, on vérifie si l'utilisateur pose une
        # question ou exprime une incompréhension.
        # Si oui → on répond + on re-pose la même question (step inchangé).
        # Si non → flux normal d'extraction.
        intent = await self._detect_intent(query, field)

        if intent == "question":
            return await self._handle_user_question(
                query, current_idx, state, session_id
            )

        # ── CAS 3b : Extraction de l'entité attendue ────────────────
        success, extracted_value = await self._extract_entity(field, query)

        if not success:
            # Réponse courte prédéfinie — PAS de LLM pour les erreurs de validation
            # → élimine la verbosité médicale observée en v1
            logger.info(
                f"[{session_id}] Extraction '{field}' échouée "
                f"pour : '{query[:50]}'"
            )
            return {
                "answer": step_cfg["followup"],
                "step": current_idx,
                "total": TOTAL_STEPS,
                "completed": False,
            }

        # ── CAS 4 : Avancement dans la state machine ────────────────
        state["collected_data"][field] = extracted_value
        state["memory"].append({"role": "user", "content": query})
        state["step"] += 1
        next_idx: int = state["step"]

        logger.info(
            f"[{session_id}] Étape {current_idx} → '{field}' = "
            f"'{extracted_value}' | Étape suivante : {next_idx}"
        )

        # ── CAS 5 : Fin du questionnaire ────────────────────────────
        if next_idx >= TOTAL_STEPS:
            nom = state["collected_data"].get("nom", "")
            farewell = (
                f"Merci {nom}. "
                "J'ai bien enregistré toutes vos informations. "
                "Votre dossier est transmis pour analyse médicale."
            )
            state["completed"] = True
            state["memory"].append({"role": "assistant", "content": farewell})
            self.session_manager.save(session_id, state)
            return {
                "answer": farewell,
                "step": TOTAL_STEPS,
                "total": TOTAL_STEPS,
                "completed": True,
                "needs_report": True,
                "collected_data": state["collected_data"],
            }

        # ── CAS 6 : Génération de la réponse intermédiaire ──────────
        next_cfg = STEPS[next_idx]
        next_question: str = next_cfg["question"]

        # RAG uniquement aux étapes qui le nécessitent (3 et 9)
        rag_sources: List[Dict] = []
        if next_cfg.get("use_rag") and self.initialized and self.document_chunks:
            rag_result = await self.query(query)
            rag_sources = rag_result.get("sources", [])

        # Prompt de confirmation + question suivante
        # Le LLM confirme en 1 phrase, puis pose next_question mot pour mot.
        confirmation_system = (
            f"{PERSONA}\n"
            "L'utilisateur vient de répondre. "
            "En UNE phrase maximum, confirme que tu as bien noté sa réponse "
            "(sans la répéter en entier ni ajouter d'explication médicale). "
            f"Puis pose EXACTEMENT cette question, sans la modifier : "
            f"'{next_question}'"
        )

        answer = await self._call_llm_chat(
            [
                {"role": "system", "content": confirmation_system},
                {"role": "user", "content": query},
            ],
            temperature=0.1,
        )

        state["memory"].append({"role": "assistant", "content": answer})
        self.session_manager.save(session_id, state)

        return {
            "answer": answer,
            "step": next_idx,
            "total": TOTAL_STEPS,
            "completed": False,
            "sources": rag_sources,
        }

    # ═══════════════════════════════════════════════════════════════
    # SECTION 5 — GÉNÉRATION DE RAPPORT
    # ═══════════════════════════════════════════════════════════════

    async def analyze_symptoms_for_report(
        self, session_id: str
    ) -> Dict[str, Any]:
        """
        Génère un rapport médical structuré à partir des données collectées.

        Paramètre
        ---------
        session_id : str — identifiant de la session Redis terminée.

        Retourne un dict avec tous les champs du rapport PDF.
        """
        state = self.session_manager.get(session_id)
        data: Dict = state.get("collected_data", {})

        if not any(v for v in data.values()):
            logger.warning(f"[{session_id}] Données vides pour le rapport.")
            return self._fallback_report(data)

        prompt_msgs = [
            {
                "role": "system",
                "content": (
                    "Tu es un assistant administratif médical. "
                    "Tu reçois des données de pré-consultation. "
                    "Retourne UNIQUEMENT un JSON valide, sans texte avant ni après, "
                    "sans balises markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Données collectées :\n"
                    f"{json.dumps(data, ensure_ascii=False, indent=2)}\n\n"
                    "Génère exactement ce JSON :\n"
                    "{\n"
                    '  "pseudonyme": "...",\n'
                    '  "age": "...",\n'
                    '  "sexe": "...",\n'
                    '  "contact": "Non renseigné",\n'
                    '  "resume_symptomes": "...",\n'
                    '  "fievre": "...",\n'
                    '  "duree": "...",\n'
                    '  "antecedents": "...",\n'
                    '  "medicaments": "...",\n'
                    '  "zone_risque": "...",\n'
                    '  "autres_symptomes": "...",\n'
                    '  "observations": "Synthèse clinique en 2-3 phrases.",\n'
                    '  "facteurs_risque": ["liste", "des", "facteurs"],\n'
                    '  "niveau_urgence": "Faible | Modéré | Élevé | Critique",\n'
                    '  "recommandations": "..."\n'
                    "}\n\n"
                    "Règle : si un champ est absent des données, mets "
                    '"Non renseigné".'
                ),
            },
        ]

        resp_text = await self._call_llm_chat(
            prompt_msgs, json_mode=True, temperature=0.1
        )

        try:
            cleaned: Dict = json.loads(resp_text)

            # Normalisation de facteurs_risque
            risks = cleaned.get("facteurs_risque", ["Non identifié"])
            if isinstance(risks, str):
                risks = [risks]
            cleaned["facteurs_risque"] = risks

            # Garantit que contact est toujours non renseigné (jamais de téléphone)
            cleaned["contact"] = "Non renseigné"

            return cleaned

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Erreur parsing rapport [{session_id}] : {e}")
            return self._fallback_report(data)

    def _fallback_report(self, data: Dict) -> Dict[str, Any]:
        """Rapport de secours en cas d'erreur LLM — évite de retourner None."""
        return {
            "pseudonyme": data.get("nom", "Inconnu"),
            "age": str(data.get("age", "N/A")),
            "sexe": data.get("sexe", "N/A"),
            "contact": "Non renseigné",
            "resume_symptomes": data.get("symptomes_principaux", "Non précisé"),
            "fievre": data.get("fievre", "Non renseigné"),
            "duree": data.get("duree_symptomes", "Non renseigné"),
            "antecedents": data.get("antecedents_malaria", "Non renseigné"),
            "medicaments": data.get("medicaments_en_cours", "Non renseigné"),
            "zone_risque": data.get("zone_geographique", "Non renseigné"),
            "autres_symptomes": data.get("autres_symptomes", "Non renseigné"),
            "observations": "Rapport généré en mode dégradé — vérification manuelle requise.",
            "facteurs_risque": ["Erreur de génération"],
            "niveau_urgence": "Modéré",
            "recommandations": "Consulter un professionnel de santé.",
        }

    # ── Utilitaires ─────────────────────────────────────────────────

    def get_stats(self) -> Dict:
        return {
            "status": "ok",
            "engine": "Groq / llama-3.3-70b-versatile",
            "total_steps": TOTAL_STEPS,
            "rag_initialized": self.initialized,
            "rag_chunks": len(self.document_chunks),
        }