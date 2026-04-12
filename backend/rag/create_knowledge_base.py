import json
from pathlib import Path

# -----------------------------
# 1. Directives OMS (structure, pas les questions brutes)
# -----------------------------
OMS_RULES = {
    "identification": {
        "title": "Identification du patient",
        "items": [
            {"key": "nom/pseudonyme", "type": "text", "required": True},
            {"key": "âge", "type": "number", "required": True},
            {"key": "sexe", "type": "choice", "options": ["Homme", "Femme"], "required": True},
            {"key": "lieu de résidence", "type": "text"},
            {"key": "téléphone de contact", "type": "phone", "sensitive": True}
        ]
    },
    "symptomes_non_compliques": {
        "title": "Symptômes non compliqués",
        "items": [
            {"key": "fièvre", "type": "yes_no", "required": True, "follow_up": "durée fièvre (jours)"},
            {"key": "frissons/sueurs", "type": "yes_no"},
            {"key": "maux de tête", "type": "yes_no"},
            {"key": "nausées/vomissements", "type": "yes_no"},
            {"key": "fatigue/faiblesse", "type": "yes_no"}
        ]
    },
    "symptomes_graves": {
        "title": "Symptômes graves (alerte OMS)",
        "items": [
            {"key": "convulsions", "type": "yes_no"},
            {"key": "difficulté respiratoire", "type": "yes_no"},
            {"key": "coma/confusion", "type": "yes_no"},
            {"key": "saignements inhabituels", "type": "yes_no"},
            {"key": "incapacité à boire/manger/allaiter", "type": "yes_no"}
        ]
    },
    "groupes_a_risques": {
        "title": "Groupes vulnérables",
        "items": [
            {"key": "grossesse", "type": "yes_no", "sensitive": True},
            {"key": "enfant <5 ans malade", "type": "yes_no"},
            {"key": "maladie chronique", "type": "choice", 
             "options": ["Aucune", "Diabète", "VIH", "Drépanocytose", "Autre"]}
        ]
    },
    "contexte_transmission": {
        "title": "Contexte de transmission",
        "items": [
            {"key": "voyage récent zone paludisme", "type": "yes_no", "follow_up": "lieu/date du retour"},
            {"key": "exposition moustiques", "type": "choice", 
             "options": ["Souvent", "Parfois", "Rarement", "Jamais"]}
        ]
    },
    "cloture_conversation": {
        "title": "Clôture",
        "items": [
            {"key": "commentaires libres", "type": "text"},
            {"key": "consentement partage rapport", "type": "yes_no", "sensitive": True}
        ]
    }
}

# -----------------------------
# 2. Génération automatique
# -----------------------------
def generate_questions():
    kb = {"sections": []}
    q_counter = 1

    for section_id, section in OMS_RULES.items():
        sec = {"id": section_id, "title": section["title"], "questions": []}
        for item in section["items"]:
            q = {
                "id": f"q{q_counter:03d}",
                "text": build_question_text(item),
                "type": item.get("type", "text"),
                "required": item.get("required", False),
                "sensitive": item.get("sensitive", False),
                "priority": q_counter
            }
            if "options" in item:
                q["options"] = item["options"]

            sec["questions"].append(q)
            q_counter += 1

            # follow-up
            if "follow_up" in item:
                sec["questions"].append({
                    "id": f"q{q_counter:03d}",
                    "text": build_question_text({"key": item["follow_up"]}),
                    "type": "text",
                    "required": True,
                    "priority": q_counter
                })
                q_counter += 1

        kb["sections"].append(sec)
    return kb


def build_question_text(item: dict) -> str:
    """Construit une question fermée/semi-fermée adaptée."""
    key = item["key"] if isinstance(item, dict) else item

    mapping = {
        "nom/pseudonyme": "Quel prénom ou pseudonyme souhaitez-vous utiliser ?",
        "âge": "Quel est votre âge (en années) ?",
        "sexe": "Quel est votre sexe ?",
        "lieu de résidence": "Où résidez-vous actuellement (ville/pays) ?",
        "téléphone de contact": "Veuillez indiquer un numéro de téléphone (facultatif).",
        "fièvre": "Avez-vous eu de la fièvre ces derniers jours ? (Oui/Non)",
        "durée fièvre (jours)": "Depuis combien de jours avez-vous de la fièvre ?",
        "frissons/sueurs": "Avez-vous ressenti des frissons ou sueurs ? (Oui/Non)",
        "maux de tête": "Avez-vous eu des maux de tête ? (Oui/Non)",
        "nausées/vomissements": "Avez-vous eu des nausées ou vomissements ? (Oui/Non)",
        "fatigue/faiblesse": "Vous sentez-vous fatigué(e) ou faible ? (Oui/Non)",
        "convulsions": "Avez-vous eu des convulsions récentes ? (Oui/Non)",
        "difficulté respiratoire": "Avez-vous eu des difficultés à respirer ? (Oui/Non)",
        "coma/confusion": "Avez-vous perdu connaissance ou eu un état de confusion ? (Oui/Non)",
        "saignements inhabituels": "Avez-vous eu des saignements inhabituels ? (Oui/Non)",
        "incapacité à boire/manger/allaiter": "Avez-vous eu une incapacité à boire, manger ou allaiter ? (Oui/Non)",
        "grossesse": "Êtes-vous enceinte actuellement ? (Oui/Non)",
        "enfant <5 ans malade": "Un enfant de moins de 5 ans dans votre foyer présente-t-il des symptômes ? (Oui/Non)",
        "maladie chronique": "Souffrez-vous d'une maladie chronique ?",
        "voyage récent zone paludisme": "Avez-vous voyagé récemment dans une zone de paludisme ? (Oui/Non)",
        "lieu/date du retour": "Si oui, précisez la région/pays et la date du retour.",
        "exposition moustiques": "À quelle fréquence êtes-vous exposé(e) aux moustiques ?",
        "commentaires libres": "Souhaitez-vous ajouter des informations pour le professionnel de santé ?",
        "consentement partage rapport": "Autorisez-vous l’envoi de ce rapport au professionnel de santé ? (Oui/Non)"
    }
    return mapping.get(key, f"Pouvez-vous préciser : {key} ?")

# -----------------------------
# 3. Sauvegarde
# -----------------------------
def save_knowledge_base(output_path="backend/rag/knowledge_base.json"):
    kb = generate_questions()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    print(f"✅ Knowledge base générée ({sum(len(s['questions']) for s in kb['sections'])} questions) → {output_path}")

# -----------------------------
# 4. Main
# -----------------------------
if __name__ == "__main__":
    save_knowledge_base()
