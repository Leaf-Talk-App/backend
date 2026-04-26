from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import (
    CreateGroupSchema,
    AddMemberSchema,
    SendGroupMessageSchema
)

from .service import (
    create_group,
    my_groups,
    add_member,
    send_group_message
)

router = APIRouter(
    prefix="/groups",
    tags=["Groups"]
)

@router.post("/create")
async def create(
    data: CreateGroupSchema,
    user=Depends(get_current_user)
):
    return await create_group(user, data)

@router.get("/my")
async def mine(
    user=Depends(get_current_user)
):
    return await my_groups(user)

@router.post("/add-member")
async def add(
    data: AddMemberSchema,
    user=Depends(get_current_user)
):
    return await add_member(user, data)

@router.post("/send-message")
async def send(
    data: SendGroupMessageSchema,
    user=Depends(get_current_user)
):
    return await send_group_message(user, data)