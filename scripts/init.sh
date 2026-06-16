#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# init.sh — carga inicial de dados dentro do container backend
# Uso: docker compose exec backend bash /app/scripts/init.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

echo "🔄 Aguardando banco de dados disponível..."
until pg_isready -h "${POSTGRES_HOST:-db}" \
                 -U "${POSTGRES_USER:-sus}" \
                 -d "${POSTGRES_DB:-sus_search}" 2>/dev/null; do
  echo "   aguardando... (retry em 3s)"
  sleep 3
done
echo "✅ Banco disponível"

echo ""
echo "🚀 Iniciando carga de dados..."
cd /app
python -m etl.run_all "$@"

echo ""
echo "✅ Carga concluída. Acesse:"
echo "   Frontend:  http://localhost:3000"
echo "   API Docs:  http://localhost:8000/docs"
echo "   Health:    http://localhost:8000/api/v1/health"
