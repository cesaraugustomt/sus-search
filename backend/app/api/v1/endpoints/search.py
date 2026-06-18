from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search_service import SearchService
from app.schemas.search import SearchResponse

router = APIRouter(prefix="/search", tags=["Busca"])

VALID_SOURCES = {"SIGTAP", "CID10", "CNES", "CIAP2"}


@router.get("", response_model=SearchResponse, summary="Busca unificada no SUS")
def search(
    q: Annotated[str, Query(min_length=2, max_length=200, description="Termo de busca")],
    source: Annotated[Optional[str], Query(description="Filtro por fonte: SIGTAP | CID10 | CIAP2 | CNES")] = None,
    page: Annotated[int, Query(ge=1, description="Página")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Resultados por página")] = 20,
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    Busca full-text nas bases do SUS: SIGTAP, CID-10, CIAP-2, CNES.

    - **q**: termo de busca (mínimo 2 caracteres)
    - **source**: filtra por fonte — SIGTAP | CID10 | CIAP2 | CNES (opcional)
    - **page**: número da página (padrão: 1)
    - **limit**: resultados por página (padrão: 20, máximo: 100)
    """
    if source and source.upper() not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"source deve ser um de: {', '.join(sorted(VALID_SOURCES))}",
        )

    service = SearchService(db)
    return service.search(q, source=source.upper() if source else None, page=page, limit=limit)
