#!/usr/bin/env bash
# Prueba de humo de punta a punta contra la pila levantada.
#
#   ./scripts/smoke.sh ruta/al/contrato.pdf
#
# Recorre: salud → login → subida → pipeline → hallazgos. Sin GROQ_API_KEY el
# análisis falla en el paso del modelo, y eso está bien: lo que se verifica
# aquí es todo lo anterior (extracción, OCR, segmentación, embeddings).
set -euo pipefail

API="${API:-http://localhost:8000}"
EMAIL="${ADMIN_EMAIL:-admin@develop.com.mx}"
PASSWORD="${ADMIN_PASSWORD:?Define ADMIN_PASSWORD}"
PDF="${1:?Pasa la ruta de un PDF}"

paso() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

paso "Salud"
curl -fsS "$API/api/health" && echo

paso "Login"
TOKEN=$(curl -fsS -X POST "$API/api/auth/login" \
  -d "username=$EMAIL&password=$PASSWORD" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
echo "token obtenido (${#TOKEN} caracteres)"

paso "Usuario autenticado"
curl -fsS "$API/api/auth/yo" -H "Authorization: Bearer $TOKEN"; echo

paso "Subida de $PDF"
ID=$(curl -fsS -X POST "$API/api/contratos" \
  -H "Authorization: Bearer $TOKEN" \
  -F "archivo=@$PDF;type=application/pdf" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
echo "contrato $ID"

paso "Pipeline"
for _ in $(seq 1 90); do
  ESTADO=$(curl -fsS "$API/api/contratos/$ID" -H "Authorization: Bearer $TOKEN" \
    | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["status"], d.get("paginas"), d.get("ocr_aplicado"), len(d.get("clausulas",[])), len(d.get("hallazgos",[])), d.get("error_msg") or "", sep="|")')
  IFS='|' read -r ST PAGS OCR NCLAU NHALL ERR <<<"$ESTADO"
  LINEA=$(printf '  %-12s págs=%-4s ocr=%-5s cláusulas=%-4s hallazgos=%s' "$ST" "$PAGS" "$OCR" "$NCLAU" "$NHALL")
  # Solo se imprime cuando algo cambia: con \r el log capturado queda ilegible.
  [ "$LINEA" != "${PREVIA:-}" ] && echo "$LINEA" && PREVIA="$LINEA"
  case "$ST" in
    listo) echo "  terminado"; break ;;
    error) echo "  falló: $ERR"; break ;;
  esac
  sleep 2
done

paso "Tablero"
curl -fsS "$API/api/dashboard?dias=30" -H "Authorization: Bearer $TOKEN" \
  | python3 -m json.tool | head -20
