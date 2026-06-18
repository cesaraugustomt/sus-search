"""
Endpoints FHIR R4 — SUS Search Terminology Server

Implementa um subconjunto da especificação HL7 FHIR R4 Terminology Services:
  GET /fhir/CodeSystem/{source}/$lookup?code=XXXX
  GET /fhir/ValueSet/$expand?filter=xxx&source=SIGTAP
  GET /fhir/resource/{source}/{code}
  GET /fhir/metadata

Referência: https://www.hl7.org/fhir/terminology-service.html
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.term_repository import TermRepository
from app.services import fhir_service as fhir

router = APIRouter(prefix="/fhir", tags=["fhir"])
FHIR_MEDIA_TYPE = "application/fhir+json; charset=utf-8"

_SOURCE_ALIASES = {
    "sigtap":  "SIGTAP",
    "icd-10":  "CID10",
    "icd10":   "CID10",
    "cid-10":  "CID10",
    "cid10":   "CID10",
    "ciap-2":  "CIAP2",
    "ciap2":   "CIAP2",
    "icpc-2":  "CIAP2",
    "icpc2":   "CIAP2",
    "cnes":    "CNES",
}


def _resolve_source(raw: str) -> str:
    resolved = _SOURCE_ALIASES.get(raw.lower().strip())
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"CodeSystem '{raw}' não reconhecido. Use: sigtap, icd-10, ciap-2, cnes",
        )
    return resolved


@router.get("/CodeSystem/{source}/$lookup", summary="Lookup FHIR — busca um código em um CodeSystem")
def codesystem_lookup(
    source: str,
    code:   str = Query(..., description="Código a buscar"),
    db:     Session = Depends(get_db),
):
    src  = _resolve_source(source)
    repo = TermRepository(db)
    c    = code.strip().upper() if src in ("CID10", "CIAP2") else code.strip()
    term = repo.get_by_code(c, source=src)
    if not term:
        return JSONResponse(
            status_code=404,
            content={"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found",
                "diagnostics": f"Código '{code}' não encontrado no CodeSystem '{source}'."}]},
            media_type=FHIR_MEDIA_TYPE,
        )
    return JSONResponse(content=fhir.build_lookup_response(term), media_type=FHIR_MEDIA_TYPE)


@router.get("/resource/{source}/{code}", summary="Recurso FHIR completo")
def get_fhir_resource(source: str, code: str, db: Session = Depends(get_db)):
    src  = _resolve_source(source)
    repo = TermRepository(db)
    c    = code.strip().upper() if src in ("CID10", "CIAP2") else code.strip()
    term = repo.get_by_code(c, source=src)
    if not term:
        return JSONResponse(
            status_code=404,
            content={"resourceType": "OperationOutcome", "issue": [{"severity": "error", "code": "not-found",
                "diagnostics": f"Código '{code}' não encontrado para '{source}'."}]},
            media_type=FHIR_MEDIA_TYPE,
        )
    return JSONResponse(content=fhir.term_to_fhir(term), media_type=FHIR_MEDIA_TYPE)


@router.get("/ValueSet/$expand", summary="Expansão de ValueSet FHIR")
def valueset_expand(
    filter: str = Query(...),
    source: str = Query("SIGTAP", description="SIGTAP | CID10 | CIAP2 | CNES"),
    count:  int = Query(20, ge=1, le=100),
    db:     Session = Depends(get_db),
):
    src          = _resolve_source(source)
    repo         = TermRepository(db)
    terms, total = repo.search(query=filter, source=src, page=1, limit=count)
    return JSONResponse(content=fhir.build_valueset_expand(terms, filter, src, total), media_type=FHIR_MEDIA_TYPE)


@router.get("/metadata", summary="CapabilityStatement do servidor FHIR")
def fhir_metadata():
    return JSONResponse(content={
        "resourceType": "CapabilityStatement",
        "id": "sus-search-fhir",
        "status": "active",
        "date": "2026-06-17",
        "kind": "instance",
        "software": {"name": "SUS Search", "version": "1.0.0"},
        "implementation": {
            "description": "Servidor de terminologia SUS — SIGTAP, CID-10, CIAP-2, CNES",
            "url": "https://sus-search-g9lu.vercel.app/api/v1/fhir",
        },
        "fhirVersion": "4.0.1",
        "format": ["application/fhir+json"],
        "rest": [{"mode": "server", "resource": [
            {"type": "Procedure",    "interaction": [{"code": "read"}], "operation": [{"name": "$lookup"}]},
            {"type": "Condition",    "interaction": [{"code": "read"}], "operation": [{"name": "$lookup"}]},
            {"type": "Observation",  "interaction": [{"code": "read"}]},
            {"type": "Organization", "interaction": [{"code": "read"}]},
            {"type": "ValueSet",     "interaction": [{"code": "search-type"}], "operation": [{"name": "$expand"}]},
        ]}],
    }, media_type=FHIR_MEDIA_TYPE)
