from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency para injeção de sessão nos endpoints do FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Cria extensões, tabelas, índices e constraints no PostgreSQL.
    Idempotente — seguro rodar múltiplas vezes.
    """
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent;"))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS sources (
                id           SERIAL PRIMARY KEY,
                code         VARCHAR(20) UNIQUE NOT NULL,
                name         VARCHAR(200) NOT NULL,
                description  TEXT,
                official_url VARCHAR(500),
                competency   VARCHAR(10),
                record_count INTEGER DEFAULT 0,
                loaded_at    TIMESTAMPTZ
            );
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS terms (
                id                BIGSERIAL PRIMARY KEY,
                code              TEXT,
                name              TEXT NOT NULL,
                description       TEXT,
                source            VARCHAR(20) NOT NULL
                                      REFERENCES sources(code) ON UPDATE CASCADE,
                category          TEXT,
                subcategory       TEXT,
                additional_info   JSONB DEFAULT '{}',
                official_url      TEXT,
                source_competency VARCHAR(10),
                last_updated      TIMESTAMPTZ,
                created_at        TIMESTAMPTZ DEFAULT NOW(),
                search_vector     TSVECTOR
            );
        """))

        # Constraint de unicidade para ON CONFLICT funcionar no bulk_insert
        conn.execute(text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_terms_code_source'
                ) THEN
                    ALTER TABLE terms
                    ADD CONSTRAINT uq_terms_code_source UNIQUE (code, source);
                END IF;
            END
            $$;
        """))

        # Trigger para manter o search_vector atualizado
        conn.execute(text("""
            CREATE OR REPLACE FUNCTION update_terms_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector :=
                    setweight(
                        to_tsvector('portuguese',
                            unaccent(coalesce(NEW.name, ''))
                        ), 'A'
                    ) ||
                    setweight(
                        to_tsvector('portuguese',
                            unaccent(coalesce(NEW.description, ''))
                        ), 'B'
                    ) ||
                    setweight(
                        to_tsvector('simple',
                            unaccent(coalesce(NEW.code, ''))
                        ), 'A'
                    ) ||
                    setweight(
                        to_tsvector('portuguese',
                            unaccent(coalesce(NEW.category, ''))
                        ), 'C'
                    );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """))

        conn.execute(text("""
            DROP TRIGGER IF EXISTS terms_search_vector_trigger ON terms;
            CREATE TRIGGER terms_search_vector_trigger
                BEFORE INSERT OR UPDATE OF name, description, code, category
                ON terms
                FOR EACH ROW
                EXECUTE FUNCTION update_terms_search_vector();
        """))

        # Índices
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_terms_search "
            "ON terms USING GIN(search_vector);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_terms_source ON terms(source);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_terms_code ON terms(code);"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_terms_name_trgm "
            "ON terms USING GIN(name gin_trgm_ops);"
        ))

        # Fontes conhecidas
        conn.execute(text("""
            INSERT INTO sources (code, name, description, official_url)
            VALUES
              ('SIGTAP', 'SIGTAP',
               'Tabela de Procedimentos, Medicamentos e OPM do SUS',
               'http://sigtap.datasus.gov.br'),
              ('CID10', 'CID-10 / RTS',
               'Classificação Internacional de Doenças - 10ª Revisão',
               'https://rts.saude.gov.br'),
              ('CNES', 'CNES',
               'Cadastro Nacional de Estabelecimentos de Saúde',
               'https://cnes.datasus.gov.br')
            ON CONFLICT (code) DO NOTHING;
        """))

        conn.commit()
