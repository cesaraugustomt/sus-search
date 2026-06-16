# SUS Search 🔬

Mecanismo de busca unificado para recursos oficiais do SUS.  
**Projeto acadêmico — PPGINFOS/UFSC — Informática em Saúde.**

---

## Fontes integradas

| Fonte | Conteúdo | Atualização |
|---|---|---|
| **SIGTAP** | Procedimentos, Medicamentos e OPM do SUS | Mensal |
| **CID-10 / RTS** | Classificação Internacional de Doenças (via SIGTAP) | Mensal |
| **CNES** | Cadastro Nacional de Estabelecimentos de Saúde | Mensal |

---

## Stack

- **Backend**: FastAPI · SQLAlchemy · PostgreSQL (full-text search com `tsvector` + GIN index)  
- **Frontend**: React 18 · Vite · TypeScript  
- **Infra**: Docker · Docker Compose  
- **Testes**: Pytest (backend) · Vitest (frontend)

---

## Início rápido (Docker)

```bash
# 1. Clone e configure
git clone <repo-url> sus-search
cd sus-search
cp .env.example .env        # edite senhas se necessário

# 2. Build e subida dos serviços
docker compose up -d --build

# 3. Aguarde o backend inicializar (~20s) e monitore
docker compose logs -f backend

# 4. Carregue os dados (~5–30 min dependendo da conexão)
docker compose exec backend python -m etl.run_all

# 5. Acesse
open http://localhost:3000          # Interface de busca
open http://localhost:8000/docs     # Swagger / OpenAPI
```

---

## Desenvolvimento local (sem Docker)

### Pré-requisitos
- Python 3.12+
- Node.js 20+
- PostgreSQL 15 rodando localmente (ou `docker compose up -d db`)

### Backend

```bash
cd backend

# Ambiente virtual
python3.12 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .\.venv\Scripts\activate      # Windows PowerShell

pip install -r requirements.txt

# Variáveis de ambiente
export DATABASE_URL="postgresql://sus:sus_search_2025@localhost:5432/sus_search"
export DATA_DIR="./data"
export DEBUG=true

# Sobe só o banco via Docker
docker compose up -d db

# Inicia a API com hot-reload
uvicorn app.main:app --reload --port 8000

# Em outro terminal — carrega dados
python -m etl.run_all
```

### Frontend

```bash
cd frontend
npm install

# URL da API em modo dev
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# Acesse: http://localhost:5173
```

---

## Carga de dados (ETL)

```bash
# Dentro do container (recomendado em produção)
docker compose exec backend python -m etl.run_all

# Opções disponíveis
python -m etl.run_all --skip-sigtap    # carrega apenas CNES
python -m etl.run_all --skip-cnes      # carrega apenas SIGTAP + CID-10
python -m etl.run_all --data-dir /tmp  # diretório personalizado

# Script auxiliar
./scripts/update_data.sh
./scripts/update_data.sh --skip-cnes
```

> **Nota sobre SIGTAP**: o ETL acessa automaticamente `sigtap.datasus.gov.br`
> para obter o ZIP da última competência. Se o portal estiver instável, 
> baixe manualmente e salve em `./data/sigtap.zip` antes de rodar o ETL.

---

## Testes

### Backend

```bash
cd backend
source .venv/bin/activate

# ── Testes unitários (sem banco de dados)
pytest tests/unit -v

# ── Testes de integração (requer PostgreSQL)
export TEST_DATABASE_URL="postgresql://sus:sus_search_2025@localhost:5432/sus_search_test"
pytest tests/integration -v

# ── Todos com relatório de cobertura
pytest -v --cov=app --cov=etl --cov-report=term-missing

# ── Cobertura em HTML
pytest --cov=app --cov=etl --cov-report=html
open htmlcov/index.html
```

### Frontend

```bash
cd frontend

npm run test               # execução única
npm run test:watch         # modo watch (TDD)
npm run test:coverage      # com relatório de cobertura
```

---

## API — Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/v1/search?q=...` | Busca full-text paginada |
| `GET` | `/api/v1/search?q=...&source=CID10` | Busca filtrada por fonte |
| `GET` | `/api/v1/sources` | Fontes disponíveis e estatísticas |
| `GET` | `/api/v1/terms/{id}` | Detalhe de um termo |
| `GET` | `/api/v1/health` | Health check da API |
| `GET` | `/docs` | Swagger UI interativo |
| `GET` | `/redoc` | ReDoc |

**Parâmetros de busca:**

| Param | Tipo | Padrão | Descrição |
|---|---|---|---|
| `q` | string | — | Termo de busca (obrigatório, ≥2 chars) |
| `source` | string | — | Filtrar: `SIGTAP` \| `CID10` \| `CNES` |
| `page` | int | 1 | Página (começa em 1) |
| `limit` | int | 20 | Resultados por página (máx: 100) |

**Exemplo de resposta:**

```json
{
  "query": "pneumonia",
  "total": 42,
  "page": 1,
  "limit": 20,
  "pages": 3,
  "results": [
    {
      "id": 1234,
      "code": "J18.9",
      "name": "PNEUMONIA NÃO ESPECIFICADA",
      "source": "CID10",
      "category": "Classificação Internacional de Doenças",
      "official_url": "https://rts.saude.gov.br",
      "source_competency": "04/2025"
    }
  ]
}
```

---

## Atualização mensal

```bash
# Sugestão de cron (1º dia de cada mês, 3h da manhã)
# 0 3 1 * * cd /path/sus-search && ./scripts/update_data.sh >> /var/log/sus-search-etl.log 2>&1

./scripts/update_data.sh
```

---

## Troubleshooting

### Banco não inicializa
```bash
docker compose logs db
docker compose restart db
docker compose exec db psql -U sus -d sus_search -c "SELECT version();"
```

### ETL falha no download do SIGTAP
```bash
# Verifique conectividade
curl -I "http://sigtap.datasus.gov.br/tabela-unificada/app/download.jsp"

# Baixe manualmente e salve em ./data/sigtap.zip
# Depois re-execute (o ETL detecta o arquivo local)
docker compose exec backend python -m etl.run_all
```

### Busca retorna 0 resultados após ETL
```bash
# Confira se os dados foram inseridos
docker compose exec db psql -U sus -d sus_search \
  -c "SELECT source, COUNT(*) FROM terms GROUP BY source ORDER BY source;"

# Force reindexação do tsvector (dispara o trigger)
docker compose exec db psql -U sus -d sus_search \
  -c "UPDATE terms SET name = name WHERE search_vector IS NULL;"
```

### API retorna CORS error no browser
Edite `.env` e adicione o domínio do frontend em `ALLOWED_ORIGINS`:
```
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173,http://meu-dominio.com
```
Reinicie: `docker compose restart backend`

### Frontend não encontra a API
```bash
# Confira a variável VITE_API_URL em frontend/.env.local
echo $VITE_API_URL

# Teste diretamente
curl http://localhost:8000/api/v1/health
```

---

## Estrutura do projeto

```
sus-search/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # search.py · sources.py · health.py
│   │   ├── core/               # config.py · logging.py
│   │   ├── db/                 # session.py (init_db, get_db)
│   │   ├── models/             # term.py (Term, Source)
│   │   ├── repositories/       # term_repository.py
│   │   ├── schemas/            # search.py (Pydantic v2)
│   │   ├── services/           # search_service.py
│   │   └── main.py             # FastAPI app + lifespan
│   ├── etl/
│   │   ├── base.py             # parser TXT posicional, retry HTTP, ETLResult
│   │   ├── sigtap.py           # scraper + ZIP parser (procedimentos + CID-10)
│   │   ├── cnes.py             # CKAN API + CSV parser
│   │   └── run_all.py          # orquestrador CLI
│   └── tests/
│       ├── unit/               # sem banco — mock SQLAlchemy
│       └── integration/        # com PostgreSQL real
├── frontend/
│   ├── src/
│   │   ├── components/         # SearchBar · ResultCard · Pagination · …
│   │   ├── hooks/              # useSearch.ts
│   │   ├── services/           # api.ts
│   │   └── types/              # index.ts
│   └── tests/
│       ├── components/         # SearchBar · ResultCard
│       └── services/           # api.test.ts
├── nginx/                      # nginx.conf (proxy reverso)
├── data/                       # ZIPs e CSVs baixados (gitignored)
├── scripts/                    # init.sh · update_data.sh
├── docker-compose.yml
├── .env.example
└── README.md
```
