import secrets
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import HTTPException
from jose import JWTError, jwt
import httpx
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token
from .models import build_user


def _generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_reset_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "purpose": "password_reset",
        "exp": datetime.utcnow() + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_reset_token(token: str) -> str:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired token") from exc

    if payload.get("purpose") != "password_reset" or not payload.get("sub"):
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return payload["sub"]


async def register_user(data, db):
    user_exists = await db.users.find_one({"email": data.email})
    if user_exists:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = build_user(data.model_dump())
    user["password"] = hash_password(data.password)
    user["verification_code"] = _generate_code()
    user["verification_code_expires_at"] = datetime.utcnow() + timedelta(minutes=15)

    result = await db.users.insert_one(user)

    return {
        "message": "User created",
        "id": str(result.inserted_id),
        "verification_code": user["verification_code"],
    }


async def login_user(data, db):
    user = await db.users.find_one({"email": data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user["_id"]), "email": user["email"]})
    return {"access_token": token, "token_type": "bearer"}


async def verify_email_code(data, db):
    query = {"verification_code": data.code}
    if data.email:
        query["email"] = data.email

    user = await db.users.find_one(query)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code")

    expires_at = user.get("verification_code_expires_at")
    if not expires_at or expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Code expired")

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {"verified": True},
            "$unset": {"verification_code": "", "verification_code_expires_at": ""},
        },
    )
    return {"message": "Email verified"}


async def resend_verification_code(email: str, db):
    user = await db.users.find_one({"email": email})
    if not user:
        return {"message": "If the email exists, a new code was sent"}

    if user.get("verified"):
        return {"message": "Email already verified"}

    code = _generate_code()
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "verification_code": code,
                "verification_code_expires_at": datetime.utcnow() + timedelta(minutes=15),
            }
        },
    )
    return {"message": "Verification code sent", "name": user.get("name", ""), "code": code}


async def request_password_reset(email: str, db):
    user = await db.users.find_one({"email": email})
    if not user:
        return {"message": "If the email exists, reset instructions were sent"}

    token = generate_reset_token(str(user["_id"]))
    return {
        "message": "If the email exists, reset instructions were sent",
        "name": user.get("name", ""),
        "token": token,
    }


async def reset_password(token: str, password: str, db):
    user_id = decode_reset_token(token)
    hashed_password = hash_password(password)

    result = await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_password}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    return {"message": "Password updated"}


async def exchange_google_code(code: str, redirect_uri: str):
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    async with httpx.AsyncClient(timeout=10) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if token_response.status_code != 200:
        try:
            google_error = token_response.json()
            message = google_error.get("error_description") or google_error.get("error")
        except Exception:
            message = token_response.text
        raise HTTPException(
            status_code=400,
            detail=message or "Failed to exchange Google authorization code",
        )

    payload = token_response.json()
    id_token_str = payload.get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=400, detail="Google id_token was not returned")

    try:
        google_user = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Google token") from exc

    email = google_user.get("email")
    name = google_user.get("name") or "Usuário Google"
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    return {"email": email, "name": name}


async def login_or_create_google_user(google_profile: dict, db):
    email = google_profile["email"]
    user = await db.users.find_one({"email": email})

    if not user:
        user = build_user(
            {
                "name": google_profile["name"],
                "email": email,
                "password": secrets.token_urlsafe(24),
            }
        )
        user["password"] = hash_password(secrets.token_urlsafe(24))
        user["verified"] = True
        user["auth_provider"] = "google"
        result = await db.users.insert_one(user)
        user["_id"] = result.inserted_id
    else:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"verified": True, "auth_provider": "google"}},
        )

    token = create_access_token({"sub": str(user["_id"]), "email": email})
    return {"access_token": token, "token_type": "bearer"}


def verify_google_id_token(id_token_str: str):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth is not configured")

    try:
        google_user = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid Google token") from exc

    email = google_user.get("email")
    name = google_user.get("name") or "Usuário Google"
    if not email:
        raise HTTPException(status_code=400, detail="Google account has no email")

    return {"email": email, "name": name}
