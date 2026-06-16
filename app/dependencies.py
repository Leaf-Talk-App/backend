from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from bson import ObjectId

from app.core.config import settings
from app.core.database import get_database

security = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token missing"
        )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    if "sub" not in payload or "email" not in payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )

    # Invalidação de sessão no logout: o token carrega "tv" (token_version) e
    # precisa bater com a versão atual do usuário. Ao deslogar, a versão é
    # incrementada → todos os tokens antigos param de valer. Tokens/usuários
    # legados (sem tv/token_version) usam 0 → continuam válidos até o 1º logout.
    db = get_database()
    try:
        user = await db.users.find_one(
            {"_id": ObjectId(payload["sub"])}, {"token_version": 1}
        )
    except Exception:
        user = None

    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("tv", 0) != user.get("token_version", 0):
        raise HTTPException(status_code=401, detail="Session expired")

    return payload