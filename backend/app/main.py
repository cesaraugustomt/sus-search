import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.session import init_db
from app.api.v1.router import router as v1_router

settings = get_settings()
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Inicializa banco de dados na subida da aplicação."""
    logger.info("Inicializando banco de dados...")
    try:
        init_db()
        logger.info("Banco de dados pronto.")
    except Exception as e:
        logger.error(f"Falha na inicialização do banco: {e}")
    yield
    logger.info("Encerrando aplicação.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ---------------------------------------------------------------- Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ------------------------------------------------------------------ Routers
app.include_router(v1_router, prefix=settings.API_PREFIX)


# ------------------------------------------- Handler global de exceções
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Erro não tratado: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erro interno do servidor. Consulte os logs para mais detalhes."},
    )


# ------------------------------------------ Endpoint raiz (redirect para docs)
@app.get("/", include_in_schema=False)
def root():
    return {"message": "SUS Search API", "docs": "/docs", "version": settings.VERSION}
