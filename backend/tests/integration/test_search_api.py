"""
Testes de integração — API ↔ Banco de dados (PostgreSQL).
Requer a variável de ambiente TEST_DATABASE_URL apontando para
um banco PostgreSQL de teste disponível.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import app
from app.db.session import get_db, init_db


# ── setup do banco de teste
@pytest.fixture(scope="module", autouse=True)
def setup_test_db(pg_engine):
    """Inicializa o banco de testes e insere fixtures."""
    with pg_engine.connect() as conn:
        # Limpa dados anteriores
        conn.execute(text("DELETE FROM terms WHERE source IN ('SIGTAP','CID10','CNES')"))
        # Insere registros de teste
        conn.execute(text("""
            INSERT INTO terms (code, name, description, source, category, official_url, source_competency)
            VALUES
              ('0301010013', 'CONSULTA MÉDICA EM ATENÇÃO BÁSICA', NULL, 'SIGTAP', 'Procedimento SUS', 'http://sigtap.datasus.gov.br', '04/2025'),
              ('J18.9', 'PNEUMONIA NÃO ESPECIFICADA', 'Infecção pulmonar inespecífica', 'CID10', 'Classificação Internacional de Doenças', 'https://rts.saude.gov.br', '04/2025'),
              ('2078596', 'HOSPITAL UNIVERSITÁRIO POLYDORO ERNANI', 'Florianópolis — SC', 'CNES', 'Estabelecimento de Saúde', 'https://cnes.datasus.gov.br', NULL)
            ON CONFLICT DO NOTHING;
        """))
        conn.commit()


@pytest.fixture
def client(pg_session):
    """TestClient com sessão de banco injetada."""
    app.dependency_overrides[get_db] = lambda: pg_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── health check
class TestHealthEndpoint:
    def test_health_ok(self, client):
        """Objetivo: /health deve retornar status ok com banco disponível."""
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert data["total_terms"] >= 3


# ── busca
class TestSearchEndpoint:
    def test_busca_por_nome(self, client):
        """Objetivo: buscar 'pneumonia' deve retornar pelo menos 1 resultado CID-10."""
        resp = client.get("/api/v1/search", params={"q": "pneumonia"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        nomes = [r["name"].lower() for r in data["results"]]
        assert any("pneumonia" in n for n in nomes)

    def test_busca_por_codigo(self, client):
        """Objetivo: buscar pelo código J18.9 deve retornar o termo CID-10."""
        resp = client.get("/api/v1/search", params={"q": "J18.9"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    def test_filtro_por_source(self, client):
        """Objetivo: filtro source=CID10 deve retornar apenas termos CID-10."""
        resp = client.get("/api/v1/search", params={"q": "pneumonia", "source": "CID10"})
        assert resp.status_code == 200
        data = resp.json()
        for r in data["results"]:
            assert r["source"] == "CID10"

    def test_query_muito_curta_retorna_422(self, client):
        """Objetivo: query com menos de 2 chars deve retornar 422."""
        resp = client.get("/api/v1/search", params={"q": "a"})
        assert resp.status_code == 422

    def test_paginacao(self, client):
        """Objetivo: page e limit devem ser respeitados."""
        resp = client.get("/api/v1/search", params={"q": "hospital", "page": 1, "limit": 1})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) <= 1

    def test_termo_inexistente_retorna_total_zero(self, client):
        """Objetivo: busca por termo inexistente deve retornar total=0."""
        resp = client.get("/api/v1/search", params={"q": "xyzxyzxyz123"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []


# ── sources
class TestSourcesEndpoint:
    def test_lista_fontes(self, client):
        """Objetivo: /sources deve retornar lista de fontes conhecidas."""
        resp = client.get("/api/v1/sources")
        assert resp.status_code == 200
        codes = [s["code"] for s in resp.json()]
        assert "SIGTAP" in codes
        assert "CID10" in codes
        assert "CNES" in codes


# ── term detail
class TestTermDetail:
    def test_detalhar_termo_existente(self, client):
        """Objetivo: GET /terms/{id} deve retornar o termo correto."""
        # Busca primeiro para obter um ID válido
        search_resp = client.get("/api/v1/search", params={"q": "pneumonia"})
        results = search_resp.json()["results"]
        if not results:
            pytest.skip("Sem resultados para detalhar")
        term_id = results[0]["id"]
        resp = client.get(f"/api/v1/terms/{term_id}")
        assert resp.status_code == 200
        assert "name" in resp.json()

    def test_detalhar_termo_inexistente_retorna_404(self, client):
        resp = client.get("/api/v1/terms/999999999")
        assert resp.status_code == 404
