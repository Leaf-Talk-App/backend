from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.core.database import get_database
from .questions import QUESTIONS, QUIZ_SIZE

_MAX_DURATION_MS = 1000 * 60 * 60 * 2  # 2h — descarta tempos absurdos
_RANK_SORT = [("score", -1), ("duration_ms", 1), ("created_at", 1)]


def _serialize(a: dict, position: int | None = None) -> dict:
    created = a.get("created_at")
    return {
        "name": a.get("name", ""),
        "score": a.get("score", 0),
        "total": a.get("total", QUIZ_SIZE),
        "duration_ms": a.get("duration_ms", 0),
        "created_at": created.isoformat() if created else None,
        **({"position": position} if position is not None else {}),
    }


async def submit_attempt(data) -> dict:
    db = get_database()

    name = (data.name or "").strip()[:40]
    if not name:
        raise HTTPException(status_code=400, detail="Informe seu nome para participar.")

    now = datetime.now(timezone.utc)

    # Anti-spam: bloqueia reenvio do MESMO nome em menos de 5s (além do rate
    # limit por IP no router). Evita duplicar a entrada por duplo-clique.
    recent = await db.quiz_attempts.find_one(
        {"name": name, "created_at": {"$gt": now - timedelta(seconds=5)}}
    )
    if recent:
        raise HTTPException(status_code=429, detail="Aguarde alguns segundos antes de enviar de novo.")

    # Correção por id (cada device recebeu um sorteio diferente). Dedup por id
    # para ninguém inflar a pontuação repetindo a mesma pergunta.
    total = QUIZ_SIZE
    seen = set()
    score = 0
    for r in (data.responses or []):
        if r.id in seen:
            continue
        seen.add(r.id)
        if 0 <= r.id < len(QUESTIONS) and r.answer == QUESTIONS[r.id]["answer"]:
            score += 1
    score = min(score, total)
    duration = min(max(0, int(data.duration_ms or 0)), _MAX_DURATION_MS)

    doc = {
        "name": name,
        "score": score,
        "total": total,
        "duration_ms": duration,
        "created_at": now,
    }
    await db.quiz_attempts.insert_one(doc)

    # Posição = quantas tentativas são estritamente melhores + 1.
    # Critérios: mais acertos → menor tempo → quem terminou antes.
    better = await db.quiz_attempts.count_documents(
        {
            "$or": [
                {"score": {"$gt": score}},
                {"score": score, "duration_ms": {"$lt": duration}},
                {"score": score, "duration_ms": duration, "created_at": {"$lt": now}},
            ]
        }
    )
    return _serialize(doc, position=better + 1)


async def get_ranking(limit: int = 50) -> dict:
    db = get_database()
    attempts = await db.quiz_attempts.find().sort(_RANK_SORT).to_list(limit)
    total = await db.quiz_attempts.count_documents({})
    return {
        "ranking": [_serialize(a, position=i + 1) for i, a in enumerate(attempts)],
        "participants": total,
    }


async def get_stats() -> dict:
    db = get_database()
    return {"participants": await db.quiz_attempts.count_documents({})}


async def reset_ranking(key: str) -> dict:
    """Zera o ranking (apaga todas as tentativas). Exige a chave secreta
    (QUIZ_ADMIN_KEY). Se a chave não estiver configurada, o reset é negado."""
    from app.core.config import settings

    if not settings.QUIZ_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Reset desabilitado (defina QUIZ_ADMIN_KEY).")
    if key != settings.QUIZ_ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Chave inválida.")

    db = get_database()
    result = await db.quiz_attempts.delete_many({})
    return {"message": "Ranking zerado", "removidos": result.deleted_count}
