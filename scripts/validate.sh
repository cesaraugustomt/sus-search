#!/usr/bin/env bash
# ============================================================
# validate.sh — checklist completo de validação do SUS Search
# Uso: bash scripts/validate.sh
# Requer: Docker Compose rodando + curl + python3
# ============================================================
set -euo pipefail

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[1;33m'
NC='\033[0m'

pass() { echo -e "  ${GRN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; FAILURES=$((FAILURES+1)); }
info() { echo -e "  ${YLW}→${NC} $1"; }

FAILURES=0
API="http://localhost:8000/api/v1"
FRONT="http://localhost:3000"

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   SUS Search — Validação completa            ║"
echo "╚══════════════════════════════════════════════╝"

# ── 1. Containers
echo -e "\n${YLW}1. Containers${NC}"
for svc in sus_search_db sus_search_backend sus_search_frontend; do
  if docker ps --filter "name=$svc" --filter "status=running" | grep -q "$svc"; then
    pass "Container $svc rodando"
  else
    fail "Container $svc NÃO está rodando"
  fi
done

# ── 2. Banco
echo -e "\n${YLW}2. Banco de dados${NC}"
if docker compose exec -T db pg_isready -U sus -d sus_search &>/dev/null; then
  pass "PostgreSQL respondendo"
else
  fail "PostgreSQL não responde"
fi

TOTAL=$(docker compose exec -T db psql -U sus -d sus_search -tAc \
  "SELECT COUNT(*) FROM terms;" 2>/dev/null || echo "0")
if [ "$TOTAL" -gt 1000 ]; then
  pass "Banco tem $TOTAL termos indexados"
else
  fail "Banco com poucos termos: $TOTAL (esperado >1000)"
fi

# ── 3. API
echo -e "\n${YLW}3. API (FastAPI)${NC}"
HEALTH=$(curl -sf "$API/health" 2>/dev/null || echo '{}')
STATUS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','?'))" 2>/dev/null)
if [ "$STATUS" = "ok" ]; then
  pass "Health check: $STATUS"
  TERMS=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total_terms',0))")
  info "Total de termos na API: $TERMS"
else
  fail "Health check retornou: $STATUS"
fi

# ── 4. Busca full-text
echo -e "\n${YLW}4. Busca FTS${NC}"
for QUERY in "acupuntura" "pneumonia" "consulta" "J18"; do
  RESULT=$(curl -sf "$API/search?q=$QUERY" 2>/dev/null || echo '{}')
  TOTAL_Q=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo 0)
  if [ "$TOTAL_Q" -gt 0 ]; then
    pass "Busca '$QUERY': $TOTAL_Q resultado(s)"
  else
    fail "Busca '$QUERY': 0 resultados"
  fi
done

# ── 5. Filtro por fonte
echo -e "\n${YLW}5. Filtros por fonte${NC}"
for SRC in SIGTAP CID10; do
  RESULT=$(curl -sf "$API/search?q=consulta&source=$SRC" 2>/dev/null || echo '{}')
  N=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))" 2>/dev/null || echo 0)
  if [ "$N" -gt 0 ]; then
    pass "Filtro $SRC: $N resultado(s)"
  else
    fail "Filtro $SRC: 0 resultados"
  fi
done

# ── 6. Endpoint /sources
echo -e "\n${YLW}6. Fontes registradas${NC}"
SOURCES=$(curl -sf "$API/sources" 2>/dev/null || echo '[]')
for SRC in SIGTAP CID10; do
  if echo "$SOURCES" | python3 -c "import sys,json; codes=[s['code'] for s in json.load(sys.stdin)]; assert '$SRC' in codes" 2>/dev/null; then
    RC=$(echo "$SOURCES" | python3 -c "import sys,json; s=[s for s in json.load(sys.stdin) if s['code']=='$SRC'][0]; print(s.get('record_count',0))")
    pass "Fonte $SRC: $RC registros"
  else
    fail "Fonte $SRC não encontrada em /sources"
  fi
done

# ── 7. Frontend
echo -e "\n${YLW}7. Frontend${NC}"
HTTP_CODE=$(curl -so /dev/null -w "%{http_code}" "$FRONT" 2>/dev/null || echo 0)
if [ "$HTTP_CODE" = "200" ]; then
  pass "Frontend acessível em $FRONT"
else
  fail "Frontend retornou HTTP $HTTP_CODE"
fi

# ── 8. API DEMAS (pública)
echo -e "\n${YLW}8. API DEMAS (externa)${NC}"
DEMAS=$(curl -sf "https://apidadosabertos.saude.gov.br/cnes/estabelecimentos?limit=1" 2>/dev/null || echo '{}')
if echo "$DEMAS" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('estabelecimentos') or isinstance(d,list)" 2>/dev/null; then
  pass "API DEMAS acessível e retornando JSON"
else
  fail "API DEMAS não está respondendo corretamente"
fi

# ── 9. Modo Perguntar (se LLM configurado)
echo -e "\n${YLW}9. Módulo Perguntar (LLM)${NC}"
ASK_RESP=$(curl -sf -X POST "$API/ask" \
  -H 'Content-Type: application/json' \
  -d '{"question":"o que é acupuntura?"}' 2>/dev/null || echo '{}')
ERR=$(echo "$ASK_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('error',''))" 2>/dev/null || echo "erro")
if [ -z "$ERR" ] || [ "$ERR" = "None" ]; then
  ANS=$(echo "$ASK_RESP" | python3 -c "import sys,json; a=json.load(sys.stdin).get('answer',''); print(a[:60]+'...' if len(a)>60 else a)" 2>/dev/null)
  pass "LLM respondeu: $ANS"
elif echo "$ERR" | grep -qi "configurado"; then
  info "LLM não configurado (adicione LLM_BASE_URL e LLM_API_KEY ao .env)"
else
  fail "LLM retornou erro: $ERR"
fi

# ── Resumo
echo ""
echo "══════════════════════════════════════════════"
if [ "$FAILURES" -eq 0 ]; then
  echo -e "  ${GRN}✅ Todos os testes passaram!${NC}"
  echo ""
  echo "  Frontend:  $FRONT"
  echo "  API Docs:  http://localhost:8000/docs"
  echo "  Health:    $API/health"
else
  echo -e "  ${RED}❌ $FAILURES teste(s) falharam${NC}"
  echo "  Verifique os logs: docker compose logs backend"
fi
echo "══════════════════════════════════════════════"
echo ""
exit $FAILURES
