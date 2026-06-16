from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class TermResponse(BaseModel):
    """Schema de um resultado de busca individual."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: Optional[str] = None
    name: str
    description: Optional[str] = None
    source: str
    category: Optional[str] = None
    subcategory: Optional[str] = None
    additional_info: Optional[dict[str, Any]] = Field(default_factory=dict)
    official_url: Optional[str] = None
    source_competency: Optional[str] = None
    last_updated: Optional[datetime] = None
    created_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Schema da resposta paginada de busca."""
    query: str
    total: int
    page: int
    limit: int
    pages: int
    results: list[TermResponse]


class SourceResponse(BaseModel):
    """Schema de uma fonte de dados."""
    model_config = ConfigDict(from_attributes=True)

    code: str
    name: str
    description: Optional[str] = None
    official_url: Optional[str] = None
    competency: Optional[str] = None
    record_count: int = 0
    loaded_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    """Schema da resposta de health check."""
    status: str
    version: str
    database: str
    total_terms: int
