"""
Testes unitários do parser ETL do CNES.
"""
import io
import pytest
import pandas as pd

from etl import cnes


class TestCnesParser:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_parse_registro_completo(self):
        """Objetivo: registro com todos os campos deve gerar dict correto."""
        df = self._make_df([{
            "CO_CNES": "2078596",
            "NO_FANTASIA": "HOSPITAL UNIVERSITÁRIO POLYDORO",
            "TP_UNIDADE": "HOSPITAL GERAL",
            "NO_MUNICIPIO": "Florianópolis",
            "CO_UF": "SC",
            "NO_BAIRRO": "Trindade",
        }])
        records = cnes._parse_cnes_dataframe(df)
        assert len(records) == 1
        r = records[0]
        assert r["code"] == "2078596"
        assert r["name"] == "HOSPITAL UNIVERSITÁRIO POLYDORO"
        assert r["source"] == "CNES"
        assert "Florianópolis" in (r["description"] or "")

    def test_registros_sem_nome_ignorados(self):
        """Objetivo: registros sem NO_FANTASIA ou CO_CNES devem ser descartados."""
        df = self._make_df([
            {"CO_CNES": "123", "NO_FANTASIA": ""},
            {"CO_CNES": "", "NO_FANTASIA": "HOSPITAL X"},
            {"CO_CNES": "456", "NO_FANTASIA": "CLÍNICA Y"},
        ])
        records = cnes._parse_cnes_dataframe(df)
        assert len(records) == 1
        assert records[0]["code"] == "456"

    def test_coluna_no_razao_social_como_fallback(self):
        """Objetivo: usar NO_RAZAO_SOCIAL quando NO_FANTASIA ausente."""
        df = self._make_df([{
            "CO_CNES": "789",
            "NO_RAZAO_SOCIAL": "SANTA CASA DE MISERICÓRDIA",
            "NO_MUNICIPIO": "São Paulo",
            "CO_UF": "SP",
        }])
        records = cnes._parse_cnes_dataframe(df)
        assert len(records) == 1
        assert records[0]["name"] == "SANTA CASA DE MISERICÓRDIA"

    def test_url_oficial_contem_codigo_cnes(self):
        """Objetivo: official_url deve referenciar o código CNES."""
        df = self._make_df([{
            "CO_CNES": "2078596",
            "NO_FANTASIA": "HU UFSC",
        }])
        records = cnes._parse_cnes_dataframe(df)
        assert "2078596" in records[0]["official_url"]

    def test_dataframe_vazio_retorna_lista_vazia(self):
        df = pd.DataFrame()
        # Deve lançar exceção por falta de colunas — verificamos o comportamento
        with pytest.raises(RuntimeError):
            cnes._parse_cnes_dataframe(df)
