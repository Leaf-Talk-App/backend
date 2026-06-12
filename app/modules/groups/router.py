from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from .schemas import (
    CreateGroupSchema,
    AddMemberSchema,
    RemoveMemberSchema,
    SendGroupMessageSchema,
    UpdateGroupSchema,
    SetAdminSchema,
)

from .service import (
    create_group,
    my_groups,
    get_group,
    get_group_messages,
    add_member,
    remove_member,
    leave_group,
    join_by_code,
    send_group_message,
    update_group,
    set_admin,
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


@router.post("/remove-member")
async def remove(
    data: RemoveMemberSchema,
    user=Depends(get_current_user)
):
    return await remove_member(user, data)


@router.post("/update")
async def update(
    data: UpdateGroupSchema,
    user=Depends(get_current_user)
):
    return await update_group(user, data)


@router.post("/set-admin")
async def set_admin_route(
    data: SetAdminSchema,
    user=Depends(get_current_user)
):
    return await set_admin(user, data)


@router.post("/send-message")
async def send(
    data: SendGroupMessageSchema,
    user=Depends(get_current_user)
):
    return await send_group_message(user, data)


@router.post("/join/{code}")
async def join(
    code: str,
    user=Depends(get_current_user)
):
    return await join_by_code(user, code)


# Rotas com path param dinâmico ficam por último para não capturar /my, /create etc.
@router.get("/{group_id}/messages")
async def messages(
    group_id: str,
    skip: int = 0,
    limit: int = 50,
    user=Depends(get_current_user)
):
    return await get_group_messages(user, group_id, skip, limit)


@router.post("/{group_id}/leave")
async def leave(
    group_id: str,
    user=Depends(get_current_user)
):
    return await leave_group(user, group_id)


@router.get("/{group_id}")
async def detail(
    group_id: str,
    user=Depends(get_current_user)
):
    return await get_group(user, group_id)
