from fastapi import APIRouter, status
from .schemas import RegisterSchema, LoginSchema
from .service import register_user, login_user

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED
)
async def register(data: RegisterSchema):
    return await register_user(data)

@router.post("/login")
async def login(data: LoginSchema):
    return await login_user(data)