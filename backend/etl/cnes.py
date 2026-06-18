"""
DEPRECATED — Este módulo foi substituído por demas_cnes.py.
Mantido apenas para compatibilidade de imports legados.
"""
from etl.demas_cnes import DEMASCNESEtl as CNESEtl  # noqa: F401

__all__ = ["CNESEtl"]
