#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "Submitting declaration..."
curl -s -X POST "$BASE_URL/submit" \
  -H "Content-Type: application/json" \
  -d '{ "producer_id": "GREENPACK-001", "month": "2026-04", "declared_quantities_kg": { "rigid_plastic": 12000, "flexible_plastic": 8500, "multilayer_plastic": 3200 } }'

echo
echo "Getting reconciliation summary..."
curl -s "$BASE_URL/summary/GREENPACK-001/2026-04"

echo
echo "Asking policy question..."
curl -s -X POST "$BASE_URL/ask" \
  -H "Content-Type: application/json" \
  -d '{ "question": "What evidence should GreenPack keep for an audit?" }'

echo
