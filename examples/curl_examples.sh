#!/usr/bin/env bash
# Ejemplos de uso del SIS Facturador con curl.
# Cambia BASE_URL si estas apuntando al deploy de Vercel en lugar de local.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "== Health =="
curl -sS "$BASE_URL/v1/health" | python -m json.tool
echo

echo "== Health del cert =="
curl -sS "$BASE_URL/v1/health/cert" | python -m json.tool
echo

echo "== Emitiendo factura desde examples/factura.json =="
curl -sS -X POST "$BASE_URL/v1/invoices" \
    -H "Content-Type: application/json" \
    -d @"$(dirname "$0")/factura.json" | python -m json.tool
echo

echo "== Emitiendo boleta desde examples/boleta.json =="
curl -sS -X POST "$BASE_URL/v1/invoices" \
    -H "Content-Type: application/json" \
    -d @"$(dirname "$0")/boleta.json" | python -m json.tool
