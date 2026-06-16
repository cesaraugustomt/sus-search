from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.search_service import SearchService
from app.schemas.search import SourceResponse

router = APIRouter(prefix="/sources", tags=["Fontes"])


@router.get("", response_model=list[SourceResponse], summary="Lista fontes de dados disponíveis")
def list_sources(db: Session = Depends(get_db)) -> list[SourceResponse]:
    """
    Retorna todas as fontes de dados integradas ao SUS Search,
    com informações de competência, contagem de registros e data da última carga.
    """
    service = SearchService(db)
    return service.list_sources()
