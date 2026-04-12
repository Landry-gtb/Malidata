#!/bin/bash

RESPONSE=$(curl -s -X POST http://localhost:8000/api/chat/start -H "Content-Type: application/json" -d '{"user_info": {}}')
SESSION_ID=$(echo "$RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])")

echo "Session: $SESSION_ID"

# Identification
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Jean\"}" > /dev/null
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"35\"}" > /dev/null
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"M\"}" > /dev/null
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"0123456789\"}" > /dev/null

# État initial
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"J'ai de la fievre et mal a la tete\"}" | python3 -m json.tool

# 7 questions médicales
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"3 jours\"}" | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Oui\"}" | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Oui\"}" | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Non\"}" | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Oui, Afrique\"}" | python3 -m json.tool
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Non\"}" | python3 -m json.tool

echo "=== DERNIERE QUESTION - NEEDS_REPORT DEVRAIT ETRE TRUE ==="
curl -s -X POST http://localhost:8000/api/chat/message -H "Content-Type: application/json" -d "{\"session_id\": \"$SESSION_ID\", \"message\": \"Oui\"}" | python3 -m json.tool
