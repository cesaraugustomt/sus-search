# Entry point para deploy na Vercel (Python serverless)
# A Vercel detecta este arquivo e roteia todas as requisições para o FastAPI app
import sys
import os

# Garante que o diretório backend esteja no path para imports funcionarem
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app  # noqa: F401 — exportado para a Vercel
