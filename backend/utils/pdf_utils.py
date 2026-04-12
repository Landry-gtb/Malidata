"""
utils/pdf_utils.py v2
══════════════════════════════════════════════════════════════
Changements vs v1 :
  #1  user_info['pseudonyme'] → user_info['nom']
  #2  user_info['telephone']  → supprimé (non collecté en v2)
  #3  6 champs médicaux ajoutés au PDF :
        fievre · duree_symptomes · antecedents_malaria
        medicaments_en_cours · zone_geographique · autres_symptomes
  #4  Correspondance couleur urgence corrigée (casse insensible)
  #5  Niveau "Critique" ajout couleur bordeaux
  #6  Section 2 : tableau médical détaillé (toutes les réponses)
══════════════════════════════════════════════════════════════
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY


# ── Palette couleurs urgence ──────────────────────────────────────────
# Clés en minuscules normalisées — insensible à la casse en entrée
_URGENCE_COLORS = {
    "faible":   colors.HexColor("#27ae60"),   # vert
    "modéré":   colors.HexColor("#e67e22"),   # orange
    "modere":   colors.HexColor("#e67e22"),   # alias sans accent
    "élevé":    colors.HexColor("#e74c3c"),   # rouge
    "eleve":    colors.HexColor("#e74c3c"),   # alias sans accent
    "critique": colors.HexColor("#7b241c"),   # bordeaux
}

def _urgence_color(niveau: str) -> colors.Color:
    """Retourne la couleur correspondant au niveau d'urgence (casse ignorée)."""
    import unicodedata
    # Normalise : minuscules + suppression des accents pour le fallback
    key = niveau.strip().lower()
    if key in _URGENCE_COLORS:
        return _URGENCE_COLORS[key]
    # Fallback sans accents
    key_no_accent = "".join(
        c for c in unicodedata.normalize("NFD", key)
        if unicodedata.category(c) != "Mn"
    )
    return _URGENCE_COLORS.get(key_no_accent, colors.HexColor("#e67e22"))


# ── Générateur principal ─────────────────────────────────────────────

def generate_medical_report_pdf(
    filepath: str,
    user_info: dict,
    responses: list,
    analysis: dict,
    session_id: str,
) -> None:
    """
    Génère un rapport PDF médical professionnel.

    Paramètres
    ----------
    filepath    : chemin absolu du fichier PDF à créer
    user_info   : dict issu de collected_data (champs v2)
    responses   : liste de messages [{role, content}] issus de memory
    analysis    : dict issu de analyze_symptoms_for_report()
    session_id  : identifiant de session (pour traçabilité)
    """

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Styles personnalisés ─────────────────────────────────────────
    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#2c3e50"),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=12,
        textColor=colors.HexColor("#667eea"),
        spaceAfter=12,
        alignment=TA_CENTER,
    )
    warning_style = ParagraphStyle(
        "Warning",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#c0392b"),
        backColor=colors.HexColor("#ffeaa7"),
        borderPadding=10,
        spaceAfter=16,
        alignment=TA_JUSTIFY,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=11,
        alignment=TA_JUSTIFY,
        spaceAfter=4,
    )
    reco_style = ParagraphStyle(
        "Reco",
        parent=styles["Normal"],
        fontSize=11,
        textColor=colors.HexColor("#27ae60"),
        alignment=TA_JUSTIFY,
    )
    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        alignment=TA_CENTER,
    )

    col_label = 6 * cm
    col_value = 11 * cm

    def _table(data, label_w=col_label, value_w=col_value, header_color="#3498db"):
        t = Table(data, colWidths=[label_w, value_w])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor(header_color)),
            ("TEXTCOLOR",     (0, 0), (0, -1), colors.white),
            ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return t

    def _sep():
        t = Table([[""]], colWidths=[17 * cm])
        t.setStyle(TableStyle([
            ("LINEABOVE", (0, 0), (-1, 0), 1.5, colors.HexColor("#667eea")),
        ]))
        return t

    def _val(d: dict, key: str) -> str:
        v = d.get(key)
        return str(v) if v else "Non renseigné"

    # ════════════════════════════════════════════════════════════════
    # EN-TÊTE
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("RAPPORT D'ÉVALUATION PRÉ-CONSULTATION", title_style))
    story.append(Paragraph("Malaria · Malidata System", subtitle_style))
    story.append(_sep())
    story.append(Spacer(1, 0.4 * cm))

    # Métadonnées du document
    meta_data = [
        ["Date de génération :", datetime.now().strftime("%d/%m/%Y à %H:%M")],
        ["ID de session :",      session_id[:13] + "..."],
        ["Type d'évaluation :",  "Symptômes paludisme"],
    ]
    meta_t = Table(meta_data, colWidths=[col_label, col_value])
    meta_t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#ecf0f1")),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    story.append(meta_t)
    story.append(Spacer(1, 0.6 * cm))

    # Disclaimer
    story.append(Paragraph(
        "⚠️ AVERTISSEMENT MÉDICAL : Ce document est un rapport informatif de pré-consultation "
        "généré automatiquement. Il ne constitue EN AUCUN CAS un diagnostic médical. "
        "Seul un professionnel de santé qualifié peut établir un diagnostic et prescrire un traitement. "
        "En cas de symptômes graves ou persistants, consultez immédiatement un médecin.",
        warning_style,
    ))

    # ════════════════════════════════════════════════════════════════
    # SECTION 1 — INFORMATIONS PATIENT
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("1. INFORMATIONS PATIENT", styles["Heading2"]))

    patient_data = [
        ["Nom / Prénom :",  _val(user_info, "nom")],     # v2 : "nom" (plus "pseudonyme")
        ["Âge :",           f"{_val(user_info, 'age')} ans"],
        ["Sexe :",          _val(user_info, "sexe")],
        # Téléphone supprimé — non collecté en v2 (données PII non justifiées)
    ]
    story.append(_table(patient_data))
    story.append(Spacer(1, 0.8 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 2 — DONNÉES MÉDICALES COLLECTÉES
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("2. DONNÉES MÉDICALES COLLECTÉES", styles["Heading2"]))

    medical_data = [
        ["Symptômes principaux :", _val(user_info, "symptomes_principaux")],
        ["Fièvre / Température :", _val(user_info, "fievre")],
        ["Durée des symptômes :",  _val(user_info, "duree_symptomes")],
        ["Antécédents malaria :",  _val(user_info, "antecedents_malaria")],
        ["Médicaments en cours :", _val(user_info, "medicaments_en_cours")],
        ["Zone géographique :",    _val(user_info, "zone_geographique")],
        ["Autres symptômes :",     _val(user_info, "autres_symptomes")],
    ]
    story.append(_table(medical_data, header_color="#8e44ad"))
    story.append(Spacer(1, 0.8 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 3 — RÉSUMÉ DES SYMPTÔMES (analyse LLM)
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("3. RÉSUMÉ DES SYMPTÔMES", styles["Heading2"]))
    story.append(Paragraph(_val(analysis, "resume_symptomes"), body_style))
    story.append(Spacer(1, 0.6 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 4 — OBSERVATIONS PRÉLIMINAIRES
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("4. OBSERVATIONS PRÉLIMINAIRES", styles["Heading2"]))
    story.append(Paragraph(_val(analysis, "observations"), body_style))
    story.append(Spacer(1, 0.6 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 5 — FACTEURS DE RISQUE
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("5. FACTEURS DE RISQUE IDENTIFIÉS", styles["Heading2"]))
    facteurs = analysis.get("facteurs_risque", ["Non identifié"])
    if isinstance(facteurs, str):
        facteurs = [facteurs]
    for facteur in facteurs:
        story.append(Paragraph(f"• {facteur}", styles["Normal"]))
    story.append(Spacer(1, 0.6 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 6 — NIVEAU D'URGENCE
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("6. NIVEAU D'URGENCE ESTIMÉ", styles["Heading2"]))
    niveau = analysis.get("niveau_urgence", "Modéré")
    urgence_table = Table([[niveau.upper()]], colWidths=[17 * cm])
    urgence_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), _urgence_color(niveau)),
        ("TEXTCOLOR",     (0, 0), (-1, -1), colors.white),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 14),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
    ]))
    story.append(urgence_table)
    story.append(Spacer(1, 0.6 * cm))

    # ════════════════════════════════════════════════════════════════
    # SECTION 7 — RECOMMANDATIONS
    # ════════════════════════════════════════════════════════════════
    story.append(Paragraph("7. RECOMMANDATIONS", styles["Heading2"]))
    story.append(Paragraph(_val(analysis, "recommandations"), reco_style))
    story.append(Spacer(1, 1.2 * cm))

    # ════════════════════════════════════════════════════════════════
    # PIED DE PAGE
    # ════════════════════════════════════════════════════════════════
    story.append(_sep())
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Malidata System — Outil d'aide à la pré-consultation médicale", footer_style))
    story.append(Paragraph("Document confidentiel — Usage médical uniquement", footer_style))
    story.append(Paragraph(
        f"Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')} · Session {session_id[:8]}",
        footer_style,
    ))

    doc.build(story)
    print(f"✅ Rapport PDF généré : {filepath}")