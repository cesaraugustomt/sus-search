"""
FHIR R4 Resource Builder — SUS Search

Converte termos do banco (SIGTAP, CID-10, CIAP-2, CNES) em recursos FHIR R4.
Segue os perfis brasileiros da RNDS e o padrão HL7 FHIR R4.

CodeSystems:
  SIGTAP: http://www.saude.gov.br/fhir/r4/CodeSystem/sigtap
  CID-10: http://hl7.org/fhir/sid/icd-10
  CIAP-2: http://hl7.org/fhir/sid/icpc-2
  CNES:   http://www.saude.gov.br/fhir/r4/CodeSystem/cnes
"""
import json
from datetime import datetime, timezone
from typing import Optional

from app.models.term import Term

CS_SIGTAP  = "http://www.saude.gov.br/fhir/r4/CodeSystem/sigtap"
CS_CID10   = "http://hl7.org/fhir/sid/icd-10"
CS_CIAP2   = "http://hl7.org/fhir/sid/icpc-2"
CS_CNES    = "http://www.saude.gov.br/fhir/r4/CodeSystem/cnes"
RNDS_BASE  = "http://www.saude.gov.br/fhir/r4"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_competencia(raw: Optional[str]) -> Optional[str]:
    if not raw or len(raw) < 6:
        return raw
    return f"{raw[0:4]}-{raw[4:6]}"


def _parse_info(term: Term) -> dict:
    try:
        ai = term.additional_info
        return (ai if isinstance(ai, dict) else json.loads(ai or "{}")) or {}
    except Exception:
        return {}


# ─────────────────────────────────── SIGTAP → Procedure

def sigtap_to_procedure(term: Term) -> dict:
    info = _parse_info(term)
    comp = _fmt_competencia(term.source_competency)
    extensions = []
    for url_slug, key in [
        ("complexidade", "complexidade"),
        ("tipo-financiamento", "tipo_financiamento"),
        ("valor-ambulatorial", "valor_ambulatorial"),
        ("valor-hospitalar",   "valor_hospitalar"),
        ("faixa-etaria",       "faixa_etaria"),
        ("sexo-compativel",    "sexo_compativel"),
    ]:
        if info.get(key):
            extensions.append({"url": f"{RNDS_BASE}/StructureDefinition/{url_slug}", "valueString": info[key]})
    if comp:
        extensions.append({"url": f"{RNDS_BASE}/StructureDefinition/competencia-sigtap", "valueString": comp})

    reason_codes = [
        {"coding": [{"system": CS_CID10, "code": cid}]}
        for cid in (info.get("cids_compativeis") or [])[:5]
    ]
    resource: dict = {
        "resourceType": "Procedure",
        "id": f"sigtap-{term.code}",
        "meta": {"profile": [f"{RNDS_BASE}/StructureDefinition/BRProcedimento"], "lastUpdated": _now_iso()},
        "status": "unknown",
        "code": {"coding": [{"system": CS_SIGTAP, "code": term.code, "display": term.name}], "text": term.name},
    }
    if term.category:
        resource["category"] = {"text": term.category}
    if extensions:
        resource["extension"] = extensions
    if reason_codes:
        resource["reasonCode"] = reason_codes
    return resource


# ─────────────────────────────────── CID-10 → Condition

def cid10_to_condition(term: Term) -> dict:
    info = _parse_info(term)
    resource: dict = {
        "resourceType": "Condition",
        "id": f"cid-{term.code}",
        "meta": {"profile": [f"{RNDS_BASE}/StructureDefinition/BRCondicaoSaude"], "lastUpdated": _now_iso()},
        "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
        "code": {"coding": [{"system": CS_CID10, "code": term.code, "display": term.name}], "text": term.name},
    }
    if info.get("capitulo"):
        resource["category"] = [{"text": info["capitulo"]}]
    n_procs = info.get("n_procedimentos", 0)
    procs   = info.get("procedimentos_exemplos", [])
    if n_procs:
        resource["note"] = [{"text": f"{n_procs} procedimento(s) SUS (SIGTAP) compatível(is). Exemplos: {', '.join(procs[:3])}"}]
    return resource


# ─────────────────────────────────── CIAP-2 → Observation / Condition / Procedure

def ciap2_to_fhir(term: Term) -> dict:
    """
    Mapeamento CIAP-2 → FHIR R4 por componente:
      01-29 Sintomas/queixas  → Observation (status: preliminary)
      30-49 Procedimentos     → Procedure
      70-99 Diagnósticos      → Condition
    """
    info = _parse_info(term)
    try:
        num = int(term.code[1:]) if term.code and term.code[1:].isdigit() else 0
    except (ValueError, IndexError):
        num = 0

    coding = {"system": CS_CIAP2, "code": term.code, "display": term.name}

    if 70 <= num <= 99:
        resource: dict = {
            "resourceType": "Condition",
            "id": f"ciap2-{term.code}",
            "meta": {"profile": [f"{RNDS_BASE}/StructureDefinition/BRCondicaoSaude"], "lastUpdated": _now_iso()},
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "code": {"coding": [coding], "text": term.name},
        }
        if info.get("capitulo"):
            resource["category"] = [{"text": info["capitulo"]}]
        return resource

    if 30 <= num <= 49:
        return {
            "resourceType": "Procedure",
            "id": f"ciap2-{term.code}",
            "meta": {"lastUpdated": _now_iso()},
            "status": "unknown",
            "code": {"coding": [coding], "text": term.name},
            "category": {"text": info.get("capitulo", "")},
        }

    # Sintomas (01-29) e demais → Observation
    return {
        "resourceType": "Observation",
        "id": f"ciap2-{term.code}",
        "meta": {"lastUpdated": _now_iso()},
        "status": "preliminary",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "exam"}]}],
        "code": {"coding": [coding], "text": term.name},
        "note": [{"text": f"Componente CIAP-2: {info.get('componente', '')}. Capítulo: {info.get('capitulo', '')}"}],
    }


# ─────────────────────────────────── CNES → Organization

def cnes_to_organization(term: Term) -> dict:
    info = _parse_info(term)
    resource: dict = {
        "resourceType": "Organization",
        "id": f"cnes-{term.code}",
        "meta": {"profile": [f"{RNDS_BASE}/StructureDefinition/BREstabelecimentoSaude"], "lastUpdated": _now_iso()},
        "identifier": [{"system": CS_CNES, "value": term.code}],
        "name": term.name,
        "active": True,
    }
    addr: dict = {}
    if info.get("municipio"): addr["city"]    = info["municipio"]
    if info.get("uf"):        addr["state"]   = info["uf"]
    if info.get("bairro"):    addr["district"]= info["bairro"]
    if addr:
        addr["country"] = "BR"
        resource["address"] = [addr]
    if info.get("latitude") and info.get("longitude"):
        resource["extension"] = [{
            "url": "http://hl7.org/fhir/StructureDefinition/geolocation",
            "extension": [
                {"url": "latitude",  "valueDecimal": float(info["latitude"])},
                {"url": "longitude", "valueDecimal": float(info["longitude"])},
            ],
        }]
    if info.get("telefone"):
        resource["telecom"] = [{"system": "phone", "value": info["telefone"]}]
    return resource


# ─────────────────────────────────── FHIR $lookup (Parameters)

def build_lookup_response(term: Term) -> dict:
    info = _parse_info(term)
    comp = _fmt_competencia(term.source_competency)
    system_map = {"SIGTAP": CS_SIGTAP, "CID10": CS_CID10, "CIAP2": CS_CIAP2, "CNES": CS_CNES}
    system = system_map.get(term.source, "")

    params = [
        {"name": "name",    "valueString": term.source},
        {"name": "display", "valueString": term.name},
    ]
    if comp:   params.append({"name": "version", "valueString": comp})
    if system: params.append({"name": "system",  "valueUri":   system})

    prop_map = {
        "complexidade":       "complexidade",
        "tipo_financiamento": "tipo-financiamento",
        "valor_ambulatorial": "valor-ambulatorial",
        "valor_hospitalar":   "valor-hospitalar",
        "faixa_etaria":       "faixa-etaria",
        "sexo_compativel":    "sexo-compativel",
        "capitulo":           "capitulo-cid",
        "componente":         "componente-ciap2",
        "n_procedimentos":    "n-procedimentos-sus",
        "n_cids_compativeis": "n-cids-compativeis",
    }
    for info_key, fhir_prop in prop_map.items():
        val = info.get(info_key)
        if val is not None:
            params.append({
                "name": "property",
                "part": [
                    {"name": "code",  "valueCode":   fhir_prop},
                    {"name": "value", "valueString": str(val)},
                ],
            })

    return {"resourceType": "Parameters", "parameter": params}


# ─────────────────────────────────── FHIR ValueSet $expand

def build_valueset_expand(terms: list[Term], filter_str: str, source: str, total: int) -> dict:
    system_map = {"SIGTAP": CS_SIGTAP, "CID10": CS_CID10, "CIAP2": CS_CIAP2, "CNES": CS_CNES}
    system = system_map.get(source.upper(), CS_SIGTAP)
    slug   = filter_str.lower().replace(" ", "-")[:40]

    contains = [
        {"system": system, "code": t.code, "display": t.name}
        for t in terms if t.code
    ]

    return {
        "resourceType": "ValueSet",
        "id": f"{source.lower()}-{slug}",
        "url": f"{RNDS_BASE}/ValueSet/{source.lower()}-{slug}",
        "version": "1.0.0",
        "name": f"VS{source.title()}{slug.title().replace('-','')}",
        "title": f"ValueSet {source} — {filter_str}",
        "status": "draft",
        "date": _now_iso(),
        "description": f"Expansão do CodeSystem {source} para o filtro '{filter_str}'.",
        "compose": {"include": [{"system": system, "filter": [{"property": "display", "op": "contains", "value": filter_str}]}]},
        "expansion": {
            "identifier": f"urn:uuid:sus-search-{slug}",
            "timestamp":  _now_iso(),
            "total":      total,
            "offset":     0,
            "contains":   contains,
        },
    }


# ─────────────────────────────────── dispatcher principal

def term_to_fhir(term: Term) -> dict:
    """Converte qualquer termo do banco para o recurso FHIR correspondente."""
    if term.source == "SIGTAP": return sigtap_to_procedure(term)
    if term.source == "CID10":  return cid10_to_condition(term)
    if term.source == "CIAP2":  return ciap2_to_fhir(term)
    if term.source == "CNES":   return cnes_to_organization(term)
    return {"resourceType": "Basic", "code": {"text": term.name}}
