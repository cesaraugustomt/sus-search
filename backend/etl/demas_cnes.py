"""
ETL CNES via DEMAS — importa estabelecimentos sem autenticação.

A API DEMAS é pública e gratuita.
Não requer login, senha ou token.

Uso:
  python -m etl.run_all --source cnes
"""
import json
import logging
import os
from typing import Optional

from etl.base import BaseETL
from etl.demas_client import (
    get_todos_municipio,
    get_estabelecimentos,
    normalizar,
    MUNICIPIO_FLORIANOPOLIS,
    UF_SC,
)

logger = logging.getLogger(__name__)

# Municípios padrão. Expanda aqui para importar mais cidades.
# Use get_estabelecimentos(codigo_uf=42) para importar todo SC.
DEFAULT_MUNICIPIOS: list[int] = [
    MUNICIPIO_FLORIANOPOLIS,   # 420540
    # 420910,  # Joinville
    # 420270,  # Blumenau
]


class DEMASCNESEtl(BaseETL):
    SOURCE_CODE = "CNES"

    def __init__(
        self,
        db,
        data_dir: Optional[str] = None,
        municipios: Optional[list[int]] = None,
    ):
        super().__init__(db, data_dir)
        self.municipios = municipios or DEFAULT_MUNICIPIOS

    def extract(self) -> list[dict]:
        all_raw: list[dict] = []
        for municipio in self.municipios:
            logger.info(f"[DEMAS] Buscando município {municipio}...")
            items = get_todos_municipio(
                codigo_municipio=municipio,
                status=1,
            )
            logger.info(f"[DEMAS] {len(items)} estabelecimentos em {municipio}")
            all_raw.extend(items)
        logger.info(f"[DEMAS] Total: {len(all_raw)} estabelecimentos")
        return all_raw

    def transform(self, raw: list[dict]) -> list[dict]:
        records = [normalizar(item) for item in raw if normalizar(item)]
        logger.info(f"[DEMAS] {len(records)} registros normalizados")
        return records
