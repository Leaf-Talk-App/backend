"""Leaf Quiz — experiência ao vivo da apresentação. Endpoints PÚBLICOS (alunos
respondem sem conta). Correção e ranking no servidor; anti-fraude básico."""
from fastapi import APIRouter, Request, Query
from app.core.ratelimit import limiter
from .schemas import QuizSubmitSchema
from .questions import sample_questions, QUIZ_SIZE
from .service import submit_attempt, get_ranking, get_stats, reset_ranking

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.get("/questions")
async def questions():
    # 10 perguntas ALEATÓRIAS (de um banco de 50), em ordem aleatória — cada
    # dispositivo recebe um conjunto/ordem diferente.
    return {"questions": sample_questions(), "total": QUIZ_SIZE}


@router.post("/submit")
@limiter.limit("10/minute")
async def submit(request: Request, data: QuizSubmitSchema):
    return await submit_attempt(data)


@router.get("/ranking")
async def ranking(limit: int = 50):
    return await get_ranking(min(max(limit, 1), 100))


@router.get("/stats")
async def stats():
    return await get_stats()


@router.post("/reset")
@limiter.limit("10/minute")
async def reset(request: Request, key: str = Query(default="")):
    # Zera o ranking. Protegido por chave (QUIZ_ADMIN_KEY). Use entre sessões.
    return await reset_ranking(key)
