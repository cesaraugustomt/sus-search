from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search_service import SearchService
from app.schemas.search import SearchResponse

router = APIRouter(prefix="/search", tags=["Busca"])


@router.get("", response_model=SearchResponse, summary="Busca unificada no SUS")
def search(
    q: Annotated[str, Query(min_length=2, max_length=200, description="Termo de busca")],
    source: Annotated[Optional[str], Query(description="Filtro por fonte: SIGTAP | CID10 | CNES")] = None,
    page: Annotated[int, Query(ge=1, description="Página")] = 1,
    limit: Annotated[int, Query(ge=1, le=100, description="Resultados por página")] = 20,
    db: Session = Depends(get_db),
) -> SearchResponse:
    """
    Realiza busca full-text nas bases do SUS (SIGTAP, CID-10, CNES).

    - **q**: termo de busca em linguagem natural (mínimo 2 caracteres)
    - **source**: filtra por fonte específica (opcional)
    - **page**: número da página (padrão: 1)
    - **limit**: resultados por página (padrão: 20, máximo: 100)
    """
    if source and source.upper() not in {"SIGTAP", "CID10", "CNES"}:
        raise HTTPException(
            status_code=422,
            detail="source deve ser SIGTAP, CID10 ou CNES",
        )

    service = SearchService(db)
    return service.search(q, source=source, page=page, limit=limit)
