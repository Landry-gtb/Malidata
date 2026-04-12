#!/bin/bash
BASE_URL="http://localhost:8000"
PASS=0
FAIL=0
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

separator() { echo -e "${CYAN}──────────────────────────────────────────${NC}"; }

check_step() {
    local label="$1"
    local expected_step="$2"
    local response="$3"
    actual_step=$(echo "$response" | grep -o '"step":[0-9]*' | grep -o '[0-9]*')
    completed=$(echo "$response" | grep -o '"completed":true')
    answer=$(echo "$response" | grep -o '"response":"[^"]*"' | sed 's/"response":"//;s/"$//')
    echo -e "  Réponse  : ${YELLOW}${answer:0:80}${NC}"
    echo -e "  Step     : $actual_step / 10"
    if [ "$actual_step" = "$expected_step" ] || [ -n "$completed" ]; then
        echo -e "  Statut   : ${GREEN}✅ PASS${NC}"
        PASS=$((PASS + 1))
    else
        echo -e "  Statut   : ${RED}❌ FAIL — attendu step=$expected_step, obtenu step=$actual_step${NC}"
        FAIL=$((FAIL + 1))
    fi
}

send() {
    curl -s -X POST "$BASE_URL/api/chat/message" \
        -H "Content-Type: application/json" \
        -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"$1\"}"
}

separator
echo -e "${CYAN}Démarrage session...${NC}"
START=$(curl -s -X POST "$BASE_URL/api/chat/start")
SESSION_ID=$(echo "$START" | grep -o '"session_id":"[^"]*"' | sed 's/"session_id":"//;s/"$//')
WELCOME=$(echo "$START" | grep -o '"response":"[^"]*"' | sed 's/"response":"//;s/"$//')

if [ -z "$SESSION_ID" ]; then
    echo -e "${RED}❌ Impossible de démarrer une session.${NC}"
    exit 1
fi
echo -e "  Session  : ${GREEN}$SESSION_ID${NC}"
echo -e "  Message  : ${YELLOW}$WELCOME${NC}"

separator; echo -e "${CYAN}Test 1 — Nom${NC}"
R=$(send "Je mappelle Marie"); check_step "Nom" "1" "$R"

separator; echo -e "${CYAN}Test 2 — Âge${NC}"
R=$(send "32 ans"); check_step "Âge" "2" "$R"

separator; echo -e "${CYAN}Test 3 — Sexe${NC}"
R=$(send "Femme"); check_step "Sexe" "3" "$R"

separator; echo -e "${CYAN}Test 4 — Symptômes${NC}"
R=$(send "Fièvre et maux de tête depuis 3 jours"); check_step "Symptômes" "4" "$R"

separator; echo -e "${CYAN}Test 5 — Fièvre${NC}"
R=$(send "Oui 39.5 degrés"); check_step "Fièvre" "5" "$R"

separator; echo -e "${CYAN}Test 6 — Durée${NC}"
R=$(send "Depuis 4 jours"); check_step "Durée" "6" "$R"

separator; echo -e "${CYAN}Test 7 — Antécédents${NC}"
R=$(send "Oui il y a 2 ans"); check_step "Antécédents" "7" "$R"

separator; echo -e "${CYAN}Test 8 — Médicaments${NC}"
R=$(send "Je prends du paracétamol"); check_step "Médicaments" "8" "$R"

separator; echo -e "${CYAN}Test 9 — Zone${NC}"
R=$(send "Oui zone forestière la semaine dernière"); check_step "Zone" "9" "$R"

separator; echo -e "${CYAN}Test 10 — Autres symptômes${NC}"
R=$(send "Frissons et nausées"); check_step "Autres" "10" "$R"

separator; echo -e "${CYAN}Test Bonus — Rapport PDF${NC}"
REPORT=$(curl -s -X POST "$BASE_URL/api/reports/generate" \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"$SESSION_ID\"}")
report_status=$(echo "$REPORT" | grep -o '"status":"success"')
download_url=$(echo "$REPORT" | grep -o '"download_url":"[^"]*"' | sed 's/"download_url":"//;s/"$//')
if [ -n "$report_status" ]; then
    echo -e "  ${GREEN}✅ PDF généré — $BASE_URL$download_url${NC}"
    PASS=$((PASS + 1))
else
    echo -e "  ${RED}❌ Échec PDF — $REPORT${NC}"
    FAIL=$((FAIL + 1))
fi

separator
echo -e "${CYAN}══════════ BILAN ══════════${NC}"
echo -e "  ${GREEN}✅ Réussis : $PASS${NC}"
echo -e "  ${RED}❌ Échoués : $FAIL${NC}"
[ $FAIL -eq 0 ] && echo -e "\n  ${GREEN}🎉 Backend v2 validé !${NC}" || echo -e "\n  ${YELLOW}⚠️  $FAIL test(s) à corriger.${NC}"
separator
