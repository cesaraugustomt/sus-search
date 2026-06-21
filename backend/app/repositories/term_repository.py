import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from app.models.term import Term, Source


class TermRepository:

    def __init__(self, db: Session) -> None:
        self.db = db

    # ─────────────────────────────────────────────────────── busca full-text
    def search(
        self,
        query: str,
        source: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Term], int]:
        offset = (page - 1) * limit
        where_clauses = [
            "search_vector @@ plainto_tsquery('portuguese', unaccent(:q))"
        ]
        params: dict = {"q": query, "limit": limit, "offset": offset}

        if source:
            where_clauses.append("source = :source")
            params["source"] = source.upper()

        where_sql = " AND ".join(where_clauses)

        total: int = (
            self.db.execute(
                text(f"SELECT COUNT(*) FROM terms WHERE {where_sql}"), params
            ).scalar() or 0
        )

        rows = (
            self.db.execute(
                text(f"""
                    SELECT
                        id, code, name, description, source, category, subcategory,
                        additional_info, official_url, source_competency,
                        last_updated, created_at,
                        ts_rank(search_vector,
                            plainto_tsquery('portuguese', unaccent(:q))
                        ) AS rank
                    FROM  terms
                    WHERE {where_sql}
                    ORDER BY rank DESC, name ASC
                    LIMIT :limit OFFSET :offset
                """),
                params,
            )
            .mappings()
            .all()
        )

        term_objs: list[Term] = []
        for row in rows:
            t = Term()
            for col in (
                "id", "code", "name", "description", "source",
                "category", "subcategory", "additional_info",
                "official_url", "source_competency", "last_updated", "created_at",
            ):
                setattr(t, col, row[col])
            term_objs.append(t)

        return term_objs, total

    # ─────────────────────────────────────────────────── busca por id/código
    def get_by_code(self, code: str, source: Optional[str] = None) -> Optional[Term]:
        stmt = select(Term).where(Term.code == code)
        if source:
            stmt = stmt.where(Term.source == source.upper())
        return self.db.execute(stmt).scalars().first()

    def get_by_id(self, term_id: int) -> Optional[Term]:
        return self.db.get(Term, term_id)

    # ────────────────────────────────────────────────────────── escrita em lote
    #
    # IMPORTANTE — transação atômica:
    # Nenhum destes métodos faz commit() por conta própria. O commit é
    # responsabilidade exclusiva de quem orquestra a operação (ver
    # etl/base.py BaseETL.load()), garantindo que delete + insert
    # aconteçam na MESMA transação. Se o insert falhar ou retornar 0
    # registros, um rollback() desfaz o delete também — nunca ficamos
    # com a fonte apagada e vazia.
    #
    def bulk_insert(self, records: list[dict]) -> int:
        """
        Insere em lote. NÃO comita — ver nota acima.
        CAST(:additional_info AS jsonb) evita conflito entre o operador
        de cast PostgreSQL '::' e a detecção de parâmetros do SQLAlchemy.
        ON CONFLICT (code, source) WHERE code IS NOT NULL DO NOTHING
        garante idempotência sem duplicatas.
        """
        if not records:
            return 0

        stmt = text("""
            INSERT INTO terms
                (code, name, description, source, category, subcategory,
                 additional_info, official_url, source_competency, last_updated)
            VALUES
                (:code, :name, :description, :source, :category, :subcategory,
                 CAST(:additional_info AS jsonb),
                 :official_url, :source_competency, :last_updated)
            ON CONFLICT (code, source)
            WHERE code IS NOT NULL
            DO NOTHING
        """)
        self.db.execute(stmt, records)
        return len(records)

    def delete_by_source(self, source: str) -> int:
        """Remove registros de uma fonte. NÃO comita — ver nota acima."""
        result = self.db.execute(
            text("DELETE FROM terms WHERE source = :source"),
            {"source": source.upper()},
        )
        return result.rowcount

    # ──────────────────────────────────────────────────── estatísticas fontes
    def list_sources(self) -> list[Source]:
        return self.db.execute(select(Source).order_by(Source.code)).scalars().all()

    def update_source_stats(
        self, source_code: str, count: int, competency: Optional[str] = None
    ) -> None:
        """Atualiza estatísticas da fonte. NÃO comita — ver nota acima."""
        params: dict = {"code": source_code, "count": count}
        extra = ""
        if competency:
            extra = ", competency = :competency"
            params["competency"] = competency
        self.db.execute(
            text(f"""
                UPDATE sources
                   SET record_count = :count, loaded_at = NOW() {extra}
                 WHERE code = :code
            """),
            params,
        )

    def count_all(self) -> int:
        return self.db.execute(text("SELECT COUNT(*) FROM terms")).scalar() or 0
