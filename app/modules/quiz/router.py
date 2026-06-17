"""Leaf Quiz — experiência ao vivo da apresentação. Endpoints PÚBLICOS (alunos
respondem sem conta). Correção e ranking no servidor; anti-fraude básico."""
from fastapi import APIRouter, Request
from app.core.ratelimit import limiter
from .schemas import QuizSubmitSchema
from .questions import public_questions, QUESTIONS
from .service import submit_attempt, get_ranking, get_stats

router = APIRouter(prefix="/quiz", tags=["Quiz"])


@router.get("/questions")
async def questions():
    return {"questions": public_questions(), "total": len(QUESTIONS)}


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
