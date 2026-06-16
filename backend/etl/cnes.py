"""
ETL CNES — Cadastro Nacional de Estabelecimentos de Saúde.

Estratégias de download (em ordem de tentativa):
  1. API CKAN do OpenDataSUS (package_show)
  2. Scraping da página do dataset no OpenDataSUS
  3. Fallback em arquivo local via CNES_LOCAL_CSV=...

O CNES é um arquivo grande (~150-300 MB). A variável CNES_MAX_ROWS
limita a importação para o MVP (padrão: 50.000 registros).
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from etl.base import BaseETL, download_file

settings = get_settings()
logger   = logging.getLogger(__name__)

# ── configurações
CKAN_API        = "https://opendatasus.saude.gov.br/api/3/action"
DATASET_PAGE    = "https://opendatasus.saude.gov.br/dataset/cnes-cadastro-nacional-de-estabelecimentos-de-saude"
CNES_DATASET_ID = "cnes-cadastro-nacional-de-estabelecimentos-de-saude"
CNES_MAX_ROWS   = int(os.environ.get("CNES_MAX_ROWS", "50000"))


# ─────────────────────────────────────────────────── descoberta da URL

def _try_ckan_api(session: requests.Session) -> Optional[str]:
    """Estratégia 1: API CKAN /package_show."""
    try:
        resp = session.get(
            f"{CKAN_API}/package_show",
            params={"id": CNES_DATASET_ID},
            timeout=20,
        )
        if not resp.ok or not resp.text.strip():
            logger.warning(f"CKAN API retornou status={resp.status_code} body vazio.")
            return None
        data      = resp.json()
        resources = data.get("result", {}).get("resources", [])
        for r in resources:
            if r.get("format", "").upper() == "CSV" and r.get("url"):
                logger.info(f"CNES URL via CKAN API: {r['url']}")
                return r["url"]
        # fallback: primeiro resource com URL
        for r in resources:
            if r.get("url"):
                logger.info(f"CNES URL via CKAN API (fallback): {r['url']}")
                return r["url"]
    except Exception as exc:
        logger.warning(f"CKAN API falhou: {exc}")
    return None


def _try_page_scraping(session: requests.Session) -> Optional[str]:
    """Estratégia 2: scraping da página HTML do dataset."""
    try:
        resp = session.get(DATASET_PAGE, timeout=20)
        if not resp.ok:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Links de download direto (geralmente em .csv ou .CSV)
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if re.search(r"\.(csv|CSV)($|\?)", href):
                url = href if href.startswith("http") else f"https://opendatasus.saude.gov.br{href}"
                logger.info(f"CNES URL via scraping: {url}")
                return url
        # Qualquer link de recurso dentro da página
        for tag in soup.find_all("a", href=True, class_=re.compile("resource")):
            href = tag["href"]
            if href.startswith("http"):
                logger.info(f"CNES URL via scraping (resource): {href}")
                return href
    except Exception as exc:
        logger.warning(f"Scraping da página CNES falhou: {exc}")
    return None


def _try_ckan_search(session: requests.Session) -> Optional[str]:
    """Estratégia 3: busca genérica via package_search."""
    try:
        resp = session.get(
            f"{CKAN_API}/package_search",
            params={"q": "cnes estabelecimentos", "rows": 5},
            timeout=20,
        )
        if not resp.ok or not resp.text.strip():
            return None
        results = resp.json().get("result", {}).get("results", [])
        for pkg in results:
            if "cnes" in pkg.get("name", "").lower():
                for r in pkg.get("resources", []):
                    if r.get("format", "").upper() == "CSV" and r.get("url"):
                        logger.info(f"CNES URL via package_search: {r['url']}")
                        return r["url"]
    except Exception as exc:
        logger.warning(f"CKAN package_search falhou: {exc}")
    return None


def get_cnes_csv_url() -> Optional[str]:
    """Tenta as três estratégias em sequência e retorna a primeira URL válida."""
    session = requests.Session()
    session.headers["User-Agent"] = (
        "SUSSearch/1.0 (mestrado PPGINFOS/UFSC; contato: github.com/sus-search)"
    )

    for strategy in (_try_ckan_api, _try_page_scraping, _try_ckan_search):
        url = strategy(session)
        if url:
            return url

    return None


# ─────────────────────────────────────────────────── leitura do CSV

def _read_csv(path: Path) -> pd.DataFrame:
    """Lê o CSV do CNES tolerando variações de encoding e separador."""
    for enc in ("utf-8", "latin-1", "cp1252"):
        for sep in (",", ";", "\t"):
            try:
                df = pd.read_csv(
                    path, encoding=enc, sep=sep, dtype=str,
                    low_memory=False, on_bad_lines="skip",
                )
                if df.shape[1] > 3:
                    logger.info(
                        f"CSV lido: {df.shape[0]} linhas, {df.shape[1]} colunas "
                        f"(enc={enc}, sep={sep!r})"
                    )
                    return df
            except Exception:
                continue
    raise ValueError(f"Não foi possível ler o CSV do CNES: {path}")


# ─────────────────────────────────────────────────── classe ETL

class CNESEtl(BaseETL):
    SOURCE_CODE = "CNES"

    def __init__(self, db, data_dir: Optional[str] = None,
                 local_csv: Optional[str] = None):
        super().__init__(db, data_dir)
        self.local_csv = local_csv or os.environ.get("CNES_LOCAL_CSV")
        self.csv_path  = self.data_dir / "cnes_latest.csv"

    def _ensure_csv(self) -> Path:
        # 1. CSV local explícito
        if self.local_csv:
            path = Path(self.local_csv)
            if path.exists():
                logger.info(f"Usando CSV local: {path}")
                return path
            raise FileNotFoundError(
                f"CNES_LOCAL_CSV apontado mas não encontrado: {self.local_csv}"
            )

        # 2. CSV já em cache
        if self.csv_path.exists():
            logger.info(f"CSV em cache: {self.csv_path} — reutilizando.")
            return self.csv_path

        # 3. Download automático com fallbacks
        url = get_cnes_csv_url()
        if not url:
            raise RuntimeError(
                "Não foi possível localizar o CSV do CNES.\n"
                "Opções:\n"
                "  • Baixe manualmente em https://opendatasus.saude.gov.br\n"
                "    e salve em ./data/cnes_latest.csv\n"
                "  • Ou defina: CNES_LOCAL_CSV=/caminho/para/arquivo.csv\n"
                "  • Ou rode apenas o SIGTAP: python -m etl.run_all --source sigtap"
            )
        return download_file(url, self.csv_path, timeout=settings.REQUESTS_TIMEOUT)

    def extract(self) -> list[dict]:
        csv_path = self._ensure_csv()
        df = _read_csv(csv_path)

        # Normaliza nomes de colunas
        df.columns = [c.strip().upper().replace(" ", "_") for c in df.columns]
        df = df.fillna("")

        if CNES_MAX_ROWS and len(df) > CNES_MAX_ROWS:
            logger.info(f"Limitando CNES a {CNES_MAX_ROWS} de {len(df)} registros.")
            df = df.head(CNES_MAX_ROWS)

        return df.to_dict("records")

    def transform(self, raw: list[dict]) -> list[dict]:
        records: list[dict] = []

        def pick(row: dict, *candidates: str) -> str:
            for c in candidates:
                v = row.get(c, "").strip()
                if v:
                    return v
            return ""

        for row in raw:
            code = pick(row, "CO_CNES", "CNES", "CO_ESTABELECIMENTO")
            name = pick(row,
                        "NO_FANTASIA", "NO_RAZAO_SOCIAL",
                        "NOME_FANTASIA", "RAZAO_SOCIAL")
            if not name:
                continue

            municipio  = pick(row, "NO_MUNICIPIO", "MUNICIPIO", "DS_MUNICIPIO")
            uf         = pick(row, "CO_UF", "SG_UF", "UF")
            tipo       = pick(row, "DS_TIPO_UNIDADE", "TP_UNIDADE", "NO_TIPO_UNIDADE")
            logradouro = pick(row, "NO_LOGRADOURO", "LOGRADOURO")
            bairro     = pick(row, "NO_BAIRRO", "BAIRRO")
            telefone   = pick(row, "NU_TELEFONE", "TELEFONE")
            lat        = pick(row, "NU_LATITUDE", "LATITUDE")
            lon        = pick(row, "NU_LONGITUDE", "LONGITUDE")

            desc_parts = [p for p in [tipo, logradouro, bairro, municipio, uf] if p]
            description = " — ".join(desc_parts) if desc_parts else name

            extra: dict = {}
            if municipio:  extra["municipio"] = municipio
            if uf:         extra["uf"]        = uf
            if telefone:   extra["telefone"]  = telefone
            if lat and lon:
                extra["latitude"]  = lat
                extra["longitude"] = lon

            records.append({
                "code":             code or None,
                "name":             name,
                "description":      description,
                "source":           "CNES",
                "category":         tipo or "Estabelecimento de Saúde",
                "subcategory":      municipio or None,
                "additional_info":  json.dumps(extra),
                "official_url": (
                    "https://cnes.datasus.gov.br/pages/estabelecimentos"
                    f"/consulta.jsp?codigo={code}" if code else
                    "https://cnes.datasus.gov.br"
                ),
                "source_competency": None,
                "last_updated":      None,
            })

        logger.info(f"[CNES] {len(records)} estabelecimentos após transformação.")
        return records
