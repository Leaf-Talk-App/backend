from fastapi import APIRouter, Depends
from bson import ObjectId
from app.dependencies import get_current_user
from app.core.database import get_database
from .schemas import UpdateUserSchema, BlockUserSchema
from .service import (
    get_me,
    update_profile,
    search_users,
    get_user_by_id,
    block_user,
    unblock_user,
    list_blocked_users,
)
from .serializers import serialize_user

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me")
async def me(user=Depends(get_current_user)):
    return await get_me(user)


@router.patch("/profile")
async def profile(data: UpdateUserSchema, user=Depends(get_current_user)):
    return await update_profile(user, data)


@router.get("/search")
async def search(
    q: str = None,
    query: str = None,
    user=Depends(get_current_user),
):
    term = q or query or ""
    return await search_users(user, term)


@router.post("/block")
async def block(data: BlockUserSchema, user=Depends(get_current_user)):
    return await block_user(user, data)


@router.delete("/block/{user_id}")
async def unblock(user_id: str, user=Depends(get_current_user)):
    return await unblock_user(user, user_id)


@router.get("/blocked")
async def blocked(user=Depends(get_current_user)):
    return await list_blocked_users(user)


@router.patch("/me")
async def update_me(data: UpdateUserSchema, current_user=Depends(get_current_user)):
    db = get_database()
    user_id = current_user["sub"]  # JWT payload usa "sub", não "id"

    update_data = data.dict(exclude_unset=True)
    if not update_data:
        return {"message": "Nada para atualizar"}

    await db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": update_data},
    )

    updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
    return serialize_user(updated_user)


@router.put("/me")
async def put_me(data: UpdateUserSchema, current_user=Depends(get_current_user)):
    return await update_profile(current_user, data)


@router.get("/{user_id}")
async def get_user(user_id: str, user=Depends(get_current_user)):
    return await get_user_by_id(user_id)
