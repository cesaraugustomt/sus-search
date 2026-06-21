"""
ETL Base — classes e utilitários compartilhados por todos os importadores.

SEGURANÇA DE DADOS — leia antes de modificar:
A combinação delete-then-insert é perigosa se não for atômica. Esta classe
garante duas proteções:
  1. Guard: se transform() devolve 0 registros, ABORTA antes de deletar
     qualquer coisa — nunca apaga uma fonte para deixá-la vazia.
  2. Transação única: delete + insert + update_stats compartilham a mesma
     transação SQL. Qualquer exceção dispara rollback() do delete também.
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
    name: str
    start: int
    length: int


def parse_layout_file(content: str) -> list[FieldLayout]:
    fields: list[FieldLayout] = []
    lines = content.strip().splitlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        try:
            name   = parts[0].strip().lower()
            start  = int(parts[1].strip()) - 1
            length = int(parts[2].strip())
            fields.append(FieldLayout(name, start, length))
        except (ValueError, IndexError):
            logger.debug(f"Layout inválido ignorado: {line!r}")
    return fields


def parse_fixed_width_line(line: str, fields: list[FieldLayout]) -> dict:
    result: dict = {}
    for f in fields:
        end = f.start + f.length
        value = line[f.start:end].strip() if len(line) >= end else ""
        result[f.name] = value
    return result


def download_file(url: str, dest: Path, timeout: int = None) -> Path:
    timeout = timeout or settings.REQUESTS_TIMEOUT
    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info(f"Baixando {url} → {dest}")

    if url.lower().startswith("ftp://"):
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


class ETLAbortedSafety(RuntimeError):
    """Levantada quando o ETL é abortado por proteção de segurança de dados."""


class BaseETL(ABC):
    """Classe base para todos os importadores ETL."""

    SOURCE_CODE: str = ""

    # Lista de códigos de fonte que este ETL gerencia.
    # Por padrão, apenas SOURCE_CODE. Sobrescreva em subclasses que
    # gerenciam múltiplas fontes (ex: SIGTAPEtl gerencia SIGTAP + CID10).
    MANAGED_SOURCES: list[str] = []

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
        """
        Remove registros antigos da fonte e insere os novos — de forma ATÔMICA.

        GUARD CRÍTICO: se `records` estiver vazio, levanta ETLAbortedSafety
        e NÃO toca no banco. Isso impede que uma falha de extração (ex: ZIP
        corrompido, rate limit de API, parsing que retornou 0 linhas) apague
        dados válidos existentes sem substituí-los.
        """
        if not records:
            raise ETLAbortedSafety(
                f"[{self.SOURCE_CODE}] transform() retornou 0 registros. "
                f"Abortando SEM apagar dados existentes — provável falha "
                f"de extração (download incompleto, rate limit, parsing)."
            )

        sources = self.MANAGED_SOURCES or [self.SOURCE_CODE]
        try:
            total_deleted = 0
            for src in sources:
                total_deleted += self.repo.delete_by_source(src)
            logger.info(f"[{self.SOURCE_CODE}] {total_deleted} registros antigos marcados para remoção (não comitado ainda).")

            inserted = self.repo.bulk_insert(records)
            self.repo.update_source_stats(self.SOURCE_CODE, inserted)

            self.db.commit()   # ← commit único: delete + insert + stats juntos
            logger.info(f"[{self.SOURCE_CODE}] {inserted} inseridos. Transação comitada.")
            return inserted

        except Exception:
            self.db.rollback()
            logger.error(f"[{self.SOURCE_CODE}] Erro durante load — ROLLBACK aplicado, nenhum dado foi perdido.", exc_info=True)
            raise

    def run(self) -> int:
        logger.info(f"[{self.SOURCE_CODE}] ── ETL iniciado ──")
        raw      = self.extract()
        records  = self.transform(raw)
        inserted = self.load(records)
        logger.info(f"[{self.SOURCE_CODE}] ── ETL concluído: {inserted} termos ──")
        return inserted
