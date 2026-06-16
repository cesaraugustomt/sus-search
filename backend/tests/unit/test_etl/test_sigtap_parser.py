"""
Testes unitários do parser ETL do SIGTAP.
Não requerem banco de dados nem acesso à internet.
"""
import io
import zipfile
from pathlib import Path
import pytest

from etl.base import (
    FieldSpec,
    parse_layout_file,
    parse_fixed_line,
    decode_file,
    _find_zip_url if False else None,   # importação condicional
)
from etl import sigtap


# ── helpers para criar ZIPs de teste em memória
def _make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ── parse_layout_file
class TestParseLayoutFile:
    def test_layout_simples(self):
        """Objetivo: parsear um layout CSV de 2 campos."""
        content = "nome_campo,inicio,tamanho,tipo\nco_procedimento,1,10,TEXTO\nno_procedimento,11,100,TEXTO\n"
        specs = parse_layout_file(content)
        assert len(specs) == 2
        assert specs[0].name == "co_procedimento"
        assert specs[0].start == 0       # 1-indexed → 0-indexed
        assert specs[0].length == 10
        assert specs[1].start == 10      # 11-1 = 10

    def test_layout_header_ignorado(self):
        """Objetivo: a primeira linha (header) deve ser ignorada."""
        content = "HEADER,LINHA,IGNORADA\nco_cid,1,4,TEXTO\n"
        specs = parse_layout_file(content)
        assert len(specs) == 1
        assert specs[0].name == "co_cid"

    def test_layout_vazio_retorna_lista_vazia(self):
        specs = parse_layout_file("nome,inicio,tamanho\n")
        assert specs == []

    def test_layout_linha_invalida_ignorada(self):
        content = "nome,inicio,tamanho\nvalido,1,10,TEXTO\ninvalido,abc,xyz\n"
        specs = parse_layout_file(content)
        assert len(specs) == 1
        assert specs[0].name == "valido"


# ── parse_fixed_line
class TestParseFixedLine:
    def _layout(self):
        return [
            FieldSpec("co_procedimento", 0, 10),
            FieldSpec("no_procedimento", 10, 100),
        ]

    def test_extrai_campos_corretos(self):
        """Objetivo: extrair campos de uma linha de largura fixa."""
        line = "0301010013" + "CONSULTA MÉDICA EM ATENÇÃO BÁSICA".ljust(100)
        row = parse_fixed_line(line, self._layout())
        assert row["co_procedimento"] == "0301010013"
        assert "CONSULTA" in row["no_procedimento"]

    def test_linha_curta_retorna_string_vazia(self):
        """Objetivo: linha mais curta que o campo retorna string vazia."""
        line = "0301"
        row = parse_fixed_line(line, self._layout())
        assert row["co_procedimento"] == "0301"
        assert row["no_procedimento"] == ""

    def test_whitespace_removido(self):
        """Objetivo: espaços em branco devem ser removidos dos valores."""
        line = "J18       " + "PNEUMONIA         ".ljust(100)
        specs = [FieldSpec("co_cid", 0, 10), FieldSpec("no_cid", 10, 100)]
        row = parse_fixed_line(line, specs)
        assert row["co_cid"] == "J18"
        assert row["no_cid"] == "PNEUMONIA"


# ── decode_file
class TestDecodeFile:
    def test_decodifica_latin1(self):
        raw = "PNEUMONIA BACTERIANA".encode("latin-1")
        assert decode_file(raw) == "PNEUMONIA BACTERIANA"

    def test_decodifica_utf8(self):
        raw = "Ação Terapêutica".encode("utf-8")
        assert decode_file(raw) == "Ação Terapêutica"


# ── parse_procedures
class TestParseProcedures:
    def _make_sigtap_zip(self) -> bytes:
        layout = "nome_campo,inicio,tamanho,tipo\nco_procedimento,1,10,TEXTO\nno_procedimento,11,100,TEXTO\ndt_competencia,111,6,TEXTO\n"
        proc_line = "0301010013" + "CONSULTA MÉDICA".ljust(100) + "202504"
        return _make_zip(
            {
                "tb_procedimento_layout.txt": layout.encode("latin-1"),
                "tb_procedimento.txt": proc_line.encode("latin-1"),
            }
        )

    def test_extrai_pelo_menos_um_procedimento(self, tmp_path):
        zip_bytes = self._make_sigtap_zip()
        zip_path = tmp_path / "sigtap.zip"
        zip_path.write_bytes(zip_bytes)
        procs = sigtap.parse_procedures(zip_path)
        assert len(procs) == 1
        assert procs[0]["code"] == "0301010013"
        assert "CONSULTA" in procs[0]["name"]

    def test_retorna_lista_vazia_sem_arquivo(self, tmp_path):
        zip_bytes = _make_zip({"outro_arquivo.txt": b"conteudo"})
        zip_path = tmp_path / "sigtap.zip"
        zip_path.write_bytes(zip_bytes)
        procs = sigtap.parse_procedures(zip_path)
        assert procs == []


# ── parse_cid10_from_sigtap
class TestParseCid10:
    def _make_cid_zip(self) -> bytes:
        layout = "nome_campo,inicio,tamanho,tipo\nco_cid,1,4,TEXTO\nno_cid,5,100,TEXTO\ndt_competencia,105,6,TEXTO\n"
        cid_line = "J189" + "PNEUMONIA NÃO ESPECIFICADA".ljust(100) + "202504"
        return _make_zip(
            {
                "tb_cid_layout.txt": layout.encode("latin-1"),
                "tb_cid.txt": cid_line.encode("latin-1"),
            }
        )

    def test_extrai_pelo_menos_um_cid(self, tmp_path):
        zip_bytes = self._make_cid_zip()
        zip_path = tmp_path / "sigtap.zip"
        zip_path.write_bytes(zip_bytes)
        cids = sigtap.parse_cid10_from_sigtap(zip_path)
        assert len(cids) == 1
        assert cids[0]["code"] == "J189"

    def test_deduplicacao_codigos(self, tmp_path):
        """Objetivo: o mesmo código CID não deve aparecer duplicado."""
        layout = "nome_campo,inicio,tamanho,tipo\nco_cid,1,4,TEXTO\nno_cid,5,100,TEXTO\ndt_competencia,105,6,TEXTO\n"
        cid_dup = "J189" + "PNEUMONIA".ljust(100) + "202504\n" + \
                  "J189" + "PNEUMONIA".ljust(100) + "202504"
        zip_bytes = _make_zip({
            "tb_cid_layout.txt": layout.encode("latin-1"),
            "tb_cid.txt": cid_dup.encode("latin-1"),
        })
        zip_path = tmp_path / "sigtap.zip"
        zip_path.write_bytes(zip_bytes)
        cids = sigtap.parse_cid10_from_sigtap(zip_path)
        assert len(cids) == 1
