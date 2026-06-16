from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.services.search_service import SearchService
from app.schemas.search import HealthResponse
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/health", tags=["Saúde"])


@router.get("", response_model=HealthResponse, summary="Status da aplicação")
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """Verifica conectividade com o banco e retorna estatísticas gerais."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"

    service = SearchService(db)
    total = service.count_all()

    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        database=db_status,
        total_terms=total,
    )
