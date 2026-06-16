from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.ask_service import ask   # ← NLU baseada em regras, sem LLM externo

router = APIRouter()


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    tools_used: list[str]
    question: str


@router.post(
    "/ask",
    response_model=AskResponse,
    summary="Pergunta em linguagem natural",
    description=(
        "Recebe uma pergunta em português sobre o SUS e retorna uma resposta "
        "estruturada consultando os dados locais e a API DEMAS quando necessário. "
        "Não requer LLM externo — funciona por detecção de intenção baseada em regras."
    ),
)
def ask_question(body: AskRequest, db: Session = Depends(get_db)):
    if not body.question.strip():
        raise HTTPException(status_code=422, detail="Pergunta não pode estar vazia.")
    result = ask(question=body.question.strip(), db=db)
    return AskResponse(
        answer=result["answer"],
        tools_used=result["tools_used"],
        question=body.question,
    )
