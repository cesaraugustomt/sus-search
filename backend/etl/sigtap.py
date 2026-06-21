"""
ETL SIGTAP — procedimentos, CID-10 e relacionamento procedimento↔CID.
"""
import json
import logging
import os
import re
import zipfile
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

from app.core.config import get_settings
from etl.base import BaseETL, ETLAbortedSafety, download_file

settings = get_settings()
logger   = logging.getLogger(__name__)

GITHUB_API_URL       = "https://api.github.com/repos/RenatoKR/SIGTAP/contents/tabelas"
GITHUB_RAW_BASE      = "https://raw.githubusercontent.com/RenatoKR/SIGTAP/main/tabelas"
SIGTAP_DOWNLOAD_PAGE = "http://sigtap.datasus.gov.br/tabela-unificada/app/download.jsp"
SIGTAP_BASE_URL      = "http://sigtap.datasus.gov.br"
_ABSOLUTE_URL        = re.compile(r"^(https?|ftp)://", re.IGNORECASE)

_COMPLEXIDADE = {
    "1": "Atenção Básica", "2": "Média Complexidade",
    "3": "Alta Complexidade", "0": "Não se aplica",
}
_SEXO = {"0": "Ambos", "1": "Masculino", "3": "Feminino"}
_FINANCIAMENTO = {
    "001": "PAB", "01": "PAB", "004": "FAEC", "04": "FAEC",
    "005": "MAC", "05": "MAC", "006": "FNS",  "06": "FNS",
    "007": "FAEC","07": "FAEC",
}
_CAPITULO_CID = {
    "A": "Doenças infecciosas e parasitárias",
    "B": "Doenças infecciosas e parasitárias",
    "C": "Neoplasias (tumores)",
    "D": "Doenças do sangue / Neoplasias in situ",
    "E": "Doenças endócrinas e metabólicas",
    "F": "Transtornos mentais e comportamentais",
    "G": "Doenças do sistema nervoso",
    "H": "Doenças do olho / ouvido",
    "I": "Doenças do aparelho circulatório",
    "J": "Doenças do aparelho respiratório",
    "K": "Doenças do aparelho digestivo",
    "L": "Doenças da pele",
    "M": "Doenças do sistema osteomuscular",
    "N": "Doenças do aparelho geniturinário",
    "O": "Gravidez, parto e puerpério",
    "P": "Afecções perinatais",
    "Q": "Malformações congênitas",
    "R": "Sintomas e sinais anormais",
    "S": "Lesões e causas externas",
    "T": "Lesões e causas externas",
    "V": "Causas externas de morbidade",
    "W": "Causas externas de morbidade",
    "X": "Causas externas de morbidade",
    "Y": "Causas externas de morbidade",
    "Z": "Fatores que influenciam o estado de saúde",
}


def _val_reais(raw: str) -> Optional[str]:
    try:
        v = raw.strip()
        if not v or v == "0" * len(v):
            return None
        c = int(v)
        return None if c == 0 else f"R$ {c/100:,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except Exception:
        return None


def _faixa_etaria(min_raw: str, max_raw: str) -> Optional[str]:
    """
    Constrói a faixa etária SÓ quando há restrição real.
      "0000" / "9999" → None (sem restrição — não exibe)
      "0000" / "0060" → "até 60 anos"
      "0012" / "9999" → "a partir de 12 anos"
      "0012" / "0060" → "12 a 60 anos"
    """
    try:
        n_min = int(min_raw.strip()) if min_raw.strip() else 0
        n_max = int(max_raw.strip()) if max_raw.strip() else 0
        tem_min = n_min > 0
        tem_max = 0 < n_max < 9999
        if not tem_min and not tem_max:
            return None
        if tem_min and tem_max:
            return f"{n_min} a {n_max} anos"
        if tem_min:
            return f"a partir de {n_min} anos"
        return f"até {n_max} anos"
    except Exception:
        return None


def _get_url_from_github() -> Optional[str]:
    try:
        resp = requests.get(GITHUB_API_URL, timeout=15)
        resp.raise_for_status()
        zips = sorted(
            [f for f in resp.json() if isinstance(f, dict) and f.get("name","").endswith(".zip")],
            key=lambda f: f["name"], reverse=True,
        )
        if zips:
            url = zips[0].get("download_url") or f"{GITHUB_RAW_BASE}/{zips[0]['name']}"
            logger.info(f"[SIGTAP] GitHub mirror: {zips[0]['name']} → {url}")
            return url
    except Exception as exc:
        logger.warning(f"[SIGTAP] GitHub API falhou: {exc}")
    return None


def _get_url_from_portal() -> Optional[str]:
    try:
        resp = requests.get(SIGTAP_DOWNLOAD_PAGE, timeout=20, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup.find_all("a", href=True):
            href: str = tag["href"]
            if re.search(r"\.zip", href, re.IGNORECASE) and "competencia" in href.lower():
                return href if _ABSOLUTE_URL.match(href) else f"{SIGTAP_BASE_URL}/{href.lstrip('/')}"
    except Exception as exc:
        logger.warning(f"[SIGTAP] Portal falhou: {exc}")
    return None


def get_sigtap_zip_url() -> Optional[str]:
    return _get_url_from_github() or _get_url_from_portal()


def _find_in_zip(zf: zipfile.ZipFile, basename: str) -> Optional[str]:
    pat = basename.lower()
    for name in zf.namelist():
        if os.path.basename(name).lower() == pat:
            return name
    return None


def _read_raw(zf: zipfile.ZipFile, basename: str) -> Optional[str]:
    e = _find_in_zip(zf, basename)
    return zf.read(e).decode("latin-1") if e else None


def _parse_procedimentos(content: str) -> list[dict]:
    records = []
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if not line or len(line) < 11:
            continue
        code = line[0:10].strip()
        name = line[10:110].strip() if len(line) > 10 else ""
        if not code or not name or not re.match(r"^\d{10}$", code):
            continue
        rec: dict = {
            "co_procedimento": code,
            "no_procedimento": name,
            "dt_competencia":  line[110:116].strip() if len(line) > 110 else "",
        }
        if len(line) > 122: rec["qt_max_exec"]      = line[116:122].strip()
        if len(line) > 143: rec["vl_hospitalar"]    = line[134:143].strip()
        if len(line) > 152: rec["vl_ambulatorial"]  = line[143:152].strip()
        if len(line) > 161: rec["vl_profissional"]  = line[152:161].strip()
        if len(line) > 180: rec["co_complexidade"]  = line[179:180].strip()
        if len(line) > 181: rec["co_sexo"]          = line[180:181].strip()
        if len(line) > 185: rec["vl_idade_min"]     = line[181:185].strip()
        if len(line) > 189: rec["vl_idade_max"]     = line[185:189].strip()
        if len(line) > 193: rec["co_financiamento"] = line[190:193].strip()
        records.append(rec)
    logger.info(f"[SIGTAP] {len(records)} procedimentos parseados.")
    return records


def _parse_cid(content: str) -> list[dict]:
    seen: set[str] = set()
    records = []
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if not line or len(line) < 5:
            continue
        code = line[0:4].strip()
        name = line[4:104].strip() if len(line) > 4 else ""
        if code and code not in seen:
            seen.add(code)
            records.append({
                "co_cid": code, "no_cid": name,
                "dt_competencia": line[104:110].strip() if len(line) > 104 else "",
            })
    logger.info(f"[CID10] {len(records)} códigos únicos.")
    return records


def _parse_proc_cid_compat(content: str) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    proc_to_cids: dict[str, list[str]] = {}
    cid_to_procs: dict[str, list[str]] = {}
    n = 0
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if not line or len(line) < 14:
            continue
        proc = line[0:10].strip()
        cid  = line[10:14].strip()
        if not proc or not cid or not re.match(r"^\d{10}$", proc):
            continue
        proc_to_cids.setdefault(proc, []).append(cid)
        cid_to_procs.setdefault(cid,  []).append(proc)
        n += 1
    logger.info(f"[SIGTAP×CID] {n:,} pares | {len(proc_to_cids):,} procedimentos | {len(cid_to_procs):,} CIDs")
    return proc_to_cids, cid_to_procs


def _parse_grupos(content: str) -> dict[str, str]:
    result = {}
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if line and len(line) >= 3:
            result[line[0:2].strip()] = line[2:102].strip()
    return result


def _parse_subgrupos(content: str) -> dict[str, str]:
    result = {}
    for line in content.splitlines():
        line = line.rstrip("\r\n")
        if line and len(line) >= 5:
            result[line[0:4].strip()] = line[4:104].strip()
    return result


class SIGTAPEtl(BaseETL):
    SOURCE_CODE = "SIGTAP"

    def __init__(self, db, data_dir: Optional[str] = None, local_zip: Optional[str] = None):
        super().__init__(db, data_dir)
        self.local_zip      = local_zip or os.environ.get("SIGTAP_LOCAL_ZIP")
        self.zip_path       = self.data_dir / "sigtap_latest.zip"
        self._proc_to_cids: dict[str, list[str]] = {}
        self._cid_to_procs: dict[str, list[str]] = {}

    def _ensure_zip(self) -> Path:
        if self.local_zip:
            path = Path(self.local_zip)
            if path.exists():
                return path
            raise FileNotFoundError(f"ZIP local não encontrado: {self.local_zip}")
        if self.zip_path.exists():
            logger.info(f"ZIP em cache: {self.zip_path}")
            return self.zip_path
        url = get_sigtap_zip_url()
        if not url:
            raise RuntimeError("ZIP SIGTAP não encontrado.")
        return download_file(url, self.zip_path, timeout=settings.REQUESTS_TIMEOUT)

    def extract(self) -> list[dict]:
        zip_path = self._ensure_zip()
        raw: list[dict] = []
        with zipfile.ZipFile(zip_path, "r") as zf:
            if proc_raw := _read_raw(zf, "tb_procedimento.txt"):
                for r in _parse_procedimentos(proc_raw):
                    r["_type"] = "procedimento"
                    raw.append(r)
            if cid_raw := _read_raw(zf, "tb_cid.txt"):
                for r in _parse_cid(cid_raw):
                    r["_type"] = "cid"
                    raw.append(r)
            compat_raw = _read_raw(zf, "rl_procedimento_cid.txt")
            if compat_raw:
                self._proc_to_cids, self._cid_to_procs = _parse_proc_cid_compat(compat_raw)
            grp       = _read_raw(zf, "tb_grupo.txt")
            grupos    = _parse_grupos(grp) if grp else {}
            sub       = _read_raw(zf, "tb_sub_grupo.txt")
            subgrupos = _parse_subgrupos(sub) if sub else {}

        for r in raw:
            if r.get("_type") == "procedimento":
                code = r["co_procedimento"]
                r["_grupo"]    = grupos.get(code[:2], "")
                r["_subgrupo"] = subgrupos.get(code[:4], "")

        logger.info(f"Total extraído: {len(raw)}")
        return raw

    def transform(self, raw: list[dict]) -> list[dict]:
        records: list[dict] = []
        n_proc = n_cid = 0

        for r in raw:
            tipo = r.pop("_type", "procedimento")

            if tipo == "procedimento":
                code = r["co_procedimento"]
                name = r["no_procedimento"]
                info: dict = {}

                if (v := r.get("co_complexidade", "")):
                    info["complexidade"] = _COMPLEXIDADE.get(v, v)
                if (v := r.get("co_sexo", "")) and v != "0":
                    info["sexo_compativel"] = _SEXO.get(v, v)

                fin = r.get("co_financiamento", "")
                if fin:
                    fin_k = fin.lstrip("0") or fin
                    info["tipo_financiamento"] = _FINANCIAMENTO.get(fin, _FINANCIAMENTO.get(fin_k, fin_k))

                if (v := _val_reais(r.get("vl_ambulatorial", ""))): info["valor_ambulatorial"] = v
                if (v := _val_reais(r.get("vl_hospitalar",  ""))): info["valor_hospitalar"]   = v
                if (v := _val_reais(r.get("vl_profissional",""))): info["valor_profissional"]  = v

                faixa = _faixa_etaria(r.get("vl_idade_min",""), r.get("vl_idade_max",""))
                if faixa:
                    info["faixa_etaria"] = faixa

                qt = r.get("qt_max_exec","").strip().lstrip("0")
                if qt:
                    try: info["qt_maxima_execucao"] = int(qt)
                    except Exception: pass

                cids = self._proc_to_cids.get(code, [])
                if cids:
                    info["cids_compativeis"]   = cids[:20]
                    info["n_cids_compativeis"] = len(cids)

                records.append({
                    "code":              code,
                    "name":              name,
                    "description":       name,
                    "source":            "SIGTAP",
                    "category":          r.pop("_grupo","")    or None,
                    "subcategory":       r.pop("_subgrupo","") or None,
                    "additional_info":   json.dumps(info, ensure_ascii=False),
                    "official_url":      f"http://sigtap.datasus.gov.br/tabela-unificada/app/sec/procedimento/exibir/{code}",
                    "source_competency": r.get("dt_competencia") or None,
                    "last_updated":      None,
                })
                n_proc += 1

            elif tipo == "cid":
                code = r["co_cid"]
                name = r["no_cid"]
                if not code or not name:
                    continue
                capitulo = _CAPITULO_CID.get(code[0].upper(), "")
                info: dict = {}
                if capitulo: info["capitulo"] = capitulo
                procs = self._cid_to_procs.get(code, [])
                if procs:
                    info["n_procedimentos"]        = len(procs)
                    info["procedimentos_exemplos"] = procs[:5]

                records.append({
                    "code":              code,
                    "name":              name,
                    "description":       f"{capitulo} — {name}" if capitulo else name,
                    "source":            "CID10",
                    "category":          capitulo or "Classificação Internacional de Doenças",
                    "subcategory":       None,
                    "additional_info":   json.dumps(info, ensure_ascii=False),
                    "official_url":      "https://rts.saude.gov.br",
                    "source_competency": r.get("dt_competencia") or None,
                    "last_updated":      None,
                })
                n_cid += 1

        logger.info(f"[transform] SIGTAP={n_proc} | CID10={n_cid} | total={len(records)}")
        return records

    def load(self, records: list[dict]) -> int:
        """
        Remove SIGTAP + CID10 antigos e insere os novos — de forma ATÔMICA.

        GUARDS CRÍTICOS (proteção contra a perda de dados que já aconteceu):
          1. Se SIGTAP ou CID10 vier vazio na extração (ex: ZIP corrompido,
             rate limit no GitHub mirror, parsing parcial) → ABORTA sem
             tocar no banco. Nunca apaga uma fonte para deixá-la vazia.
          2. delete + insert + stats das DUAS fontes ficam na MESMA
             transação. Qualquer exceção dispara rollback() completo.
        """
        n_sigtap = sum(1 for r in records if r.get("source") == "SIGTAP")
        n_cid10  = sum(1 for r in records if r.get("source") == "CID10")

        if n_sigtap == 0 or n_cid10 == 0:
            raise ETLAbortedSafety(
                f"[SIGTAP] Extração incompleta — SIGTAP={n_sigtap}, CID10={n_cid10}. "
                f"Abortando SEM apagar dados existentes."
            )

        try:
            for src in ("SIGTAP", "CID10"):
                deleted = self.repo.delete_by_source(src)
                logger.info(f"[{src}] {deleted} registros antigos marcados (não comitado ainda).")

            inserted = self.repo.bulk_insert(records)

            comp_sigtap = next((r["source_competency"] for r in records if r.get("source") == "SIGTAP" and r.get("source_competency")), None)
            comp_cid10  = next((r["source_competency"] for r in records if r.get("source") == "CID10"  and r.get("source_competency")), None)
            self.repo.update_source_stats("SIGTAP", n_sigtap, competency=comp_sigtap)
            self.repo.update_source_stats("CID10",  n_cid10,  competency=comp_cid10)

            self.db.commit()
            logger.info(f"SIGTAP={n_sigtap} (comp={comp_sigtap}) | CID10={n_cid10} (comp={comp_cid10}) | total={inserted} | Transação comitada.")
            return inserted

        except Exception:
            self.db.rollback()
            logger.error("[SIGTAP] Erro durante load — ROLLBACK aplicado, nenhum dado foi perdido.", exc_info=True)
            raise
