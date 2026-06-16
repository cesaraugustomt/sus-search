"""
Testes unitários do SearchService.
Usa mock do repositório — sem banco de dados.
"""
import math
from unittest.mock import MagicMock, patch
import pytest

from app.services.search_service import SearchService
from app.schemas.search import TermResponse


def _make_term(
    id=1,
    code="J18.9",
    name="PNEUMONIA NÃO ESPECIFICADA",
    source="CID10",
    category="Classificação Internacional de Doenças",
):
    t = MagicMock()
    t.id = id
    t.code = code
    t.name = name
    t.description = None
    t.source = source
    t.category = category
    t.subcategory = None
    t.additional_info = {}
    t.official_url = "https://rts.saude.gov.br"
    t.source_competency = "04/2025"
    t.last_updated = None
    t.created_at = None
    return t


class TestSearchService:
    def _make_svc(self, terms=None, total=None):
        """Cria um SearchService com repositório mockado."""
        db = MagicMock()
        svc = SearchService(db)
        terms = terms or []
        total = total if total is not None else len(terms)
        svc.repo = MagicMock()
        svc.repo.search.return_value = (terms, total)
        return svc

    # ── busca normal
    def test_search_retorna_resultados(self):
        """Objetivo: garantir que o serviço retorna SearchResponse bem formado."""
        term = _make_term()
        svc = self._make_svc(terms=[term], total=1)
        resp = svc.search("pneumonia")
        assert resp.total == 1
        assert resp.query == "pneumonia"
        assert len(resp.results) == 1
        assert resp.results[0].name == "PNEUMONIA NÃO ESPECIFICADA"

    def test_search_query_vazia_retorna_zero(self):
        """Objetivo: query vazia não deve acionar o repositório."""
        svc = self._make_svc()
        resp = svc.search("   ")
        assert resp.total == 0
        assert resp.results == []
        svc.repo.search.assert_not_called()

    def test_paginacao_correta(self):
        """Objetivo: calcular número de páginas corretamente."""
        svc = self._make_svc(terms=[_make_term()], total=45)
        resp = svc.search("consulta", page=2, limit=20)
        assert resp.pages == math.ceil(45 / 20)
        assert resp.page == 2
        assert resp.limit == 20

    def test_limit_maximo_respeitado(self):
        """Objetivo: limit não pode ultrapassar MAX_PAGE_SIZE."""
        svc = self._make_svc()
        svc.search("consulta", limit=9999)
        call_args = svc.repo.search.call_args
        assert call_args[1]["limit"] <= 100

    def test_source_invalido_ignorado(self):
        """Objetivo: source inválido deve ser descartado silenciosamente."""
        svc = self._make_svc()
        svc.search("exame", source="FONTE_INEXISTENTE")
        call_args = svc.repo.search.call_args
        assert call_args[1]["source"] is None

    def test_source_valido_normalizado_maiusculo(self):
        """Objetivo: source deve ser normalizado para maiúsculas."""
        svc = self._make_svc()
        svc.search("consulta", source="sigtap")
        call_args = svc.repo.search.call_args
        assert call_args[1]["source"] == "SIGTAP"

    def test_total_zero_sem_resultados(self):
        """Objetivo: quando total=0, pages deve ser 0."""
        svc = self._make_svc(terms=[], total=0)
        resp = svc.search("termoInexistente")
        assert resp.pages == 0
        assert resp.total == 0
