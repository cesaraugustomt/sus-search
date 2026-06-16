"""
ETL Base — classes e utilitários compartilhados por todos os importadores.
"""
import ftplib
import logging
import os
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.repositories.term_repository import TermRepository

settings = get_settings()
logger = logging.getLogger(__name__)


@dataclass
class FieldLayout:
    """Define a posição e tamanho de um campo em um arquivo TXT posicional."""
    name: str
    start: int   # 0-indexado
    length: int


def parse_layout_file(content: str) -> list[FieldLayout]:
    """
    Lê o arquivo de layout do SIGTAP/RTS.
    Formato: CSV com colunas  nome, posição_inicial (1-indexed), tamanho, ...
    Converte posição para 0-indexed.
    """
    fields: list[FieldLayout] = []
    lines = content.strip().splitlines()
    for line in lines[1:]:       # pula cabeçalho
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            name   = parts[0].strip().lower()
            start  = int(parts[1].strip()) - 1   # 1-idx → 0-idx
            length = int(parts[2].strip())
            fields.append(FieldLayout(name, start, length))
        except (ValueError, IndexError):
            logger.debug(f"Layout inválido ignorado: {line!r}")
    return fields


def parse_fixed_width_line(line: str, fields: list[FieldLayout]) -> dict:
    """Extrai campos de uma linha de largura fixa usando o layout."""
    result: dict = {}
    for f in fields:
        end = f.start + f.length
        value = line[f.start:end].strip() if len(line) >= end else ""
        result[f.name] = value
    return result


def download_file(url: str, dest: Path, timeout: int = None) -> Path:
    """
    Faz download de um arquivo e salva em `dest`.
    Suporta HTTP, HTTPS e FTP (via urllib).
    """
    timeout = timeout or settings.REQUESTS_TIMEOUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Baixando {url} → {dest}")

    if url.lower().startswith("ftp://"):
        # requests não suporta FTP — usa urllib, que suporta nativamente
        urllib.request.urlretrieve(url, str(dest))
    else:
        resp = requests.get(url, timeout=timeout, stream=True, verify=False)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                f.write(chunk)

    size_kb = dest.stat().st_size / 1024
    logger.info(f"Download concluído: {dest} ({size_kb:.1f} KB)")
    return dest


class BaseETL(ABC):
    """Classe base para todos os importadores ETL."""

    SOURCE_CODE: str = ""

    def __init__(self, db: Session, data_dir: Optional[str] = None):
        self.db        = db
        self.repo      = TermRepository(db)
        self.data_dir  = Path(data_dir or settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def extract(self) -> list[dict]:
        """Baixa e parseia os dados brutos. Retorna lista de dicts."""
        ...

    @abstractmethod
    def transform(self, raw: list[dict]) -> list[dict]:
        """Transforma dicts brutos no formato do banco."""
        ...

    def load(self, records: list[dict]) -> int:
        """Remove registros antigos da fonte e insere os novos."""
        logger.info(f"[{self.SOURCE_CODE}] Removendo registros antigos...")
        deleted = self.repo.delete_by_source(self.SOURCE_CODE)
        logger.info(f"[{self.SOURCE_CODE}] {deleted} removidos.")

        logger.info(f"[{self.SOURCE_CODE}] Inserindo {len(records)} registros...")
        inserted = self.repo.bulk_insert(records)
        self.repo.update_source_stats(self.SOURCE_CODE, inserted)
        logger.info(f"[{self.SOURCE_CODE}] {inserted} inseridos.")
        return inserted

    def run(self) -> int:
        logger.info(f"[{self.SOURCE_CODE}] ── ETL iniciado ──")
        raw      = self.extract()
        records  = self.transform(raw)
        inserted = self.load(records)
        logger.info(f"[{self.SOURCE_CODE}] ── ETL concluído: {inserted} termos ──")
        return inserted
