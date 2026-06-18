from fastapi import APIRouter
from app.api.v1.endpoints import search, sources, health, ask, fhir

router = APIRouter()
router.include_router(search.router,  tags=["busca"])
router.include_router(sources.router, tags=["fontes"])
router.include_router(health.router,  tags=["infra"])
router.include_router(ask.router,     tags=["perguntar"])
router.include_router(fhir.router,    tags=["fhir"])
