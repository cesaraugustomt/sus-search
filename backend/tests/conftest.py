"""
conftest.py — fixtures compartilhadas para todos os testes backend.
"""
import os
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Banco em memória SQLite para testes unitários (sem PostgreSQL)
SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def sqlite_engine():
    """Engine SQLite em memória para testes que não precisam de FTS."""
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
    yield engine
    engine.dispose()


@pytest.fixture
def sqlite_session(sqlite_engine):
    from sqlalchemy.orm import Session
    with Session(sqlite_engine) as session:
        yield session


# ── Banco PostgreSQL de teste (necessário para testes de integração)
POSTGRES_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://sus:sus_search_2025@localhost:5432/sus_search_test",
)


@pytest.fixture(scope="session")
def pg_engine():
    """Engine PostgreSQL para testes de integração."""
    engine = create_engine(POSTGRES_TEST_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        pytest.skip("PostgreSQL de teste não disponível — skipping integration tests")
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def pg_session_factory(pg_engine):
    from app.db.session import init_db
    import os
    os.environ["DATABASE_URL"] = POSTGRES_TEST_URL
    init_db()
    Factory = sessionmaker(bind=pg_engine)
    return Factory


@pytest.fixture
def pg_session(pg_session_factory):
    session = pg_session_factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


# ── Amostras de dados
SAMPLE_TERMS = [
    {
        "code": "0301010013",
        "name": "CONSULTA MÉDICA EM ATENÇÃO BÁSICA",
        "description": None,
        "source": "SIGTAP",
        "category": "Procedimento SUS",
        "subcategory": None,
        "additional_info": "{}",
        "official_url": "http://sigtap.datasus.gov.br",
        "source_competency": "04/2025",
        "last_updated": None,
    },
    {
        "code": "J18.9",
        "name": "PNEUMONIA NÃO ESPECIFICADA",
        "description": None,
        "source": "CID10",
        "category": "Classificação Internacional de Doenças",
        "subcategory": None,
        "additional_info": "{}",
        "official_url": "https://rts.saude.gov.br",
        "source_competency": "04/2025",
        "last_updated": None,
    },
    {
        "code": "2078596",
        "name": "HOSPITAL UNIVERSITÁRIO POLYDORO ERNANI",
        "description": "Florianópolis — SC",
        "source": "CNES",
        "category": "Estabelecimento de Saúde",
        "subcategory": "HOSPITAL GERAL",
        "additional_info": "{}",
        "official_url": "https://cnes.datasus.gov.br",
        "source_competency": None,
        "last_updated": None,
    },
]
