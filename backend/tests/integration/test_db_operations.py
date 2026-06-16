"""
Testes de integração: operações ETL ↔ banco de dados.
Requerem PostgreSQL via TEST_DATABASE_URL.
"""
import json
import pytest
from sqlalchemy import text

from app.repositories.term_repository import TermRepository


@pytest.fixture(autouse=True)
def clean_test_terms(pg_session):
    """Remove termos de teste antes e depois de cada teste."""
    pg_session.execute(
        text("DELETE FROM terms WHERE source IN ('SIGTAP','CID10','CNES') AND code LIKE 'TEST%'")
    )
    pg_session.commit()
    yield
    pg_session.execute(
        text("DELETE FROM terms WHERE source IN ('SIGTAP','CID10','CNES') AND code LIKE 'TEST%'")
    )
    pg_session.commit()


def _make_term(code: str, name: str, source: str = "SIGTAP") -> dict:
    return {
        "code": f"TEST_{code}",
        "name": name,
        "description": f"Descrição de {name}",
        "source": source,
        "category": "Teste",
        "subcategory": None,
        "additional_info": json.dumps({}),
        "official_url": "http://exemplo.gov.br",
        "source_competency": "04/2025",
        "last_updated": None,
    }


class TestBulkInsertAndSearch:
    def test_inserir_e_recuperar_por_busca(self, pg_session):
        """
        Objetivo: registros inseridos via bulk_insert devem ser
        encontrados na busca FTS em seguida.
        Cenário: inserir 'CONSULTA DE URGÊNCIA', buscar por 'urgência'.
        Resultado esperado: ao menos 1 resultado.
        """
        repo = TermRepository(pg_session)
        repo.bulk_insert([_make_term("URGENCIA", "CONSULTA DE URGÊNCIA")])
        pg_session.commit()

        results, total = repo.search("urgência", page=1, limit=10)
        assert total >= 1
        nomes = [r.name for r in results]
        assert any("URGÊNCIA" in n.upper() for n in nomes)

    def test_busca_por_codigo(self, pg_session):
        """
        Objetivo: busca pelo código deve retornar o termo correspondente.
        Cenário: inserir termo com código TEST_J189, buscar por 'TEST_J189'.
        """
        repo = TermRepository(pg_session)
        repo.bulk_insert([_make_term("J189", "PNEUMONIA NÃO ESPECIFICADA", "CID10")])
        pg_session.commit()

        results, total = repo.search("TEST_J189", page=1, limit=10)
        assert total >= 1

    def test_filtro_por_source(self, pg_session):
        """
        Objetivo: filtro source=CID10 deve retornar apenas termos CID10.
        Cenário: inserir termos de fontes diferentes, filtrar por CID10.
        """
        repo = TermRepository(pg_session)
        repo.bulk_insert([
            _make_term("PROC1", "PROCEDIMENTO PARA TESTE", "SIGTAP"),
            _make_term("CID1", "DOENÇA PARA TESTE", "CID10"),
        ])
        pg_session.commit()

        results, total = repo.search("teste", source="CID10", page=1, limit=10)
        for r in results:
            assert r.source == "CID10"

    def test_delete_by_source_remove_apenas_fonte_especificada(self, pg_session):
        """
        Objetivo: delete_by_source deve remover apenas os termos da fonte indicada.
        Cenário: inserir SIGTAP e CID10, deletar SIGTAP.
        Resultado: CID10 permanece.
        """
        repo = TermRepository(pg_session)
        repo.bulk_insert([
            _make_term("SIG1", "PROCEDIMENTO SIGTAP", "SIGTAP"),
            _make_term("CID2", "DOENÇA CID10", "CID10"),
        ])
        pg_session.commit()

        repo.delete_by_source("SIGTAP")

        results_sigtap, _ = repo.search("sigtap", source="SIGTAP")
        codes_sigtap = [r.code for r in results_sigtap if r.code and r.code.startswith("TEST_")]
        assert "TEST_SIG1" not in codes_sigtap

    def test_busca_sem_resultados_retorna_zero(self, pg_session):
        """
        Objetivo: busca por termo inexistente deve retornar total=0.
        Cenário: buscar por 'xkzqwm_xyz_inexistente'.
        """
        repo = TermRepository(pg_session)
        _, total = repo.search("xkzqwm_xyz_inexistente_2025", page=1, limit=10)
        assert total == 0

    def test_paginacao_retorna_subset_correto(self, pg_session):
        """
        Objetivo: paginação deve respeitar limit e offset.
        Cenário: inserir 5 termos com nome similar, buscar com limit=2.
        """
        repo = TermRepository(pg_session)
        records = [_make_term(f"PAG{i}", f"TERMO PAGINAÇÃO {i}") for i in range(5)]
        repo.bulk_insert(records)
        pg_session.commit()

        results_p1, total = repo.search("paginação", page=1, limit=2)
        results_p2, _ = repo.search("paginação", page=2, limit=2)

        assert len(results_p1) <= 2
        ids_p1 = {r.id for r in results_p1}
        ids_p2 = {r.id for r in results_p2}
        assert ids_p1.isdisjoint(ids_p2), "Páginas não devem ter itens em comum"
