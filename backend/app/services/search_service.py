import math
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.repositories.term_repository import TermRepository
from app.schemas.search import SearchResponse, TermResponse, SourceResponse
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class SearchService:
    """
    Camada de negócio para busca de termos.
    Orquestra TermRepository e formata as respostas para a API.
    """

    def __init__(self, db: Session) -> None:
        self.repo = TermRepository(db)

    def search(
        self,
        query: str,
        source: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> SearchResponse:
        query = query.strip()
        if not query:
            return SearchResponse(
                query=query, total=0, page=page,
                limit=limit, pages=0, results=[]
            )

        limit = min(limit, settings.MAX_PAGE_SIZE)
        page = max(page, 1)

        logger.info(f"Busca: q={query!r} source={source!r} page={page} limit={limit}")

        terms, total = self.repo.search(query, source=source, page=page, limit=limit)
        pages = math.ceil(total / limit) if total > 0 else 0

        results = [TermResponse.model_validate(t) for t in terms]

        return SearchResponse(
            query=query,
            total=total,
            page=page,
            limit=limit,
            pages=pages,
            results=results,
        )

    def list_sources(self) -> list[SourceResponse]:
        sources = self.repo.list_sources()
        return [SourceResponse.model_validate(s) for s in sources]

    def count_all(self) -> int:
        return self.repo.count_all()
