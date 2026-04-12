import os
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY manquante dans .env")

logger = logging.getLogger(__name__)

llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    api_key=GEMINI_API_KEY,
    temperature=0.3,
    max_output_tokens=512,
)

def humanize_question(question_text: str, previous_answers: dict, rag_context: str = "") -> str:
    try:
        context_parts = []
        if previous_answers:
            recent = list(previous_answers.items())[-3:]
            for q_id, answer in recent:
                context_parts.append(f"- {answer}")
        
        context_text = "\n".join(context_parts) if context_parts else "Début de conversation"
        
        prompt = (
            f"Tu es un assistant médical empathique.\n\n"
            f"Contexte médical OMS:\n{rag_context[:500] if rag_context else 'Non disponible'}\n\n"
            f"Réponses précédentes du patient:\n{context_text}\n\n"
            f"Question technique à reformuler: {question_text}\n\n"
            f"👉 Reformule cette question de manière:\n"
            f"- Naturelle et conversationnelle\n"
            f"- Empathique\n"
            f"- En français\n"
            f"- SANS donner de diagnostic\n"
            f"- Maximum 2 phrases\n\n"
            f"Question reformulée:"
        )
        
        response = llm.invoke(prompt)
        return response.content.strip()
        
    except Exception as e:
        logger.error(f"Erreur humanize_question: {e}")
        return _humanize_fallback(question_text)

def _humanize_fallback(question_text: str) -> str:
    replacements = {
        "Quel prénom ou pseudonyme": "Comment puis-je vous appeler ?",
        "Quel est votre âge": "Quel âge avez-vous ?",
        "Quel est votre sexe": "Êtes-vous un homme ou une femme ?",
        "Où résidez-vous": "Dans quelle ville habitez-vous ?",
        "Avez-vous eu de la fièvre": "Avez-vous de la fièvre en ce moment ?",
        "Depuis combien de jours": "Depuis quand avez-vous ces symptômes ?",
    }
    
    for old, new in replacements.items():
        if old in question_text:
            return new
    
    return question_text