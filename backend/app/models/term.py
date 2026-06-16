from sqlalchemy import (
    BigInteger, Column, DateTime, ForeignKey,
    Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    official_url = Column(String(500))
    competency = Column(String(10))
    record_count = Column(Integer, default=0)
    loaded_at = Column(DateTime(timezone=True))

    terms = relationship("Term", back_populates="source_obj", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Source code={self.code!r}>"


class Term(Base):
    __tablename__ = "terms"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    code = Column(Text, index=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    source = Column(String(20), ForeignKey("sources.code", onupdate="CASCADE"), nullable=False, index=True)
    category = Column(Text)
    subcategory = Column(Text)
    additional_info = Column(JSONB, default={})
    official_url = Column(Text)
    source_competency = Column(String(10))
    last_updated = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    search_vector = Column(TSVECTOR)

    source_obj = relationship("Source", back_populates="terms", foreign_keys=[source])

    def __repr__(self) -> str:
        return f"<Term source={self.source!r} code={self.code!r} name={self.name[:40]!r}>"
