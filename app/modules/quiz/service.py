from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.core.database import get_database
from .questions import QUESTIONS

_MAX_DURATION_MS = 1000 * 60 * 60 * 2  # 2h — descarta tempos absurdos
_RANK_SORT = [("score", -1), ("duration_ms", 1), ("created_at", 1)]


def _serialize(a: dict, position: int | None = None) -> dict:
    created = a.get("created_at")
    return {
        "name": a.get("name", ""),
        "score": a.get("score", 0),
        "total": a.get("total", len(QUESTIONS)),
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

    answers = data.answers or []
    total = len(QUESTIONS)
    score = sum(
        1 for i, q in enumerate(QUESTIONS) if i < len(answers) and answers[i] == q["answer"]
    )
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
