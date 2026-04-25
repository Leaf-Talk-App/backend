from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import UpdateProfileSchema
from .service import (
    get_me,
    update_profile,
    search_users
)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.get("/me")
async def me(user=Depends(get_current_user)):
    return await get_me(user)

@router.patch("/profile")
async def profile(
    data: UpdateProfileSchema,
    user=Depends(get_current_user)
):
    return await update_profile(user, data)

@router.get("/search")
async def search(
    q: str,
    user=Depends(get_current_user)
):
    return await search_users(q)