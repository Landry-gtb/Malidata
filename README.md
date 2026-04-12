# 🦟 Malidata — Chatbot Médical Intelligent pour la Malaria

> Système de pré-consultation intelligent pour la collecte structurée de données symptomatiques liées à la malaria.

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![Redis](https://img.shields.io/badge/Redis-7-red?logo=redis)](https://redis.io)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)
[![LLM](https://img.shields.io/badge/LLM-Groq%20Llama--3.3--70b-orange)](https://groq.com)

---

> ⚠️ **Avertissement médical** — Malidata est un outil d'aide à la pré-consultation. Il **ne pose pas de diagnostic médical** et **ne remplace pas une consultation professionnelle**. En cas de symptômes graves, consultez immédiatement un médecin.

---

## Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Architecture technique](#architecture-technique)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Utilisation](#utilisation)
- [Structure du projet](#structure-du-projet)
- [Pipeline RAG — fonctionnement](#pipeline-rag--fonctionnement)
- [API Reference](#api-reference)
- [Tests](#tests)
- [Roadmap](#roadmap)
- [Contribuer](#contribuer)
- [Licence](#licence)

---

## Vue d'ensemble

La malaria reste un défi majeur de santé publique dans de nombreuses régions du monde. L'accès limité aux professionnels de santé retarde souvent le diagnostic et la prise en charge.

**Malidata** automatise la phase de pré-consultation en :
- Guidant le patient à travers **10 étapes structurées** d'identification et de collecte symptomatique
- Répondant intelligemment aux questions et incompréhensions du patient pendant la consultation
- Générant un **rapport PDF professionnel** transmissible au médecin
- Exposant les données collectées via un **dashboard dédié aux professionnels de santé**

---

## Architecture technique

```
┌─────────────────────────────────────────────────────────────┐
│                        Patient                              │
└──────────────────────────┬──────────────────────────────────┘
                           │
                    ┌──────▼──────┐
                    │  React/Vite │  :5173
                    │  Frontend   │
                    └──────┬──────┘
                           │ HTTP/REST
                    ┌──────▼──────┐
                    │   FastAPI   │  :8000
                    │   Backend   │
                    └──────┬──────┘
                    ┌──────┼──────────────┐
             ┌──────▼──┐  ┌▼──────┐  ┌───▼────┐
             │  Redis  │  │ FAISS │  │  Groq  │
             │Sessions │  │ Index │  │  LLM   │
             └─────────┘  └───────┘  └────────┘
                           │
                    ┌──────▼──────┐
                    │  Streamlit  │  :8501
                    │  Dashboard  │
                    └─────────────┘
                           │
                        Médecin
```

### Stack technique

| Composant | Technologie | Rôle |
|---|---|---|
| **Backend** | FastAPI + Python 3.11 | API REST, orchestration |
| **LLM** | Groq / Llama-3.3-70b | Extraction, réponses, rapport |
| **RAG** | LangChain + FAISS + SentenceTransformers | Base de connaissances malaria |
| **Sessions** | Redis 7 | État conversationnel multi-utilisateurs |
| **Frontend** | React 18 + Vite | Interface patient |
| **Dashboard** | Streamlit | Interface professionnels de santé |
| **Rapports** | ReportLab | Génération PDF |
| **Infra** | Docker Compose | Orchestration des services |

---

## Fonctionnalités

### ✅ Implémentées (v2.1)

#### Pipeline conversationnel
- **10 étapes structurées** : 3 d'identification (nom, âge, sexe) + 7 médicales (symptômes, fièvre, durée, antécédents, médicaments, zone géographique, autres symptômes)
- **Extraction d'entités intelligente** via LLM JSON-mode (`temperature=0.0`) — capture `"Je m'appelle Claude, j'ai 28 ans"` correctement
- **Détection d'intention** — distingue une question d'une réponse : si le patient demande `"Pourquoi avez-vous besoin de mon âge ?"`, le bot répond et re-pose la même question sans perdre le fil
- **Vouvoiement constant** garanti par persona fixe injectée à chaque appel LLM
- **Réponses concises** — `max_tokens=300`, aucune explication médicale non sollicitée

#### Gestion de session
- **Isolation totale** par `session_id` Redis — multi-utilisateurs natif
- **TTL automatique** — sessions expirées après 1 heure
- **État complet persisté** : étape courante, données collectées, historique dialogue

#### RAG (Retrieval-Augmented Generation)
- **4113 chunks** indexés depuis les documents PDF médicaux
- **Activation conditionnelle** — RAG déclenché uniquement aux étapes 3 (symptômes) et 9 (autres symptômes) pour éviter les injections hors-contexte
- **Recherche sémantique** via FAISS + `all-MiniLM-L6-v2`

#### Rapports PDF
- Génération automatique à la fin du questionnaire
- 7 sections : informations patient, données médicales, résumé symptômes, observations, facteurs de risque, niveau d'urgence, recommandations
- Niveaux d'urgence codés par couleur : Faible (vert) / Modéré (orange) / Élevé (rouge) / Critique (bordeaux)
- Sécurité path traversal sur l'endpoint de téléchargement

#### Frontend
- Barre de progression `Étape X / 10` animée
- Déclenchement automatique du rapport PDF à la fin
- Input désactivé après complétion du questionnaire
- Lien de téléchargement direct dans l'interface

#### Sécurité
- Données anonymisées — aucun numéro de téléphone collecté
- Sessions temporaires Redis avec TTL
- Endpoint `/download` protégé contre le path traversal
- CORS configuré par variable d'environnement

### 🔜 Prévues (roadmap)

- **Phase 2** — Migration PostgreSQL, authentification JWT pour le dashboard
- **Phase 3** — Amélioration RAG, notifications, tests de couverture
- **Phase 4** — Intégrations HL7/FHIR, application mobile

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) avec intégration WSL2 activée
- [Node.js 18+](https://nodejs.org/) pour le frontend
- Clé API [Groq](https://console.groq.com) (gratuite)
- Git

---

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/Landry-gtb/malidata.git
cd malidata
```

### 2. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Édite `.env` et renseigne ta clé Groq :

```bash
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. Démarrer le backend

```bash
# Build et démarrage des services (backend + Redis)
docker compose build --no-cache
docker compose up -d

# Vérifier que tout est opérationnel
docker compose ps
curl http://localhost:8000/health
```

Réponse attendue :
```json
{
  "status": "healthy",
  "rag_initialized": true,
  "rag_chunks": 4113,
  "llm_engine": "Groq / llama-3.3-70b-versatile",
  "groq_api_key_set": true,
  "total_steps": 10
}
```

> ⏳ Le premier démarrage prend ~60 secondes le temps de charger le modèle d'embedding et l'index FAISS.

### 4. Démarrer le frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend disponible sur [http://localhost:5173](http://localhost:5173)

### 5. Dashboard médecin (optionnel)

```bash
cd dashboard
python -m venv venv
source venv/bin/activate   # Windows : venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Dashboard disponible sur [http://localhost:8501](http://localhost:8501)

---

## Configuration

### Variables d'environnement (`.env`)

| Variable | Obligatoire | Description | Défaut |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | Clé API Groq | — |
| `REDIS_HOST` | ✅ | Hôte Redis | `redis` |
| `REDIS_PORT` | | Port Redis | `6379` |
| `REDIS_DB` | | Base Redis | `0` |
| `VECTOR_STORE_PATH` | | Chemin index FAISS | `/app/storage/faiss_index.idx` |
| `FRONTEND_URL` | | URL frontend (CORS) | `http://localhost:5173` |
| `RAG_TOP_K` | | Nombre de chunks RAG | `3` |
| `DEBUG` | | Mode debug | `False` |

### Ajout de documents médicaux au RAG

Place tes fichiers PDF dans `backend/data/` avant le premier démarrage. L'index FAISS est construit automatiquement au lancement. Pour reconstruire l'index après ajout de documents :

```bash
# Supprimer l'index existant
docker exec malaria_backend rm -f /app/storage/faiss_index.idx
docker exec malaria_backend rm -f /app/storage/faiss_index.idx.meta

# Redémarrer pour reconstruire
docker compose restart backend
```

---

## Utilisation

### Flux patient complet

```
1. Ouvrir http://localhost:5173
2. Cliquer "Démarrer l'Évaluation"
3. Répondre aux 10 questions (identification + médicales)
4. Le rapport PDF est généré automatiquement à la fin
5. Télécharger le rapport et le transmettre au médecin
```

### Questions couvertes par le questionnaire

| # | Champ | Question |
|---|---|---|
| 0 | Prénom | Quel est votre prénom ? |
| 1 | Âge | Quel est votre âge ? |
| 2 | Sexe | Êtes-vous un homme ou une femme ? |
| 3 | Symptômes principaux | Quels symptômes vous ont amené(e) à consulter ? |
| 4 | Fièvre | Avez-vous de la fièvre ? Quelle température ? |
| 5 | Durée | Depuis combien de temps ressentez-vous ces symptômes ? |
| 6 | Antécédents | Avez-vous déjà eu la malaria ? |
| 7 | Médicaments | Prenez-vous actuellement des médicaments ? |
| 8 | Zone géographique | Avez-vous voyagé dans une zone à risque ? |
| 9 | Autres symptômes | Avez-vous d'autres symptômes ? |

---

## Structure du projet

```
malidata/
├── backend/
│   ├── routers/
│   │   ├── chat.py          # Endpoints conversation (/start, /message, /history)
│   │   ├── rag.py           # Endpoints RAG (/query, /report, /health)
│   │   └── reports.py       # Endpoints PDF (/generate, /download, /list)
│   ├── utils/
│   │   └── pdf_utils.py     # Génération rapports PDF (ReportLab)
│   ├── data/                # Documents PDF source pour le RAG
│   ├── reports/             # Rapports PDF générés
│   ├── storage/             # Index FAISS persisté
│   ├── app.py               # Application FastAPI + lifespan
│   ├── rag_pipeline.py      # Orchestrateur principal (RAG + LLM + sessions)
│   ├── database.py          # Initialisation base de données
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── services/
│       │   └── api.js       # Client API (axios)
│       ├── App.jsx          # Interface principale (chat + progression + rapport)
│       ├── App.css
│       └── main.jsx
├── dashboard/               # Interface Streamlit (professionnels de santé)
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Pipeline RAG — fonctionnement

### Architecture de décision à chaque message

```
Message patient reçu
        │
        ▼
┌───────────────────┐
│  _detect_intent() │  ← LLM JSON-mode, temperature=0.0
└───────┬───────────┘
        │
   ┌────┴────┐
   │         │
"question" "response"
   │         │
   ▼         ▼
Répond  _extract_entity()
+         │
re-pose  ┌─┴──┐
question │    │
(step   OK  FAIL
inchangé)│    │
         ▼    ▼
      Avancer followup
       step   court
```

### Températures LLM par usage

| Usage | Température | Raison |
|---|---|---|
| Détection d'intention | `0.0` | Classification déterministe |
| Extraction d'entités | `0.0` | Extraction déterministe |
| Réponses conversationnelles | `0.1` | Légère variabilité naturelle |
| Génération rapport | `0.1` | Synthèse cohérente |

### Activation du RAG

Le RAG n'est **pas déclenché à chaque message** — uniquement aux étapes où le contexte médical est utile :

- **Étape 3** (symptômes principaux) — enrichit la compréhension des symptômes décrits
- **Étape 9** (autres symptômes) — complète le tableau clinique

---

## API Reference

### Chat

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/chat/start` | Démarre une session, retourne `session_id` + message d'accueil |
| `POST` | `/api/chat/message` | Envoie un message, retourne réponse + `step` + `completed` |
| `GET` | `/api/chat/history/{session_id}` | Historique et données collectées |
| `DELETE` | `/api/chat/session/{session_id}` | Supprime une session (RGPD) |

### RAG

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/rag/query` | Recherche sémantique dans l'index FAISS |
| `POST` | `/api/rag/report` | Génère l'analyse médicale structurée |
| `GET` | `/api/rag/health` | État du pipeline RAG |

### Rapports

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/reports/generate` | Génère le PDF d'une session terminée |
| `GET` | `/api/reports/download/{filename}` | Télécharge un rapport PDF |
| `GET` | `/api/reports/list` | Liste tous les rapports disponibles |

### Format de réponse `/api/chat/message`

```json
{
  "response": "Je viens de noter votre réponse. Quel est votre âge ?",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "step": 1,
  "total": 10,
  "completed": false,
  "needs_report": false
}
```

Documentation interactive complète : [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Tests

### Test automatisé complet (10 étapes + PDF)

```bash
cd malidata

cat > test_malidata.sh << 'SCRIPT'
#!/bin/bash
BASE_URL="http://localhost:8000"
PASS=0; FAIL=0
GREEN='\033[0;32m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

send() { curl -s -X POST "$BASE_URL/api/chat/message" \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"$1\"}"; }

check() {
    local step=$(echo "$3" | grep -o '"step":[0-9]*' | grep -o '[0-9]*')
    local ok=$(echo "$3" | grep -o '"completed":true')
    echo -e "  Step: $step/10"
    if [ "$step" = "$2" ] || [ -n "$ok" ]; then
        echo -e "  ${GREEN}✅ PASS${NC}"; PASS=$((PASS+1))
    else
        echo -e "  ${RED}❌ FAIL — attendu $2, obtenu $step${NC}"; FAIL=$((FAIL+1))
    fi
}

START=$(curl -s -X POST "$BASE_URL/api/chat/start")
SESSION_ID=$(echo "$START" | grep -o '"session_id":"[^"]*"' | sed 's/"session_id":"//;s/"$//')
[ -z "$SESSION_ID" ] && echo "❌ Backend inaccessible" && exit 1
echo -e "${CYAN}Session : $SESSION_ID${NC}"

check "Nom"       "1"  "$(send 'Je mappelle Marie')"
check "Âge"       "2"  "$(send '32 ans')"
check "Sexe"      "3"  "$(send 'Femme')"
check "Symptômes" "4"  "$(send 'Fièvre et maux de tête')"
check "Fièvre"    "5"  "$(send 'Oui 39.5 degrés')"
check "Durée"     "6"  "$(send 'Depuis 4 jours')"
check "Antéc."    "7"  "$(send 'Oui il y a 2 ans')"
check "Médic."    "8"  "$(send 'Paracétamol')"
check "Zone"      "9"  "$(send 'Zone forestière')"
check "Autres"    "10" "$(send 'Frissons et nausées')"

REPORT=$(curl -s -X POST "$BASE_URL/api/reports/generate" \
    -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\"}")
[ -n "$(echo "$REPORT" | grep 'success')" ] && \
    echo -e "${GREEN}✅ PDF généré${NC}" && PASS=$((PASS+1)) || \
    echo -e "${RED}❌ PDF échoué${NC}" && FAIL=$((FAIL+1))

echo -e "\n${CYAN}Bilan : ${GREEN}$PASS ✅${NC} / ${RED}$FAIL ❌${NC}"
[ $FAIL -eq 0 ] && echo -e "${GREEN}🎉 Tous les tests passent !${NC}"
SCRIPT

chmod +x test_malidata.sh && bash test_malidata.sh
```

### Test manuel — détection d'intention

```bash
SESSION="votre-session-id"

# Tester une question de l'utilisateur à l'étape âge
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"message\": \"Pourquoi avez-vous besoin de mon âge ?\"}"

# Réponse attendue :
# - step = inchangé (même étape)
# - réponse contient une explication + re-pose la question de l'âge
```

### Health checks

```bash
# Backend
curl http://localhost:8000/health

# RAG
curl http://localhost:8000/api/rag/health

# Redis (depuis le conteneur)
docker exec malaria_redis redis-cli ping
```

---

## Roadmap

### ✅ Phase 1 — Validation (terminée)

- Pipeline RAG complet (LangChain + FAISS + Groq)
- State machine conversationnelle 10 étapes
- Extraction d'entités LLM JSON-mode
- Détection d'intention (questions vs réponses)
- Gestion de sessions Redis multi-utilisateurs
- Génération de rapports PDF professionnels
- Frontend React avec barre de progression
- Sécurisation des endpoints
- Tests automatisés

### 🔜 Phase 2 — Production-Ready

- [ ] Migration SQLite → PostgreSQL
- [ ] Authentification JWT pour le dashboard médecin
- [ ] Tests unitaires et d'intégration (couverture ≥ 80%)
- [ ] Rate limiting sur les endpoints publics
- [ ] Logs structurés (JSON) + intégration monitoring

### 🔜 Phase 3 — Croissance

- [ ] Amélioration du pipeline RAG (reranking, chunking adaptatif)
- [ ] Notifications (email médecin à réception du rapport)
- [ ] Support multilingue (français, anglais, langues locales)
- [ ] Optimisation mobile du frontend

### 🔜 Phase 4 — Écosystème

- [ ] Intégrations HL7/FHIR pour l'interopérabilité des systèmes de santé
- [ ] Application mobile (React Native)
- [ ] Mode hors-ligne partiel
- [ ] Tableau de bord analytique (épidémiologie locale)

---

## Contribuer

Les contributions sont les bienvenues. Merci de suivre ces étapes :

1. Fork le projet
2. Crée une branche feature : `git checkout -b feature/ma-fonctionnalite`
3. Commit tes changements : `git commit -m 'feat: description claire'`
4. Push la branche : `git push origin feature/ma-fonctionnalite`
5. Ouvre une Pull Request

### Convention de commits

```
feat:     nouvelle fonctionnalité
fix:      correction de bug
docs:     documentation
refactor: refactoring sans changement de comportement
test:     ajout ou modification de tests
chore:    maintenance (deps, config)
```

---

## Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## Avertissement légal

Malidata est un outil de **pré-consultation** uniquement. Il ne constitue en aucun cas un avis médical, un diagnostic ou une prescription. Les informations collectées sont à titre indicatif et doivent être validées par un professionnel de santé qualifié.

**En cas d'urgence médicale, contactez immédiatement les services d'urgence locaux.**

---

<div align="center">
  <p>Malidata v2.1 — Construit avec ❤️ pour améliorer l'accès aux soins</p>
  <p>
    <a href="http://localhost:8000/docs">API Docs</a> •
    <a href="http://localhost:5173">Frontend</a> •
    <a href="http://localhost:8501">Dashboard</a>
  </p>
</div>
