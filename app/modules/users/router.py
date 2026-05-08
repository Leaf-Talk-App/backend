from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import UpdateProfileSchema
from .service import (
    get_me,
    update_profile,
    search_users
)
from .schemas import BlockUserSchema
from .service import (
    block_user,
    unblock_user,
    list_blocked_users
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
   return await search_users(user, q)

@router.post("/block")
async def block(
    data: BlockUserSchema,
    user=Depends(get_current_user)
):
    return await block_user(user, data)


@router.delete("/block/{user_id}")
async def unblock(
    user_id: str,
    user=Depends(get_current_user)
):
    return await unblock_user(user, user_id)


@router.get("/blocked")
async def blocked(
    user=Depends(get_current_user)
):
    return await list_blocked_users(user)