#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# update_data.sh — atualiza os dados de uma ou todas as fontes
# Uso:
#   ./scripts/update_data.sh                  → todas as fontes
#   ./scripts/update_data.sh --skip-cnes      → só SIGTAP + CID-10
#   ./scripts/update_data.sh --skip-sigtap    → só CNES
# ─────────────────────────────────────────────────────────────
set -euo pipefail

echo "════════════════════════════════════════"
echo " SUS Search — Atualização de Dados"
echo "════════════════════════════════════════"
date

# Verifica se os containers estão rodando
if ! docker compose ps --status running backend 2>/dev/null | grep -q backend; then
  echo "⚠️  Container backend não está rodando. Subindo com run --rm..."
  docker compose run --rm backend python -m etl.run_all "$@"
else
  docker compose exec backend python -m etl.run_all "$@"
fi

echo ""
echo "✅ Atualização concluída em $(date)"
