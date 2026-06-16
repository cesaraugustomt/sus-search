from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Banco — obrigatório em produção via variável de ambiente DATABASE_URL
    DATABASE_URL: str = "postgresql://sus:changeme@localhost:5432/sus_search"

    # API
    PROJECT_NAME: str  = "SUS Search"
    VERSION: str       = "1.0.0"
    DESCRIPTION: str   = "Mecanismo de busca unificado para informações oficiais do SUS"
    API_PREFIX: str    = "/api/v1"
    DEBUG: bool        = False
    LOG_LEVEL: str     = "INFO"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost"

    # ETL
    DATA_DIR: str         = "/tmp/sus_data"
    REQUESTS_TIMEOUT: int = 120

    # LLM opcional — compatível com Groq, Ollama, OpenAI (ver .env.example)
    LLM_BASE_URL: Optional[str] = None
    LLM_API_KEY:  Optional[str] = None
    LLM_MODEL:    str           = "llama-3.3-70b-versatile"

    # Paginação
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int     = 100

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
