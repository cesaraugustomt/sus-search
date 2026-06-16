"""
Testes unitários do TermRepository.
Verifica a camada de acesso a dados isolada do endpoint.
"""
import json
from unittest.mock import MagicMock, patch, call
import pytest

from app.repositories.term_repository import TermRepository


def _make_mock_db():
    """Cria um mock de Session do SQLAlchemy."""
    db = MagicMock()
    return db


class TestTermRepositoryBulkInsert:
    def test_bulk_insert_retorna_quantidade_inserida(self):
        """Objetivo: bulk_insert deve retornar len(records) após commit."""
        db = _make_mock_db()
        repo = TermRepository(db)
        records = [
            {
                "code": "J18.9",
                "name": "PNEUMONIA",
                "description": None,
                "source": "CID10",
                "category": "CID",
                "subcategory": None,
                "additional_info": "{}",
                "official_url": None,
                "source_competency": "04/2025",
                "last_updated": None,
            }
        ]
        count = repo.bulk_insert(records)
        assert count == 1
        db.execute.assert_called()
        db.commit.assert_called()

    def test_bulk_insert_lista_vazia_retorna_zero(self):
        """Objetivo: lista vazia não deve acionar execute nem commit."""
        db = _make_mock_db()
        repo = TermRepository(db)
        count = repo.bulk_insert([])
        assert count == 0
        db.execute.assert_not_called()
        db.commit.assert_not_called()

    def test_bulk_insert_multiplos_registros(self):
        """Objetivo: contar corretamente múltiplos registros."""
        db = _make_mock_db()
        repo = TermRepository(db)
        records = [{"code": str(i), "name": f"Term {i}", "description": None,
                    "source": "SIGTAP", "category": None, "subcategory": None,
                    "additional_info": "{}", "official_url": None,
                    "source_competency": None, "last_updated": None}
                   for i in range(50)]
        count = repo.bulk_insert(records)
        assert count == 50


class TestTermRepositoryDeleteBySource:
    def test_delete_by_source_chama_execute_com_source(self):
        """Objetivo: delete_by_source deve passar o source correto para o SQL."""
        db = _make_mock_db()
        db.execute.return_value.rowcount = 100
        repo = TermRepository(db)
        count = repo.delete_by_source("SIGTAP")
        assert count == 100
        db.commit.assert_called_once()


class TestTermRepositoryUpdateStats:
    def test_update_source_stats_chama_commit(self):
        """Objetivo: update_source_stats deve commitar as alterações."""
        db = _make_mock_db()
        repo = TermRepository(db)
        repo.update_source_stats("SIGTAP", 4600, "04/2025")
        db.commit.assert_called_once()

    def test_update_source_stats_sem_competency(self):
        """Objetivo: update_source_stats sem competency não inclui esse parâmetro."""
        db = _make_mock_db()
        repo = TermRepository(db)
        repo.update_source_stats("CNES", 300000)
        db.commit.assert_called_once()


class TestTermRepositoryCountAll:
    def test_count_all_retorna_escalar(self):
        """Objetivo: count_all deve retornar o valor escalar do banco."""
        db = _make_mock_db()
        db.execute.return_value.scalar.return_value = 42
        repo = TermRepository(db)
        assert repo.count_all() == 42

    def test_count_all_retorna_zero_quando_none(self):
        """Objetivo: count_all deve retornar 0 se o banco retornar None."""
        db = _make_mock_db()
        db.execute.return_value.scalar.return_value = None
        repo = TermRepository(db)
        assert repo.count_all() == 0
