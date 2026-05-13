from fastapi import HTTPException
from app.core.database import get_database
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token
)
from .models import build_user


async def register_user(data, db):
    user_exists = await db.users.find_one({
        "email": data.email
    })

    if user_exists:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    user = build_user(data.model_dump())

    user["password"] = hash_password(data.password)

    result = await db.users.insert_one(user)

    return {
        "message": "User created",
        "id": str(result.inserted_id)
    }


async def login_user(data, db):
    user = await db.users.find_one({
        "email": data.email
    })

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    valid = verify_password(
        data.password,
        user["password"]
    )

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token({
        "sub": str(user["_id"]),
        "email": user["email"]
    })

    return {
        "access_token": token,
        "token_type": "bearer"
    }